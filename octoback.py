import argparse
import logging
import os
import signal
import sys

# Import command controllers from commands module
from modules.commands import (
    add_to_index,
    initialize_environment,
    list_index,
    remove_from_index,
    restore_from_backup,
    run_backup,
    run_compress,
    run_prune,
    run_uncompress,
)

description_message = """
Octo is a lightweight CLI backup manager that separates the "intent" (what to back up) from the "action"
(the actual backup process). By maintaining a curated index of files and folders, Octo ensures your
backup vault remains organized and predictable.
"""


def setup_logging(verbose=False):
    """
    Sets up custom logging format and levels.
    If verbose is True, configures standard output logger with prefix formatting.
    """
    root_logger = logging.getLogger()
    # Clear any existing active log handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    if verbose:
        handler = logging.StreamHandler()

        # Custom logging formatter that appends tags depending on message severity
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
        # If verbose mode is off, suppress log output (disable logs below CRITICAL+1)
        root_logger.setLevel(logging.CRITICAL + 1)


def main():
    """
    CLI command dispatcher. Parses input arguments and triggers subcommand handlers.
    
    This is the main entry point for the Octo backup manager CLI tool. It supports
    various commands for managing backups including adding files/directories to 
    the index, restoring from backup, initializing the environment, running backups,
    compressing/expanding backup vaults, listing indexed items, and pruning stale paths.
    
    Commands:
      init        Initialize the environment and create configuration file
      add         Add directory to the index
      remove/rm   Remove directory or file from the index
      restore     Restore a specific directory from backup
      backup      Run the backup process based on the index
      compress    Compress entire backup vault into tarball
      expand      Expand tarball into the backup vault
      list        List all files in the index using TUI
      prune       Prune non-existent paths from the index
    
    Options:
      -v, --verbose  Enable verbose logging
    """
    parser = argparse.ArgumentParser(
        description=description_message, usage="%(prog)s [command] [options]"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    # Subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="commands")

    # 'add' command configuration
    add_parser = subparsers.add_parser("add", help="Add a directory to the index.")
    add_parser.add_argument(
        "add",
        type=str,
        nargs="*",
        default=["."],
        help="Directory paths or folder names (current directory if not specified)",
    )
    # The -g/--granular flag replaced the confusing -R/--recursive flag.
    # It allows indexing files individually (for selective TUI restoration) instead of tracking folders as a single dynamic unit.
    add_parser.add_argument(
        "-g",
        "--granular",
        action="store_true",
        help="Index files individually for granular restore control",
    )

    # 'restore' command configuration
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

    # 'init' command configuration
    subparsers.add_parser(
        "init", help="Initialize the environment and create the configuration file."
    )

    # 'backup' command configuration
    subparsers.add_parser("backup", help="Run the backup process based on the index.")

    # 'remove' command configuration
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

    # 'zip' command configuration
    subparsers.add_parser(
        "compress", help="Compress the entire backup vault into a tarball."
    )

    # 'unzip' command configuration
    subparsers.add_parser("expand", help="Expand a tarball into the backup vault.")

    # 'list' command configuration
    subparsers.add_parser("list", help="List all files in the index using the TUI.")

    # 'prune' command configuration
    subparsers.add_parser("prune", help="Prune non-existent paths from the index.")

    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    # Dispatch parsed subcommands to their respective helper functions
    if args.command == "add":
        add_to_index(args.add, granular=args.granular)
    elif args.command in ["remove", "rm"]:
        remove_from_index(args.path)
    elif args.command == "restore":
        restore_from_backup(args.restore, all_files=args.all)
    elif args.command == "init":
        initialize_environment()
    elif args.command == "backup":
        run_backup()
    elif args.command == "compress":
        run_compress()
    elif args.command == "expand":
        run_uncompress()
    elif args.command == "list":
        list_index()
    elif args.command == "prune":
        run_prune()
    else:
        # Fallback to help display if no subcommand or invalid command is entered
        parser.print_help()


if __name__ == "__main__":
    # Signal interrupt trap handler (Ctrl-C)
    def signal_handler(sig, frame):
        try:
            sys.stdout.write("\rExiting... \033[K\n")
            sys.stdout.flush()
        except Exception:
            pass
        os._exit(130)

    # Attach SIGINT signal listener
    signal.signal(signal.SIGINT, signal_handler)

    try:
        main()
    except EOFError:
        # Handle Ctrl-D (EOF) exit
        try:
            sys.stdout.write("\rExiting... \033[K\n")
            sys.stdout.flush()
        except Exception:
            pass
        os._exit(130)
