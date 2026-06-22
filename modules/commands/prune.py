import os

from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine
from modules.ui import print_success, print_error, print_info

engine = Engine()


def run_prune():
    if not engine.config.load_config(DEFAULT_CONFIG):
        print_error("Configuration file not found")
        return
    index_path = engine.config.configuration["storage"]["index_path"]

    if os.path.exists(index_path):
        engine.load_index(index_path)
    else:
        print_error("Index file does not exist")
        return

    removed = []
    for source in list(engine.index):
        if not os.path.exists(source):
            engine.remove_from_index(source)
            removed.append(source)

    if removed:
        engine.save_index(index_path)
        print_success(f"Pruned {len(removed)} missing paths from index")
        for r in removed:
            print_info(f"  {r}")
    else:
        print_info("Nothing to prune")
