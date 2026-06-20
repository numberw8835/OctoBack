import sys

def format_time(seconds):
    if seconds is None or seconds < 0:
        return "--s"
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"


def format_bytes(bytes_count):
    if bytes_count < 1024:
        return f"{bytes_count}B"
    elif bytes_count < 1024 * 1024:
        return f"{bytes_count / 1024:.1f}KB"
    elif bytes_count < 1024 * 1024 * 1024:
        return f"{bytes_count / (1024 * 1024):.1f}MB"
    else:
        return f"{bytes_count / (1024 * 1024 * 1024):.1f}GB"


def format_speed(bytes_per_sec):
    if bytes_per_sec is None or bytes_per_sec < 0:
        return "--B/s"
    return f"{format_bytes(bytes_per_sec)}/s"


def draw_status_bar(total_bytes_copied, total_bytes_needed, est_total, total_speed,
                    local_bytes_copied, local_bytes_needed,
                    current_action):
    total_pct = (total_bytes_copied / total_bytes_needed * 100) if total_bytes_needed > 0 else 100
    total_bar_len = 6
    total_filled = int(total_bar_len * total_pct / 100)
    total_bar = "█" * total_filled + "░" * (total_bar_len - total_filled)

    local_pct = (local_bytes_copied / local_bytes_needed * 100) if local_bytes_needed > 0 else 100
    local_bar_len = 6
    local_filled = int(local_bar_len * local_pct / 100)
    local_bar = "█" * local_filled + "░" * (local_bar_len - local_filled)

    est_total_str = format_time(est_total)

    total_bytes_str = f"{format_bytes(total_bytes_copied)}/{format_bytes(total_bytes_needed)}"
    local_bytes_str = f"{format_bytes(local_bytes_copied)}/{format_bytes(local_bytes_needed)}"
    speed_total_str = format_speed(total_speed)

    use_color = sys.stdout.isatty()
    CYAN = "\033[36m" if use_color else ""
    GREEN = "\033[32m" if use_color else ""
    RESET = "\033[0m" if use_color else ""
    BOLD = "\033[1m" if use_color else ""

    status_line = (
        f"\r{BOLD}Tot:{RESET} {CYAN}[{total_bar}] {total_pct:5.1f}% ({total_bytes_str}, {speed_total_str}, ETA {est_total_str}){RESET} | "
        f"{BOLD}Loc:{RESET} {GREEN}[{local_bar}] {local_pct:5.1f}% ({local_bytes_str}){RESET} | "
        f"{current_action}"
    )

    sys.stdout.write(status_line + "\033[K")
    sys.stdout.flush()
