# Widget Patterns

## Menus

- Keep one selected index and one active item identifier.
- Separate menu content from menu painting.
- Support arrows, home/end, enter, and escape consistently.
- Render disabled items distinctly without using color alone.

## List Views

- Keep `selected_index`, `top_row`, and optional filter text separate.
- Clamp selection after filtering or resize.
- Keep one-line rows visually simple and stable.
- Show empty-state text when no rows are available.

## Tables

- Define columns as data, not hand-written per-row coordinate math.
- Separate horizontal scroll from vertical scroll.
- Keep header rendering independent from body rendering.
- Truncate predictably and show focus or selection clearly.

## Forms

- Define field order explicitly.
- Keep per-field validation separate from keystroke handling.
- Make tab and shift-tab focus travel predictable.
- Support escape to cancel and enter to submit only when the form design is clear about it.

## Dialogs And Confirm Popups

- Keep modal visibility in app state.
- Freeze background focus while the dialog is active.
- Route keys to the modal first.
- Keep dialogs narrow, obvious, and dismissible with escape.

## Tabs

- Keep current tab id separate from focused widget inside the tab.
- Avoid hiding important state transitions when switching tabs.
- Preserve per-tab scroll or selection only if that improves usability.

## Status Bars

- Reserve them for concise mode, selection count, errors, or key hints.
- Keep status messages short-lived or explicitly persistent.
- Avoid stuffing the status bar with every available shortcut.

## Help Overlays

- Use them for discoverability, not as a substitute for sane defaults.
- Group keys by mode or widget.
- Keep the overlay dismissible with escape or `q`.

## Logs Or Console Panes

- Keep append-only content separate from viewport state.
- Auto-follow only when the user has not manually scrolled away.
- Distinguish severity with text and spacing, not just color.

## Split Views

- Compute pane rectangles from a single layout function.
- Keep each pane responsible for its own render and scroll logic.
- Make focus movement between panes explicit.
- Collapse or simplify the layout gracefully on narrow terminals.

## Scrolling Regions

- Distinguish current cursor row from scroll origin.
- Clamp offsets after resize, filtering, or content changes.
- Support line-wise and page-wise motion.
- Use pads when content is much larger than the viewport and pad semantics genuinely help.
