import logging
import os
import re
import subprocess
import tarfile


class Controller:
    """
    Executes file system operations including recursive directories scanning,
    path comparisons, copying files using rsync, and tar archive compression/decompression.
    """

    def scan_folder_for_files(self, directory: str):
        """
        Scans a directory recursively and returns absolute paths of all files found.
        Uses os.walk for nested file traversal.
        """
        stuff = set()
        try:
            for paths, _, files in os.walk(directory):
                for file in files:
                    stuff.add(os.path.abspath(os.path.join(paths, file)))
        except Exception as e:
            logging.error(f"Error scanning directory {directory}: {e}")
        return stuff

    def copy_to(self, pathA: str, pathB: str, progress_callback=None):
        """
        Copies source A to destination B, using rsync.
        Supports a callback for real-time percentage updates from rsync's progress2 output.
        """

        # Verify that the source path exists

        if not os.path.exists(pathA):
            logging.error(f"Source {pathA} does not exist.")
            return False

        logging.info(f"source {pathA} located")

        # Ensure the parent directory structure of the destination exists or create it

        dest_dir = os.path.dirname(pathB)
        if not os.path.exists(dest_dir):
            try:
                os.makedirs(dest_dir, exist_ok=True)
                logging.info(f"Created destination directory: {dest_dir}")
            except OSError as e:
                logging.error(f"Failed to create destination: {e}")
                return False

        logging.info(f"destination {dest_dir} located")

        # Build the rsync command. Append a trailing slash if copying a directory.

        src = f"{pathA}/" if os.path.isdir(pathA) else pathA
        command = [
            "rsync",
            "-avH",
            "--info=progress2",
            src,
            pathB,
        ]

        # Regex fallback to capture the percentage from rsync --info=progress2 output (e.g., " 45%")
        progress_re = re.compile(r"(\d+)%")

        try:
            # Use Popen to read stdout line-by-line while the process is running
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            files_transferred = 0
            for line in process.stdout or []:
                xfr_match = re.search(r"xfr#(\d+)", line)
                if xfr_match:
                    files_transferred = max(files_transferred, int(xfr_match.group(1)))

                if progress_callback:
                    parts = line.strip().split()
                    if len(parts) >= 2 and parts[1].endswith("%") and parts[1][:-1].isdigit():
                        try:
                            # Parse raw byte number and percentage from progress2 output
                            size_str = parts[0].upper()
                            units = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
                            if size_str and size_str[-1] in units:
                                curr_bytes = int(float(size_str[:-1]) * units[size_str[-1]])
                            else:
                                curr_bytes = int(float(size_str.replace(",", "")))
                            pct = int(parts[1][:-1])
                            percent = pct / 100.0
                            total_bytes = int(curr_bytes * 100 / pct) if pct > 0 else 0
                            progress_callback(percent, curr_bytes, total_bytes)
                        except Exception:
                            # Fallback if raw parse fails
                            match = progress_re.search(line)
                            if match:
                                percent = float(match.group(1)) / 100.0
                                progress_callback(percent, 0, 0)
                    else:
                        match = progress_re.search(line)
                        if match:
                            percent = float(match.group(1)) / 100.0
                            progress_callback(percent, 0, 0)

            process.wait()

            if progress_callback:
                progress_callback(1.0)
            if process.returncode == 0:
                logging.info(f"copy successful from {pathA} to {pathB}")
                return True
            else:
                logging.error(f"rsync failed with exit code {process.returncode}")
                return False

        except Exception as e:
            logging.error(f"Error during rsync execution: {e}")
            return False

    def compress(self, path: str) -> str:
        """
        Compresses the specified directory into a .tar.gz archive using system tar.

        :param path: The path to the directory to be compressed
        :return: The absolute path to the compressed file if successful, raises an exception otherwise
        """
        # Validate that the source path exists
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            logging.error(f"Source directory {abs_path} does not exist.")
            raise FileNotFoundError(f"Source directory {abs_path} does not exist.")

        # Ensure that the destination directory is writable
        dest_dir = os.path.dirname(abs_path)
        if not os.access(dest_dir, os.W_OK):
            logging.error(f"Destination directory {dest_dir} is not writable.")
            raise PermissionError(f"Destination directory {dest_dir} is not writable.")

        # Construct the tar compression command (-czf: compress, gzip, file output)
        base_name = os.path.basename(abs_path)
        compressed_path = os.path.join(dest_dir, f"{base_name}.tar.gz")
        command = [
            "tar",
            "-czf",
            compressed_path,
            "-C",
            os.path.dirname(abs_path),
            base_name,
        ]

        logging.info(f"Running compression command: {' '.join(command)}")
        try:
            # Run the compression subprocess
            subprocess.run(command, check=True)
            logging.info(f"Compression successful: {compressed_path}")
            return compressed_path
        except subprocess.CalledProcessError as e:
            logging.error(
                f"Failed to compress {abs_path}: Command '{' '.join(command)}' returned non-zero exit status {e.returncode}."
            )
            raise RuntimeError(
                f"Failed to compress {abs_path}: Command '{' '.join(command)}' returned non-zero exit status {e.returncode}."
            )

    def uncompress(self, path_to_tar: str, target: str, dest: str) -> bool:
        """
        Extracts a target file or directory from a .tar.gz archive to dest.
        Strips top-level parent paths and protects against Directory Traversal (Zip Slip).
        """
        # Ensure that the target tar archive exists
        if not os.path.exists(path_to_tar):
            logging.error(f"Archive {path_to_tar} does not exist.")
            return False

        try:
            with tarfile.open(path_to_tar, "r:gz") as tar:
                # Normalize target path to strip any trailing slashes
                target_norm = target.rstrip("/")
                members_to_extract = []

                # Find all files inside the archive matching the target query
                for member in tar.getmembers():
                    if member.name == target_norm or member.name.startswith(
                        target_norm + "/"
                    ):
                        members_to_extract.append(member)

                if not members_to_extract:
                    logging.error(f"Target '{target}' not found in archive.")
                    return False

                # Ensure output destination directory exists
                abs_dest = os.path.abspath(dest)
                os.makedirs(abs_dest, exist_ok=True)

                # Find parent path of target to omit it during relative extraction
                parent_dir = os.path.dirname(target_norm)

                for member in members_to_extract:
                    # Rewrite the member extraction path to drop cleanly into dest directory
                    if parent_dir:
                        member.name = os.path.relpath(member.name, parent_dir)

                    # Security Mitigation: Prevent Directory Traversal / Zip Slip vulnerability
                    # Verify that the final resolved absolute path lies within the destination folder
                    target_path = os.path.abspath(os.path.join(abs_dest, member.name))
                    if os.path.commonpath([abs_dest, target_path]) != abs_dest:
                        logging.error(f"Path traversal attempt blocked: {member.name}")
                        return False

                    # Extract the member natively
                    tar.extract(member, path=abs_dest)

                logging.info(f"Successfully extracted '{target}' to '{dest}'")
                return True

        except Exception as e:
            logging.error(f"Failed to extract {target} from {path_to_tar}: {e}")
            return False

