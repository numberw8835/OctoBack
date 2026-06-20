import argparse
import logging
import os
import sys
import signal

from modules.commands import (
    add_to_index,
    remove_from_index,
    restore_from_backup,
    initialize_environment,
    run_backup,
    cleanup_temp_dirs,
    run_zip,
    run_unzip,
)

description_message = """
Octo is a lightweight CLI backup manager that separates the "intent" (what to back up) from the "action"
(the actual backup process). By maintaining a curated index of files and folders, Octo ensures your
backup vault remains organized and predictable.
"""


def setup_logging(verbose=False):
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    if verbose:
        handler = logging.StreamHandler()

        class OctoFormatter(logging.Formatter):
            def format(self, record):
                if record.levelno == logging.INFO:
                    return f"[octoback] {record.getMessage()}"
                elif record.levelno == logging.WARNING:
                    return f"[warning] {record.getMessage()}"
                elif record.levelno == logging.ERROR:
                    return f"[error] {record.getMessage()}"
                elif record.levelno >= logging.CRITICAL:
                    return f"[critical] {record.getMessage()}"
                return record.getMessage()

        handler.setFormatter(OctoFormatter())
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
    else:
        root_logger.setLevel(logging.CRITICAL + 1)


def main():
    parser = argparse.ArgumentParser(
        description=description_message, usage="%(prog)s [command] [options]"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    # Subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="commands")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a directory to the index.")
    add_parser.add_argument(
        "add",
        type=str,
        nargs="*",
        default=["."],
        help="Directory paths or folder names (current directory if not specified)",
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
        "restore",
        type=str,
        nargs="?",
        default=None,
        help="Directory path or folder name to restore (defaults to current directory if not specified)",
    )
    restore_parser.add_argument(
        "--all", action="store_true", help="Restore all files in the directory"
    )

    # Init command
    subparsers.add_parser(
        "init", help="Initialize the environment and create the configuration file."
    )

    # Backup command
    subparsers.add_parser("backup", help="Run the backup process based on the index.")

    # Remove command
    remove_parser = subparsers.add_parser(
        "remove", aliases=["rm"], help="Remove a directory or file from the index."
    )
    remove_parser.add_argument(
        "path",
        type=str,
        nargs="*",
        default=["."],
        help="Directory or file paths to remove (defaults to current directory if not specified)",
    )

    # Zip command
    subparsers.add_parser("zip", help="Compress the entire backup vault into a ZIP file.")

    # Unzip command
    subparsers.add_parser("unzip", help="Decompress the backup vault ZIP file back to the vault.")

    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    if args.command == "add":
        add_to_index(args.add, recursive=args.recursive)
    elif args.command in ["remove", "rm"]:
        remove_from_index(args.path)
    elif args.command == "restore":
        restore_from_backup(args.restore, all_files=args.all)
    elif args.command == "init":
        initialize_environment()
    elif args.command == "backup":
        run_backup()
    elif args.command == "zip":
        run_zip()
    elif args.command == "unzip":
        run_unzip()
    else:
        parser.print_help()


if __name__ == "__main__":
    def signal_handler(sig, frame):
        cleanup_temp_dirs()
        try:
            sys.stdout.write("\r¬φ\033[K\n")
            sys.stdout.flush()
        except Exception:
            pass
        os._exit(130)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        main()
    except EOFError:
        cleanup_temp_dirs()
        try:
            sys.stdout.write("\r¬φ\033[K\n")
            sys.stdout.flush()
        except Exception:
            pass
        os._exit(130)
