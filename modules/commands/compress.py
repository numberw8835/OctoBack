import os
import tarfile

from tqdm import tqdm

from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine

engine = Engine()


def get_total_path_size(folder_path):
    total_size = 0
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                if not os.path.islink(file_path) and os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
            except (OSError, FileNotFoundError):
                continue
    return int(total_size)


def create_tar(vault_path, tar_path):
    total_size = get_total_path_size(vault_path)
    try:
        with tqdm(
            total=total_size,
            desc="Compressing...",
            unit="bytes",
            unit_scale=True,
            dynamic_ncols=True,
        ) as pbar:
            with tarfile.open(tar_path, "w:gz") as tar:
                for root, _, files in os.walk(vault_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            arcname = os.path.relpath(file_path, start=vault_path)
                            # Get the size before adding.
                            if not os.path.islink(file_path) and os.path.isfile(
                                file_path
                            ):
                                file_size = os.path.getsize(file_path)
                                tar.add(file_path, arcname)
                                pbar.update(file_size)
                        except Exception as e:
                            print(f"failed to add file {file_path} to tar")
    except Exception as e:
        print(f"failed to compress the vault {e}")


def run_compress():
    """
    Compresses the entire backup vault directory into a single tar.gz archive.
    Uses tqdm to show the progress.
    """
    # Load configuration settings
    if not engine.config.load_config(DEFAULT_CONFIG):
        print("config file not found, please run 'octoback init' first.")
        return

    vault_path = engine.config.configuration["storage"]["vault_path"]

    # Verify that the vault directory exists before compressing it
    if not os.path.exists(vault_path):
        print(f"vault directory not found {vault_path}")
        return

    # Setup the names of the compressed folder
    vault_path = vault_path.rstrip(os.sep)
    tar_file = vault_path + ".tar.gz"

    create_tar(vault_path, tar_file)

    print(f"vault has been compressed to {tar_file}")
