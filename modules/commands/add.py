import os
from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine

engine = Engine()


def add_to_index(paths, recursive=False):
    if not engine.config.load_config(DEFAULT_CONFIG):
        print("error: config file not found, please run 'octoback init' first.")
        return
    index_path = engine.config.configuration["storage"]["index_path"]

    if os.path.exists(index_path):
        engine.load_index(index_path)

    for path in paths:
        if recursive:
            files = engine.controller.scan_folder_for_files(path)
            engine.update_index(files)
            print(f"recursively added files from {path} to the index")
        else:
            abs_path = os.path.abspath(path)
            if abs_path in engine.index:
                print(f"{path} is already in the index")
            else:
                engine.add_folder_to_index(path)
                print(f"added {path} to the index")

    engine.save_index(index_path)
    print("index has been successfully saved")
