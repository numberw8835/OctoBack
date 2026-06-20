import logging
import os
import subprocess
import tarfile

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Controller:
    def scan_folder_for_files(self, directory: str):
        """
        Scans a directory and returns all the files.
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
        Compares two paths and returns the unmatched components.

        Returns:
            A tuple containing two lists:
                - The first list contains the remaining components of pathA that are not in common with pathB.
                - The second list contains the remaining components of pathB that are not in common with pathA.
        """

        # Split paths into components
        split_path_A = pathA.split("/")
        split_path_B = pathB.split("/")

        # Log the paths being compared
        logging.info(f"Comparing path A: {pathA} and path B: {pathB}")

        # Find the length of the shorter path
        min_len = min(len(split_path_A), len(split_path_B))

        # Compare components up to the length of the shorter path
        for i in range(min_len):
            if split_path_A[i] != split_path_B[i]:
                logging.info(
                    f"First mismatch at index {i}: Path A component {split_path_A[i]} vs Path B component {split_path_B[i]}"
                )
                return (split_path_A[i:], split_path_B[i:])

        # Return any remaining unmatched components for unequal-length paths
        logging.info("Paths are identical up to the common prefix.")
        return (split_path_A[min_len:], split_path_B[min_len:])

    def copy_to(self, pathA: str, pathB: str, quiet: bool = False) -> bool:
        """
        Copies files from pathA to pathB using rsync.
        Ensures no recopying if the destination already has the same files.

        :param pathA: The source path
        :param pathB: The destination path
        :param quiet: If True, suppresses output and logging
        :return: True if copying was successful, False otherwise
        """
        # Ensure the source exists
        if not os.path.exists(pathA):
            if not quiet:
                logging.error(f"Source {pathA} does not exist.")
            return False

        # Ensure the destination directory exists or create it
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

        # Determine the rsync command
        src = f"{pathA}/" if os.path.isdir(pathA) else pathA
        if quiet:
            command = ["rsync", "-aH", "--ignore-existing", src, pathB]
        else:
            command = ["rsync", "-avhH", "--ignore-existing", "--info=progress2", src, pathB]

        try:
            # Run the rsync command for copying
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
        Compresses the specified directory using tar.

        :param path: The path to the directory to be compressed
        :return: The path to the compressed file if compression was successful, raises an error otherwise
        """
        # Ensure the source directory exists
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            logging.error(f"Source directory {abs_path} does not exist.")
            raise FileNotFoundError(f"Source directory {abs_path} does not exist.")

        # Determine a valid destination path
        dest_dir = os.path.dirname(abs_path)
        if not os.access(dest_dir, os.W_OK):
            logging.error(f"Destination directory {dest_dir} is not writable.")
            raise PermissionError(f"Destination directory {dest_dir} is not writable.")

        # Construct the tar command
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
            # Run the tar command for compression
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
        Extracts a target (file or folder) from a .tar.gz archive to dest
        without preserving the top-level parent paths.
        """
        if not os.path.exists(path_to_tar):
            logging.error(f"Archive {path_to_tar} does not exist.")
            return False

        try:
            with tarfile.open(path_to_tar, "r:gz") as tar:
                # Normalize target path to strip any trailing slashes
                target_norm = target.rstrip("/")
                members_to_extract = []

                # Collect everything that matches the target file or lives inside the target folder
                for member in tar.getmembers():
                    if member.name == target_norm or member.name.startswith(
                        target_norm + "/"
                    ):
                        members_to_extract.append(member)

                if not members_to_extract:
                    logging.error(f"Target '{target}' not found in archive.")
                    return False

                abs_dest = os.path.abspath(dest)
                os.makedirs(abs_dest, exist_ok=True)

                # Determine the parent path we want to strip away (e.g., 'modules' from 'modules/util')
                parent_dir = os.path.dirname(target_norm)

                for member in members_to_extract:
                    # Rewrite the internal path so it drops neatly right into dest
                    if parent_dir:
                        member.name = os.path.relpath(member.name, parent_dir)

                    # Prevent Directory Traversal / Zip Slip vulnerability
                    target_path = os.path.abspath(os.path.join(abs_dest, member.name))
                    if os.path.commonpath([abs_dest, target_path]) != abs_dest:
                        logging.error(f"Path traversal attempt blocked: {member.name}")
                        return False

                    # Native extract handles both files and folders automatically
                    tar.extract(member, path=abs_dest)

                logging.info(f"Successfully extracted '{target}' to '{dest}'")
                return True

        except Exception as e:
            logging.error(f"Failed to extract {target} from {path_to_tar}: {e}")
            return False
