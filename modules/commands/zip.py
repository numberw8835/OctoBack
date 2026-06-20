import os
import shutil
from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine

engine = Engine()


def run_zip():
    if not engine.config.load_config(DEFAULT_CONFIG):
        print("error: config file not found, please run 'octoback init' first.")
        return

    vault_path = engine.config.configuration["storage"]["vault_path"]

    if not os.path.exists(vault_path):
        print(f"error: vault directory not found: {vault_path}")
        return

    zip_base = vault_path.rstrip(os.sep)
    zip_file = zip_base + ".zip"

    try:
        shutil.make_archive(zip_base, "zip", vault_path)
        print(f"vault has been successfully zipped to {zip_file}")
    except Exception as e:
        print(f"error zipping vault: {e}")
