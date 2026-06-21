import logging
import os

import yaml

# Initialize root logger configuration for utility operations
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Config:
    """
    Manages loading, parsing, updating, and saving the YAML configuration file for the backup utility.
    """

    def __init__(self) -> None:
        # Dictionary representation of the configuration loaded from file
        self.configuration = dict()

    def load_config(self, path: str) -> bool:
        """
        Loads the YAML config from the given path.
        Also resolves any user home directory tilde paths ('~') inside storage keys.
        """
        try:
            with open(path, "r") as f:
                self.configuration = yaml.safe_load(f)

            # Expand standard user home-relative paths (~) for portability and absolute routing.
            if self.configuration and "storage" in self.configuration:
                for key in ["index_path", "vault_path"]:
                    if key in self.configuration["storage"]:
                        val = self.configuration["storage"][key]
                        if isinstance(val, str):
                            self.configuration["storage"][key] = os.path.expanduser(val)

            logging.info(f"Config loaded from {path} successfully.")
            return True
        except FileNotFoundError as e:
            logging.error(
                f"config file not found at {path}, please run `octoback init`"
            )
            return False
        except Exception as e:
            logging.error(f"couldn't load config from {path}: {e}")
            return False

    def save_config(self, path: str):
        """
        Saves the current config to a YAML file at the given path.
        Uses an atomic write-replace pattern (writing to .tmp first) to prevent configuration corruption.
        """
        try:
            # Ensure the config base directory exists
            dir_name = os.path.dirname(path)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)

            # Atomic file swap pattern to prevent configuration loss in case of system interrupts
            tmp_path = path + ".tmp"
            with open(tmp_path, "w") as f:
                yaml.safe_dump(self.configuration, f)
            os.replace(tmp_path, path)
            logging.info(f"config saved to {path} successfully.")
        except Exception as e:
            logging.error(f"couldn't save config from {path}: {e}")

    def set_config(self, config: dict):
        """
        Creates a new config dictionary in-memory.
        """
        self.configuration = config
        logging.info("new config has been set.")
