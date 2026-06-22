import curses

def run_tui(items, select_mode=True):
    """
    Dynamic, scrollable TUI for selecting items with search and page navigation.
    
    :param items: List of string items (paths) to display
    :param select_mode: True to allow selection; False for view-only
    """
    if not items:
        return [] if select_mode else None

    def main_curses(stdscr):
        curses.curs_set(0)
        stdscr.keypad(True)
        
        selected_set = set()
        current_idx = 0
        scroll_offset = 0
        search_query = ""
        in_search_mode = False
        
        while True:
            stdscr.clear()
            max_y, max_x = stdscr.getmaxyx()
            
            # Require minimum dimensions
            if max_y < 8 or max_x < 30:
                stdscr.addstr(0, 0, "Terminal too small.")
                stdscr.refresh()
                stdscr.getch()
                return None

            # Calculate dynamic visible rows (leaving room for items, search bar, and instructions)
            max_rows = max_y - 4
            if max_rows <= 0:
                max_rows = 1

            # Filter items based on the search query
            if search_query:
                filtered_items = [item for item in items if search_query.lower() in item.lower()]
            else:
                filtered_items = items

            # Constrain current_idx within filtered bounds
            if not filtered_items:
                current_idx = 0
            else:
                current_idx = max(0, min(current_idx, len(filtered_items) - 1))

            # Adjust scroll_offset to keep current_idx visible on screen
            if current_idx < scroll_offset:
                scroll_offset = current_idx
            elif current_idx >= scroll_offset + max_rows:
                scroll_offset = current_idx - max_rows + 1

            # Make sure scroll_offset is within valid bounds
            if scroll_offset > len(filtered_items) - max_rows:
                scroll_offset = max(0, len(filtered_items) - max_rows)
            if scroll_offset < 0:
                scroll_offset = 0

            # Render visible items
            if not filtered_items:
                try:
                    stdscr.addstr(1, 2, "¬ No matches found", curses.A_DIM)
                except curses.error:
                    pass
            else:
                visible_items = filtered_items[scroll_offset : scroll_offset + max_rows]
                for idx, item in enumerate(visible_items):
                    actual_idx = scroll_offset + idx
                    
                    if actual_idx == current_idx:
                        marker = ">"
                        attr = curses.A_REVERSE
                    else:
                        marker = " "
                        attr = curses.A_NORMAL
                    
                    if select_mode and item in selected_set:
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

            # Render search/filter bar
            if in_search_mode:
                search_line = f"Search: {search_query}█"
                search_attr = curses.A_BOLD
            elif search_query:
                search_line = f"Filter: {search_query} (press Esc to clear)"
                search_attr = curses.A_DIM
            else:
                search_line = ""
                search_attr = curses.A_NORMAL

            if search_line:
                try:
                    stdscr.addstr(max_y - 3, 2, search_line[:max_x - 4], search_attr)
                except curses.error:
                    pass

            # Display instructions/status bar at the bottom
            if in_search_mode:
                instructions = "type to search • backspace: delete • enter: lock filter • esc: cancel"
            else:
                instructions = (
                    "j/k: move • PgUp/PgDn • space: select • /: search • enter: confirm • o: restore .octoback • q: quit"
                    if select_mode
                    else "j/k: move • PgUp/PgDn • /: search • enter/q: quit"
                )
            
            # Show counter if there are hidden items
            if len(filtered_items) > max_rows:
                indicator = f" ({current_idx + 1}/{len(filtered_items)})"
                status_text = instructions[:max_x - len(indicator) - 4] + indicator
            else:
                status_text = instructions[:max_x - 4]
                
            try:
                stdscr.addstr(max_y - 2, 2, status_text)
            except curses.error:
                pass

            stdscr.refresh()
            
            key = stdscr.getch()
            
            if in_search_mode:
                if key in [27]:  # Esc (cancel search)
                    search_query = ""
                    in_search_mode = False
                elif key in [10, 13]:  # Enter (accept filter)
                    in_search_mode = False
                elif key in [8, 127, curses.KEY_BACKSPACE]:  # Backspace
                    if len(search_query) > 0:
                        search_query = search_query[:-1]
                elif 32 <= key <= 126:  # Normal typing
                    search_query += chr(key)
            else:
                if key in [ord('k'), curses.KEY_UP]:
                    if filtered_items:
                        current_idx = (current_idx - 1) % len(filtered_items)
                elif key in [ord('j'), curses.KEY_DOWN]:
                    if filtered_items:
                        current_idx = (current_idx + 1) % len(filtered_items)
                elif key in [curses.KEY_PPAGE, 2, 21]:  # Page Up, Ctrl+B, Ctrl+U
                    if filtered_items:
                        current_idx = max(0, current_idx - max_rows)
                elif key in [curses.KEY_NPAGE, 4, 6]:  # Page Down, Ctrl+D, Ctrl+F
                    if filtered_items:
                        current_idx = min(len(filtered_items) - 1, current_idx + max_rows)
                elif key == ord('/'):
                    in_search_mode = True
                elif key == ord(' ') and select_mode:
                    if filtered_items:
                        current_item = filtered_items[current_idx]
                        if current_item in selected_set:
                            selected_set.remove(current_item)
                        else:
                            selected_set.add(current_item)
                elif key == ord('o') and select_mode:
                    return "__restore_octoback__"
                elif key in [10, 13]:  # Enter
                    break
                elif key in [27]:  # Esc
                    if search_query:
                        search_query = ""
                        current_idx = 0
                    else:
                        return None
                elif key in [ord('q')]:  # q key
                    return None

        if select_mode:
            return [item for item in items if item in selected_set]
        else:
            return filtered_items[current_idx] if filtered_items else None

    return curses.wrapper(main_curses)