import logging
import os

import yaml

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Config:
    def __init__(self) -> None:
        self.configuration = dict()

    def load_config(self, path: str) -> bool:
        """
        Loads the YAML config from the given path.
        """
        try:
            with open(path, "r") as f:
                self.configuration = yaml.safe_load(f)
            # Expand ~ in loaded configuration paths
            if self.configuration and "storage" in self.configuration:
                for key in ["index_path", "vault_path"]:
                    if key in self.configuration["storage"]:
                        val = self.configuration["storage"][key]
                        if isinstance(val, str):
                            self.configuration["storage"][key] = os.path.expanduser(val)
            logging.info(f"Config loaded from {path} successfully.")
            return True
        except FileNotFoundError as e:
            logging.error(f"Config file not found at {path}, please do: octoback init")
            return False
        except Exception as e:
            logging.error(f"Error loading config from {path}: {e}")
            return False

    def save_config(self, path: str):
        """
        Saves the current config to a YAML file at the given path.
        """
        try:
            dir_name = os.path.dirname(path)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)
            tmp_path = path + ".tmp"
            with open(tmp_path, "w") as f:
                yaml.safe_dump(self.configuration, f)
            os.replace(tmp_path, path)
            logging.info(f"Config saved to {path} successfully.")
        except Exception as e:
            logging.error(f"Error saving config from {path}: {e}")

    def set_config(self, config: dict):
        """
        Creates a new config dictionary.
        """
        self.configuration = config
        logging.info("New config created.")
