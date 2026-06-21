import curses


def run_tui(items, select_mode=True):
    if not items:
        return [] if select_mode else None

    def main_curses(stdscr):
        try:
            curses.curs_set(0)  # Hide cursor by default
        except Exception:
            pass
        stdscr.keypad(True)
        try:
            curses.use_default_colors()
        except Exception:
            pass

        # Initialize colors
        if curses.has_colors():
            curses.init_pair(1, curses.COLOR_CYAN, -1)
            curses.init_pair(2, curses.COLOR_GREEN, -1)
            curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_CYAN)
            curses.init_pair(4, curses.COLOR_YELLOW, -1)
            color_info = curses.color_pair(1)
            color_selected = curses.color_pair(2)
            color_highlight = curses.color_pair(3)
            color_match = curses.color_pair(4)
        else:
            color_info = curses.A_NORMAL
            color_selected = curses.A_BOLD
            color_highlight = curses.A_REVERSE
            color_match = curses.A_UNDERLINE

        selected = [False] * len(items)
        current_idx = 0
        start_idx = 0

        # Vim-like search state
        search_mode = False
        search_query = ""
        matches = []
        match_idx = -1
        pre_search_idx = 0
        last_search_query = ""

        # Pending 'g' for double-tap 'gg'
        pending_g = False

        def update_search():
            nonlocal matches, match_idx, current_idx
            if not search_query:
                matches = []
                match_idx = -1
                return

            matches = [
                i
                for i, item in enumerate(items)
                if search_query.lower() in item.lower()
            ]
            if matches:
                if current_idx in matches:
                    match_idx = matches.index(current_idx)
                else:
                    # Jump cursor to the first match at or after current cursor
                    next_matches = [m for m in matches if m >= current_idx]
                    if next_matches:
                        current_idx = next_matches[0]
                    else:
                        current_idx = matches[0]
                    match_idx = matches.index(current_idx)
            else:
                match_idx = -1

        while True:
            stdscr.erase()
            max_y, max_x = stdscr.getmaxyx()

            # Dynamic Margin adjustments based on screen size
            margin_top = 2
            margin_left = 4
            margin_right = 4
            margin_bottom = 3

            if max_x < 60:
                margin_left = 2
                margin_right = 2
            if max_y < 16:
                margin_top = 1
                margin_bottom = 2

            box_top = margin_top
            box_bottom = max_y - margin_bottom - 1
            box_left = margin_left
            box_right = max_x - margin_right - 1
            visible_height = box_bottom - box_top - 1

            if visible_height <= 0 or (box_right - box_left) < 10:
                stdscr.addstr(0, 0, "Terminal too small.", color_info)
                stdscr.refresh()
                key = stdscr.getch()
                if key in [ord("q"), 27]:
                    return None
                continue

            # Scroll viewport adjustment
            if current_idx < start_idx:
                start_idx = current_idx
            elif current_idx >= start_idx + visible_height:
                start_idx = current_idx - visible_height + 1

            # 1. Render Header
            stdscr.addstr(
                margin_top - 1,
                margin_left,
                "OctoBack Restore" if select_mode else "OctoBack Index",
                curses.A_BOLD | color_info,
            )

            # 2. Render Box Borders (Fancy Rounded Borders)
            try:
                # Top border
                stdscr.addstr(
                    box_top,
                    box_left,
                    "╭" + "─" * (box_right - box_left - 1) + "╮",
                    color_info,
                )
                # Side borders
                for y in range(box_top + 1, box_bottom):
                    stdscr.addstr(y, box_left, "│", color_info)
                    stdscr.addstr(y, box_right, "│", color_info)
                # Bottom border
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

                # Limit content width to prevent wrapping/spilling out of the box
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
                    # Pad line with spaces for full background highlighted bar inside the box borders
                    padded_line = line_text.ljust(box_right - box_left - 1)
                    stdscr.addstr(y, box_left + 1, padded_line, color_highlight)
                else:
                    # Draw normal row with checkmarks and search highlight
                    stdscr.addstr(y, box_left + 1, f" {bullet} ", curses.A_NORMAL)

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

                    active_query = search_query if search_mode else last_search_query
                    matched = False
                    if active_query:
                        pos = display_text.lower().find(active_query.lower())
                        if pos != -1:
                            prefix = display_text[:pos]
                            match_part = display_text[pos : pos + len(active_query)]
                            suffix = display_text[pos + len(active_query) :]

                            stdscr.addstr(y, text_x, prefix, curses.A_NORMAL)
                            stdscr.addstr(
                                y,
                                text_x + len(prefix),
                                match_part,
                                color_match | curses.A_BOLD,
                            )
                            stdscr.addstr(
                                y,
                                text_x + len(prefix) + len(match_part),
                                suffix,
                                curses.A_NORMAL,
                            )
                            matched = True

                    if not matched:
                        stdscr.addstr(y, text_x, display_text, curses.A_NORMAL)

            # 4. Render Status Line
            status_y = box_bottom + 1
            stdscr.move(status_y, 0)
            stdscr.clrtoeol()

            if select_mode:
                status_text = f"  {current_idx + 1}/{len(items)} | Selected: {sum(selected)}/{len(items)}"
            else:
                status_text = f"  {current_idx + 1}/{len(items)}"

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
                    curses.curs_set(1)  # Show cursor for text entry
                except Exception:
                    pass
                stdscr.addstr(prompt_y, margin_left, f"/{search_query}")
                stdscr.move(prompt_y, margin_left + 1 + len(search_query))
            else:
                try:
                    curses.curs_set(0)  # Hide cursor in normal mode
                except Exception:
                    pass
                if select_mode:
                    help_text = "j/k: down/up  •  space: select  •  a: toggle all  •  /: search  •  enter: restore  •  q/esc: quit"
                else:
                    help_text = "j/k: down/up  •  /: search  •  enter/q/esc: quit"
                stdscr.addstr(prompt_y, margin_left, help_text, curses.A_DIM)

            stdscr.refresh()

            # Wait for user input
            key = stdscr.getch()

            if key == curses.KEY_RESIZE:
                continue

            if search_mode:
                if key in [10, 13]:  # Enter accepts search
                    last_search_query = search_query
                    search_mode = False
                elif key == 27:  # ESC cancels search, resets cursor position
                    search_query = ""
                    current_idx = pre_search_idx
                    search_mode = False
                elif key == 7:  # Ctrl-G: Next match
                    if matches:
                        match_idx = (match_idx + 1) % len(matches)
                        current_idx = matches[match_idx]
                elif key == 20:  # Ctrl-T: Prev match
                    if matches:
                        match_idx = (match_idx - 1) % len(matches)
                        current_idx = matches[match_idx]
                elif key in [curses.KEY_BACKSPACE, 127, 8, ord("\b")]:
                    if len(search_query) > 0:
                        search_query = search_query[:-1]
                        update_search()
                elif 32 <= key <= 126:
                    search_query += chr(key)
                    update_search()
            else:
                # Normal Mode Keys
                if key in [curses.KEY_UP, ord("k")]:
                    current_idx = (current_idx - 1) % len(items)
                    pending_g = False
                elif key in [curses.KEY_DOWN, ord("j")]:
                    current_idx = (current_idx + 1) % len(items)
                    pending_g = False
                elif key == 4:  # Ctrl-D: Page Down (scroll half-page)
                    page_step = max(1, visible_height // 2)
                    current_idx = min(len(items) - 1, current_idx + page_step)
                    pending_g = False
                elif key == 21:  # Ctrl-U: Page Up (scroll half-page)
                    page_step = max(1, visible_height // 2)
                    current_idx = max(0, current_idx - page_step)
                    pending_g = False
                elif key == ord("g"):
                    if pending_g:
                        current_idx = 0
                        pending_g = False
                    else:
                        pending_g = True
                elif key == ord("G"):
                    current_idx = len(items) - 1
                    pending_g = False
                elif key == ord(" "):
                    if select_mode:
                        selected[current_idx] = not selected[current_idx]
                    pending_g = False
                elif key == ord("a"):
                    if select_mode:
                        if all(selected):
                            selected = [False] * len(items)
                        else:
                            selected = [True] * len(items)
                    pending_g = False
                elif key == ord("/"):
                    search_mode = True
                    pre_search_idx = current_idx
                    search_query = ""
                    matches = []
                    match_idx = -1
                    pending_g = False
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
                elif key in [10, 13]:  # Enter
                    break
                elif key in [ord("q"), 27]:  # 'q' or Esc
                    return None
                else:
                    pending_g = False

        if select_mode:
            return [items[i] for i, sel in enumerate(selected) if sel]
        else:
            return items[current_idx]

    return curses.wrapper(main_curses)
