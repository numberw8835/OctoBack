import argparse
import logging
import os

from modules import Engine

OCTO_DIR = os.path.expanduser("~/.octoback")
DEFAULT_CONFIG = os.path.join(OCTO_DIR, "octo.yaml")
DEFAULT_INDEX = os.path.join(OCTO_DIR, "index.json")
DEFAULT_VAULT = os.path.expanduser("~/Vault")

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
        nargs="?",
        default=".",
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
    subparsers.add_parser(
        "backup", help="Run the backup process based on the index."
    )

    args = parser.parse_args()

    if args.command == "add":
        add_to_index(args.add, recursive=args.recursive)
    elif args.command == "restore":
        restore_from_backup(args.restore, all_files=args.all)
    elif args.command == "init":
        initialize_environment()
    elif args.command == "backup":
        run_backup()
    else:
        parser.print_help()


def add_to_index(path, recursive=False):
    if not engine.config.load_config(DEFAULT_CONFIG):
        return
    index_path = engine.config.configuration["storage"]["index_path"]

    if os.path.exists(index_path):
        engine.load_index(index_path)

    if recursive:
        files = engine.controller.scan_folder_for_files(path)
        engine.update_index(files)
    else:
        engine.add_folder_to_index(path)

    engine.save_index(index_path)


def run_tui(items):
    import curses

    def main_curses(stdscr):
        curses.curs_set(0)  # Hide cursor
        stdscr.keypad(True)
        curses.use_default_colors()

        # Initialize color pairs if color support is available
        if curses.has_colors():
            # Use default terminal background (-1)
            curses.init_pair(1, curses.COLOR_CYAN, -1)
            curses.init_pair(2, curses.COLOR_GREEN, -1)
            curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
            color_info = curses.color_pair(1)
            color_selected = curses.color_pair(2)
            color_highlight = curses.color_pair(3)
        else:
            color_info = curses.A_NORMAL
            color_selected = curses.A_BOLD
            color_highlight = curses.A_REVERSE

        selected = [False] * len(items)
        current_idx = 0
        start_idx = 0

        while True:
            stdscr.clear()
            max_y, max_x = stdscr.getmaxyx()
            visible_height = max_y - 6  # Leave room for headers/footers

            # Render header
            stdscr.addstr(0, 0, " === OctoBack Restore TUI === ", curses.A_BOLD | color_info)
            stdscr.addstr(1, 0, "Use Up/Down (or j/k) to navigate | Space to select | 'a' to toggle all", curses.A_DIM)
            stdscr.addstr(2, 0, "Press Enter to restore selected | 'q' or ESC to cancel", curses.A_DIM)
            stdscr.addstr(3, 0, "-" * min(max_x - 1, 70), curses.A_DIM)

            # Calculate scrolling window
            if current_idx < start_idx:
                start_idx = current_idx
            elif current_idx >= start_idx + visible_height:
                start_idx = current_idx - visible_height + 1

            # Render items
            for i in range(min(visible_height, len(items) - start_idx)):
                idx = start_idx + i
                item = items[idx]
                
                # Format item row
                chk_box = "[x]" if selected[idx] else "[ ]"
                style = color_highlight if idx == current_idx else curses.A_NORMAL
                
                # Color the checked boxes differently if not highlighted
                if selected[idx] and idx != current_idx:
                    stdscr.addstr(4 + i, 2, chk_box, color_selected | curses.A_BOLD)
                    stdscr.addstr(4 + i, 6, item, style)
                else:
                    stdscr.addstr(4 + i, 2, f"{chk_box} {item}", style)

            # Render footer with scroll indicator
            if len(items) > visible_height:
                stdscr.addstr(max_y - 1, 0, f" -- Scroll for more ({current_idx + 1}/{len(items)}) -- ", color_info)

            stdscr.refresh()

            key = stdscr.getch()

            if key in [curses.KEY_UP, ord('k')]:
                current_idx = (current_idx - 1) % len(items)
            elif key in [curses.KEY_DOWN, ord('j')]:
                current_idx = (current_idx + 1) % len(items)
            elif key == ord(' '):
                selected[current_idx] = not selected[current_idx]
            elif key == ord('a'):
                if all(selected):
                    selected = [False] * len(items)
                else:
                    selected = [True] * len(items)
            elif key in [10, 13]:  # Enter
                break
            elif key in [ord('q'), 27]:  # 'q' or Esc
                return None

        return [items[i] for i, sel in enumerate(selected) if sel]

    return curses.wrapper(main_curses)


