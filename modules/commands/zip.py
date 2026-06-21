import os
import zipfile

from tqdm import tqdm

from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine

engine = Engine()


def run_zip():
    """
    Compresses the entire backup vault directory into a single ZIP archive.
    Uses tqdm to show the progress.
    """
    # Load configuration settings
    if not engine.config.load_config(DEFAULT_CONFIG):
        print("error: config file not found, please run 'octoback init' first.")
        return

    vault_path = engine.config.configuration["storage"]["vault_path"]

    # Verify that the vault directory exists before compressing it
    if not os.path.exists(vault_path):
        print(f"error: vault directory not found: {vault_path}")
        return

    # Derive zip output filename (e.g. Vault.zip in parent directory of vault)
    zip_base = vault_path.rstrip(os.sep)
    zip_file = zip_base + ".zip"

    try:

        # Helper function to walk through source directory and zip files, updating the progress bar.
        def zip_progress(src, dst, pbar):
            with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(src):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, src)
                        zf.write(file_path, arcname=arcname)
                        # Increment progress bar by 1 file
                        pbar.update(1)

        # Recursively count the total number of files in the vault to establish the progress bar limit.
        total_files = sum(len(files) for _, _, files in os.walk(vault_path))
        with tqdm(total=total_files, desc="Zipping") as pbar:
            zip_progress(vault_path, zip_file, pbar)
            pbar.close()

        print(f"vault has been successfully zipped to {zip_file}")
    except Exception as e:
        print(f"error zipping vault: {e}")
