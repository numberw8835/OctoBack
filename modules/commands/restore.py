import os
from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine
from modules.util.paths import get_vault_target_path, get_source_path_from_vault
from modules.ui import draw_progress

engine = Engine()

def restore_from_backup(path, all_files=False):
    if not engine.config.load_config(DEFAULT_CONFIG):
        print("config not found")
        return
    config = engine.config.configuration
    vault_path = config["storage"]["vault_path"]
    index_path = config["storage"]["index_path"]

    if os.path.exists(index_path):
        engine.load_index(index_path)

    file_list = []
    for source in engine.index:
        vault_target = get_vault_target_path(source, vault_path)
        if not os.path.exists(vault_target):
            continue

        if os.path.isdir(vault_target):
            for root, _, files in os.walk(vault_target):
                for file in files:
                    vault_file = os.path.join(root, file)
                    orig_file = get_source_path_from_vault(vault_file, vault_path)
                    file_list.append((vault_file, orig_file))
        elif os.path.isfile(vault_target):
            orig_file = get_source_path_from_vault(vault_target, vault_path)
            file_list.append((vault_target, orig_file))

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
            print("no indexed files found in current directory")
            return

        matching_paths.sort()
        rel_paths = [os.path.relpath(p, cwd) for p in matching_paths]
        
        from modules.tui import run_tui
        selected_rel = run_tui(rel_paths)
        if not selected_rel:
            print("no files selected")
            return

        selected_abs = {os.path.abspath(os.path.join(cwd, p)) for p in selected_rel}
        for vault_file, orig_file in file_list:
            matched = False
            for abs_path in selected_abs:
                if orig_file == abs_path or orig_file.startswith(abs_path + os.sep):
                    matched = True
                    break
            if matched:
                to_restore.append((vault_file, orig_file))
    elif path:
        abs_target = os.path.abspath(path)
        for vault_file, orig_file in file_list:
            if orig_file == abs_target or orig_file.startswith(abs_target + os.sep):
                to_restore.append((vault_file, orig_file))
    else:
        # Default to restoring current directory
        abs_target = os.getcwd()
        for vault_file, orig_file in file_list:
            if orig_file == abs_target or orig_file.startswith(abs_target + os.sep):
                to_restore.append((vault_file, orig_file))

    if not to_restore:
        print("nothing to restore")
        return

    # Copy files and draw progress
    total_files = len(to_restore)
    files_completed = 0
    for vault_file, orig_file in to_restore:
        def update_progress_callback(percent):
            nonlocal files_completed
            global_progress = (files_completed + percent) / total_files
            draw_progress(
                index=int(global_progress * 100),
                total=100,
                current_file=os.path.basename(orig_file),
                action="restoring ",
            )

        # Make sure destination directories exist
        os.makedirs(os.path.dirname(orig_file), exist_ok=True)
        success = engine.controller.copy_to(
            vault_file, orig_file, progress_callback=update_progress_callback
        )
        if success:
            files_completed += 1
