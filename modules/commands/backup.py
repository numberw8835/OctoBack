import os
import shutil
import fcntl
import logging

from modules.constants import DEFAULT_CONFIG, OCTO_DIR
from modules.engine import Engine
from modules.ui import draw_progress
from modules.util.paths import get_vault_target_path

engine = Engine()
lock_file = None


def cleanup_temp_dirs():
    pass


def run_backup():
    if not engine.config.load_config(DEFAULT_CONFIG):
        print("error: config file not found, please run 'octoback init' first.")
        return

    vault_path = engine.config.configuration["storage"]["vault_path"]
    index_path = engine.config.configuration["storage"]["index_path"]

    if os.path.exists(index_path):
        engine.load_index(index_path)

    if not engine.index:
        print("index is empty, nothing to backup")
        return

    # 1. Collect all source files from indexed files/folders
    all_source_files = []
    for path in engine.index:
        if not os.path.exists(path):
            continue
        if os.path.isdir(path):
            for root_dir, _, files in os.walk(path):
                for f in files:
                    abs_f = os.path.abspath(os.path.join(root_dir, f))
                    all_source_files.append(abs_f)
        else:
            all_source_files.append(os.path.abspath(path))

    total_files = len(all_source_files)
    if total_files == 0:
        print("no files found to backup")
        return

    # 2. Acquire lockfile to prevent concurrent backups
    lock_file_path = os.path.join(OCTO_DIR, "backup.lock")
    try:
        global lock_file
        lock_file = open(lock_file_path, "w")
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("another backup instance is already running, aborting")
        return
    except Exception as e:
        print(f"failed to acquire backup lock: {e}")
        return

    # Disable logging warnings from internal operations temporarily during backup progress bar
    root_logger = logging.getLogger()
    old_level = root_logger.level
    root_logger.setLevel(logging.WARNING)

    try:
        for i, src_file in enumerate(all_source_files):
            dest_file = get_vault_target_path(src_file, vault_path)
            current_name = os.path.basename(src_file)

            draw_progress(i, total_files, current_name, "backing up")

            should_copy = True
            if os.path.exists(dest_file):
                try:
                    src_stat = os.stat(src_file)
                    dest_stat = os.stat(dest_file)
                    # Skip only if size matches and source is not newer than destination
                    if src_stat.st_size == dest_stat.st_size and src_stat.st_mtime <= dest_stat.st_mtime:
                        should_copy = False
                except Exception:
                    pass

            if should_copy:
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                try:
                    shutil.copy2(src_file, dest_file)
                except PermissionError:
                    try:
                        if os.path.exists(dest_file):
                            os.chmod(dest_file, 0o666)
                            os.remove(dest_file)
                        shutil.copy2(src_file, dest_file)
                    except Exception:
                        raise

        # Complete progress bar display
        draw_progress(total_files, total_files, "complete", "backing up")
        import sys
        sys.stdout.write("\n")
        print("backup successfully completed")

    except Exception as e:
        import sys
        sys.stdout.write("\n")
        print(f"error during backup: {e}")
    finally:
        root_logger.setLevel(old_level)
        if lock_file:
            try:
                lock_file.close()
            except Exception:
                pass
