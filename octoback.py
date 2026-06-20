import argparse
import json
import logging
import os

from modules import Engine

OCTO_DIR = os.path.expanduser("~/.octoback")
DEFAULT_CONFIG = os.path.join(OCTO_DIR, "octo.yaml")
DEFAULT_INDEX = os.path.join(OCTO_DIR, "index.json")
DEFAULT_VAULT = os.path.expanduser("~/Vault")

description_message = """
Octo is a lightweight CLI backup manager that separates the "intent" (what to back up) from the "action"
(the actual backup process). By maintaining a curated index of files and folders, Octo ensures your
backup vault remains organized and predictable.
"""


def main():
    parser = argparse.ArgumentParser(
        description=description_message, usage="%(prog)s [command] [options]"
    )

    # Subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="commands")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a directory to the index.")
    add_parser.add_argument(
        "add",
        type=str,
        nargs="?",
        default=".",
        help="Directory path or folder name (current directory if not specified)",
    )
    add_parser.add_argument(
        "-R",
        "--recursive",
        action="store_true",
        help="Perform the operation recursively",
    )

    # Restore command
    restore_parser = subparsers.add_parser(
        "restore", help="Restore a specific directory from the backup."
    )
    restore_parser.add_argument(
        "restore",
        type=str,
        nargs="?",
        default=None,
        help="Directory path or folder name to restore (defaults to current directory if not specified)",
    )
    restore_parser.add_argument(
        "--all", action="store_true", help="Restore all files in the directory"
    )

    # Init command
    subparsers.add_parser(
        "init", help="Initialize the environment and create the configuration file."
    )

    # Backup command
    subparsers.add_parser("backup", help="Run the backup process based on the index.")

    # Remove command
    remove_parser = subparsers.add_parser(
        "remove", aliases=["rm"], help="Remove a directory or file from the index."
    )
    remove_parser.add_argument(
        "path",
        type=str,
        nargs="?",
        default=".",
        help="Directory or file path to remove (defaults to current directory if not specified)",
    )

    args = parser.parse_args()

    if args.command == "add":
        add_to_index(args.add, recursive=args.recursive)
    elif args.command in ["remove", "rm"]:
        remove_from_index(args.path)
    elif args.command == "restore":
        restore_from_backup(args.restore, all_files=args.all)
    elif args.command == "init":
        initialize_environment()
    elif args.command == "backup":
        run_backup()
    else:
        parser.print_help()


def add_to_index(path, recursive=False):
    if not engine.config.load_config(DEFAULT_CONFIG):
        return
    index_path = engine.config.configuration["storage"]["index_path"]

    if os.path.exists(index_path):
        engine.load_index(index_path)

    if recursive:
        files = engine.controller.scan_folder_for_files(path)
        engine.update_index(files)
    else:
        engine.add_folder_to_index(path)

    engine.save_index(index_path)


def remove_from_index(path):
    if not engine.config.load_config(DEFAULT_CONFIG):
        logging.error("Failed to load config. Please run 'octoback init' first.")
        return
    index_path = engine.config.configuration["storage"]["index_path"]

    if os.path.exists(index_path):
        engine.load_index(index_path)
    else:
        logging.info("Index file does not exist. Nothing to remove.")
        return

    if engine.remove_from_index(path):
        engine.save_index(index_path)


