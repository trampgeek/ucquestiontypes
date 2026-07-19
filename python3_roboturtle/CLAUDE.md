# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RoboTurtle is a Reeborg-inspired Moodle CodeRunner question type that lets students write Python to control a robot turtle navigating a grid world. It runs Python in-browser using [Skulpt](https://skulpt.org/) and grades submissions on the Jobe server.

## Build System

**Never edit `prototypeextra.html`, `template.py`, `assembledrobot.py`, or `editor.html` directly** — they are generated files.

All Python logic lives in `classes/`. After changing anything there, rebuild:

```bash
python build.py
```

This processes four `.template` files using `{INCLUDE:path}` directives:
1. `assembledrobot.py.template` → `assembledrobot.py` (all classes concatenated)
2. `template.py.template` → `template.py` (Jobe server grader, includes assembledrobot + turtle stubs)
3. `prototypeextra.html.template` → `prototypeextra.html` (browser HTML, includes assembledrobot via Skulpt)
4. `editor.html.template` → `editor.html` (standalone visual test-case builder; see "World editor" below)

Lines marked `#omitfrombuild` are stripped during the build — they are used for VS Code type checking (e.g., `from turtle import Turtle`) and must not appear in the assembled output.

`build.py` also substitutes two markers, both derived from `classes/item_types.py`: `{ITEM_EMOJI_JS}` (a JS object literal) and `{ITEM_TYPE_OPTIONS_HTML}` (a list of `<option>` elements). `editor.html.template` uses both, so its item pickers can never drift out of sync with `item_types.py` the way they once did by hand.

## Architecture

The same Python code runs in two environments:

| Environment | File | How Python runs |
|-------------|------|----------------|
| Browser (student UI) | `prototypeextra.html` | Skulpt (Python-in-browser) |
| Jobe server (grading) | `template.py` | CPython |

`turtle.py` in the repo root is a stub that satisfies `from turtle import Turtle, Screen` on the Jobe server without doing any graphics.

### Class Hierarchy

