---
name: ncurses-ui
description: Build and refactor keyboard-driven terminal interfaces with ncurses in C or C++. Use when Codex needs to design, implement, debug, or clean up an interactive TUI built on ncurses or curses, including app-loop structure, windows, pads, panels, forms, menus, focus handling, resize behavior, scrolling, redraw strategy, colors, and terminal lifecycle cleanup. Do not use this skill for generic CLI tools, ANSI-only terminal styling, GUI work, web frontends, or unrelated C/C++ tasks.
---

# Ncurses UI

Use this skill for interactive ncurses work only.

The goal is not to produce a flashy demo. The goal is to produce a stable, readable, keyboard-first terminal interface with clear separation between state, input, layout, and rendering.

## Trigger Boundary

Use this skill when the task involves any of:

- ncurses or curses application code
- keyboard-driven terminal UI architecture in C or C++
- windows, pads, panels, menus, forms, dialogs, status bars, or help overlays
- input focus, resize behavior, redraw flicker, scrolling, or cleanup bugs in ncurses apps
- refactoring a messy TUI into cleaner state, layout, and rendering boundaries

Do not use this skill when the task is primarily:

- a non-interactive CLI tool
- ANSI escape styling without an interactive curses event loop
- GUI work such as Qt, GTK, Cocoa, Win32, or Electron
- web frontend work
- generic C or C++ implementation not tied to a curses interface
- unrelated build, algorithm, or data-structure work

## Core Rules

- Separate application state from drawing code.
- Separate key dispatch from business logic and state transitions.
- Separate layout computation from paint functions.
- Keep the main loop small and explicit: initialize, compute layout, read input, update state, redraw dirty regions, cleanup.
- Prefer predictable keyboard navigation over clever keybindings.
- Treat terminal init and cleanup as correctness work, not polish.
- Handle `KEY_RESIZE` and minimum-size fallbacks explicitly.
- Use panels, pads, forms, menus, or subwindows only when they simplify behavior.
- Keep color and attribute usage restrained and readable.
- Keep non-UI logic testable outside ncurses where practical.

## Opening Pass

When the user asks for ncurses work:

1. Inspect the existing app loop and terminal lifecycle first.
2. Identify the current boundaries for:
   - persistent app state
   - focused widget or pane
   - layout math
   - rendering
   - key dispatch
3. If the code mixes all of those together, split the problem before adding features.
4. Check for cleanup and resize handling before polishing visuals.
5. Match the repository language and style.

Language choice:

- If the target repo is plain C, prefer C structs plus helper functions over forced object hierarchies.
- If the target repo is C++, prefer small structs or classes with clear ownership and RAII where it genuinely simplifies lifecycle management.
- If the repo does not establish a preference, default to the style already used by the ncurses code in that repo.

## Architecture Pattern

Default to a small loop with explicit phases:

1. initialize terminal and UI state
2. compute layout from terminal size and app state
3. read one input event
4. dispatch input to focused widget or app-level command handler
5. update scroll offsets, selection, focus, and dirty flags
6. redraw only what changed when practical
7. restore terminal state on every exit path

Prefer these boundaries:

- `AppState`: domain state plus UI selection, focus, and scroll state
- `Layout`: computed rectangles or regions derived from the current terminal size
- `dispatch_input(...)`: converts keys into high-level actions
- `render_* (...)`: paints one view or widget from state plus layout
- `cleanup(...)`: restores terminal state and destroys windows safely

Avoid giant functions that call `getch`, modify business data, compute coordinates, and paint everything in one place.

## Lifecycle And Cleanup

- Initialize ncurses once and centralize teardown.
- Restore echo, cbreak, cursor, and screen state on all return paths.
- Be careful with alternate-screen assumptions if the app or environment uses them.
- Handle startup failures after partial initialization without leaving the terminal broken.
- Treat resize and exit handling as first-class behavior.
- On crash-prone code paths, prefer a narrow ncurses surface and keep risky logic outside the rendering layer.

## Input And Focus

- Define a clear focus model before adding more keybindings.
- Normalize raw keycodes into app actions when the codebase is large enough to justify it.
- Support arrow keys, Enter, Escape, Tab, Shift-Tab, paging keys, and `KEY_RESIZE` consistently.
- Keep app-level shortcuts separate from widget-local navigation.
- Show key hints for major actions when space allows.
- Do not scatter raw `switch (ch)` logic across many files without a clear dispatch boundary.

## Layout And Rendering

- Compute layout from terminal dimensions, not magic coordinates sprinkled through paint code.
- Handle minimum terminal sizes with a clear fallback message or reduced layout.
- Distinguish cursor position, selection, and scroll offset.
- Prefer incremental redraws and `wnoutrefresh` plus `doupdate` patterns when the screen is split into several regions.
- Redraw the full screen only when the layout or theme truly changed.
- Make focused, selected, disabled, loading, and error states distinguishable without relying on color alone.

## Scrolling And Large Content

- Use viewport math or pads intentionally for long lists, tables, logs, and detail views.
- Keep the selected row, top visible row, and horizontal scroll offset as separate state.
- Ensure page-up and page-down semantics are consistent.
- Keep headers or status lines pinned when that improves orientation.

## Maintainability Rules

- Prefer helper structs or small classes for UI state over sprawling globals.
- Document invariants around focus, selection ranges, and scroll bounds.
- Keep widget rendering modular.
- Keep ncurses calls near rendering boundaries rather than mixed into domain logic.
- Refactor before adding a new pane or modal if the current file is already monolithic.

## Reference Map

- Read `references/design-principles.md` for app-loop structure, separation of concerns, redraw strategy, cleanup discipline, and resize handling.
- Read `references/widget-patterns.md` for menus, list views, tables, forms, dialogs, tabs, split views, status bars, logs, and scrolling regions.
- Read `references/anti-patterns.md` for concrete ncurses mistakes to avoid.
- Read `references/examples.md` for typical request shapes and what good responses should optimize for.

## Helper Script

Use the scaffold only when a clean starter is actually useful.

```bash
python scripts/scaffold_ncurses_app.py --output-dir <dir> --app-name <name> --language <c|cpp>
```

The scaffold is intentionally small. It gives a maintainable starting point with:

- terminal init and cleanup
- explicit app state and layout structs
- resize-aware loop structure
- focused input dispatch
- layout and render split

Do not treat the scaffold as a framework. Adapt it to the target repo's build system and naming conventions.

## Output Requirements

When using this skill, be explicit about:

- the focus model
- which state is persistent versus derived
- how resize is handled
- how scrolling is represented
- which redraw strategy is being used
- how cleanup is guaranteed
- which logic is intentionally kept testable outside ncurses

## Hard No's

- Do not turn this into a generic C or C++ skill.
- Do not silently switch the user to another TUI library.
- Do not optimize around speculative flicker or performance issues before the structure is correct.
- Do not add flashy color or animation if it weakens clarity or portability.
- Do not couple domain logic tightly to ncurses calls.