def run_tui(items):
    import curses

    def main_curses(stdscr):
        curses.curs_set(0)  # Hide cursor
        stdscr.keypad(True)
        curses.use_default_colors()

        # Initialize color pairs if color support is available
        if curses.has_colors():
            # Use default terminal background (-1)
            curses.init_pair(1, curses.COLOR_CYAN, -1)
            curses.init_pair(2, curses.COLOR_GREEN, -1)
            curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
            color_info = curses.color_pair(1)
            color_selected = curses.color_pair(2)
            color_highlight = curses.color_pair(3)
        else:
            color_info = curses.A_NORMAL
            color_selected = curses.A_BOLD
            color_highlight = curses.A_REVERSE

        selected = [False] * len(items)
        current_idx = 0
        start_idx = 0

        while True:
            stdscr.clear()
            max_y, max_x = stdscr.getmaxyx()
            visible_height = max_y - 6  # Leave room for headers/footers

            # Render header
            stdscr.addstr(
                0, 0, " === OctoBack Restore TUI === ", curses.A_BOLD | color_info
            )
            stdscr.addstr(
                1,
                0,
                "Use Up/Down (or j/k) to navigate | Space to select | 'a' to toggle all",
                curses.A_DIM,
            )
            stdscr.addstr(
                2,
                0,
                "Press Enter to restore selected | 'q' or ESC to cancel",
                curses.A_DIM,
            )
            stdscr.addstr(3, 0, "-" * min(max_x - 1, 70), curses.A_DIM)

            # Calculate scrolling window
            if current_idx < start_idx:
                start_idx = current_idx
            elif current_idx >= start_idx + visible_height:
                start_idx = current_idx - visible_height + 1

            # Render items
            for i in range(min(visible_height, len(items) - start_idx)):
                idx = start_idx + i
                item = items[idx]

                # Format item row
                chk_box = "[x]" if selected[idx] else "[ ]"
                style = color_highlight if idx == current_idx else curses.A_NORMAL

                # Color the checked boxes differently if not highlighted
                if selected[idx] and idx != current_idx:
                    stdscr.addstr(4 + i, 2, chk_box, color_selected | curses.A_BOLD)
                    stdscr.addstr(4 + i, 6, item, style)
                else:
                    stdscr.addstr(4 + i, 2, f"{chk_box} {item}", style)

            # Render footer with scroll indicator
            if len(items) > visible_height:
                stdscr.addstr(
                    max_y - 1,
                    0,
                    f" -- Scroll for more ({current_idx + 1}/{len(items)}) -- ",
                    color_info,
                )

            stdscr.refresh()

            key = stdscr.getch()

            if key in [curses.KEY_UP, ord("k")]:
                current_idx = (current_idx - 1) % len(items)
            elif key in [curses.KEY_DOWN, ord("j")]:
                current_idx = (current_idx + 1) % len(items)
            elif key == ord(" "):
                selected[current_idx] = not selected[current_idx]
            elif key == ord("a"):
                if all(selected):
                    selected = [False] * len(items)
                else:
                    selected = [True] * len(items)
            elif key in [10, 13]:  # Enter
                break
            elif key in [ord("q"), 27]:  # 'q' or Esc
                return None

        return [items[i] for i, sel in enumerate(selected) if sel]

    return curses.wrapper(main_curses)


def calculate_sha1(filepath):
    import hashlib

    sha1 = hashlib.sha1()
    try:
        with open(filepath, "rb") as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                sha1.update(data)
        return sha1.hexdigest()
    except Exception:
        return None


def restore_from_backup(path, all_files=False):
    engine.config.load_config(DEFAULT_CONFIG)
    if not engine.config.configuration:
        logging.error("Failed to load config. Please run 'octoback init' first.")
        return

    vault_path = engine.config.configuration["storage"]["vault_path"]
    index_path = engine.config.configuration["storage"]["index_path"]
    checksums_path = os.path.join(vault_path, "checksums.json")

    if os.path.exists(index_path):
        engine.load_index(index_path)

    if not engine.index:
        logging.info("Index is empty. Nothing to restore.")
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
            logging.error(f"Error loading checksums: {e}")

    def verify_block_integrity(block_file, block_id):
        if not checksums or block_id not in checksums:
            return True  # If no checksum stored, bypass validation
        current_sha = calculate_sha1(block_file)
        expected_sha = checksums[block_id]
        if current_sha != expected_sha:
            logging.critical(
                f"INTEGRITY ERROR: Corruption detected in archive '{block_file}'! Checksum mismatch."
            )
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
            logging.info("No indexed files found in the current directory.")
            return

        matching_paths.sort()
        rel_paths = [os.path.relpath(p, cwd) for p in matching_paths]

        selected_rel_paths = run_tui(rel_paths)
        if not selected_rel_paths:
            logging.info("Restoration cancelled or no files selected.")
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
                logging.error(f"Cannot find block ID for path: {abs_p}")
                continue

            block_file = os.path.join(vault_path, f"{block_id}.tar.gz")
            if not os.path.exists(block_file):
                logging.error(f"Block archive not found: {block_file}")
                continue

            # Verify integrity
            if not verify_block_integrity(block_file, block_id):
                return

            archive_target = abs_p.lstrip(os.sep)
            dest = os.path.dirname(abs_p)
            logging.info(f"Restoring {abs_p} from {block_id}...")
            engine.controller.uncompress(block_file, archive_target, dest)
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
                logging.error(f"Block archive not found: {block_file}")
                continue

            # Verify integrity
            if not verify_block_integrity(block_file, block_id):
                return

            for item in items:
                archive_target = item.lstrip(os.sep)
                dest = os.path.dirname(item)
                logging.info(f"Restoring {item} from {block_id}...")
                engine.controller.uncompress(block_file, archive_target, dest)
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
            logging.warning(
                f"Path '{abs_target}' is not in the index. Restoration may fail."
            )
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

            logging.info(f"Restoring {abs_target} from {block_id}...")
            success = engine.controller.uncompress(block_file, archive_target, dest)
            if success:
                success_any = True

        if success_any:
            logging.info(f"Successfully restored to {abs_target}")
        else:
            logging.error(f"Failed to restore {abs_target}")


def initialize_environment():
    config = {
        "storage": {
            "index_path": DEFAULT_INDEX,
            "vault_path": DEFAULT_VAULT,
        }
    }

    engine.config.set_config(config)
    engine.config.save_config(DEFAULT_CONFIG)


