import os
from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine

engine = Engine()


def remove_from_index(path):
    if not engine.config.load_config(DEFAULT_CONFIG):
        print("error: config file not found, please run 'octoback init' first.")
        return
    index_path = engine.config.configuration["storage"]["index_path"]

    if os.path.exists(index_path):
        engine.load_index(index_path)
    else:
        print("index file does not exist")
        return

    initial_len = len(engine.index)
    if engine.remove_from_index(path):
        removed_count = initial_len - len(engine.index)
        print(f"removed {removed_count} items matching {path} from the index")
        engine.save_index(index_path)
        print("index has been successfully saved")
    else:
        print(f"no items matching {path} found in the index")
