import fcntl
import logging
import os
from genericpath import exists

from modules.constants import DEFAULT_CONFIG, OCTO_DIR
from modules.engine import Engine
from modules.ui import draw_progress
from modules.util.paths import get_vault_target_path

engine = Engine()
lock_file = None

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


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

    sources = set()
    for source in engine.index:
        if not os.path.exists(source):
            continue
        if os.path.isdir(source):
            for root, _, files in os.walk(source):
                for file in files:
                    file_path = os.path.join(root, file)
                    sources.add(file_path)
        elif os.path.isfile(source) and not os.path.islink(source):
            sources.add(source)

    total_files = len(sources)
    logging.info(f"{total_files} files found and ready for backing up")

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

        total_bytes = 0
        for source in sources:
            if os.path.isfile(source):
                total_bytes += os.path.getsize(source)

        # Copy the files to the vault
        files_completed = 0
        for source in sources:
            dest = get_vault_target_path(source, vault_path)

            # Define callback for the current file's progress
            def update_progress_callback(percent):
                nonlocal files_completed
                # Calculate global percentage: (completed files + progress of current) / total
                global_progress = (files_completed + percent) / total_files
                draw_progress(
                    index=int(global_progress * 100),
                    total=100,
                    current_file=os.path.basename(source),
                    action="backing up ",
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
                print(f"\nfailed to backup {source}")
        print()
    finally:
        if lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()
