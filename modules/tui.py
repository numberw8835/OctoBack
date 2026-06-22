import curses

def run_tui(items, select_mode=True):
    """
    Simple TUI for selecting items.
    
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
        
        while True:
            stdscr.clear()
            max_y, max_x = stdscr.getmaxyx()
            
            if max_y < 10 or max_x < 30:
                stdscr.addstr(0, 0, "Terminal too small.")
                stdscr.refresh()
                stdscr.getch()
                return None

            # Display items
            for i, item in enumerate(items):
                if i == current_idx:
                    marker = ">" 
                else:
                    marker = " "
                
                if select_mode and selected[i]:
                    check = "[x]"
                elif select_mode:
                    check = "[ ]"
                else:
                    check = ""
                    
                display_text = f"{marker} {check} {item}"
                if i < max_y - 3:  # Leave room for instructions
                    stdscr.addstr(i + 1, 2, display_text[:max_x-4])

            # Show instructions
            if select_mode:
                stdscr.addstr(max_y - 2, 2, "j/k: move • space: select • enter: confirm • o: restore .octoback • q: quit")
            else:
                stdscr.addstr(max_y - 2, 2, "j/k: move • enter/q: quit")

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