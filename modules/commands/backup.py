import os
import json
import logging
import shutil
import time
import fcntl

from modules.constants import DEFAULT_CONFIG, OCTO_DIR
from modules.engine import Engine
from modules.util.crypto import calculate_sha1
from modules.ui import draw_status_bar, format_bytes

engine = Engine()

active_temp_dirs = []
lock_file = None


def cleanup_temp_dirs():
    for d in active_temp_dirs:
        shutil.rmtree(d, ignore_errors=True)
    shutil.rmtree(os.path.expanduser("~/.octoback/temp_vault"), ignore_errors=True)
    shutil.rmtree(os.path.expanduser("~/.octoback/temp_vault_packages"), ignore_errors=True)


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
        print("no files found to backup")
        return

    # Calculate file sizes and total bytes
    file_sizes = {}
    total_bytes = 0
    for block_id, files in block_files.items():
        for f in files:
            try:
                sz = os.path.getsize(f)
                file_sizes[f] = sz
                total_bytes += sz
            except OSError:
                file_sizes[f] = 0

    # 3. Create temporary directories for staging inside the Vault parent directory
    # Acquire lockfile to prevent concurrent backups
    lock_file_path = os.path.join(OCTO_DIR, "backup.lock")
    try:
        # Open/Create lock file and keep active reference in local scope
        global lock_file
        lock_file = open(lock_file_path, "w")
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("another backup instance is already running, aborting")
        return
    except Exception as e:
        print(f"failed to acquire backup lock: {e}")
        return

    vault_parent = os.path.dirname(vault_path)
    os.makedirs(vault_parent, exist_ok=True)
    temp_vault = os.path.join(vault_parent, ".octo_temp_vault")
    temp_packages = os.path.join(vault_parent, ".octo_temp_packages")

    # Track active temporary directories globally for signal handler cleanup
    global active_temp_dirs
    active_temp_dirs.clear()
    active_temp_dirs.extend([temp_vault, temp_packages])

    # Check available disk space
    try:
        stat_v = os.statvfs(vault_parent)
        free_space = stat_v.f_frsize * stat_v.f_bavail
        required_space = int(total_bytes * 1.5) + 100 * 1024 * 1024
        if free_space < required_space:
            print(f"error: insufficient disk space on vault drive (required: {format_bytes(required_space)}, available: {format_bytes(free_space)})")
            return
    except Exception as e:
        print(f"warning: could not verify available disk space: {e}")

    shutil.rmtree(temp_vault, ignore_errors=True)
    shutil.rmtree(temp_packages, ignore_errors=True)
    os.makedirs(temp_vault, exist_ok=True)
    os.makedirs(temp_packages, exist_ok=True)

    checksums = {}  # block_id -> sha1_hash
    new_manifest = {}

    # Load old manifest and checksums if they exist in the current Vault
    old_manifest = {}
    old_checksums = {}
    manifest_path_old = os.path.join(vault_path, "manifest.json")
    checksums_path_old = os.path.join(vault_path, "checksums.json")

    if os.path.exists(manifest_path_old):
        try:
            with open(manifest_path_old, "r") as f:
                old_manifest = json.load(f)
        except Exception:
            pass

    if os.path.exists(checksums_path_old):
        try:
            with open(checksums_path_old, "r") as f:
                old_checksums = json.load(f)
        except Exception:
            pass

    start_time = time.time()
    total_bytes_copied = 0

    # Save log level and lower to WARNING temporarily so status bar controls stdout
    root_logger = logging.getLogger()
    old_level = root_logger.level
    root_logger.setLevel(logging.WARNING)

    try:
        # 4. Copy, compress, and calculate checksums for each block
        for block_id, files in block_files.items():
            local_total_bytes = sum(file_sizes[f] for f in files)

            # Check if block is unchanged
            is_unchanged = False
            archive_path_old = os.path.join(vault_path, f"{block_id}.tar.gz")
            if (
                os.path.exists(archive_path_old)
                and block_id in old_manifest
                and block_id in old_checksums
            ):
                manifest_entry = old_manifest[block_id]
                manifest_files = manifest_entry.get("files", {})

                # Check if exact set of files matches
                if set(files) == set(manifest_files.keys()):
                    files_match = True
                    for f in files:
                        try:
                            stat = os.stat(f)
                            mtime_diff = abs(stat.st_mtime - manifest_files[f]["mtime"])
                            if stat.st_size != manifest_files[f]["size"] or mtime_diff > 0.01:
                                files_match = False
                                break
                        except Exception:
                            files_match = False
                            break

                    if files_match:
                        try:
                            archive_stat = os.stat(archive_path_old)
                            if archive_stat.st_size == manifest_entry.get("archive_size", 0):
                                is_unchanged = True
                        except Exception:
                            pass

            if is_unchanged:
                # Update status bar before copy
                elapsed_total = time.time() - start_time
                if total_bytes_copied > 0 and elapsed_total > 0.1:
                    speed_total = total_bytes_copied / elapsed_total
                    remaining_bytes_total = total_bytes - total_bytes_copied
                    est_total = remaining_bytes_total / speed_total
                else:
                    speed_total = None
                    est_total = None

                draw_status_bar(
                    total_bytes_copied, total_bytes, est_total, speed_total,
                    local_total_bytes, local_total_bytes,
                    f"Skipping {block_id} (unchanged)"
                )

                # Copy existing archive file to temp packages
                compressed_archive = os.path.join(temp_packages, f"{block_id}.tar.gz")
                shutil.copy2(archive_path_old, compressed_archive)

                # Retain old metadata
                checksums[block_id] = old_checksums[block_id]
                new_manifest[block_id] = old_manifest[block_id]

                total_bytes_copied += local_total_bytes
                continue

            # Standard copy
            block_temp_dir = os.path.join(temp_vault, block_id)
            os.makedirs(block_temp_dir, exist_ok=True)

            local_bytes_copied = 0
            local_start_time = time.time()

            # Copy block files mirroring absolute paths
            for f in files:
                rel_path = f.lstrip(os.sep)
                dest_f = os.path.join(block_temp_dir, rel_path)

                current_file_name = os.path.basename(f)
                if len(current_file_name) > 25:
                    current_file_name = current_file_name[:22] + "..."

                # Calculate time estimations
                elapsed_total = time.time() - start_time
                if total_bytes_copied > 0 and elapsed_total > 0.1:
                    speed_total = total_bytes_copied / elapsed_total
                    remaining_bytes_total = total_bytes - total_bytes_copied
                    est_total = remaining_bytes_total / speed_total
                else:
                    speed_total = None
                    est_total = None

                draw_status_bar(
                    total_bytes_copied, total_bytes, est_total, speed_total,
                    local_bytes_copied, local_total_bytes,
                    f"Copying {current_file_name}"
                )

                engine.controller.copy_to(f, dest_f, quiet=True)

                # Add progress
                sz = file_sizes[f]
                local_bytes_copied += sz
                total_bytes_copied += sz

            # Compression stage status update
            elapsed_total = time.time() - start_time
            if total_bytes_copied > 0 and elapsed_total > 0.1:
                speed_total = total_bytes_copied / elapsed_total
                remaining_bytes_total = total_bytes - total_bytes_copied
                est_total = remaining_bytes_total / speed_total
            else:
                speed_total = None
                est_total = None

            draw_status_bar(
                total_bytes_copied, total_bytes, est_total, speed_total,
                local_bytes_copied, local_total_bytes,
                "Compressing..."
            )

            compressed_archive = os.path.join(temp_packages, f"{block_id}.tar.gz")

            subdirs = os.listdir(block_temp_dir)
            if not subdirs:
                continue

            command = [
                "tar",
                "-cvzf",
                compressed_archive,
                "-C",
                block_temp_dir,
            ] + subdirs

            import subprocess
            from queue import Queue, Empty
            from threading import Thread

            try:
                env = os.environ.copy()
                gzip_level = -1
                if engine.config.configuration and "storage" in engine.config.configuration:
                    gzip_level = engine.config.configuration["storage"].get("gzip_level", -1)
                env["GZIP"] = str(gzip_level)

                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    env=env,
                    text=True
                )

                # Set up non-blocking stdout reading using a daemon thread and Queue
                output_queue = Queue()
                def read_stdout(stream, queue):
                    try:
                        for line in stream:
                            queue.put(line.strip())
                    except Exception:
                        pass
                    finally:
                        try:
                            stream.close()
                        except Exception:
                            pass

                reader_thread = Thread(target=read_stdout, args=(process.stdout, output_queue))
                reader_thread.daemon = True
                reader_thread.start()

                spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                spin_idx = 0
                current_file = ""

                while process.poll() is None:
                    # Drain queue to get the latest file being compressed
                    while True:
                        try:
                            line = output_queue.get_nowait()
                            if line:
                                current_file = os.path.basename(line)
                                if len(current_file) > 25:
                                    current_file = current_file[:22] + "..."
                        except Empty:
                            break

                    try:
                        compressed_bytes = os.path.getsize(compressed_archive)
                    except OSError:
                        compressed_bytes = 0
                    compressed_str = format_bytes(compressed_bytes)

                    elapsed_total = time.time() - start_time
                    if total_bytes_copied > 0 and elapsed_total > 0.1:
                        speed_total = total_bytes_copied / elapsed_total
                        remaining_bytes_total = total_bytes - total_bytes_copied
                        est_total = remaining_bytes_total / speed_total
                    else:
                        speed_total = None
                        est_total = None

                    action_str = f"Compressing {spinner[spin_idx]} ({compressed_str})"
                    if current_file:
                        action_str += f" - {current_file}"

                    draw_status_bar(
                        total_bytes_copied, total_bytes, est_total, speed_total,
                        local_bytes_copied, local_total_bytes,
                        action_str
                    )
                    spin_idx = (spin_idx + 1) % len(spinner)
                    time.sleep(0.1)

                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, command)

                # Calculate and store checksum
                sha = calculate_sha1(compressed_archive)
                if sha:
                    checksums[block_id] = sha

                # Store block manifest
                try:
                    archive_size = os.path.getsize(compressed_archive)
                except OSError:
                    archive_size = 0

                block_manifest_files = {}
                for f in files:
                    try:
                        stat = os.stat(f)
                        block_manifest_files[f] = {
                            "size": stat.st_size,
                            "mtime": stat.st_mtime
                        }
                    except Exception:
                        pass

                new_manifest[block_id] = {
                    "files": block_manifest_files,
                    "archive_size": archive_size
                }

            except Exception as e:
                import sys
                sys.stdout.write("\n")
                root_logger.setLevel(old_level)
                print(f"error: failed to compress block {block_id}: {e}")
                shutil.rmtree(temp_vault, ignore_errors=True)
                shutil.rmtree(temp_packages, ignore_errors=True)
                return

        # Finished loop: print newline and restore logger
        import sys
        sys.stdout.write("\n")
        root_logger.setLevel(old_level)

    except Exception as e:
        import sys
        sys.stdout.write("\n")
        root_logger.setLevel(old_level)
        print(f"error: during copy loop: {e}")
        return

    # Write the checksums JSON file inside the temp_packages staging dir
    checksums_path = os.path.join(temp_packages, "checksums.json")
    try:
        with open(checksums_path, "w") as f:
            json.dump(checksums, f)
    except Exception as e:
        print(f"error: failed to save checksums: {e}")
        shutil.rmtree(temp_vault, ignore_errors=True)
        shutil.rmtree(temp_packages, ignore_errors=True)
        return

    # Write the manifest.json inside the temp_packages staging dir
    manifest_path = os.path.join(temp_packages, "manifest.json")
    try:
        with open(manifest_path, "w") as f:
            json.dump(new_manifest, f)
    except Exception as e:
        print(f"error: failed to save manifest: {e}")
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

        print("backup successfully completed")
    except Exception as e:
        print(f"error: replacing vault files: {e}")
        # Try to rollback if old vault was moved
        if os.path.exists(backup_vault_path):
            shutil.rmtree(vault_path, ignore_errors=True)
            shutil.move(backup_vault_path, vault_path)
    finally:
        # Explicitly terminate subprocess to prevent deallocator warnings on exit
        if 'process' in locals() and process and process.poll() is None:
            try:
                process.kill()
                process.wait()
            except Exception:
                pass
        # Restore logger in finally just to be absolutely safe
        root_logger.setLevel(old_level)
        # 6. Clean up temp directories
        shutil.rmtree(temp_vault, ignore_errors=True)
        shutil.rmtree(temp_packages, ignore_errors=True)
