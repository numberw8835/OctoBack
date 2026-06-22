import json
import os
import subprocess

from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine

engine = Engine()


def list_index():
    """
    Lists all indexed files and directories using bat (if available) or falls back to stdout.
    Initializes the engine, loads index.json, sorts the records, and displays them.
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

    # Display as JSON using bat or fallback to simple printing
    json_content = json.dumps(items, indent=2)
    command_name = ["bat", "batcat"]
    for name in command_name:
        try:
            result = subprocess.run(
                [
                    name,
                    "--style=numbers,header",
                    "--paging=never",
                    "--language=json",
                    "--theme=OneHalfDark",
                ],
                input=json_content,
                text=True,
                capture_output=True,
                check=True,
            )

            try:
                from colorama import Fore, Style, init

                init(autoreset=True)
                print(Fore.MAGENTA + result.stdout)
            except ImportError:
                pass  # no colorama, just print raw
            break  # success — stop the loop
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue  # try next command in list

    else:  # this runs only if the loop completed without `break`
        print("please install bat or batcat for formatted output. Current index:")
        print(json_content)
