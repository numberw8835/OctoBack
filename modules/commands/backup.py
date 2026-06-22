import fcntl
import logging
import os

from modules.constants import DEFAULT_CONFIG, OCTO_DIR
from modules.engine import Engine
from modules.ui import draw_progress, human_readable_size
from modules.util.paths import get_vault_target_path

engine = Engine()
lock_file = None


def run_backup():
    config_path = DEFAULT_CONFIG

    if not engine.config.load_config(config_path):
        print("octo.yaml couldn't be found")

    # Retrieve paths from the configuration
    vault_path = engine.config.configuration["storage"]["vault_path"]
    index_path = engine.config.configuration["storage"]["index_path"]

    # Load the index if it exists
    if os.path.exists(index_path):
        engine.load_index(index_path)

    # Check if the index is empty
    if not engine.index:
        print("index is empty, nothing to backup")
        return

    sources = [s for s in engine.index if os.path.exists(s)]
    total_files = len(sources)
    logging.info(f"{total_files} items found and ready for backing up")

    # Aquire a lock to prevent concurrent backups

    lock_file_path = os.path.join(OCTO_DIR, "backup.lock")
    try:
        global lock_file
        lock_file = open(lock_file_path, "w")
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("another backup instance is already running")
        return
    except Exception as e:
        print(f"failed to acquire backup lock {e}")
        return

    try:
        # Create the vault
        try:
            os.makedirs(vault_path, exist_ok=True)
        except FileExistsError:
            print("vault already exists, skipping creation")
        except Exception as e:
            print(f"failed to create vault {e}")
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