def restore_from_backup(path, all_files=False):
    engine.config.load_config(DEFAULT_CONFIG)
    if not engine.config.configuration:
        logging.error("Failed to load config. Please run 'octoback init' first.")
        return

    vault_path = engine.config.configuration["storage"]["vault_path"]
    index_path = engine.config.configuration["storage"]["index_path"]
    block_path = os.path.join(vault_path, "block.tar.gz")

    if not os.path.exists(block_path):
        logging.error(f"Backup archive not found at {block_path}")
        return

    if os.path.exists(index_path):
        engine.load_index(index_path)

    # Check for TUI mode
    if path == "list":
        cwd = os.getcwd()
        matching_paths = []
        for indexed_path in engine.index:
            if indexed_path == cwd or indexed_path.startswith(cwd + os.sep):
                matching_paths.append(indexed_path)

        if not matching_paths:
            logging.info("No indexed files found in the current directory.")
            return

        matching_paths.sort()
        rel_paths = [os.path.relpath(p, cwd) for p in matching_paths]

        selected_rel_paths = run_tui(rel_paths)
        if not selected_rel_paths:
            logging.info("Restoration cancelled or no files selected.")
            return

        for rel_p in selected_rel_paths:
            abs_p = os.path.abspath(os.path.join(cwd, rel_p))
            archive_target = abs_p.lstrip(os.sep)
            dest = os.path.dirname(abs_p)
            logging.info(f"Restoring {abs_p}...")
            engine.controller.uncompress(block_path, archive_target, dest)
        return

    if all_files:
        if not engine.index:
            logging.info("Index is empty. Nothing to restore.")
            return
        for item in engine.index:
            archive_target = item.lstrip(os.sep)
            dest = os.path.dirname(item)
            logging.info(f"Restoring {item} to {dest}...")
            engine.controller.uncompress(block_path, archive_target, dest)
    else:
        # Default to current directory if path not specified
        if not path:
            path = os.getcwd()
        
        abs_target = os.path.abspath(path)
        
        # Check if the path, its parent, or any of its children are in the index
        is_indexed = False
        for indexed_path in engine.index:
            if (abs_target == indexed_path 
                or abs_target.startswith(indexed_path + os.sep)
                or indexed_path.startswith(abs_target + os.sep)):
                is_indexed = True
                break
        
        if not is_indexed:
            logging.warning(f"Path '{abs_target}' is not in the index. Restoration may fail or be empty.")

        archive_target = abs_target.lstrip(os.sep)
        dest = os.path.dirname(abs_target)
        logging.info(f"Restoring {abs_target}...")
        success = engine.controller.uncompress(block_path, archive_target, dest)
        if success:
            logging.info(f"Successfully restored to {abs_target}")
        else:
            logging.error(f"Failed to restore {abs_target}")


def initialize_environment():
    config = {
        "storage": {
            "index_path": DEFAULT_INDEX,
            "vault_path": DEFAULT_VAULT,
        }
    }

    engine.config.set_config(config)
    engine.config.save_config(DEFAULT_CONFIG)


def run_backup():
    engine.config.load_config(DEFAULT_CONFIG)
    if not engine.config.configuration:
        logging.error("Failed to load config. Please run 'octoback init' first.")
        return

    vault_path = engine.config.configuration["storage"]["vault_path"]
    index_path = engine.config.configuration["storage"]["index_path"]

    if os.path.exists(index_path):
        engine.load_index(index_path)

    if not engine.index:
        logging.info("Index is empty. Nothing to backup.")
        return

    # Ensure vault exists
    import shutil
    os.makedirs(vault_path, exist_ok=True)

    # Move old block.tar.gz out of the way to prevent self-compression
    block_path = os.path.join(vault_path, "block.tar.gz")
    backup_block_path = os.path.join(vault_path, "block.tar.gz.bak")
    if os.path.exists(block_path):
        try:
            shutil.move(block_path, backup_block_path)
        except Exception as e:
            logging.error(f"Failed to move old backup out of the way: {e}")
            return

    # Remove previous uncompressed folders/files in the vault
    try:
        for item in os.listdir(vault_path):
            item_path = os.path.join(vault_path, item)
            if item_path == backup_block_path:
                continue
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
    except Exception as e:
        logging.error(f"Error preparing vault: {e}")
        # Try to restore backup block if we failed early
        if os.path.exists(backup_block_path):
            shutil.move(backup_block_path, block_path)
        return

    # Copy all indexed items mirroring their absolute paths
    for path in engine.index:
        if not os.path.exists(path):
            logging.warning(f"Indexed path {path} does not exist. Skipping.")
            continue
        rel_path = path.lstrip(os.sep)
        dest_path = os.path.join(vault_path, rel_path)
        logging.info(f"Copying {path} to vault mirror...")
        engine.controller.copy_to(path, dest_path)

    # Compress the Vault contents (to prevent the Vault/ prefix in the archive)
    logging.info("Compressing vault...")
    compressed_file = os.path.join(os.path.dirname(vault_path), "Vault.tar.gz")
    
    subdirs = [item for item in os.listdir(vault_path) if os.path.join(vault_path, item) != backup_block_path]
    if not subdirs:
        logging.error("Vault is empty. Nothing to compress.")
        if os.path.exists(backup_block_path):
            shutil.move(backup_block_path, block_path)
        return

    command = [
        "tar",
        "-czf",
        compressed_file,
        "-C",
        vault_path,
    ] + subdirs

    try:
        import subprocess
        subprocess.run(command, check=True)
        logging.info(f"Compression successful: {compressed_file}")
    except Exception as e:
        logging.error(f"Compression failed: {e}")
        # Try to restore backup block
        if os.path.exists(backup_block_path):
            shutil.move(backup_block_path, block_path)
        return

    # Move block.tar.gz inside the vault
    try:
        shutil.move(compressed_file, block_path)
        logging.info(f"Backup package saved to {block_path}")
        if os.path.exists(backup_block_path):
            os.remove(backup_block_path)
    except Exception as e:
        logging.error(f"Failed to move package to vault: {e}")
        # Try to restore backup block
        if os.path.exists(backup_block_path):
            shutil.move(backup_block_path, block_path)
        return

    # Clean up the uncompressed mirror directories in vault
    try:
        for item in os.listdir(vault_path):
            item_path = os.path.join(vault_path, item)
            if item_path == block_path:
                continue
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        logging.info("Uncompressed backup files cleaned up successfully.")
    except Exception as e:
        logging.error(f"Error cleaning up uncompressed files in vault: {e}")


if __name__ == "__main__":
    engine = Engine()
    main()