- **`Item`** (`classes/item.py`) — collectible object; type names and emoji symbols come from `ITEM_TYPES` in `classes/item_types.py` (kept dependency-free so `build.py` can load it directly)
- **`RoboTurtle`** (`classes/roboturtle.py`) — extends `turtle.Turtle`; carries an item inventory
- **`World`** (`classes/world.py`) — base class; manages grid, wall segments, items, rendering; subclasses auto-register via `__init_subclass__` into `World._registry` for factory instantiation. Also owns the optional **text output** feature (not a subclass — an opt-in available to every world type): if `world_params` contains `expected_texts`, `World` reserves a text bar below the grid, `send_text()` displays the most recent message there, and `check_final_state()` requires `sent_texts == expected_texts`. Subclasses that override `check_final_state()` must call `super().check_final_state()` first so this check still runs. `on_world_loaded()` is a no-op hook, called once by `worldloader.load_world()` after walls/robot/items are all placed but before drawing — `PickUpItemsWorld` uses it to snapshot item counts (items don't exist yet during `__init__`, since `worldloader` adds them afterwards).
  - **`TargetWorld`** — goal: robot reaches a target cell
  - **`PickUpItemsWorld`** — goal: collect all items and (optionally) redeposit them at one or more dump locations (`world_params['item_dumps']`), extends `TargetWorld`. Each dump has a `location`, optional `type` (default `'Any'`), `icon`, and optional `count` — if `count` is omitted it's auto-derived in `on_world_loaded()` from how many matching items exist in the world at load time, so authors don't have to hand-count e.g. "all the leaves". A dump with a non-`'Any'` `type` fails separately if wrong-typed items are found there. The old singular `item_dump: {location, num_items}` format is still accepted (mapped to a single `Any`/`trash` entry in `item_dumps`) if `item_dumps` itself isn't present, for backward compatibility with existing questions.
  - **`PathWorld`** — goal: robot follows an exact required path
- **`BotController`** (`classes/botcontroller.py`) — command interface wrapping a `World`; implements `move()`, `turn_left/right()`, `take/put/toss()` (each returns the item's type name), `build_wall()`, `inventory()`, `send_text()` (raises if `expected_texts` isn't set), query methods
- **`worldloader.py`** — `load_world(data)` instantiates the world via `World.create()`, populates it, sets `_current_world` / `_current_controller` globals
- **`globalcommands.py`** — thin wrappers around `_current_controller` for Reeborg-style global API (`move()`, `turn_left()`, etc.)

### Wall Representation

Walls are stored as a `set` of unit edge segments `((x1,y1),(x2,y2))`. `is_wall_between()` computes the required edge segment for a potential move and does an O(1) set lookup. Longer walls (and the perimeter) are decomposed into unit segments on insertion.

### JavaScript (`roboturtle.js`)

Loaded once per page via a singleton loader pattern (`window._skulptLoader`). Skulpt scripts are fetched from `/local/skulpt/skulpt/` (path adjusted for `localhost` dev). The `___textareaId___` placeholder is replaced by CodeRunner with a unique per-question ID at render time.

On "Run": Skulpt executes `prefix_code + load_world(tests[currentTest]) + student_code`. Goal checking uses a `__ROBOTURTLE_GOAL__:` marker printed to stdout and intercepted by the JS output handler. A modal dialog reports pass/fail to the student.

## Deployment

After building:
1. Copy `prototypeextra.html` into the CodeRunner prototype's **prototypeextra** field.
2. Copy `template.py` into the prototype's **template** field.
3. Copy the `skulpt/` folder to `moodle/public/local/skulpt/` on the Moodle server.

## World JSON Format

```json
{
  "world_class": "TargetWorld",
  "world_params": {"target": [5, 5], "target_icon": "flag"},
  "grid_size": [8, 8],
  "robot_start": {"position": [0, 0], "heading": "north"},
  "walls": [[[3, 0], [3, 4]]],
  "blocked_cells": [[[2, 2], [3, 3]]],
  "items": [{"type": "star", "position": [2, 3], "count": 1},
            {"type": "key",  "position": "inventory", "count": 2}]
}
```

`blocked_cells` entries are `[[x0,y0],[x1,y1]]` corner pairs that expand into rectangular areas. `items` with `"position": "inventory"` start in the robot's inventory.

Any `world_class` can opt into the text-output feature by adding `expected_texts` to `world_params` — an ordered list of strings that the student's code must produce via `send_text()`, e.g. `{"target": [5, 5], "expected_texts": ["Starting", "Done"]}`. This is independent of `world_class`; it works the same for `TargetWorld`, `PickUpItemsWorld`, and `PathWorld`.

`PickUpItemsWorld`'s `item_dumps` example — sort leaves into a trash can and stars into a box, with counts auto-derived from however many of each are placed in `items`:
```json
"world_params": {
  "target": [7, 7],
  "item_dumps": [
    {"location": [0, 7], "type": "leaf", "icon": "trash"},
    {"location": [7, 0], "type": "star", "icon": "box"}
  ]
}
```

## Extending the Question Type

**Add a new item type:** edit `classes/item_types.py`, add to `ITEM_TYPES`, then `python build.py` (this also regenerates `editor.html`'s item pickers).

**Add a new world type:** create a new file in `classes/`, subclass `World` (or a subclass), override `check_final_state()` to populate `self.fail_messages`. Add `{INCLUDE:classes/yourworld.py}` to `assembledrobot.py.template`.

**Add a robot command:** add a method to `BotController` in `classes/botcontroller.py`, then add a global wrapper in `classes/globalcommands.py`, and expose it in the `namespace` dict in `template.py.template`.

## Testing

There is no automated test suite. Test by:
1. Running `python build.py`
2. Copying the generated files into a Moodle CodeRunner question prototype
3. Previewing the question in Moodle

For quick local Python logic checks, you can run `assembledrobot.py` directly (it imports from the stubs in `turtle.py` implicitly via `template.py`).
