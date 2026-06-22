import fcntl
import logging
import os

from modules.constants import DEFAULT_CONFIG, OCTO_DIR
from modules.engine import Engine
from modules.ui import draw_progress, human_readable_size, print_success, print_error, print_warning
from modules.util.paths import get_vault_target_path

engine = Engine()
lock_file = None


def run_backup(paths=None, all=False):
    config_path = DEFAULT_CONFIG

    if not engine.config.load_config(config_path):
        print_error("Configuration file not found. Please run 'octoback init' first.")
        return

    # Retrieve paths from the configuration
    vault_path = engine.config.configuration["storage"]["vault_path"]
    index_path = engine.config.configuration["storage"]["index_path"]

    # Load the index if it exists
    if os.path.exists(index_path):
        engine.load_index(index_path)

    # Check if .octoback is in the index. If not, add it and print the message.
    octo_dir_abs = os.path.abspath(OCTO_DIR)
    if octo_dir_abs not in engine.index:
        print_success("I got you, 🐙")
        engine.add_folder_to_index(OCTO_DIR)
        engine.save_index(index_path)

    # Check if the index is empty
    if not engine.index:
        print_warning("Index is empty, nothing to back up")
        return

    if all:
        sources = [s for s in engine.index if os.path.exists(s)]
    else:
        if not paths:
            paths = ["."]
        requested_abs = [os.path.abspath(p) for p in paths]
        sources_set = set()
        for t in requested_abs:
            for s in engine.index:
                if s == t or s.startswith(t + os.sep):
                    if os.path.exists(s):
                        sources_set.add(s)
            if os.path.exists(t):
                if t in engine.index or any(t.startswith(idx + os.sep) for idx in engine.index):
                    sources_set.add(t)
        sources = sorted(list(sources_set))

    if not sources:
        print_warning("Nothing to back up")
        return

    total_files = len(sources)
    logging.info(f"{total_files} items found and ready for backing up")

    # Acquire a lock to prevent concurrent backups
    lock_file_path = os.path.join(OCTO_DIR, "backup.lock")
    try:
        global lock_file
        lock_file = open(lock_file_path, "w")
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print_error("Another backup instance is already running")
        return
    except Exception as e:
        print_error(f"Failed to acquire backup lock: {e}")
        return

    try:
        # Create the vault
        try:
            os.makedirs(vault_path, exist_ok=True)
        except Exception as e:
            print_error(f"Failed to create vault: {e}")
            return

        # Copy the items to the vault
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

        files_completed = 0
        for source in sources:
            dest = get_vault_target_path(source, vault_path)
            source_size = get_path_size(source)

            # Define callback for the current item's progress
            def update_progress_callback(percent, current_bytes=0, total_bytes=0):
                nonlocal files_completed
                # Calculate global percentage: (completed items + progress of current) / total
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
                    current_file=os.path.basename(source),
                    action="backing up ",
                    extra_info=extra_info,
                )

            logging.info(f"backing up {source} to {dest}")
            # Perform the copy with the callback
            success = engine.controller.copy_to(
                source, dest, progress_callback=update_progress_callback
            )

            if success:
                logging.info(f"successfully backed up {source}")
                files_completed += 1
            else:
                logging.warning(f"failed to backup {source}")
        print()
    finally:
        if lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()
