import json
import logging
import os

from modules.util.config import Config
from modules.util.controller import Controller

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class TrieNode:
    def __init__(self, name):
        self.name = name
        self.files = []
        self.children = {}
        self.total_size = 0


class Engine:
    def __init__(self) -> None:
        self.index = set()  # set of (path, block_id) tuples
        self.config = Config()
        self.controller = Controller()

    def add_folder_to_index(self, directory: str):
        """
        Adds a folder to the index.
        """
        abs_path = os.path.abspath(directory)
        exists = any(path == abs_path for path, _ in self.index)
        if exists:
            logging.info(f"Directory {directory} already indexed.")
        else:
            self.index.add((abs_path, None))
            logging.info(f"Directory {directory} added to index.")

    def update_index(self, stuff: set):
        """
        Updates the index with new files.
        """
        existing_paths = {path for path, _ in self.index}
        new_files = stuff - existing_paths
        if not new_files:
            logging.info("No new files to add to the index.")
        else:
            for f in new_files:
                self.index.add((f, None))

    def partition_directory(self, dir_path, threshold):
        # 1. Collect all files under dir_path
        all_files = []
        for root_dir, _, files in os.walk(dir_path):
            for f in files:
                fp = os.path.abspath(os.path.join(root_dir, f))
                try:
                    all_files.append((fp, os.path.getsize(fp)))
                except OSError:
                    continue

        # 2. If total size <= threshold, keep the entire directory as one block
        total_size = sum(sz for _, sz in all_files)
        if total_size <= threshold:
            block_id = "block_" + dir_path.strip("/").replace("/", "_")
            return [(dir_path, block_id)]

        # 3. Build Trie of the files relative to dir_path
        root = TrieNode(os.path.basename(dir_path))
        root.total_size = total_size

        for fp, sz in all_files:
            rel = os.path.relpath(fp, os.path.dirname(dir_path))
            parts = rel.split("/")
            curr = root
            for part in parts[1:-1]:
                if part not in curr.children:
                    curr.children[part] = TrieNode(part)
                curr = curr.children[part]
                curr.total_size += sz
            curr.files.append((fp, sz))

        # 4. Recursively partition the Trie
        partitions = []

        def recurse(node, current_abs_path):
            if node.total_size <= threshold:
                block_id = "block_" + current_abs_path.strip("/").replace("/", "_")
                node_files = []
                def collect(n):
                    for f, _ in n.files:
                        node_files.append(f)
                    for child in n.children.values():
                        collect(child)
                collect(node)
                if node_files:
                    partitions.append((current_abs_path, block_id))
                return

            # Split: process children
            remainder_files = [f for f, _ in node.files]
            for child_name, child_node in node.children.items():
                child_abs_path = os.path.join(current_abs_path, child_name)
                if child_node.total_size > threshold:
                    recurse(child_node, child_abs_path)
                else:
                    child_files = []
                    def collect(n):
                        for f, _ in n.files:
                            child_files.append(f)
                        for child in n.children.values():
                            collect(child)
                    collect(child_node)
                    if child_files:
                        block_id = "block_" + child_abs_path.strip("/").replace("/", "_")
                        partitions.append((child_abs_path, block_id))

            if remainder_files:
                block_id = "block_" + current_abs_path.strip("/").replace("/", "_") + "_remainder"
                partitions.append((current_abs_path, block_id))

        recurse(root, dir_path)
        return partitions

    def repartition_index(self, threshold=50 * 1024 * 1024):
        paths_to_partition = {path for path, _ in self.index}
        new_mappings = set()
        for path in paths_to_partition:
            if not os.path.exists(path):
                continue
            if os.path.isdir(path):
                partitions = self.partition_directory(path, threshold)
                for sub_path, block_id in partitions:
                    new_mappings.add((sub_path, block_id))
            else:
                block_id = "block_" + path.strip("/").replace("/", "_")
                new_mappings.add((path, block_id))
        self.index = new_mappings

    def save_index(self, path):
        """
        Writes the index to a file on disk.
        """
        self.repartition_index()
        try:
            with open(path, "w") as f:
                json.dump(list(self.index), f)
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
                        self.index.add((item, None))
                    elif isinstance(item, (list, tuple)) and len(item) == 2:
                        self.index.add(tuple(item))
            logging.info(f"Index loaded from {path} successfully.")
        except Exception as e:
            logging.error(f"Error loading index from {path}: {e}")
