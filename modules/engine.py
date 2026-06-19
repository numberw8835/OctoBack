import json
import logging
import os
import subprocess

import yaml

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class engine:
    def __init__(self) -> None:
        self.index = set()
        self.config = dict()

    def scan_folder(self, directory: str):
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

    def write_index_to_disk(self):
        """
        Writes the index to a file on disk.
        """
        path = self.config["storage"]["index_path"]
        try:
            with open(path, "w") as f:
                json.dump(list(self.index), f)
            logging.info(f"Index written to {path} successfully.")
        except Exception as e:
            logging.error(f"Error writing index to {path}: {e}")

    def load_index_from_disk(self):
        """
        Loads the index from a file on disk.
        """
        path = self.config["storage"]["index_path"]
        try:
            with open(path, "r") as f:
                self.index.update(json.load(f))
            logging.info(f"Index loaded from {path} successfully.")
        except Exception as e:
            logging.error(f"Error loading index from {path}: {e}")

    def load_config(self, path: str):
        """
        Loads the YAML config from the given path.
        """
        try:
            with open(path, "r") as f:
                self.config = yaml.safe_load(f)
            logging.info(f"Config loaded from {path} successfully.")
        except Exception as e:
            logging.error(f"Error loading config from {path}: {e}")

    def save_config(self, path: str):
        """
        Saves the current config to a YAML file at the given path.
        """
        try:
            with open(path, "w") as f:
                yaml.safe_dump(self.config, f)
            logging.info(f"Config saved to {path} successfully.")
        except Exception as e:
            logging.error(f"Error saving config from {path}: {e}")
