import sys

def human_readable_size(size_bytes: int) -> str:
    """
    Converts bytes into a human-readable format (B, KB, MB, GB, TB).
    """
    val = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if val < 1024.0:
            return f"{val:.1f}{unit}"
        val /= 1024.0
    return f"{val:.1f}PB"

# ANSI color codes for minimalist formal logic theme
C_GREEN = "\033[32m"
C_CYAN = "\033[36m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_GREY = "\033[90m"
C_RESET = "\033[0m"

# Formal Logic Symbols:
# ⊤ (Top/True) = Success
# ⊥ (Bottom/False) = Error
# ∴ (Therefore) = Info
# ¬ (Negation) = Warning/Not Found

def print_success(message: str):
    print(f"{C_GREEN}⊤{C_RESET} {message}")

def print_info(message: str):
    print(f"{C_GREY}∴ {message}{C_RESET}")

def print_warning(message: str):
    print(f"{C_YELLOW}¬{C_RESET} {message}")

def print_error(message: str):
    print(f"{C_RED}⊥{C_RESET} {message}")

def draw_progress(
    index: int, total: int, current_file: str, action: str = "backing up", extra_info: str = ""
):
    """
    Renders a text-based progress bar in the CLI terminal.
    Uses carriage return (\r) to overwrite the current line in real-time.
    """
    pct = int(index / total * 100) if total > 0 else 100
    bar_len = 15
    filled = int(bar_len * pct / 100)
    
    # Minimalist thin-line progress bar
    bar = f"{C_CYAN}" + "━" * filled + f"{C_GREY}" + "─" * (bar_len - filled) + f"{C_RESET}"

    # Truncate filename if it is too long to display nicely
    if len(current_file) > 25:
        current_file = current_file[:22] + "..."

    suffix = f" {C_GREY}{extra_info}{C_RESET}" if extra_info else ""
    action_clean = action.strip()
    
    sys.stdout.write(f"\r{C_CYAN}{action_clean}{C_RESET} {bar} {pct}% | {C_GREY}{current_file}{C_RESET}{suffix}\033[K")
    sys.stdout.flush()
