import logging
import os

from modules.constants import DEFAULT_CONFIG, OCTO_DIR
from modules.engine import Engine
from modules.ui import draw_progress, human_readable_size, print_success, print_error, print_warning, print_info
from modules.util.paths import get_vault_target_path

engine = Engine()


def restore_from_backup(path, all_files=False):
    if not engine.config.load_config(DEFAULT_CONFIG):
        print_error("Configuration file not found. Please run 'octoback init' first.")
        return
    config = engine.config.configuration
    vault_path = config["storage"]["vault_path"]
    index_path = config["storage"]["index_path"]

    if os.path.exists(index_path):
        engine.load_index(index_path)

    # Collect top-level vault target directories and their corresponding original paths
    file_list = []
    for source in engine.index:
        vault_target = get_vault_target_path(source, vault_path)
        if os.path.exists(vault_target):
            file_list.append((vault_target, os.path.abspath(source)))

    # Control flow: search/filter files to restore based on input path
    to_restore = []
    if all_files:
        to_restore = file_list
    elif path == "list":
        cwd = os.getcwd()
        matching_paths = []
        for indexed_path in engine.index:
            if indexed_path == cwd or indexed_path.startswith(cwd + os.sep):
                matching_paths.append(indexed_path)

        if not matching_paths:
            print_warning("No indexed files found in current directory")
            return

        matching_paths.sort()
        rel_paths = [os.path.relpath(p, cwd) for p in matching_paths]

        from modules.tui import run_tui

        selected_rel = run_tui(rel_paths)
        if not selected_rel:
            print_warning("No files selected")
            return

        if selected_rel == "__restore_octoback__":
            abs_target = os.path.abspath(OCTO_DIR)
            vault_file = get_vault_target_path(abs_target, vault_path)
            if os.path.exists(vault_file):
                to_restore.append((vault_file, abs_target))
            else:
                print_error(".octoback backup not found in vault")
                return
        else:
            selected_abs = {os.path.abspath(os.path.join(cwd, p)) for p in selected_rel}
            for vault_file, orig_file in file_list:
                if orig_file in selected_abs:
                    to_restore.append((vault_file, orig_file))
    else:
        target = path if path else os.getcwd()
        abs_target = os.path.abspath(target)
        if abs_target in [os.path.abspath(os.path.expanduser("~")), "/"]:
            print_error("Restoring the home directory or system root directly is unsafe due to active files.")
            print_info("Please specify a specific subdirectory to restore, or run: `octoback restore list`")
            return

        # Find all indexed paths that are at or under abs_target
        matching_indexed = []
        for s in engine.index:
            if s == abs_target or s.startswith(abs_target + os.sep):
                matching_indexed.append(s)
        
        if matching_indexed:
            # Restore the matched indexed paths
            for s in matching_indexed:
                vault_file = get_vault_target_path(s, vault_path)
                if os.path.exists(vault_file):
                    to_restore.append((vault_file, s))
        else:
            # If target itself is inside an indexed folder, restore the target itself
            is_inside_indexed = any(abs_target.startswith(idx + os.sep) for idx in engine.index)
            if is_inside_indexed:
                vault_file = get_vault_target_path(abs_target, vault_path)
                if os.path.exists(vault_file):
                    to_restore.append((vault_file, abs_target))

    if not to_restore:
        print_warning("Nothing to restore")
        return

    # Copy files and draw progress
    def get_path_size(path):
        if os.path.isfile(path):
            return os.path.getsize(path)
        total = 0
        for root, _, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                if not os.path.islink(fp):
                    try:
                        total += os.path.getsize(fp)
                    except OSError:
                        pass
        return total

    total_files = len(to_restore)
    files_completed = 0
    failed_files = []
    for vault_file, orig_file in to_restore:
        source_size = get_path_size(vault_file)

        def update_progress_callback(percent, current_bytes=0, total_bytes=0):
            nonlocal files_completed
            global_progress = (files_completed + percent) / total_files

            if total_bytes == 0:
                total_bytes = source_size
                current_bytes = int(source_size * percent)

            extra_info = ""
            if total_bytes > 0:
                curr_str = human_readable_size(current_bytes)
                tot_str = human_readable_size(total_bytes)
                extra_info = f"({curr_str} / {tot_str} | {int(percent * 100)}%)"

            draw_progress(
                index=int(global_progress * 100),
                total=100,
                current_file=os.path.basename(orig_file),
                action="restoring ",
                extra_info=extra_info,
            )

        # Make sure destination directories exist
        os.makedirs(os.path.dirname(orig_file), exist_ok=True)
        logging.info(f"restoring {vault_file} to {orig_file}")
        success = engine.controller.copy_to(
            vault_file, orig_file, progress_callback=update_progress_callback
        )
        if success:
            logging.info(f"successfully restored {orig_file}")
            files_completed += 1
        else:
            logging.warning(f"failed to restore {orig_file}")
            failed_files.append(orig_file)
    print()

    if failed_files:
        print_error("Failed to restore files:")
        for f in failed_files:
            print_info(f"  {f}")
