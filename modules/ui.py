import sys
import time


def draw_progress(
    index: int, total: int, current_file: str, action: str = "backing up"
):
    pct = int(index / total * 100) if total > 0 else 100
    bar_len = 20
    filled = int(bar_len * pct / 100)
    bar = "█" * filled + "░" * (bar_len - filled)

    if len(current_file) > 30:
        current_file = current_file[:27] + "..."

    sys.stdout.write(f"\r{action} [{bar}] {pct}% | {current_file}\033[K")
    sys.stdout.flush()



