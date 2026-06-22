from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine
from modules.ui import print_success

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
        }
    }

    # Assign and write configuration parameters to ~/.octoback/octo.yaml
    engine.config.set_config(config)
    engine.config.save_config(DEFAULT_CONFIG)
    print_success("Config initialized at ~/.octoback/octo.yaml")