def run_backup():
    engine.config.load_config(DEFAULT_CONFIG)
    if not engine.config.configuration:
        logging.error("Failed to load config. Please run 'octoback init' first.")
        return

    vault_path = engine.config.configuration["storage"]["vault_path"]
    index_path = engine.config.configuration["storage"]["index_path"]

    if os.path.exists(index_path):
        engine.load_index(index_path)

    if not engine.index:
        logging.info("Index is empty. Nothing to backup.")
        return

    # 1. Expand all indexed paths to a set of absolute file paths
    all_files = set()
    for path, _ in engine.index:
        if not os.path.exists(path):
            continue
        if os.path.isdir(path):
            for root_dir, _, files in os.walk(path):
                for f in files:
                    all_files.add(os.path.abspath(os.path.join(root_dir, f)))
        else:
            all_files.add(os.path.abspath(path))

    # 2. Group files by block_id using longest prefix match
    block_files = {}  # block_id -> list of file paths
    for filepath in all_files:
        best_match_block = None
        best_len = -1
        for indexed_path, block_id in engine.index:
            if filepath == indexed_path:
                best_match_block = block_id
                break
            if filepath.startswith(indexed_path + os.sep):
                if len(indexed_path) > best_len:
                    best_len = len(indexed_path)
                    best_match_block = block_id

        if best_match_block:
            if best_match_block not in block_files:
                block_files[best_match_block] = []
            block_files[best_match_block].append(filepath)

    if not block_files:
        logging.warning("No files found to backup.")
        return

    # 3. Create temporary directories for staging
    import shutil

    temp_vault = os.path.expanduser("~/.octoback/temp_vault")
    temp_packages = os.path.expanduser("~/.octoback/temp_vault_packages")

    shutil.rmtree(temp_vault, ignore_errors=True)
    shutil.rmtree(temp_packages, ignore_errors=True)
    os.makedirs(temp_vault, exist_ok=True)
    os.makedirs(temp_packages, exist_ok=True)

    checksums = {}  # block_id -> sha1_hash

    # 4. Copy, compress, and calculate checksums for each block
    for block_id, files in block_files.items():
        block_temp_dir = os.path.join(temp_vault, block_id)
        os.makedirs(block_temp_dir, exist_ok=True)

        # Copy block files mirroring absolute paths
        for f in files:
            rel_path = f.lstrip(os.sep)
            dest_f = os.path.join(block_temp_dir, rel_path)
            engine.controller.copy_to(f, dest_f)

        # Compress
        logging.info(f"Compressing block {block_id}...")
        compressed_archive = os.path.join(temp_packages, f"{block_id}.tar.gz")

        subdirs = os.listdir(block_temp_dir)
        if not subdirs:
            continue

        command = [
            "tar",
            "-czf",
            compressed_archive,
            "-C",
            block_temp_dir,
        ] + subdirs

        import subprocess

        try:
            subprocess.run(command, check=True)
            logging.info(f"Successfully compressed block {block_id}")

            # Calculate and store checksum
            sha = calculate_sha1(compressed_archive)
            if sha:
                checksums[block_id] = sha
        except Exception as e:
            logging.error(f"Failed to compress block {block_id}: {e}")
            shutil.rmtree(temp_vault, ignore_errors=True)
            shutil.rmtree(temp_packages, ignore_errors=True)
            return

    # Write the checksums JSON file inside the temp_packages staging dir
    checksums_path = os.path.join(temp_packages, "checksums.json")
    try:
        with open(checksums_path, "w") as f:
            json.dump(checksums, f)
    except Exception as e:
        logging.error(f"Failed to save checksums: {e}")
        shutil.rmtree(temp_vault, ignore_errors=True)
        shutil.rmtree(temp_packages, ignore_errors=True)
        return

    # 5. Replace Vault directory atomically (Atomic Vault Swap)
    backup_vault_path = vault_path + "_old"

    try:
        # Move current vault out of the way
        if os.path.exists(vault_path):
            shutil.move(vault_path, backup_vault_path)

        # Move temp packages to be the new Vault
        shutil.move(temp_packages, vault_path)

        # Delete old Vault backup
        if os.path.exists(backup_vault_path):
            shutil.rmtree(backup_vault_path, ignore_errors=True)

        logging.info("Backup successfully completed.")
    except Exception as e:
        logging.error(f"Error replacing vault files: {e}")
        # Try to rollback if old vault was moved
        if os.path.exists(backup_vault_path):
            shutil.rmtree(vault_path, ignore_errors=True)
            shutil.move(backup_vault_path, vault_path)
    finally:
        # 6. Clean up temp directories
        shutil.rmtree(temp_vault, ignore_errors=True)
        shutil.rmtree(temp_packages, ignore_errors=True)


if __name__ == "__main__":
    import sys
    engine = Engine()
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        logging.info("Operation interrupted by user.")
        sys.exit(130)
