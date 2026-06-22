import curses

def run_tui(items, select_mode=True):
    """
    Dynamic, scrollable TUI for selecting items.
    
    :param items: List of string items (paths) to display
    :param select_mode: True to allow selection; False for view-only
    """
    if not items:
        return [] if select_mode else None

    def main_curses(stdscr):
        curses.curs_set(0)
        stdscr.keypad(True)
        
        selected = [False] * len(items)
        current_idx = 0
        scroll_offset = 0
        
        while True:
            stdscr.clear()
            max_y, max_x = stdscr.getmaxyx()
            
            # Require minimum dimensions
            if max_y < 8 or max_x < 30:
                stdscr.addstr(0, 0, "Terminal too small.")
                stdscr.refresh()
                stdscr.getch()
                return None

            # Calculate dynamic visible rows (leaving room for top border and bottom instructions)
            max_rows = max_y - 3
            if max_rows <= 0:
                max_rows = 1

            # Adjust scroll_offset to keep current_idx visible on screen
            if current_idx < scroll_offset:
                scroll_offset = current_idx
            elif current_idx >= scroll_offset + max_rows:
                scroll_offset = current_idx - max_rows + 1

            # Render visible items
            visible_items = items[scroll_offset : scroll_offset + max_rows]
            for idx, item in enumerate(visible_items):
                actual_idx = scroll_offset + idx
                
                if actual_idx == current_idx:
                    marker = ">"
                    attr = curses.A_REVERSE
                else:
                    marker = " "
                    attr = curses.A_NORMAL
                
                if select_mode and selected[actual_idx]:
                    check = "[x]"
                elif select_mode:
                    check = "[ ]"
                else:
                    check = ""
                    
                display_text = f"{marker} {check} {item}"
                # Truncate and pad to create a uniform selection bar
                display_text = display_text[:max_x - 4].ljust(max_x - 4)
                
                try:
                    stdscr.addstr(idx + 1, 2, display_text, attr)
                except curses.error:
                    pass

            # Display instructions/status bar at the bottom
            instructions = "j/k: move • space: select • enter: confirm • o: restore .octoback • q: quit" if select_mode else "j/k: move • enter/q: quit"
            
            # Show counter if there are hidden items
            if len(items) > max_rows:
                indicator = f" ({current_idx + 1}/{len(items)})"
                status_text = instructions[:max_x - len(indicator) - 4] + indicator
            else:
                status_text = instructions[:max_x - 4]
                
            try:
                stdscr.addstr(max_y - 2, 2, status_text)
            except curses.error:
                pass

            stdscr.refresh()
            
            key = stdscr.getch()
            
            if key in [ord('k'), curses.KEY_UP]:
                current_idx = (current_idx - 1) % len(items)
            elif key in [ord('j'), curses.KEY_DOWN]:
                current_idx = (current_idx + 1) % len(items)
            elif key == ord(' ') and select_mode:
                selected[current_idx] = not selected[current_idx]
            elif key == ord('o') and select_mode:
                return "__restore_octoback__"
            elif key in [10, 13]:  # Enter
                break
            elif key in [ord('q'), 27]:  # Esc or q
                return None

        if select_mode:
            return [items[i] for i, sel in enumerate(selected) if sel]
        else:
            return items[current_idx]

    return curses.wrapper(main_curses)