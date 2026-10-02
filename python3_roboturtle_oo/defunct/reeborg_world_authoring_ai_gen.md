# Reeborg World Authoring Guide

This guide explains how to create custom worlds for the Reeborg-like system using JSON configuration files.

## Overview

Worlds are defined using JSON format and can include:
- Grid dimensions and cell sizing
- Walls and obstacles
- Items (tokens, objects)
- Robot starting position and orientation
- Special world types with custom behavior

## Basic World Structure

Every world file must be a valid JSON object with the following structure:

```json
{
  "grid_size": [10, 10],
  "cell_size": 40,
  "robot_start": {
    "position": [0, 0],
    "heading": "north"
  },
  "walls": [],
  "blocked_cells": [],
  "items": []
}
```

## Required Fields

### `grid_size` (Required)

Defines the dimensions of the world grid as `[width, height]`.

**Example:**
```json
"grid_size": [10, 8]
```

This creates a world that is 10 cells wide and 8 cells tall.

## Optional Fields

### `cell_size` (Optional, default: 40)

The size of each grid cell in pixels. Larger values create bigger worlds.

**Example:**
```json
"cell_size": 50
```

### `robot_start` (Optional, default: position [0, 0], heading "north")

Defines where the robot begins and which direction it faces.

**Format:**
```json
"robot_start": {
  "position": [x, y],
  "heading": "north"
}
```

**Valid headings:** `"north"`, `"south"`, `"east"`, `"west"`

**Example:**
```json
"robot_start": {
  "position": [2, 3],
  "heading": "east"
}
```

### `walls` (Optional, default: [])

Defines wall segments in the world. Walls block the robot's movement.

**Format:** Each wall is defined by two points: `[[x1, y1], [x2, y2]]`

**Important:** Walls must be either horizontal or vertical (not diagonal).

**Examples:**
```json
"walls": [
  [[0, 5], [10, 5]],
  [[3, 0], [3, 8]]
]
```

This creates:
- A horizontal wall from (0, 5) to (10, 5)
- A vertical wall from (3, 0) to (3, 8)

### `blocked_cells` (Optional, default: [])

Defines cells that the robot cannot enter. Unlike walls (which are between cells), blocked cells make entire grid positions impassable.

**Format:** Array of `[x, y]` coordinates

**Example:**
```json
"blocked_cells": [
  [3, 3],
  [3, 4],
  [4, 3],
  [4, 4]
]
```

This creates a 2×2 blocked area in the center of the grid.

### `items` (Optional, default: [])

Defines objects that can be picked up by the robot.

**Format:** Each item has:
- `type`: String identifier for the item type (e.g., "token", "star", "apple")
- `position`: `[x, y]` coordinate
- `count`: (Optional, default: 1) Number of items at this position

**Example:**
```json
"items": [
  {
    "type": "token",
    "position": [5, 5],
    "count": 3
  },
  {
    "type": "star",
    "position": [7, 2]
  }
]
```

This places:
- 3 tokens at position (5, 5)
- 1 star at position (7, 2)

## Advanced: Custom World Types

You can specify different world classes to add special behavior or goals.

### `world_class` (Optional, default: "World")

Specifies the type of world to create.

**Built-in world types:**
- `"World"` - Basic world with no special goals
- `"TargetWorld"` - World where the robot must reach a specific target position

### `world_params` (Optional)

Additional parameters required by specific world classes.

#### TargetWorld Example

For a `TargetWorld`, you must specify a `target` position:

```json
{
  "grid_size": [10, 10],
  "world_class": "TargetWorld",
  "world_params": {
    "target": [9, 9]
  },
  "robot_start": {
    "position": [0, 0],
    "heading": "north"
  }
}
```

This creates a world where the robot must reach position (9, 9) to complete the challenge.

## Complete Example

Here's a complete world that demonstrates all features:

```json
{
  "grid_size": [12, 8],
  "cell_size": 45,
  "world_class": "TargetWorld",
  "world_params": {
    "target": [11, 7]
  },
  "robot_start": {
    "position": [0, 0],
    "heading": "east"
  },
  "walls": [
    [[0, 4], [8, 4]],
    [[8, 4], [8, 0]],
    [[4, 8], [4, 5]]
  ],
  "blocked_cells": [
    [6, 2],
    [6, 3]
  ],
  "items": [
    {
      "type": "token",
      "position": [3, 2],
      "count": 5
    },
    {
      "type": "key",
      "position": [10, 6]
    },
    {
      "type": "star",
      "position": [5, 7],
      "count": 2
    }
  ]
}
```

This creates:
- A 12×8 grid world with larger cells (45 pixels)
- A target goal at the top-right corner (11, 7)
- Robot starting at bottom-left (0, 0) facing east
- Three wall segments creating a maze-like structure
- Two blocked cells at (6, 2) and (6, 3)
- Various collectible items scattered throughout

## Tips for World Design

1. **Test coordinates carefully**: Grid coordinates typically start at (0, 0) in the bottom-left corner.

2. **Wall validation**: The system will reject diagonal walls. Keep walls horizontal or vertical.

3. **Start simple**: Begin with a basic world structure and add complexity gradually.

4. **Item placement**: Make sure items aren't placed on blocked cells or walls.

5. **Solvability**: Test that your world is actually solvable before sharing it with students!

6. **Naming conventions**: Use descriptive names for item types that make sense in your context (e.g., "apple", "coin", "gem").

## Loading Your World

To load your world, save it as a `.json` file and use:

```python
# From a file
with open("my_world.json", "r") as f:
    world_data = json.load(f)
    world = load_world(world_data)

# From a string
json_string = '{"grid_size": [10, 10], ...}'
world = load_string(json_string)
```

## Error Messages

Common errors you might encounter:

- **"World file must specify 'grid_size'"**: You forgot the required `grid_size` field
- **"Wall must be horizontal or vertical"**: You tried to create a diagonal wall
- **"TargetWorld requires 'target' in world_params"**: You specified `TargetWorld` but didn't provide a target position
- **"Unknown world class"**: The `world_class` name isn't recognized

## Next Steps

Once you've created your world, you can:
- Write challenges and lessons around it
- Create a series of progressively harder worlds
- Share your worlds with other educators
- Extend the system with custom world classes for specialized behavior

Happy world building!