import hashlib
import logging
import os

from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine
from modules.ui import C_CYAN, C_GREEN, C_RED, C_RESET, print_error


def run_check(paths):
    """
    Checks a file/folder by comparing SHA1 hashes between vault and local.

    If the file/folder exists in the vault, it calculates the SHA1 of both and prints:
    [SHA1 Vault file] : [SHA1 PC file] [Top symbol if they match else Bottom symbol]
    """
    config_path = DEFAULT_CONFIG

    engine = Engine()
    if not engine.config.load_config(config_path):
        print_error("configuration file not found. please run 'octoback init' first.")
        return

    # Load the index if it exists
    index_path = engine.config.configuration["storage"]["index_path"]
    if os.path.exists(index_path):
        engine.load_index(index_path)

    # Retrieve vault path from the configuration
    vault_path = engine.config.configuration["storage"]["vault_path"]

    # Handle default case (current directory)
    if not paths or paths == ["."]:
        paths = ["."]

    # Process each path
    for path in paths:
        # Convert the input path to absolute path
        abs_path = os.path.abspath(os.path.expanduser(path))

        # Check if path is in the index
        if abs_path not in engine.index:
            print_error(f"'{path}' is not in the index")
            continue

        # Check if vault version exists
        from modules.util.paths import get_vault_target_path

        vault_target = get_vault_target_path(abs_path, vault_path)

        if not os.path.exists(vault_target):
            print_error(f"No backup found for '{path}' in the vault")
            continue

        # Calculate SHA1 of vault file/folder
        vault_sha1 = calculate_sha1(vault_target)

        # Calculate SHA1 of local file/folder
        pc_sha1 = calculate_sha1(abs_path)

        print(f"{C_CYAN}{vault_sha1}{C_RESET} : {C_CYAN}{pc_sha1}{C_RESET}", end="")

        if vault_sha1 == pc_sha1:
            print(f" {C_GREEN}⊤{C_RESET}")
        else:
            print(f" {C_RED}⊥{C_RESET}")


def calculate_sha1(path):
    """
    Calculates SHA1 hash for a file or folder.
    For folders, hashes all files recursively.
    """
    if os.path.isfile(path):
        sha1_hash = hashlib.sha1()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha1_hash.update(chunk)
        return sha1_hash.hexdigest()

    elif os.path.isdir(path):
        # For folders, sort files for consistent hashing
        all_files = []
        for root, _, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                all_files.append(file_path)

        all_files.sort()

        sha1_hash = hashlib.sha1()
        for file_path in all_files:
            try:
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        sha1_hash.update(chunk)
            except Exception:
                continue

        return sha1_hash.hexdigest()

    else:
        logging.warning(f"Path '{path}' does not exist or is not accessible")
        return "N/A"
