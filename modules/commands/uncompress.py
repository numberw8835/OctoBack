import os
import tarfile

from tqdm import tqdm

from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine
from modules.ui import print_success, print_error, print_warning

engine = Engine()


def run_uncompress():
    """
    Decompresses the entire backup vault TAR archive back into the standard
    Vault directory structure. Uses tqdm to show progress by bytes.
    """
    if not engine.config.load_config(DEFAULT_CONFIG):
        print_error("Configuration file not found. Please run 'octoback init' first.")
        return

    vault_path = engine.config.configuration["storage"]["vault_path"]
    archive_base = vault_path.rstrip(os.sep)
    archive_file = archive_base + ".tar.gz"

    if not os.path.exists(archive_file):
        print_error(f"Archive file not found: {archive_file}")
        return

    try:
        total_size = 0
        with tarfile.open(archive_file, "r:gz") as tf_check:
            for member in tf_check.getmembers():
                if member.isfile():
                    total_size += member.size

        with tqdm(
            total=total_size,
            desc="Uncompressing...",
            unit_scale=True,
            dynamic_ncols=True,
        ) as pbar:
            with tarfile.open(archive_file, "r:gz") as tf:
                for member in tf.getmembers():
                    # Security: Prevent Zip Slip/path traversal outside of the vault
                    target_path = os.path.abspath(os.path.join(vault_path, member.name))
                    if os.path.commonpath([vault_path, target_path]) != vault_path:
                        print_warning(f"Skipping unsafe path: {member.name}")
                        continue

                    tf.extract(member, vault_path)
                    
                    if member.isfile():
                        pbar.update(member.size)

        print_success(f"Vault uncompressed to {vault_path}")
    except Exception as e:
        print_error(f"Failed to uncompress vault: {e}")
