import fcntl
import logging
import os
import re
import shutil
import subprocess

from modules.constants import DEFAULT_CONFIG, OCTO_DIR
from modules.engine import Engine
from modules.ui import draw_progress
from modules.util.paths import get_vault_target_path

engine = Engine()
lock_file = None


def cleanup_temp_dirs():
    pass


def run_backup(verbose: bool):
    # Load the default configuration and check if it exists
    if not engine.config.load_config(DEFAULT_CONFIG):
        print("error: config file not found, please run 'octoback init' first.")
        return

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

    # 1. Collect all source files from indexed files/folders
    all_source_files = set()
    for path in engine.index:
        if not os.path.exists(path):
            # engine.index.remove(path)
            continue
        if os.path.isdir(path):
            for root_dir, _, files in os.walk(path):
                for f in files:
                    abs_f = os.path.abspath(os.path.join(root_dir, f))
                    all_source_files.add(abs_f)
        else:
            all_source_files.add(os.path.abspath(path))

    unique_source_files = sorted(list(all_source_files))
    total_files = len(unique_source_files)
    if total_files == 0:
        print("no files found to backup")
        return
    else:
        print(f"{total_files} files found!")

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

    failed_files = []
    global_idx = 0

    try:
        # Group files into Home relative paths and Root relative paths
        home_source = os.path.expanduser("~")
        root_source = "/"

        home_files = []
        root_files = []

        for src_file in unique_source_files:
            if src_file.startswith(home_source + os.sep) or src_file == home_source:
                rel = os.path.relpath(src_file, home_source)
                home_files.append((src_file, rel))
            else:
                rel = os.path.relpath(src_file, root_source)
                root_files.append((src_file, rel))

        def run_rsync_batch(source_dir, dest_dir, file_tuples):
            nonlocal global_idx
            if not file_tuples:
                return
            
            os.makedirs(dest_dir, exist_ok=True)
            cmd = ["rsync", "-aH", "--from0", "--files-from=-", source_dir, dest_dir]
            
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            for src_file, rel_path in file_tuples:
                try:
                    proc.stdin.write(rel_path + "\0")
                except IOError:
                    break
                global_idx += 1
                if global_idx % 200 == 0 or global_idx == total_files:
                    draw_progress(global_idx, total_files, os.path.basename(src_file), "backing up")
                    
            try:
                proc.stdin.close()
            except IOError:
                pass
                
            stdout, stderr = proc.communicate()
            
            if proc.returncode != 0 and stderr:
                for line in stderr.splitlines():
                    if line.startswith("rsync:"):
                        match = re.search(r'"([^"]+)"', line)
                        if match:
                            rel_p = match.group(1)
                            abs_p = os.path.abspath(os.path.join(source_dir, rel_p))
                            err_msg = "transfer failed"
                            if "failed:" in line:
                                err_msg = line.split("failed:", 1)[1].strip()
                            failed_files.append((abs_p, Exception(err_msg)))
                        else:
                            failed_files.append(("rsync", Exception(line.strip())))

        # Run the batches
        run_rsync_batch(home_source, os.path.join(vault_path, "home"), home_files)
        run_rsync_batch(root_source, os.path.join(vault_path, "root"), root_files)

        # Complete progress bar display
        draw_progress(total_files, total_files, "complete", "backing up")
        import sys

        sys.stdout.write("\n")

        if failed_files:
            if verbose:
                print(
                    "warning: backup completed with warnings (skipped {} files)".format(
                        len(failed_files)
                    )
                )
                print("skipped files:")
                for src, err in failed_files:
                    print("  • {}: {}".format(os.path.basename(str(src)), err))
            else:
                print(
                    "warning: backup completed with warnings (skipped {} files)".format(
                        len(failed_files)
                    )
                )
                print("skipped files:")
                for src, err in failed_files[:5]:
                    print("  • {}: {}".format(os.path.basename(str(src)), err))
                if len(failed_files) > 5:
                    print("  ... and {} more files.".format(len(failed_files) - 5))
        else:
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
