import os

from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine
from modules.tui import run_tui

engine = Engine()


def list_index():
    """
    Lists all indexed files and directories using the interactive TUI.
    Initializes the engine, loads index.json, sorts the records, and renders the TUI.
    """
    # Load storage configuration parameter values
    if not engine.config.load_config(DEFAULT_CONFIG):
        print("config file not found, please run 'octoback init' first.")
        return

    index_path = engine.config.configuration["storage"]["index_path"]
    # Retrieve index elements from the storage json file
    if os.path.exists(index_path):
        engine.load_index(index_path)

    if not engine.index:
        print("index is empty")
        return

    # List all indexed files/folders, sorted alphabetically for readable presentation
    items = sorted(list(engine.index))

    # Run the interactive TUI in view-only mode (select_mode=False) to browse the items
    run_tui(items, select_mode=False)
