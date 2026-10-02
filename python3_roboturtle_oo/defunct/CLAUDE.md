# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RoboTurtle is a Reeborg-inspired educational programming tool for teaching introductory programming concepts. It provides a visual grid-based environment where students write Python code to control a robot turtle that navigates through worlds, avoids obstacles, and collects items.

**IMPORTANT: Virtually all development work is in `prototypeextra.html`** - the HTML file that runs within a CodeRunner question type in Moodle. The standalone Python files (roboturtle.py, etc.) are legacy prototypes and are rarely modified.

## File Structure

- **prototypeextra.html** - The main work file containing:
  - Lines 14-919: Python prefix code (RoboTurtle implementation) embedded in `<script type="text/python">`
  - Lines 928-935: Test cases template (JSON filled in by Twig template parameter `{{ testcases | json_encode }}`)
  - Lines 937-952: Student UI (output area, canvas, code textarea, Run button)
  - Lines 962-1114: JavaScript runtime (Skulpt loader and execution logic)

- **Other files** (legacy/testing only):
  - `roboturtle.py` - Standalone desktop version (rarely used)
  - `simple_example.py`, `test_roboturtle.py` - Test programs for desktop version
  - `sample_world.json`, `sample_world.yaml` - Example world files

## How It Works in CodeRunner

1. The HTML is inserted into the CodeRunner question's "prototypeextra" field
2. When loaded, Skulpt (Python-in-browser) runs the prefix code to initialize the world
3. Student writes their solution in the textarea
4. Clicking "Run" executes: prefix code + world loading + student answer
5. Test cases are provided via the `{{ testcases }}` Twig template parameter (JSON array of world specifications)

## Architecture

### Core Class Hierarchy

**World Management:**
- `World` (base class): Manages the grid, walls, blocked cells, items, and rendering
- `TargetWorld` (subclass): Adds goal-checking functionality for reaching a specific target position
- Custom world types can be created by subclassing `World` and overriding `satisfies_goal()` and `draw_goal_marker()`

**Robot System:**
- `RoboTurtle` (extends `turtle.Turtle`): Visual representation of the robot with inventory management
- `BotController`: Command interface that wraps world state and provides movement/query methods

**Item System:**
- `Item`: Single class for all collectible items, displayed using UTF-8 characters
- `ITEM_SYMBOLS` (static dict): Maps item names to UTF-8 display characters (⭐ star, 🔑 key, 🍁 leaf)
- Unknown item types display as 📦
- `ITEM_TYPES` dict: Factory mapping item type strings to Item constructors

### Two API Styles

1. **Object-oriented API** (direct controller access):
   ```python
   world = roboturtle.load('world.json')
   bot = world.bot_controller()
   bot.move()
   bot.turn_left()
   ```

2. **Global function API** (Reeborg-style for beginners):
   ```python
   import roboturtle
   from roboturtle import *
   roboturtle.load('world.json')
   move()  # Uses global _current_controller
   turn_left()
   ```

The global functions (`move()`, `turn_left()`, `at_goal()`, etc.) are convenience wrappers around `_current_controller` that's set by `load()`.

### World File Format

Worlds are defined in JSON or YAML with this structure:
- `world_class`: Class name (e.g., "TargetWorld")
- `world_params`: Parameters for world constructor (e.g., target position)
- `grid_size`: [width, height] as list of two integers
- `cell_size`: Pixel size of each grid cell
- `robot_start`: {position: [x, y], heading: "north"|"east"|"south"|"west"}
- `walls`: List of wall segments as [[x1, y1], [x2, y2]] (must be horizontal or vertical)
- `blocked_cells`: List of impassable cell positions [[x, y], ...]
- `items`: List of {type: "star"|"key"|"leaf"|<other>, position: [x, y], count: int}

The YAML parser (`world_parser.py`) is a custom implementation supporting a simplified YAML subset (2-space indentation, lists with dashes, inline lists).

### Key Implementation Details

**Wall Detection:**
- Walls are stored as line segments between grid points (prototypeextra.html:376-426)
- `is_wall_between()` determines if a wall blocks movement from one cell to adjacent cell
- Algorithm calculates the required wall segment that would block the move, then checks if any existing wall covers that segment

