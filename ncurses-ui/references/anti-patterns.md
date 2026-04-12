# Anti-Patterns

## Giant Single-Function TUI

Problem:

- one function initializes ncurses, handles keys, mutates data, computes coordinates, and paints everything

Avoid it by:

- splitting lifecycle, layout, input dispatch, state updates, and rendering into named units

## Hidden Focus State

Problem:

- the active pane or widget is implied by scattered booleans or recent key presses

Avoid it by:

- storing one explicit focus enum or identifier and routing input through it

## Layout Math Everywhere

Problem:

- magic numbers and coordinate arithmetic are duplicated across render functions

Avoid it by:

- computing rectangles once per frame or resize and passing them into render helpers

## Broken Cleanup

Problem:

- errors or early returns leave the terminal with no echo, bad cursor state, or a corrupted screen

Avoid it by:

- centralizing teardown and using one cleanup path for normal and error exits

## Full Redraw On Every Keystroke

Problem:

- every input wipes and repaints the whole screen even when only one small region changed

Avoid it by:

- tracking dirty regions or at least dirty windows and batching updates

## Raw Key Logic Scattered Everywhere

Problem:

- keycodes are hard-coded in many widgets with inconsistent behavior

Avoid it by:

- mapping raw keys to actions centrally or per widget in a consistent style

## Global Mutable State Sprawl

Problem:

- globals hold layout, mode, filters, selections, window pointers, and domain data with weak ownership

Avoid it by:

- grouping related state into app or view structs and passing references deliberately

## Hardcoded Terminal Assumptions

Problem:

- the code assumes 120 columns, fixed panes, or unlimited color support

Avoid it by:

- recalculating layout from live terminal size and providing minimum-size fallbacks

## Colors As The Only Signal

Problem:

- focus, errors, and selection are conveyed only by color differences

Avoid it by:

- combining color with text, markers, spacing, borders, or attributes

## Domain Logic Coupled To Ncurses

Problem:

- core data manipulation can only run inside a curses session

Avoid it by:

- keeping business rules and state transitions callable without window objects
