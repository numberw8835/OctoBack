import os

from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine

engine = Engine()


def add_to_index(paths, granular=False):
    # Load configuration settings; check environment is initialized
    if not engine.config.load_config(DEFAULT_CONFIG):
        print("config file not found, please run 'octoback init' first.")
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
            print(f"added file directly from {path} to the index")
        else:
            abs_path = os.path.abspath(path)
            if abs_path in engine.index:
                print(f"{path} is already in the index")
            else:
                engine.add_folder_to_index(path)
                print(f"added {path} to the index")

    # Persist changes to the index.json file
    engine.save_index(index_path)
    print("index has been successfully saved")
