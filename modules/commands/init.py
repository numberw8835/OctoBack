from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine

engine = Engine()


def initialize_environment():
    """
    Initializes the local environment by generating a default YAML configuration file (octo.yaml)
    at ~/.octoback/octo.yaml. Sets up index and vault storage directories.
    """
    config = {
        "storage": {
            # Location of the file index database (JSON format)
            "index_path": "~/.octoback/index.json",
            # Location of the directory containing raw, copied backups
            "vault_path": "~/Vault",
            # Threshold size (50MB by default) before warnings are raised or special transfer tools are selected
            "threshold_bytes": 50 * 1024 * 1024,
            # Compression level for archiving tools (default -1 uses standard system compression)
            "gzip_level": -1,
        }
    }

    # Assign and write configuration parameters to ~/.octoback/octo.yaml
    engine.config.set_config(config)
    engine.config.save_config(DEFAULT_CONFIG)
    print("config file has been established")
