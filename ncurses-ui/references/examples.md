# Example Requests

- "Build an ncurses dashboard with a header, metrics pane, log pane, and status bar."
  - Start with a layout map and explicit focus model before adding colors or panels.

- "Add a list plus detail layout to this curses program."
  - Split selection state from detail rendering and keep list scrolling separate from detail scrolling.

- "Refactor this ncurses file into reusable views."
  - Extract app state, layout computation, per-view render helpers, and centralized input dispatch first.

- "Add a popup confirm dialog."
  - Implement modal visibility in state, route keys to the dialog first, and freeze background focus while it is open.

- "Make this resize cleanly."
  - Recompute rectangles on `KEY_RESIZE`, clamp scroll and selection state, and define a minimum-size fallback.

- "Add a scrollable table."
  - Represent columns declaratively, keep header rendering fixed, and manage vertical and horizontal scroll independently.

- "Improve usability of this terminal browser."
  - Normalize keybindings, expose focus clearly, add concise key hints, and remove accidental mode ambiguity.
