import os

from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine

engine = Engine()


def run_unzip():
    """
    Decompresses the entire backup vault ZIP archive (Vault.zip) back into the standard 
    Vault directory structure. Uses tqdm to show progress.
    """
    # Load settings configuration to get vault_path
    if not engine.config.load_config(DEFAULT_CONFIG):
        print("error: config file not found, please run 'octoback init' first.")
        return

    vault_path = engine.config.configuration["storage"]["vault_path"]
    zip_base = vault_path.rstrip(os.sep)
    zip_file = zip_base + ".zip"

    # Verify that the zip package exists before extracting
    if not os.path.exists(zip_file):
        print(f"error: zip file not found: {zip_file}")
        return

    try:
        import zipfile
        from tqdm import tqdm

        # Inner function that performs decompression and updates the tqdm progress bar
        def unzip_progress(zip_file, dst, pbar):
            with zipfile.ZipFile(zip_file, "r") as zf:
                for info in zf.infolist():
                    zf.extract(info, dst)
                    pbar.update(1)

        # Retrieve the count of all files in the archive to establish progress bar total
        total_files = len(zipfile.ZipFile(zip_file).infolist())
        with tqdm(total=total_files, desc="Unzipping") as pbar:
            unzip_progress(zip_file, vault_path, pbar)
            pbar.close()

        print(f"vault has been successfully unzipped to {vault_path}")
    except Exception as e:
        print(f"error unzipping vault: {e}")
