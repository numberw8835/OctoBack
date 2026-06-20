import os
import json
from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine
from modules.util.crypto import calculate_sha1
from modules.tui import run_tui

engine = Engine()


def restore_from_backup(path, all_files=False):
    if not engine.config.load_config(DEFAULT_CONFIG):
        print("error: config file not found, please run 'octoback init' first.")
        return

    vault_path = engine.config.configuration["storage"]["vault_path"]
    index_path = engine.config.configuration["storage"]["index_path"]
    checksums_path = os.path.join(vault_path, "checksums.json")

    if os.path.exists(index_path):
        engine.load_index(index_path)

    if not engine.index:
        print("index is empty, nothing to restore")
        return

    # Check if any block_id in engine.index is None; repartition it on the fly
    if any(block_id is None for _, block_id in engine.index):
        engine.repartition_index()

    # Load checksums if they exist
    checksums = {}
    if os.path.exists(checksums_path):
        try:
            with open(checksums_path, "r") as f:
                checksums = json.load(f)
        except Exception as e:
            print(f"error: loading checksums: {e}")

    def verify_block_integrity(block_file, block_id):
        if not checksums or block_id not in checksums:
            return True  # If no checksum stored, bypass validation
        current_sha = calculate_sha1(block_file)
        expected_sha = checksums[block_id]
        if current_sha != expected_sha:
            print(f"integrity error: corruption detected in archive '{block_file}'! checksum mismatch")
            return False
        return True

    # Check for TUI mode
    if path == "list":
        cwd = os.getcwd()
        matching_paths = []
        for indexed_path, block_id in engine.index:
            if indexed_path == cwd or indexed_path.startswith(cwd + os.sep):
                matching_paths.append(indexed_path)

        if not matching_paths:
            print("no indexed files found in the current directory")
            return

        matching_paths.sort()
        rel_paths = [os.path.relpath(p, cwd) for p in matching_paths]

        selected_rel_paths = run_tui(rel_paths)
        if not selected_rel_paths:
            print("restoration cancelled or no files selected")
            return

        for rel_p in selected_rel_paths:
            abs_p = os.path.abspath(os.path.join(cwd, rel_p))

            # Find the block_id for abs_p using longest-prefix match
            block_id = None
            best_len = -1
            for indexed_path, bid in engine.index:
                if abs_p == indexed_path:
                    block_id = bid
                    break
                if abs_p.startswith(indexed_path + os.sep):
                    if len(indexed_path) > best_len:
                        best_len = len(indexed_path)
                        block_id = bid

            if not block_id:
                print(f"error: cannot find block ID for path: {abs_p}")
                continue

            block_file = os.path.join(vault_path, f"{block_id}.tar.gz")
            if not os.path.exists(block_file):
                print(f"error: block archive not found: {block_file}")
                continue

            # Verify integrity
            if not verify_block_integrity(block_file, block_id):
                return

            archive_target = abs_p.lstrip(os.sep)
            dest = os.path.dirname(abs_p)
            print(f"restoring {abs_p} from {block_id}...")
            engine.controller.uncompress(block_file, archive_target, dest)
        print("restoration successfully completed")
        return

    if all_files:
        # Group paths by block_id to minimize uncompress calls
        blocks_to_restore = {}
        for item, block_id in engine.index:
            if block_id not in blocks_to_restore:
                blocks_to_restore[block_id] = []
            blocks_to_restore[block_id].append(item)

        for block_id, items in blocks_to_restore.items():
            block_file = os.path.join(vault_path, f"{block_id}.tar.gz")
            if not os.path.exists(block_file):
                print(f"error: block archive not found: {block_file}")
                continue

            # Verify integrity
            if not verify_block_integrity(block_file, block_id):
                return

            for item in items:
                archive_target = item.lstrip(os.sep)
                dest = os.path.dirname(item)
                print(f"restoring {item} from {block_id}...")
                engine.controller.uncompress(block_file, archive_target, dest)
        print("restoration successfully completed")
        return
    else:
        if not path:
            path = os.getcwd()

        abs_target = os.path.abspath(path)

        # Check index for any matches
        matching_blocks = set()
        for indexed_path, block_id in engine.index:
            if (
                abs_target == indexed_path
                or abs_target.startswith(indexed_path + os.sep)
                or indexed_path.startswith(abs_target + os.sep)
            ):
                matching_blocks.add(block_id)

        if not matching_blocks:
            print(f"warning: path '{abs_target}' is not in the index, restoration may fail")
            block_id = "block_" + abs_target.strip("/").replace("/", "_")
            matching_blocks.add(block_id)

        archive_target = abs_target.lstrip(os.sep)
        dest = os.path.dirname(abs_target)

        success_any = False
        for block_id in matching_blocks:
            block_file = os.path.join(vault_path, f"{block_id}.tar.gz")
            if not os.path.exists(block_file):
                # Fallback to monolithic block if it exists
                monolithic_path = os.path.join(vault_path, "block.tar.gz")
                if os.path.exists(monolithic_path):
                    block_file = monolithic_path
                else:
                    continue

            # Verify integrity (if not monolithic fallback)
            if block_file != os.path.join(vault_path, "block.tar.gz"):
                if not verify_block_integrity(block_file, block_id):
                    return

            print(f"restoring {abs_target} from {block_id}...")
            success = engine.controller.uncompress(block_file, archive_target, dest)
            if success:
                success_any = True

        if success_any:
            print(f"successfully restored to {abs_target}")
        else:
            print(f"failed to restore {abs_target}")
