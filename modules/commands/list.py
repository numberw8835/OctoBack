import os
from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine
from modules.tui import run_tui

engine = Engine()

def list_index():
    if not engine.config.load_config(DEFAULT_CONFIG):
        print("error: config file not found, please run 'octoback init' first.")
        return

    index_path = engine.config.configuration["storage"]["index_path"]
    if os.path.exists(index_path):
        engine.load_index(index_path)

    if not engine.index:
        print("index is empty")
        return

    # List all indexed files/folders, sorted
    items = sorted(list(engine.index))

    # Run the TUI in view-only mode (select_mode=False)
    run_tui(items, select_mode=False)
