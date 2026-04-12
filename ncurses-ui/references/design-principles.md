# Design Principles

## Architecture Rules Of Thumb

- Keep application state separate from rendering state.
- Keep layout math separate from paint code.
- Keep key decoding and action dispatch separate from business updates.
- Keep one obvious owner for focus, selection, and scroll offsets.
- Keep ncurses-specific calls near rendering and lifecycle code.

## App Loop Shape

Default to this structure:

1. initialize terminal
2. initialize app state
3. compute layout from current terminal size
4. render dirty regions
5. read one event
6. map the event to an action
7. update state
8. mark affected regions dirty
9. cleanup on exit

Use a tighter redraw cycle when the app needs periodic refresh, but keep the same boundaries.

## Separation Of Concerns

Recommended split:

- `AppState`: selections, filters, mode, dialog visibility, model data
- `Layout`: rectangles for header, footer, sidebar, content, dialog, and scrollable regions
- `Action`: normalized input command such as `move_up`, `confirm`, `open_help`, `resize`
- `update_state(...)`: pure or mostly pure state transition logic where practical
- `render_* (...)`: focused paint functions for each region

Test layout math, action mapping, and state transitions outside ncurses whenever possible.

## Redraw Strategy

- Prefer dirty flags or dirty regions for multi-pane screens.
- Recompute layout on resize or on structural state changes.
- Use `wnoutrefresh` and `doupdate` when several windows repaint together.
- Avoid repainting everything on every keypress unless the app is genuinely tiny.
- Redraw the whole screen after theme, size, or major mode changes if that is simpler and still clear.

## Cleanup Discipline

- Centralize terminal teardown.
- Track whether ncurses init actually succeeded before calling teardown.
- Restore cursor visibility, echo, and mode changes predictably.
- Free or destroy windows and panels in a consistent order.
- Handle error exits after partial setup.

## Resize Behavior

- Treat resize as a layout event, not a special-case paint hack.
- Re-read terminal dimensions before computing regions.
- Clamp selection and scroll offsets against the new visible area.
- Provide a minimum-size fallback screen when the intended layout no longer fits.

## Practical Testing Boundary

Good unit-test targets:

- rectangle and split calculations
- visible-range calculations for lists and tables
- key-to-action mapping
- selection and scrolling state transitions
- filter and search state updates

Poor default unit-test targets:

- full terminal drawing fidelity
- precise color rendering across terminals
- complex interaction timing that depends on a real terminal emulator
