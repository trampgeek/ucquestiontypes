"""
RobotTurtle Checker - CodeRunner Integration Guide
===================================================

This module provides a headless checker for RobotTurtle questions in CodeRunner.

SETUP IN CODERUNNER
-------------------

1. Question Type: Python3
2. Template: Use a custom template (see below)
3. Test Cases: Define in the "testcases" parameter

TEMPLATE EXAMPLE
----------------

Put this in your CodeRunner template:

```python
import json
import sys

# The checker module (paste robotturtle_checker.py content here or import it)
# {{ SUPPORT_FILES.robotturtle_checker }}

# Get the testcases from the question parameters
testcases_json = '''{{ QUESTION.parameters.testcases }}'''
testcases = json.loads(testcases_json)

# Get the student's answer  
student_code = '''{{ STUDENT_ANSWER }}'''

# Run the tests
result = robotturtle_checker.run_tests(testcases, student_code)
print(result)
```

Note: The double curly braces {{ }} are CodeRunner template syntax
and will be replaced with actual values when the test runs.

QUESTION PARAMETERS
-------------------

In the "Question parameters" field, define a JSON parameter called "testcases":

{
  "testcases": [
    {
      "grid_size": [10, 10],
      "cell_size": 40,
      "world_class": "TargetWorld",
      "world_params": {
        "target": [9, 5]
      },
      "robot_start": {
        "position": [0, 0],
        "heading": "east"
      },
      "walls": [
        [[5, 0], [5, 3]]
      ],
      "blocked_cells": [],
      "items": []
    }
  ]
}

TEST CASE STRUCTURE
-------------------

Each test case is a JSON object with:

- grid_size: [width, height] - Size of the grid in cells
- cell_size: int - Size of each cell in pixels (for display, not used in checker)
- world_class: str - Type of world ("World" or "TargetWorld")
- world_params: dict - Parameters for the world class
  - For TargetWorld: {"target": [x, y]}
- robot_start: dict
  - position: [x, y] - Starting position
  - heading: str - Starting direction ("north", "east", "south", "west")
- walls: list - Wall segments as [[x1, y1], [x2, y2]]
  - Walls are grid line coordinates (not cell coordinates)
  - Always horizontal or vertical
- blocked_cells: list - Cells the robot cannot enter [[x, y], ...]
- items: list - Items in the world
  - Each item: {"type": str, "position": [x, y], "count": int}
  - Types: "star", "key", "leaf", "circle"

SUCCESS OUTPUT
--------------

If the student's code passes all tests, the checker outputs:
  "Final state is correct, well done!"

This is the ONLY output that indicates success. Any other output indicates failure.

ERROR MESSAGES
--------------

The checker provides helpful error messages:

1. Movement Errors:
   - "Cannot move: out of bounds (attempted to move to (x, y))"
   - "Cannot move: wall blocks path from (x1, y1) to (x2, y2)"
   - "Cannot move: cell (x, y) is blocked"

2. Item Errors:
   - "Cannot take: no items at position (x, y)"
   - "Cannot put: robot has no items in inventory"
   - "Cannot toss: target cell (x, y) is out of bounds"
   - "Cannot toss: wall blocks path to (x, y)"
   - "Cannot toss: cell (x, y) is blocked"

3. Goal Errors:
   - "Robot did not reach the target. Expected position: (x1, y1), Actual position: (x2, y2)"

4. Code Errors:
   - "Syntax error in your code at line N: <message>"
   - "<ErrorType> at line N: <message>"

5. Operation Limit:
   - "Operation limit exceeded: your program executed more than 1000 robot operations. Check for infinite loops."

All error messages include line numbers when possible to help students debug.

FEATURES
--------

1. Operation Counting: Prevents infinite loops by limiting to 1000 operations
2. Line Numbers: Error messages include line numbers from student code
3. Exact Error Messages: Matches the interactive version's error messages
4. Headless: No graphics, suitable for server-side checking
5. Multiple Tests: Can run multiple test cases in sequence

EXAMPLE QUESTION
----------------

Question Text:
"Write code to move the robot from its starting position to the goal (marked with a flag).
Navigate around the wall to reach the target."

Question Parameters:
{
  "testcases": [
    {
      "grid_size": [10, 10],
      "world_class": "TargetWorld",
      "world_params": {"target": [9, 5]},
      "robot_start": {"position": [0, 0], "heading": "east"},
      "walls": [[[5, 0], [5, 3]]],
      "blocked_cells": [],
      "items": []
    }
  ]
}

Expected Answer:
```python
# Navigate around the wall
for i in range(4):
    move()
turn_left()
for i in range(5):
    move()
turn_right()
for i in range(5):
    move()
```

AVAILABLE FUNCTIONS FOR STUDENTS
---------------------------------

Movement:
- move() - Move forward one cell
- turn_left() - Turn 90° counterclockwise
- turn_right() - Turn 90° clockwise

Items:
- take() - Pick up item from current cell
- put() - Place item from inventory in current cell
- toss() - Place item from inventory in cell directly ahead

Building:
- build_wall() - Build wall at edge of current cell in facing direction

Sensors (return bool):
- at_goal() - True if at the goal position
- front_is_clear() - True if can move forward
- right_is_clear() - True if cell to right is clear
- wall_in_front() - True if wall directly ahead
- wall_on_right() - True if wall to the right
- object_here() - True if item in current cell
- carries_object() - True if inventory not empty
- is_facing_north() - True if facing north

EXTENDING FOR OTHER WORLD TYPES
--------------------------------

Currently only TargetWorld is implemented. To add other world types:

1. Create a new World subclass in robotturtle_checker.py
2. Override satisfies_goal() method
3. Add to the world loading logic in load_world()
4. Document the world_params for that world type

Example for an ItemCollectionWorld:
- world_params: {"collect_type": "star", "collect_count": 5, "delivery": [8, 8]}
- satisfies_goal(): Check if correct items collected and delivered
"""

# Example of how CodeRunner would use this
if __name__ == "__main__":
    import json
    import robotturtle_checker
    
    # Example: This would come from CodeRunner's template
    testcases_json = """
    [
        {
            "grid_size": [10, 10],
            "world_class": "TargetWorld",
            "world_params": {"target": [9, 5]},
            "robot_start": {"position": [0, 0], "heading": "east"},
            "walls": [[[5, 0], [5, 3]]],
            "blocked_cells": [],
            "items": []
        }
    ]
    """
    
    testcases = json.loads(testcases_json)
    
    # Example student answer
    student_code = """
for i in range(4):
    move()
turn_left()
for i in range(5):
    move()
turn_right()
for i in range(5):
    move()
"""
    
    # Run and print result
    result = robotturtle_checker.run_tests(testcases, student_code)
    print(result)
