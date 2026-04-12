#!/usr/bin/env python3
"""Generate a small ncurses starter app with clean UI boundaries."""

from __future__ import annotations

import argparse
from pathlib import Path


def c_source(app_name: str) -> str:
    return f"""#include <locale.h>
#include <ncurses.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef enum {{
    FOCUS_LIST = 0,
    FOCUS_DETAIL = 1,
}} FocusArea;

typedef struct {{
    int y;
    int x;
    int h;
    int w;
}} Rect;

typedef struct {{
    Rect header;
    Rect list;
    Rect detail;
    Rect status;
    bool too_small;
}} Layout;

typedef struct {{
    bool running;
    bool needs_redraw;
    FocusArea focus;
    int selected_index;
    int list_scroll;
    int detail_scroll;
    char status[128];
}} AppState;

static bool g_curses_active = false;

static void restore_terminal(void) {{
    if (g_curses_active) {{
        curs_set(1);
        echo();
        nocbreak();
        endwin();
        g_curses_active = false;
    }}
}}

static int init_terminal(void) {{
    setlocale(LC_ALL, "");

    if (initscr() == NULL) {{
        return -1;
    }}

    g_curses_active = true;
    atexit(restore_terminal);

    cbreak();
    noecho();
    keypad(stdscr, TRUE);
    curs_set(0);

    if (has_colors()) {{
        start_color();
        use_default_colors();
        init_pair(1, COLOR_BLACK, COLOR_CYAN);
        init_pair(2, COLOR_YELLOW, -1);
    }}

    return 0;
}}

static Layout compute_layout(void) {{
    Layout layout;
    int rows = 0;
    int cols = 0;

    getmaxyx(stdscr, rows, cols);
    layout.too_small = rows < 8 || cols < 40;
    layout.header = (Rect){{0, 0, 1, cols}};
    layout.status = (Rect){{rows - 1, 0, 1, cols}};

    if (layout.too_small) {{
        layout.list = (Rect){{1, 0, 0, 0}};
        layout.detail = (Rect){{1, 0, 0, 0}};
        return layout;
    }}

    int body_height = rows - 2;
    int list_width = cols / 3;
    if (list_width < 18) {{
        list_width = 18;
    }}

    layout.list = (Rect){{1, 0, body_height, list_width}};
    layout.detail = (Rect){{1, list_width, body_height, cols - list_width}};
    return layout;
}}

static void update_status(AppState *state, const char *message) {{
    snprintf(state->status, sizeof(state->status), "%s", message);
}}

static void render_header(const Layout *layout, const AppState *state) {{
    mvhline(layout->header.y, layout->header.x, ' ', layout->header.w);
    if (has_colors()) {{
        attron(COLOR_PAIR(1));
    }}
    mvprintw(layout->header.y, layout->header.x + 1, "{app_name}  Tab switches focus  q quits");
    if (has_colors()) {{
        attroff(COLOR_PAIR(1));
    }}
    (void)state;
}}

static void render_list(const Layout *layout, const AppState *state) {{
    static const char *items[] = {{
        "Overview",
        "Jobs",
        "Metrics",
        "Logs",
        "Settings",
        "Help",
    }};
    const int item_count = (int)(sizeof(items) / sizeof(items[0]));
    int visible_rows = layout->list.h;
    int row = 0;

    for (row = 0; row < visible_rows; ++row) {{
        int index = state->list_scroll + row;
        mvhline(layout->list.y + row, layout->list.x, ' ', layout->list.w);
        if (index >= item_count) {{
            continue;
        }}

        if (index == state->selected_index) {{
            if (has_colors()) {{
                attron(COLOR_PAIR(2));
            }}
            mvprintw(layout->list.y + row, layout->list.x + 1, "%c %s",
                     state->focus == FOCUS_LIST ? '>' : '*', items[index]);
            if (has_colors()) {{
                attroff(COLOR_PAIR(2));
            }}
        }} else {{
            mvprintw(layout->list.y + row, layout->list.x + 1, "  %s", items[index]);
        }}
    }}
}}

static void render_detail(const Layout *layout, const AppState *state) {{
    mvhline(layout->detail.y, layout->detail.x, ' ', layout->detail.w);
    mvprintw(layout->detail.y, layout->detail.x + 1, "Focused pane: %s",
             state->focus == FOCUS_LIST ? "list" : "detail");
    mvprintw(layout->detail.y + 2, layout->detail.x + 1, "Selected row: %d", state->selected_index);
    mvprintw(layout->detail.y + 3, layout->detail.x + 1, "List scroll: %d", state->list_scroll);
    mvprintw(layout->detail.y + 4, layout->detail.x + 1, "Detail scroll: %d", state->detail_scroll);
    mvprintw(layout->detail.y + 6, layout->detail.x + 1, "Keep state, layout, input, and paint separate.");
}}

static void render_status(const Layout *layout, const AppState *state) {{
    mvhline(layout->status.y, layout->status.x, ' ', layout->status.w);
    mvprintw(layout->status.y, layout->status.x + 1, "%s", state->status);
}}

static void render_too_small(int rows, int cols) {{
    erase();
    mvprintw(0, 0, "Terminal too small");
    mvprintw(1, 0, "Need at least 8 rows x 40 cols, have %d x %d", rows, cols);
    mvprintw(3, 0, "Resize the terminal or simplify the layout.");
    refresh();
}}

static void render_app(const Layout *layout, const AppState *state) {{
    if (layout->too_small) {{
        int rows = 0;
        int cols = 0;
        getmaxyx(stdscr, rows, cols);
        render_too_small(rows, cols);
        return;
    }}

    erase();
    render_header(layout, state);
    render_list(layout, state);
    render_detail(layout, state);
    render_status(layout, state);
    refresh();
}}

static void move_selection(AppState *state, int delta) {{
    const int max_index = 5;
    int next = state->selected_index + delta;
    if (next < 0) {{
        next = 0;
    }}
    if (next > max_index) {{
        next = max_index;
    }}
    state->selected_index = next;
}}

static void sync_view_state(AppState *state, const Layout *layout) {{
    const int max_index = 5;
    if (state->selected_index < 0) {{
        state->selected_index = 0;
    }}
    if (state->selected_index > max_index) {{
        state->selected_index = max_index;
    }}
    if (state->detail_scroll < 0) {{
        state->detail_scroll = 0;
    }}
    if (layout->too_small) {{
        state->list_scroll = 0;
        state->detail_scroll = 0;
        return;
    }}

    int visible_rows = layout->list.h;
    if (visible_rows < 1) {{
        visible_rows = 1;
    }}
    if (state->selected_index < state->list_scroll) {{
        state->list_scroll = state->selected_index;
    }}
    if (state->selected_index >= state->list_scroll + visible_rows) {{
        state->list_scroll = state->selected_index - visible_rows + 1;
    }}
    if (state->list_scroll < 0) {{
        state->list_scroll = 0;
    }}
}}

static void handle_key(AppState *state, int ch) {{
    switch (ch) {{
        case 'q':
            state->running = false;
            break;
        case '\\t':
            state->focus = state->focus == FOCUS_LIST ? FOCUS_DETAIL : FOCUS_LIST;
            update_status(state, "Focus changed");
            break;
        case KEY_UP:
            if (state->focus == FOCUS_LIST) {{
                move_selection(state, -1);
                update_status(state, "Moved up");
            }} else {{
                if (state->detail_scroll > 0) {{
                    state->detail_scroll -= 1;
                }}
                update_status(state, "Detail scrolled up");
            }}
            break;
        case KEY_DOWN:
            if (state->focus == FOCUS_LIST) {{
                move_selection(state, 1);
                update_status(state, "Moved down");
            }} else {{
                state->detail_scroll += 1;
                update_status(state, "Detail scrolled down");
            }}
            break;
        case KEY_NPAGE:
            state->detail_scroll += 5;
            update_status(state, "Paged down");
            break;
        case KEY_PPAGE:
            state->detail_scroll -= state->detail_scroll >= 5 ? 5 : state->detail_scroll;
            update_status(state, "Paged up");
            break;
        case KEY_RESIZE:
            update_status(state, "Terminal resized");
            break;
        case 27:
            update_status(state, "Escape pressed");
            break;
        case '\\n':
        case KEY_ENTER:
            update_status(state, "Activate the focused item here");
            break;
        default:
            update_status(state, "Unhandled key");
            break;
    }}

    state->needs_redraw = true;
}}

int main(void) {{
    AppState state;
    memset(&state, 0, sizeof(state));
    state.running = true;
    state.needs_redraw = true;
    state.focus = FOCUS_LIST;
    update_status(&state, "Ready");

    if (init_terminal() != 0) {{
        fprintf(stderr, "failed to initialize ncurses\\n");
        return 1;
    }}

    while (state.running) {{
        Layout layout = compute_layout();
        sync_view_state(&state, &layout);
        if (state.needs_redraw) {{
            render_app(&layout, &state);
            state.needs_redraw = false;
        }}

        int ch = getch();
        handle_key(&state, ch);
    }}

    restore_terminal();
    return 0;
}}
"""


