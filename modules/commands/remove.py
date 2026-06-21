import os

from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine

engine = Engine()


def remove_from_index(paths):
    """
    Removes specified files or folders (and their sub-items) from the backup index.
    Updates index.json with the changes.
    """
    # Load settings configuration to get index_path location
    if not engine.config.load_config(DEFAULT_CONFIG):
        print("error: config file not found, please run 'octoback init' first.")
        return
    index_path = engine.config.configuration["storage"]["index_path"]

    # Load existing indexed items from index.json
    if os.path.exists(index_path):
        engine.load_index(index_path)
    else:
        print("index file does not exist")
        return

    any_removed = False
    for path in paths:
        initial_len = len(engine.index)
        # Call remove_from_index helper on engine which handles prefix/child path matching
        if engine.remove_from_index(path):
            removed_count = initial_len - len(engine.index)
            print(f"removed {removed_count} items matching {path} from the index")
            any_removed = True
        else:
            print(f"no items matching {path} found in the index")

    # If any paths were successfully deleted, save the updated index state back to disk
    if any_removed:
        engine.save_index(index_path)
        print("index has been successfully saved")
