import os
import shutil
import sys
from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine
from modules.tui import run_tui
from modules.ui import draw_progress
from modules.util.paths import get_vault_target_path

engine = Engine()


def collect_restore_files(vault_src: str, original_dest: str, file_list: list):
    if not os.path.exists(vault_src):
        return
    if os.path.isdir(vault_src):
        for root_dir, _, files in os.walk(vault_src):
            for f in files:
                abs_f = os.path.join(root_dir, f)
                rel_to_vault_src = os.path.relpath(abs_f, vault_src)
                dest_f = os.path.join(original_dest, rel_to_vault_src)
                file_list.append((abs_f, dest_f))
    else:
        file_list.append((vault_src, original_dest))


def execute_restore(file_list: list) -> bool:
    total = len(file_list)
    if total == 0:
        return False

    failed_files = []

    for i, (src, dest) in enumerate(file_list):
        current_name = os.path.basename(src)
        draw_progress(i, total, current_name, "restoring")
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                shutil.copy2(src, dest)
            except PermissionError:
                try:
                    if os.path.exists(dest):
                        os.chmod(dest, 0o666)
                        os.remove(dest)
                    shutil.copy2(src, dest)
                except Exception:
                    raise
        except Exception as e:
            failed_files.append((src, e))

    draw_progress(total, total, "complete", "restoring")
    sys.stdout.write("\n")

    if failed_files:
        print(f"warning: restoration completed with warnings (skipped {len(failed_files)} files)")
        print("skipped files:")
        for src, err in failed_files[:5]:
            print(f"  • {os.path.basename(src)}: {err}")
        if len(failed_files) > 5:
            print(f"  ... and {len(failed_files) - 5} more files.")
    
    return True


def restore_from_backup(path, all_files=False):
    if not engine.config.load_config(DEFAULT_CONFIG):
        print("error: config file not found, please run 'octoback init' first.")
        return

    vault_path = engine.config.configuration["storage"]["vault_path"]
    index_path = engine.config.configuration["storage"]["index_path"]

    if os.path.exists(index_path):
        engine.load_index(index_path)

    if not engine.index:
        print("index is empty, nothing to restore")
        return

    # Check for TUI mode
    if path == "list":
        cwd = os.getcwd()
        matching_paths = []
        for indexed_path in engine.index:
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

        file_list = []
        for rel_p in selected_rel_paths:
            abs_p = os.path.abspath(os.path.join(cwd, rel_p))
            vault_target = get_vault_target_path(abs_p, vault_path)
            collect_restore_files(vault_target, abs_p, file_list)

        if execute_restore(file_list):
            print("restoration successfully completed")
        else:
            print("nothing to restore")
        return

    if all_files:
        file_list = []
        for item in sorted(engine.index):
            vault_target = get_vault_target_path(item, vault_path)
            collect_restore_files(vault_target, item, file_list)

        if execute_restore(file_list):
            print("restoration successfully completed")
        else:
            print("nothing to restore")
        return
    else:
        if not path:
            path = os.getcwd()

        abs_target = os.path.abspath(path)

        # Check index for any matches
        has_matches = False
        for indexed_path in engine.index:
            if (
                abs_target == indexed_path
                or abs_target.startswith(indexed_path + os.sep)
                or indexed_path.startswith(abs_target + os.sep)
            ):
                has_matches = True
                break

        if not has_matches:
            print(f"warning: path '{abs_target}' is not in the index, restoration may fail")

        vault_target = get_vault_target_path(abs_target, vault_path)
        file_list = []
        collect_restore_files(vault_target, abs_target, file_list)

        if execute_restore(file_list):
            print(f"successfully restored to {abs_target}")
        else:
            print(f"failed to restore {abs_target}")
