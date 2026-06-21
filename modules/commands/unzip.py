import os

from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine

engine = Engine()


def run_unzip():
    if not engine.config.load_config(DEFAULT_CONFIG):
        print("error: config file not found, please run 'octoback init' first.")
        return

    vault_path = engine.config.configuration["storage"]["vault_path"]
    zip_base = vault_path.rstrip(os.sep)
    zip_file = zip_base + ".zip"

    if not os.path.exists(zip_file):
        print(f"error: zip file not found: {zip_file}")
        return

    try:
        import zipfile

        from tqdm import tqdm

        def unzip_progress(zip_file, dst):
            with zipfile.ZipFile(zip_file, "r") as zf:
                for info in zf.infolist():
                    zf.extract(info, dst)
                    pbar.update(1)

        total_files = len(zipfile.ZipFile(zip_file).infolist())
        with tqdm(total=total_files, desc="Unzipping") as pbar:
            unzip_progress(zip_file, vault_path)
            pbar.close()

        print(f"vault has been successfully unzipped to {vault_path}")
    except Exception as e:
        print(f"error unzipping vault: {e}")
