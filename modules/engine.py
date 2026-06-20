import json
import logging
import os

from modules.util.config import Config
from modules.util.controller import Controller

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Engine:
    def __init__(self) -> None:
        self.index = set()  # set of absolute paths
        self.config = Config()
        self.controller = Controller()

    def to_portable_path(self, path: str) -> str:
        """
        Converts absolute home-directory paths to portable '~/'-relative paths.
        """
        abs_path = os.path.abspath(path)
        home = os.path.expanduser("~")
        if abs_path == home:
            return "~"
        if abs_path.startswith(home + os.sep):
            return "~" + abs_path[len(home):]
        return abs_path

    def from_portable_path(self, path: str) -> str:
        """
        Converts portable '~/'-relative paths to absolute home-directory paths.
        """
        if path == "~":
            return os.path.expanduser("~")
        if path.startswith("~" + os.sep):
            return os.path.expanduser("~") + path[1:]
        return os.path.abspath(path)

    def add_folder_to_index(self, directory: str):
        """
        Adds a folder/file to the index.
        """
        abs_path = os.path.abspath(directory)
        if abs_path in self.index:
            logging.info(f"Path {directory} already indexed.")
        else:
            self.index.add(abs_path)
            logging.info(f"Path {directory} added to index.")

    def update_index(self, stuff: set):
        """
        Updates the index with new files.
        """
        new_files = stuff - self.index
        if not new_files:
            logging.info("No new files to add to the index.")
        else:
            for f in new_files:
                self.index.add(f)

    def remove_from_index(self, path: str) -> bool:
        """
        Removes a path (file or folder) and its children from the index.
        Returns True if any entries were removed, False otherwise.
        """
        abs_target = os.path.abspath(path)
        initial_len = len(self.index)

        self.index = {
            indexed_path
            for indexed_path in self.index
            if not (indexed_path == abs_target or indexed_path.startswith(abs_target + os.sep))
        }

        removed_count = initial_len - len(self.index)
        if removed_count > 0:
            logging.info(f"Removed {removed_count} entries matching '{path}' from the index.")
            return True
        else:
            logging.info(f"No entries matching '{path}' found in the index.")
            return False

    def save_index(self, path):
        """
        Writes the index to a file on disk.
        """
        try:
            dir_name = os.path.dirname(path)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)
            tmp_path = path + ".tmp"
            
            # Serialize to portable paths
            portable_data = [self.to_portable_path(p) for p in self.index]

            with open(tmp_path, "w") as f:
                json.dump(portable_data, f)
            os.replace(tmp_path, path)
            logging.info(f"Index written to {path} successfully.")
        except Exception as e:
            logging.error(f"Error writing index to {path}: {e}")

    def load_index(self, path):
        """
        Loads the index from a file on disk with backwards compatibility.
        """
        try:
            with open(path, "r") as f:
                data = json.load(f)
                self.index.clear()
                for item in data:
                    if isinstance(item, str):
                        abs_p = self.from_portable_path(item)
                        self.index.add(abs_p)
                    elif isinstance(item, (list, tuple)) and len(item) >= 1:
                        abs_p = self.from_portable_path(item[0])
                        self.index.add(abs_p)
            logging.info(f"Index loaded from {path} successfully.")
        except Exception as e:
            logging.error(f"Error loading index from {path}: {e}")
