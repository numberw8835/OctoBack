import curses


def run_tui(items, select_mode=True):
    """
    Renders an interactive Terminal User Interface (TUI) using curses.
    Allows scrolling, searching (Vim-like), selecting items, and confirming operations.
    
    :param items: List of string items (paths) to display
    :param select_mode: True to allow multiple checkmark selection; False for view-only browsing
    """
    if not items:
        return [] if select_mode else None

    # Internal wrapper function executing curses loop
    def main_curses(stdscr):
        try:
            # Hide standard terminal cursor by default for clean visual display
            curses.curs_set(0)  
        except Exception:
            pass
        # Enable special key capture (arrow keys, backspace, etc.)
        stdscr.keypad(True)
        try:
            # Enable transparent/default terminal background colors
            curses.use_default_colors()
        except Exception:
            pass

        # Initialize color configurations if the user's terminal supports colors
        if curses.has_colors():
            # Pair 1: Info headings (CYAN text)
            curses.init_pair(1, curses.COLOR_CYAN, -1)
            # Pair 2: Checked/Selected indicators (GREEN text)
            curses.init_pair(2, curses.COLOR_GREEN, -1)
            # Pair 3: Active line cursor highlighter (BLACK text on CYAN background)
            curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_CYAN)
            # Pair 4: Search query matching character highlight (YELLOW text)
            curses.init_pair(4, curses.COLOR_YELLOW, -1)
            
            color_info = curses.color_pair(1)
            color_selected = curses.color_pair(2)
            color_highlight = curses.color_pair(3)
            color_match = curses.color_pair(4)
        else:
            # Non-color fallback styles
            color_info = curses.A_NORMAL
            color_selected = curses.A_BOLD
            color_highlight = curses.A_REVERSE
            color_match = curses.A_UNDERLINE

        # Viewport and selection tracking state
        selected = [False] * len(items) # Boolean array indicating if items are checked
        current_idx = 0                  # Cursor line index
        start_idx = 0                    # Viewport scrolling pagination index

        # Vim-like search state
        search_mode = False
        search_query = ""
        matches = []
        match_idx = -1
        pre_search_idx = 0
        last_search_query = ""

        # Pending 'g' for double-tap 'gg'
        pending_g = False

        # Updates search matches list and cursor position based on active query
        def update_search():
            nonlocal matches, match_idx, current_idx
            if not search_query:
                matches = []
                match_idx = -1
                return

            # Find all item indexes containing the search query substring
            matches = [
                i
                for i, item in enumerate(items)
                if search_query.lower() in item.lower()
            ]
            if matches:
                # If current item matches, keep cursor on it
                if current_idx in matches:
                    match_idx = matches.index(current_idx)
                else:
                    # Otherwise, jump cursor to the first match at or after current cursor index
                    next_matches = [m for m in matches if m >= current_idx]
                    if next_matches:
                        current_idx = next_matches[0]
                    else:
                        current_idx = matches[0]
                    match_idx = matches.index(current_idx)
            else:
                match_idx = -1

        # Core rendering and interaction loop
        while True:
            stdscr.erase()
            # Retrieve current dimensions of the active curses terminal window
            max_y, max_x = stdscr.getmaxyx()

            # Dynamic layout margins depending on terminal sizing
            margin_top = 2
            margin_left = 4
            margin_right = 4
            margin_bottom = 3

            # Compress margins on smaller display interfaces
            if max_x < 60:
                margin_left = 2
                margin_right = 2
            if max_y < 16:
                margin_top = 1
                margin_bottom = 2

            # Compute boundary coordinate points for drawing container border boxes
            box_top = margin_top
            box_bottom = max_y - margin_bottom - 1
            box_left = margin_left
            box_right = max_x - margin_right - 1
            visible_height = box_bottom - box_top - 1

            # Validate that the screen is large enough to render at least minimal content layout
            if visible_height <= 0 or (box_right - box_left) < 10:
                stdscr.addstr(0, 0, "Terminal too small.", color_info)
                stdscr.refresh()
                key = stdscr.getch()
                if key in [ord("q"), 27]:
                    return None
                continue

            # Scroll viewport adjustment: keep current cursor index within the visible height bounds
            if current_idx < start_idx:
                start_idx = current_idx
            elif current_idx >= start_idx + visible_height:
                start_idx = current_idx - visible_height + 1

            # 1. Render Header: Renders title on the top margin
            stdscr.addstr(
                margin_top - 1,
                margin_left,
                "OctoBack Restore" if select_mode else "OctoBack Index",
                curses.A_BOLD | color_info,
            )

            # 2. Render Box Borders (Fancy Unicode Rounded Borders: ╭ ─ ╮ │ ╰ ╯)
            try:
                # Top border row
                stdscr.addstr(
                    box_top,
                    box_left,
                    "╭" + "─" * (box_right - box_left - 1) + "╮",
                    color_info,
                )
                # Vertical side border columns
                for y in range(box_top + 1, box_bottom):
                    stdscr.addstr(y, box_left, "│", color_info)
                    stdscr.addstr(y, box_right, "│", color_info)
                # Bottom border row
                stdscr.addstr(
                    box_bottom,
                    box_left,
                    "╰" + "─" * (box_right - box_left - 1) + "╯",
                    color_info,
                )
            except Exception:
                pass

            # 3. Render List Items Inside Box
            for i in range(min(visible_height, len(items) - start_idx)):
                idx = start_idx + i
                item_text = items[idx]
                is_current = idx == current_idx
                is_selected = selected[idx]

                y = box_top + 1 + i

                chk_box = "[x]" if is_selected else "[ ]"
                bullet = "▶" if is_current else " "

                # Limit content width to prevent text wrapping or spilling out of the border box
                if select_mode:
                    max_text_len = box_right - box_left - 8
                else:
                    max_text_len = box_right - box_left - 4

                if len(item_text) > max_text_len:
                    display_text = item_text[: max_text_len - 3] + "..."
                else:
                    display_text = item_text

                if select_mode:
                    line_text = f" {bullet} {chk_box} {display_text}"
                else:
                    line_text = f" {bullet} {display_text}"

                if is_current:
                    # Draw full highlighted background bar spanning the row width
                    padded_line = line_text.ljust(box_right - box_left - 1)
                    stdscr.addstr(y, box_left + 1, padded_line, color_highlight)
                else:
                    # Draw normal row. Start with bullet
                    stdscr.addstr(y, box_left + 1, f" {bullet} ", curses.A_NORMAL)

                    # If in selection mode, draw the check-box state with color highlight
                    if select_mode:
                        if is_selected:
                            stdscr.addstr(
                                y, box_left + 4, chk_box, color_selected | curses.A_BOLD
                            )
                        else:
                            stdscr.addstr(y, box_left + 4, chk_box, curses.A_NORMAL)
                        stdscr.addstr(y, box_left + 7, " ", curses.A_NORMAL)
                        text_x = box_left + 8
                    else:
                        text_x = box_left + 4

                    # Highlight matching substring if a search query is active
                    active_query = search_query if search_mode else last_search_query
                    matched = False
                    if active_query:
                        # Find the match position inside display_text
                        pos = display_text.lower().find(active_query.lower())
                        if pos != -1:
                            # Split display_text into three parts: prefix, match, and suffix
                            prefix = display_text[:pos]
                            match_part = display_text[pos : pos + len(active_query)]
                            suffix = display_text[pos + len(active_query) :]

                            # Draw prefix (normal style)
                            stdscr.addstr(y, text_x, prefix, curses.A_NORMAL)
                            # Draw matched query string (colored & bold highlight style)
                            stdscr.addstr(
                                y,
                                text_x + len(prefix),
                                match_part,
                                color_match | curses.A_BOLD,
                            )
                            # Draw suffix (normal style)
                            stdscr.addstr(
                                y,
                                text_x + len(prefix) + len(match_part),
                                suffix,
                                curses.A_NORMAL,
                            )
                            matched = True

                    if not matched:
                        stdscr.addstr(y, text_x, display_text, curses.A_NORMAL)

            # 4. Render Status Line: Displays cursor index, selection count, and active search match metadata
            status_y = box_bottom + 1
            stdscr.move(status_y, 0)
            stdscr.clrtoeol()

            if select_mode:
                status_text = f"  {current_idx + 1}/{len(items)} | Selected: {sum(selected)}/{len(items)}"
            else:
                status_text = f"  {current_idx + 1}/{len(items)}"

            # Append active search status information (e.g. Match 2/5)
            active_query = search_query if search_mode else last_search_query
            if active_query:
                if matches:
                    status_text += f" | Match {match_idx + 1}/{len(matches)}"
                else:
                    status_text += " | No matches"

            stdscr.addstr(status_y, margin_left, status_text, curses.A_DIM)

            # 5. Render Footer (Command Help or Search Prompt)
            prompt_y = box_bottom + 2
            stdscr.move(prompt_y, 0)
            stdscr.clrtoeol()

            if search_mode:
                try:
                    # Show curses cursor explicitly while editing search input text
                    curses.curs_set(1)  
                except Exception:
                    pass
                stdscr.addstr(prompt_y, margin_left, f"/{search_query}")
                stdscr.move(prompt_y, margin_left + 1 + len(search_query))
            else:
                try:
                    # Hide cursor when browsing in normal navigation mode
                    curses.curs_set(0)  
                except Exception:
                    pass
                if select_mode:
                    help_text = "j/k: down/up  •  space: select  •  a: toggle all  •  /: search  •  enter: restore  •  q/esc: quit"
                else:
                    help_text = "j/k: down/up  •  /: search  •  enter/q/esc: quit"
                stdscr.addstr(prompt_y, margin_left, help_text, curses.A_DIM)

            stdscr.refresh()

            # Block and wait for key input event
            key = stdscr.getch()

            # Handle terminal resize event by re-rendering layout bounds
            if key == curses.KEY_RESIZE:
                continue

            # Keyboard Input Handling: Search Mode
            if search_mode:
                if key in [10, 13]:  # Enter key confirms and saves search string
                    last_search_query = search_query
                    search_mode = False
                elif key == 27:  # ESC key cancels search and restores pre-search cursor index
                    search_query = ""
                    current_idx = pre_search_idx
                    search_mode = False
                elif key == 7:  # Ctrl-G: Move cursor forward to next match
                    if matches:
                        match_idx = (match_idx + 1) % len(matches)
                        current_idx = matches[match_idx]
                elif key == 20:  # Ctrl-T: Move cursor backward to previous match
                    if matches:
                        match_idx = (match_idx - 1) % len(matches)
                        current_idx = matches[match_idx]
                elif key in [curses.KEY_BACKSPACE, 127, 8, ord("\b")]: # Backspace handlers
                    if len(search_query) > 0:
                        search_query = search_query[:-1]
                        update_search()
                elif 32 <= key <= 126: # Printable characters are added to search query
                    search_query += c                # Keyboard Input Handling: Normal navigation mode
                # Up cursor moves cursor up (k in Vim)
                if key in [curses.KEY_UP, ord("k")]:
                    current_idx = (current_idx - 1) % len(items)
                    pending_g = False
                # Down cursor moves cursor down (j in Vim)
                elif key in [curses.KEY_DOWN, ord("j")]:
                    current_idx = (current_idx + 1) % len(items)
                    pending_g = False
                # Page down scrolling (Ctrl-D in Vim)
                elif key == 4:  # Ctrl-D: Page Down (scroll half-page)
                    page_step = max(1, visible_height // 2)
                    current_idx = min(len(items) - 1, current_idx + page_step)
                    pending_g = False
                # Page up scrolling (Ctrl-U in Vim)
                elif key == 21:  # Ctrl-U: Page Up (scroll half-page)
                    page_step = max(1, visible_height // 2)
                    current_idx = max(0, current_idx - page_step)
                    pending_g = False
                # Vim double-tap 'gg' to jump to start of list
                elif key == ord("g"):
                    if pending_g:
                        current_idx = 0
                        pending_g = False
                    else:
                        pending_g = True
                # Vim 'G' to jump to end of list
                elif key == ord("G"):
                    current_idx = len(items) - 1
                    pending_g = False
                # Spacebar toggles check/selection status on the currently focused item
                elif key == ord(" "):
                    if select_mode:
                        selected[current_idx] = not selected[current_idx]
                    pending_g = False
                # 'a' key toggles selection for all items (select all or deselect all)
                elif key == ord("a"):
                    if select_mode:
                        if all(selected):
                            selected = [False] * len(items)
                        else:
                            selected = [True] * len(items)
                    pending_g = False
                # '/' key activates Vim-like search mode
                elif key == ord("/"):
                    search_mode = True
                    pre_search_idx = current_idx
                    search_query = ""
                    matches = []
                    match_idx = -1
                    pending_g = False
                # 'n' key jumps to the next match of the active search query
                elif key == ord("n"):
                    pending_g = False
                    if last_search_query:
                        matches = [
                            i
                            for i, item in enumerate(items)
                            if last_search_query.lower() in item.lower()
                        ]
                        if matches:
                            next_matches = [m for m in matches if m > current_idx]
                            if next_matches:
                                current_idx = next_matches[0]
                            else:
                                current_idx = matches[0]
                            match_idx = matches.index(current_idx)
                # 'N' key (Shift-N) jumps to the previous match of the active search query
                elif key == ord("N"):
                    pending_g = False
                    if last_search_query:
                        matches = [
                            i
                            for i, item in enumerate(items)
                            if last_search_query.lower() in item.lower()
                        ]
                        if matches:
                            prev_matches = [m for m in matches if m < current_idx]
                            if prev_matches:
                                current_idx = prev_matches[-1]
                            else:
                                current_idx = matches[-1]
                            match_idx = matches.index(current_idx)
                # Enter key confirms selection and exits loop
                elif key in [10, 13]:  # Enter
                    break
                # 'q' or ESC cancels TUI session and returns None
                elif key in [ord("q"), 27]:  # 'q' or Esc
                    return None
                else:
                    pending_g = False

        # Returns selected items in multi-select mode, or single highlighted item in single-select mode
        if select_mode:
            return [items[i] for i, sel in enumerate(selected) if sel]
        else:
            return items[current_idx]

    # curses.wrapper safely initializes terminal settings and cleans up upon exit (even on exception)
    return curses.wrapper(main_curses)