def cpp_source(app_name: str) -> str:
    return f"""#include <ncurses.h>

#include <algorithm>
#include <array>
#include <clocale>
#include <cstdio>
#include <stdexcept>
#include <string>

enum class FocusArea {{
    list,
    detail,
}};

struct Rect {{
    int y = 0;
    int x = 0;
    int h = 0;
    int w = 0;
}};

struct Layout {{
    Rect header;
    Rect list;
    Rect detail;
    Rect status;
    bool too_small = false;
}};

struct AppState {{
    bool running = true;
    bool needs_redraw = true;
    FocusArea focus = FocusArea::list;
    int selected_index = 0;
    int list_scroll = 0;
    int detail_scroll = 0;
    std::string status = "Ready";
}};

class TerminalSession {{
  public:
    TerminalSession() {{
        std::setlocale(LC_ALL, "");
        if (initscr() == nullptr) {{
            throw std::runtime_error("failed to initialize ncurses");
        }}
        active_ = true;
        cbreak();
        noecho();
        keypad(stdscr, TRUE);
        curs_set(0);

        if (has_colors()) {{
            start_color();
            use_default_colors();
            init_pair(1, COLOR_BLACK, COLOR_CYAN);
            init_pair(2, COLOR_YELLOW, -1);
        }}
    }}

    ~TerminalSession() {{
        if (active_) {{
            curs_set(1);
            echo();
            nocbreak();
            endwin();
        }}
    }}

    TerminalSession(const TerminalSession&) = delete;
    auto operator=(const TerminalSession&) -> TerminalSession& = delete;

  private:
    bool active_ = false;
}};

auto compute_layout() -> Layout {{
    Layout layout;
    int rows = 0;
    int cols = 0;
    getmaxyx(stdscr, rows, cols);

    layout.too_small = rows < 8 || cols < 40;
    layout.header = Rect{{0, 0, 1, cols}};
    layout.status = Rect{{rows - 1, 0, 1, cols}};

    if (layout.too_small) {{
        return layout;
    }}

    const int body_height = rows - 2;
    const int list_width = std::max(18, cols / 3);
    layout.list = Rect{{1, 0, body_height, list_width}};
    layout.detail = Rect{{1, list_width, body_height, cols - list_width}};
    return layout;
}}

void render_header(const Layout& layout) {{
    mvhline(layout.header.y, layout.header.x, ' ', layout.header.w);
    if (has_colors()) {{
        attron(COLOR_PAIR(1));
    }}
    mvprintw(layout.header.y, layout.header.x + 1, "{app_name}  Tab switches focus  q quits");
    if (has_colors()) {{
        attroff(COLOR_PAIR(1));
    }}
}}

void render_list(const Layout& layout, const AppState& state) {{
    constexpr std::array<const char*, 6> items = {{
        "Overview",
        "Jobs",
        "Metrics",
        "Logs",
        "Settings",
        "Help",
    }};

    for (int row = 0; row < layout.list.h; ++row) {{
        const int index = state.list_scroll + row;
        mvhline(layout.list.y + row, layout.list.x, ' ', layout.list.w);
        if (index >= static_cast<int>(items.size())) {{
            continue;
        }}

        if (index == state.selected_index) {{
            if (has_colors()) {{
                attron(COLOR_PAIR(2));
            }}
            mvprintw(
                layout.list.y + row,
                layout.list.x + 1,
                "%c %s",
                state.focus == FocusArea::list ? '>' : '*',
                items[static_cast<std::size_t>(index)]);
            if (has_colors()) {{
                attroff(COLOR_PAIR(2));
            }}
        }} else {{
            mvprintw(layout.list.y + row, layout.list.x + 1, "  %s", items[static_cast<std::size_t>(index)]);
        }}
    }}
}}

void render_detail(const Layout& layout, const AppState& state) {{
    mvhline(layout.detail.y, layout.detail.x, ' ', layout.detail.w);
    mvprintw(
        layout.detail.y,
        layout.detail.x + 1,
        "Focused pane: %s",
        state.focus == FocusArea::list ? "list" : "detail");
    mvprintw(layout.detail.y + 2, layout.detail.x + 1, "Selected row: %d", state.selected_index);
    mvprintw(layout.detail.y + 3, layout.detail.x + 1, "List scroll: %d", state.list_scroll);
    mvprintw(layout.detail.y + 4, layout.detail.x + 1, "Detail scroll: %d", state.detail_scroll);
    mvprintw(layout.detail.y + 6, layout.detail.x + 1, "Keep state, layout, input, and paint separate.");
}}

void render_status(const Layout& layout, const AppState& state) {{
    mvhline(layout.status.y, layout.status.x, ' ', layout.status.w);
    mvprintw(layout.status.y, layout.status.x + 1, "%s", state.status.c_str());
}}

void render_too_small() {{
    int rows = 0;
    int cols = 0;
    getmaxyx(stdscr, rows, cols);
    erase();
    mvprintw(0, 0, "Terminal too small");
    mvprintw(1, 0, "Need at least 8 rows x 40 cols, have %d x %d", rows, cols);
    mvprintw(3, 0, "Resize the terminal or simplify the layout.");
    refresh();
}}

void render_app(const Layout& layout, const AppState& state) {{
    if (layout.too_small) {{
        render_too_small();
        return;
    }}

    erase();
    render_header(layout);
    render_list(layout, state);
    render_detail(layout, state);
    render_status(layout, state);
    refresh();
}}

void move_selection(AppState& state, int delta) {{
    constexpr int max_index = 5;
    state.selected_index = std::clamp(state.selected_index + delta, 0, max_index);
}}

void sync_view_state(AppState& state, const Layout& layout) {{
    constexpr int max_index = 5;
    state.selected_index = std::clamp(state.selected_index, 0, max_index);
    state.detail_scroll = std::max(0, state.detail_scroll);
    if (layout.too_small) {{
        state.list_scroll = 0;
        state.detail_scroll = 0;
        return;
    }}

    const int visible_rows = std::max(1, layout.list.h);
    if (state.selected_index < state.list_scroll) {{
        state.list_scroll = state.selected_index;
    }}
    if (state.selected_index >= state.list_scroll + visible_rows) {{
        state.list_scroll = state.selected_index - visible_rows + 1;
    }}
    state.list_scroll = std::max(0, state.list_scroll);
}}

void handle_key(AppState& state, int ch) {{
    switch (ch) {{
        case 'q':
            state.running = false;
            break;
        case '\\t':
            state.focus = state.focus == FocusArea::list ? FocusArea::detail : FocusArea::list;
            state.status = "Focus changed";
            break;
        case KEY_UP:
            if (state.focus == FocusArea::list) {{
                move_selection(state, -1);
                state.status = "Moved up";
            }} else {{
                state.detail_scroll = std::max(0, state.detail_scroll - 1);
                state.status = "Detail scrolled up";
            }}
            break;
        case KEY_DOWN:
            if (state.focus == FocusArea::list) {{
                move_selection(state, 1);
                state.status = "Moved down";
            }} else {{
                state.detail_scroll += 1;
                state.status = "Detail scrolled down";
            }}
            break;
        case KEY_NPAGE:
            state.detail_scroll += 5;
            state.status = "Paged down";
            break;
        case KEY_PPAGE:
            state.detail_scroll = std::max(0, state.detail_scroll - 5);
            state.status = "Paged up";
            break;
        case KEY_RESIZE:
            state.status = "Terminal resized";
            break;
        case 27:
            state.status = "Escape pressed";
            break;
        case '\\n':
        case KEY_ENTER:
            state.status = "Activate the focused item here";
            break;
        default:
            state.status = "Unhandled key";
            break;
    }}

    state.needs_redraw = true;
}}

int main() {{
    try {{
        TerminalSession terminal;
        AppState state;

        while (state.running) {{
            const Layout layout = compute_layout();
            sync_view_state(state, layout);
            if (state.needs_redraw) {{
                render_app(layout, state);
                state.needs_redraw = false;
            }}

            const int ch = getch();
            handle_key(state, ch);
        }}
    }} catch (const std::exception& ex) {{
        std::fprintf(stderr, "%s\\n", ex.what());
        return 1;
    }}

    return 0;
}}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, help="Directory that will receive the scaffold")
    parser.add_argument("--app-name", required=True, help="Visible application name")
    parser.add_argument("--language", choices=("c", "cpp"), default="c", help="Source language to generate")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing generated main source file",
    )
    return parser.parse_args()


def write_text(path: Path, text: str, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists; pass --force to overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_readme_text(app_name: str, language: str, source_name: str) -> str:
    return "\n".join(
        [
            f"{app_name} scaffold",
            "",
            f"Language: {language}",
            f"Entry source: {source_name}",
            "",
            "The generated starter keeps these boundaries explicit:",
            "- AppState for persistent UI state",
            "- Layout for computed rectangles",
            "- handle_key for input dispatch",
            "- render_* helpers for painting",
            "",
            "Adapt the file to the target repo's build tooling.",
        ]
    )


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    language = args.language
    source_name = "main.c" if language == "c" else "main.cpp"
    source_path = output_dir / source_name
    notes_path = output_dir / "scaffold-notes.txt"

    source_text = c_source(args.app_name) if language == "c" else cpp_source(args.app_name)
    write_text(source_path, source_text, args.force)
    write_text(notes_path, build_readme_text(args.app_name, language, source_name), True)
    print(source_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
