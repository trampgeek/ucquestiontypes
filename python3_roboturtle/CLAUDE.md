# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RoboTurtle is a Reeborg-inspired Moodle CodeRunner question type that lets students write Python to control a robot turtle navigating a grid world. It runs Python in-browser using [Skulpt](https://skulpt.org/) and grades submissions on the Jobe server.

## Build System

**Never edit `prototypeextra.html`, `template.py`, or `assembledrobot.py` directly** — they are generated files.

All Python logic lives in `classes/`. After changing anything there, rebuild:

```bash
python build.py
```

This processes three `.template` files using `{INCLUDE:path}` directives:
1. `assembledrobot.py.template` → `assembledrobot.py` (all classes concatenated)
2. `template.py.template` → `template.py` (Jobe server grader, includes assembledrobot + turtle stubs)
3. `prototypeextra.html.template` → `prototypeextra.html` (browser HTML, includes assembledrobot via Skulpt)

Lines marked `#omitfrombuild` are stripped during the build — they are used for VS Code type checking (e.g., `from turtle import Turtle`) and must not appear in the assembled output.

## Architecture

The same Python code runs in two environments:

| Environment | File | How Python runs |
|-------------|------|----------------|
| Browser (student UI) | `prototypeextra.html` | Skulpt (Python-in-browser) |
| Jobe server (grading) | `template.py` | CPython |

`turtle.py` in the repo root is a stub that satisfies `from turtle import Turtle, Screen` on the Jobe server without doing any graphics.

### Class Hierarchy

- **`Item`** (`classes/item.py`) — collectible object; `ITEM_TYPES` dict maps name → emoji symbol
- **`RoboTurtle`** (`classes/roboturtle.py`) — extends `turtle.Turtle`; carries an item inventory
- **`World`** (`classes/world.py`) — base class; manages grid, wall segments, items, rendering; subclasses auto-register via `__init_subclass__` into `World._registry` for factory instantiation
  - **`TargetWorld`** — goal: robot reaches a target cell
  - **`PickUpItemsWorld`** — goal: collect all items (optionally dump them at a location), extends `TargetWorld`
  - **`PathWorld`** — goal: robot follows an exact required path
- **`BotController`** (`classes/botcontroller.py`) — command interface wrapping a `World`; implements `move()`, `turn_left/right()`, `take/put/toss()`, `build_wall()`, query methods
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

## Extending the Question Type

**Add a new item type:** edit `classes/item.py`, add to `Item.ITEM_TYPES`.

**Add a new world type:** create a new file in `classes/`, subclass `World` (or a subclass), override `check_final_state()` to populate `self.fail_messages`. Add `{INCLUDE:classes/yourworld.py}` to `assembledrobot.py.template`.

**Add a robot command:** add a method to `BotController` in `classes/botcontroller.py`, then add a global wrapper in `classes/globalcommands.py`, and expose it in the `namespace` dict in `template.py.template`.

## Testing

There is no automated test suite. Test by:
1. Running `python build.py`
2. Copying the generated files into a Moodle CodeRunner question prototype
3. Previewing the question in Moodle

For quick local Python logic checks, you can run `assembledrobot.py` directly (it imports from the stubs in `turtle.py` implicitly via `template.py`).
