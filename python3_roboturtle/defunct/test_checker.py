"""
Test script for RobotTurtle checker
"""

import robotturtle_checker as rtc

# Example test case (from the spec)
testcase = {
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
            "type": "circle",
            "position": [3, 2],
            "count": 5
        },
        {
            "type": "leaf",
            "position": [10, 6]
        },
        {
            "type": "star",
            "position": [5, 7],
            "count": 2
        }
    ]
}

print("=" * 70)
print("TEST 1: Correct solution - simple navigation")
print("=" * 70)

# Use a simpler test case for demonstration
simple_demo_testcase = {
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
        [[5, 0], [5, 3]]  # Vertical wall that requires navigation around
    ],
    "blocked_cells": [],
    "items": []
}

correct_code = """
# Navigate around the wall to reach target
# Move east to just before wall
for i in range(4):
    move()
    
# Go north to get above the wall
turn_left()
for i in range(5):
    move()
    
# Go east past the wall to target
turn_right()
for i in range(5):
    move()
"""

result = rtc.run_tests([simple_demo_testcase], correct_code)
print(result)
print()

print("=" * 70)
print("TEST 2: Wrong final position")
print("=" * 70)

wrong_position_code = """
# Only move partway
for i in range(5):
    move()
"""

result = rtc.run_tests([testcase], wrong_position_code)
print(result)
print()

print("=" * 70)
print("TEST 3: Hit a wall")
print("=" * 70)

hit_wall_code = """
# Try to move through a wall
for i in range(4):
    move()
turn_left()
move()  # This should hit a wall
"""

result = rtc.run_tests([testcase], hit_wall_code)
print(result)
print()

print("=" * 70)
print("TEST 4: Out of bounds")
print("=" * 70)

out_of_bounds_code = """
# Try to move out of bounds
turn_left()
move()  # Try to move north from (0,0) - out of bounds
"""

result = rtc.run_tests([testcase], out_of_bounds_code)
print(result)
print()

print("=" * 70)
print("TEST 5: Take when no item present")
print("=" * 70)

no_item_code = """
take()  # No item at starting position
"""

result = rtc.run_tests([testcase], no_item_code)
print(result)
print()

print("=" * 70)
print("TEST 6: Put with empty inventory")
print("=" * 70)

empty_inventory_code = """
put()  # Nothing in inventory
"""

result = rtc.run_tests([testcase], empty_inventory_code)
print(result)
print()

print("=" * 70)
print("TEST 7: Syntax error")
print("=" * 70)

syntax_error_code = """
move()
if front_is_clear(  # Missing closing parenthesis
    move()
"""

result = rtc.run_tests([testcase], syntax_error_code)
print(result)
print()

print("=" * 70)
print("TEST 8: Infinite loop (operation limit)")
print("=" * 70)

infinite_loop_code = """
while True:
    if front_is_clear():
        move()
    else:
        turn_left()
"""

result = rtc.run_tests([testcase], infinite_loop_code)
print(result)
print()

print("=" * 70)
print("TEST 9: Simple navigation with correct solution")
print("=" * 70)

# Simpler test case
simple_testcase = {
    "grid_size": [5, 5],
    "cell_size": 40,
    "world_class": "TargetWorld",
    "world_params": {
        "target": [4, 4]
    },
    "robot_start": {
        "position": [0, 0],
        "heading": "east"
    },
    "walls": [],
    "blocked_cells": [],
    "items": []
}

simple_correct = """
# Navigate to (4, 4)
for i in range(4):
    move()
turn_left()
for i in range(4):
    move()
"""

result = rtc.run_tests([simple_testcase], simple_correct)
print(result)
print()

print("=" * 70)
print("TEST 10: Using conditionals and sensors")
print("=" * 70)

conditional_code = """
# Navigate using sensors
while not at_goal():
    if front_is_clear():
        move()
    elif right_is_clear():
        turn_right()
        move()
    else:
        turn_left()
"""

result = rtc.run_tests([simple_testcase], conditional_code)
print(result)
print()

print("=" * 70)
print("TEST 11: Item manipulation")
print("=" * 70)

item_testcase = {
    "grid_size": [5, 5],
    "cell_size": 40,
    "world_class": "TargetWorld",
    "world_params": {
        "target": [2, 0]
    },
    "robot_start": {
        "position": [0, 0],
        "heading": "east"
    },
    "walls": [],
    "blocked_cells": [],
    "items": [
        {
            "type": "star",
            "position": [1, 0],
            "count": 1
        }
    ]
}

item_code = """
# Pick up item and move to target
move()
take()
move()
"""

result = rtc.run_tests([item_testcase], item_code)
print(result)
print()

print("=" * 70)
print("TEST 12: Toss item through wall (should fail)")
print("=" * 70)

toss_wall_testcase = {
    "grid_size": [5, 5],
    "cell_size": 40,
    "world_class": "TargetWorld",
    "world_params": {
        "target": [0, 0]
    },
    "robot_start": {
        "position": [0, 0],
        "heading": "east"
    },
    "walls": [
        [[1, 0], [1, 1]]
    ],
    "blocked_cells": [],
    "items": [
        {
            "type": "star",
            "position": [0, 0],
            "count": 1
        }
    ]
}

toss_wall_code = """
take()
toss()  # Should fail - wall in the way
"""

result = rtc.run_tests([toss_wall_testcase], toss_wall_code)
print(result)
print()