**Coordinate System:**
- Grid coordinates: (0,0) is bottom-left corner
- Heading directions: "north" (up), "east" (right), "south" (down), "west" (left)
- Turtle graphics angles: north=90°, east=0°, south=270°, west=180°

**Rendering Strategy:**
- Initial world drawing uses `tracer(0)` for batch rendering, then enables `tracer(1)` for animation (prototypeextra.html:190, 297)
- `update_item_display()` redraws only the affected cell when items are picked up/placed (prototypeextra.html:329-368)
- `build_wall()` requires full screen redraw to add the new wall to the grid (prototypeextra.html:602-637)

**Robot Speed:**
- Robot starts at speed(0) to jump instantly to starting position, then switches to speed(1) for visible movement (prototypeextra.html:307, 325)
- Students can call `speed(n)` to control animation speed (0=instant, 1=slowest, 10=fast) (prototypeextra.html:915-917)

### Skulpt/Browser Compatibility

The code in prototypeextra.html differs from standard Python:
- Type hints are included in the embedded Python code (Skulpt tolerates them even though it doesn't enforce them)
- Skulpt provides Python turtle graphics in the browser via canvas rendering
- JavaScript integration: `___textareaId___` placeholders are replaced by CodeRunner with unique IDs for each question instance

## Common Development Tasks

All code modifications happen in **prototypeextra.html** within the Python prefix section (lines 14-919).

### Adding a New Item Type
1. Edit prototypeextra.html around lines 31-35 (Item.ITEM_SYMBOLS dictionary)
2. Add a new entry mapping the item name to a UTF-8 character (emoji)
3. Add the item name to the `ITEM_TYPES` dictionary (around line 53)
4. Example: `"coin": lambda: Item("coin")` and add `"coin": "🪙"` to ITEM_SYMBOLS

### Adding a New World Type
1. Edit prototypeextra.html around lines 433-491 (after World class)
2. Subclass `World` or `TargetWorld`
3. Override `satisfies_goal()` to define win condition
4. Override `draw_goal_marker()` if a visual goal indicator is needed
5. Update the world loading logic in `load_world()` (around line 740-766) if the class shouldn't be eval'd
6. Test cases provided to students will use world JSON format with your new `world_class` name

### Adding Robot Commands
1. Edit prototypeextra.html in the BotController section (lines 498-715)
2. Add method to `BotController` class
3. Add corresponding global function wrapper (lines 810-912) for beginner-friendly API
4. Always raise `RuntimeError` with descriptive messages for invalid operations

### Modifying the JavaScript Runtime
- Skulpt configuration: Lines 1051-1057
- Run logic: Lines 1049-1096
- Canvas target: Line 1061 (`Sk.TurtleGraphics.target`)
- Student code execution: Line 1072 (prefix + world loading + student answer)

### Testing Changes
1. Copy the entire prototypeextra.html into a CodeRunner question's "prototypeextra" field
2. Provide test cases as JSON array in the "testcases" template parameter
3. Preview the question and click "Run" to test

### Understanding the Execution Flow
When a student clicks "Run":
1. JavaScript clears the canvas and output (line 1073)
2. Skulpt executes: prefix code + JSON test loading + `load_world(tests[currentTest])` + student answer (line 1067-1072)
3. The world is drawn and robot is positioned by `load_world()` (line 740-803)
4. Student's code executes with access to all global functions (`move()`, `turn_left()`, etc.)

### Example Test Case Format

The `{{ testcases }}` template parameter should be a JSON array of world specifications:

```json
[
  {
    "world_class": "TargetWorld",
    "world_params": {"target": [5, 5]},
    "grid_size": [8, 8],
    "cell_size": 50,
    "robot_start": {"position": [0, 0], "heading": "north"},
    "walls": [[[3, 0], [3, 8]]],
    "items": [{"type": "star", "position": [2, 3], "count": 1}]
  }
]
```

This gets injected into the hidden script element (line 932) and loaded by the JavaScript runtime. Multiple test cases allow different world configurations for the same question.
