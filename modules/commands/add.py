import os

from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine
from modules.ui import print_success, print_info, print_error

engine = Engine()


def add_to_index(paths, granular=False):
    # Load configuration settings; check environment is initialized
    if not engine.config.load_config(DEFAULT_CONFIG):
        print_error("Configuration file not found. Please run 'octoback init' first.")
        return
    index_path = engine.config.configuration["storage"]["index_path"]

    # Load the existing index database file if it exists
    if os.path.exists(index_path):
        engine.load_index(index_path)

    for path in paths:
        if granular and os.path.isdir(path):
            files = engine.controller.scan_folder_for_files(path)
            files = {os.path.abspath(f) for f in files}
            engine.update_index(files)
            print_success(f"Added granular files from {path}")
        else:
            abs_path = os.path.abspath(os.path.expanduser(path))
            if abs_path in engine.index:
                print_info(f"{path} is already in the index")
            else:
                engine.add_folder_to_index(path)
                print_success(f"Added {path}")

    # Persist changes to the index.json file
    engine.save_index(index_path)
