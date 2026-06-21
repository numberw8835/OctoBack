import sys


def draw_progress(
    index: int, total: int, current_file: str, action: str = "backing up"
):
    """
    Renders a text-based progress bar in the CLI terminal.
    Uses carriage return (\r) to overwrite the current line in real-time.
    """
    # Calculate percentage completion
    pct = int(index / total * 100) if total > 0 else 100
    bar_len = 20
    # Compute block length for filled status
    filled = int(bar_len * pct / 100)
    # Generate progress bar characters (solid block for filled, light shade block for unfilled)
    bar = "█" * filled + "░" * (bar_len - filled)

    # Truncate filename if it is too long to display nicely in the progress line
    if len(current_file) > 30:
        current_file = current_file[:27] + "..."

    # Write the formatted progress string to stdout and clear trailing line characters using \033[K (EL)
    sys.stdout.write(f"""\r{action} [{bar}] {pct}% | {current_file}\033[K """)
    sys.stdout.flush()
