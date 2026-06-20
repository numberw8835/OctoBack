import curses
import os

def run_tui(items):
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
            stdscr.addstr(
                0, 0, " === OctoBack Restore TUI === ", curses.A_BOLD | color_info
            )
            stdscr.addstr(
                1,
                0,
                "Use Up/Down (or j/k) to navigate | Space to select | 'a' to toggle all",
                curses.A_DIM,
            )
            stdscr.addstr(
                2,
                0,
                "Press Enter to restore selected | 'q' or ESC to cancel",
                curses.A_DIM,
            )
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
                stdscr.addstr(
                    max_y - 1,
                    0,
                    f" -- Scroll for more ({current_idx + 1}/{len(items)}) -- ",
                    color_info,
                )

            stdscr.refresh()

            key = stdscr.getch()

            if key in [curses.KEY_UP, ord("k")]:
                current_idx = (current_idx - 1) % len(items)
            elif key in [curses.KEY_DOWN, ord("j")]:
                current_idx = (current_idx + 1) % len(items)
            elif key == ord(" "):
                selected[current_idx] = not selected[current_idx]
            elif key == ord("a"):
                if all(selected):
                    selected = [False] * len(items)
                else:
                    selected = [True] * len(items)
            elif key in [10, 13]:  # Enter
                break
            elif key in [ord("q"), 27]:  # 'q' or Esc
                return None

        return [items[i] for i, sel in enumerate(selected) if sel]

    return curses.wrapper(main_curses)
