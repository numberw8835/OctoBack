import logging
import os
import subprocess
import tarfile

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


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

    def compare_paths(self, pathA: str, pathB: str) -> tuple[list[str], list[str]]:
        """
        Compares two paths by splitting them into individual directory/file components.
        Returns the remaining non-matching components of each path.

        Returns:
            A tuple containing two lists:
                - components of pathA that differ from pathB.
                - components of pathB that differ from pathA.
        """

        # Split paths into components based on directory separator
        split_path_A = pathA.split("/")
        split_path_B = pathB.split("/")

        logging.info(f"Comparing path A: {pathA} and path B: {pathB}")

        # Find the length of the shorter path to prevent index bounds issues
        min_len = min(len(split_path_A), len(split_path_B))

        # Compare components index by index up to the length of the shorter path
        for i in range(min_len):
            if split_path_A[i] != split_path_B[i]:
                logging.info(
                    f"First mismatch at index {i}: Path A component {split_path_A[i]} vs Path B component {split_path_B[i]}"
                )
                return (split_path_A[i:], split_path_B[i:])

        # Return any remaining unmatched trailing components for unequal-length paths
        logging.info("Paths are identical up to the common prefix.")
        return (split_path_A[min_len:], split_path_B[min_len:])

    def copy_to(self, pathA: str, pathB: str, quiet: bool = False) -> bool:
        """
        Copies files from pathA to pathB using rsync.
        Uses --ignore-existing to ensure files already present at destination are not copied again.

        :param pathA: The source path
        :param pathB: The destination path
        :param quiet: If True, redirects outputs and suppresses logging messages
        :return: True if copying was successful, False otherwise
        """
        # Verify that the source path exists
        if not os.path.exists(pathA):
            if not quiet:
                logging.error(f"Source {pathA} does not exist.")
            return False

        # Ensure the parent directory structure of the destination exists or create it
        dest_dir = os.path.dirname(pathB)
        if not os.path.exists(dest_dir):
            try:
                os.makedirs(dest_dir)
                if not quiet:
                    logging.info(f"Created destination directory: {dest_dir}")
            except OSError as e:
                if not quiet:
                    logging.error(f"Failed to create destination directory {dest_dir}: {e}")
                return False

        # Build the rsync command. Append a trailing slash if copying a directory.
        src = f"{pathA}/" if os.path.isdir(pathA) else pathA
        if quiet:
            command = ["rsync", "-aH", "--ignore-existing", src, pathB]
        else:
            command = ["rsync", "-avhH", "--ignore-existing", "--info=progress2", src, pathB]

        try:
            # Execute the rsync subprocess
            if quiet:
                subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            else:
                subprocess.run(command, check=True)
                logging.info(f"Copy successful from {pathA} to {pathB}")
            return True
        except subprocess.CalledProcessError as e:
            if not quiet:
                logging.error(
                    f"Failed to copy from {pathA} to {pathB}: Command '{' '.join(command)}' returned non-zero exit status {e.returncode}."
                )
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
