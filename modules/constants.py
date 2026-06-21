import os

# Base directory for OctoBack user-specific files in the home directory (~/.octoback)
OCTO_DIR = os.path.expanduser("~/.octoback")

# Path to the primary configuration file (~/.octoback/octo.yaml)
DEFAULT_CONFIG = os.path.join(OCTO_DIR, "octo.yaml")

# Default path to the indexing database file (~/.octoback/index.json)
DEFAULT_INDEX = os.path.join(OCTO_DIR, "index.json")

# Default directory where the backup vault (tracked file copies) will reside (~/Vault)
DEFAULT_VAULT = os.path.expanduser("~/Vault")
