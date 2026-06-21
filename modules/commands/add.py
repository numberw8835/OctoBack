import os
from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine

engine = Engine()


def add_to_index(paths, granular=False):
    # Load configuration settings; check environment is initialized
    if not engine.config.load_config(DEFAULT_CONFIG):
        print("error: config file not found, please run 'octoback init' first.")
        return
    index_path = engine.config.configuration["storage"]["index_path"]

    # Load the existing index database file if it exists
    if os.path.exists(index_path):
        engine.load_index(index_path)

    for path in paths:
        # If --granular (-g) flag is set, recursively scan the folder to index all individual files.
        # Benefit: Allows selecting/restoring specific files in interactive TUI restore mode.
        # Drawback: Newly created files inside this folder won't be automatically tracked.
        if granular:
            files = engine.controller.scan_folder_for_files(path)
            engine.update_index(files)
            print(f"granularly added files from {path} to the index")
        # Default behavior: Index the directory path itself as a single unit.
        # Benefit: Dynamically tracks and backs up any future files added to the folder.
        # Drawback: The folder must be restored as a whole in the TUI restore mode.
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
