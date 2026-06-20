from modules.constants import DEFAULT_CONFIG
from modules.engine import Engine

engine = Engine()


def initialize_environment():
    config = {
        "storage": {
            "index_path": "~/.octoback/index.json",
            "vault_path": "~/Vault",
            "threshold_bytes": 50 * 1024 * 1024,
            "gzip_level": -1,
        }
    }

    engine.config.set_config(config)
    engine.config.save_config(DEFAULT_CONFIG)
    print("config file has been established")
