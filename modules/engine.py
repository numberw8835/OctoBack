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
        self.index = set()
        self.config = Config()
        self.controller = Controller()

    def add_folder_to_index(self, directory: str):
        """
        Adds a folder to the index.
        """
        abs_path = os.path.abspath(directory)
        if abs_path in self.index:
            logging.info(f"Directory {directory} already indexed.")
        else:
            self.index.add(abs_path)
            logging.info(f"Directory {directory} added to index.")

    def update_index(self, stuff: set):
        """
        Updates the index with new files.
        """
        new_files = stuff - self.index
        if not new_files:
            logging.info("No new files to add to the index.")
        else:
            self.index.update(new_files)

    def save_index(self, path):
        """
        Writes the index to a file on disk.
        """
        try:
            with open(path, "w") as f:
                json.dump(list(self.index), f)
            logging.info(f"Index written to {path} successfully.")
        except Exception as e:
            logging.error(f"Error writing index to {path}: {e}")

    def load_index(self, path):
        """
        Loads the index from a file on disk.
        """
        try:
            with open(path, "r") as f:
                self.index.update(json.load(f))
            logging.info(f"Index loaded from {path} successfully.")
        except Exception as e:
            logging.error(f"Error loading index from {path}: {e}")
