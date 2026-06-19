import argparse

description_message = """
Octo is a lightweight CLI backup manager that separates the "intent" (what to back up) from the "action"
(the actual backup process). By maintaining a curated index of files and folders, Octo ensures your
backup vault remains organized and predictable.
"""


def main():
    parser = argparse.ArgumentParser(
        description=description_message, usage="%(prog)s [command] [options]"
    )

    # Subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="commands")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a directory to the index.")
    add_parser.add_argument(
        "add",
        type=str,
        help="Directory path or folder name (current directory if not specified)",
    )
    add_parser.add_argument(
        "-R",
        "--recursive",
        action="store_true",
        help="Perform the operation recursively",
    )

    # Restore command
    restore_parser = subparsers.add_parser(
        "restore", help="Restore a specific directory from the backup."
    )
    restore_parser.add_argument(
        "restore", type=str, help="Directory path or folder name to restore"
    )
    restore_parser.add_argument(
        "--all", action="store_true", help="Restore all files in the directory"
    )

    # Init command
    init_parser = subparsers.add_parser(
        "init", help="Initialize the environment and create the configuration file."
    )
    init_parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="octo.yaml",
        help="Path to the configuration file (default: octo.yaml)",
    )

    # Backup command
    backup_parser = subparsers.add_parser(
        "backup", help="Run the backup process based on the index."
    )
    backup_parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="octo.yaml",
        help="Path to the configuration file (default: octo.yaml)",
    )

    args = parser.parse_args()

    if args.command == "add":
        add_to_index(args.add, recursive=args.recursive)
    elif args.command == "restore":
        restore_from_backup(args.restore, all_files=args.all)
    elif args.command == "init":
        initialize_environment(config_path=args.config)
    elif args.command == "backup":
        run_backup(config_path=args.config)
    else:
        parser.print_help()


def add_to_index(path, recursive=False):
    # Placeholder for adding a directory to the index
    print(f"Adding {path} {'recursively' if recursive else ''}")


def restore_from_backup(path, all_files=False):
    # Placeholder for restoring from backup
    print(f"Restoring {path} {'all files' if all_files else ''}")


def initialize_environment(config_path):
    # Placeholder for initializing the environment
    print(f"Initializing with config at {config_path}")


def run_backup(config_path):
    # Placeholder for running the backup process
    print(f"Running backup with config at {config_path}")


if __name__ == "__main__":
    main()
