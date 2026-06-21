import os
from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine

engine = Engine()

def run_prune():
    if not engine.config.load_config(DEFAULT_CONFIG):
        print("config file not found")
        return
    index_path = engine.config.configuration["storage"]["index_path"]
    
    if os.path.exists(index_path):
        engine.load_index(index_path)
    else:
        print("index file does not exist")
        return

    removed = []
    for source in list(engine.index):
        if not os.path.exists(source):
            engine.remove_from_index(source)
            removed.append(source)

    if removed:
        engine.save_index(index_path)
        print("pruned missing paths from index")
        for r in removed:
            print(f"  {r}")
    else:
        print("nothing to prune")
