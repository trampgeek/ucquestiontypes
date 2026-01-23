# ============================================================================
# Global command functions (Reeborg-style interface)
# ============================================================================

global _current_controller, _current_world  #omitfrombuild

def move():
    """Move the robot forward one cell."""
    _current_controller.move()


def turn_left():
    """Turn the robot 90 degrees to the left."""
    _current_controller.turn_left()


def turn_right():
    """Turn the robot 90 degrees to the right."""
    _current_controller.turn_right()


def take():
    """Pick up an item from the current cell."""
    _current_controller.take()


def put():
    """Place an item from inventory into the current cell."""
    _current_controller.put()


def toss():
    """Remove an item from inventory without placing it."""
    return _current_controller.toss()

def get_turtle():
    """Not for general use - get the actual turtle"""
    return _current_controller.get_turtle()

def build_wall():
    """Build a wall in front of the robot."""
    _current_controller.build_wall()


def at_goal() -> bool:
    """Check if the robot is at the goal."""
    return _current_controller.at_goal()


def front_is_clear() -> bool:
    """Check if the cell in front is clear."""
    return _current_controller.front_is_clear()


def right_is_clear() -> bool:
    """Check if the cell to the right is clear."""
    return _current_controller.right_is_clear()


def wall_in_front() -> bool:
    """Check if there's a wall directly in front."""
    return _current_controller.wall_in_front()


def wall_on_right() -> bool:
    """Check if there's a wall on the right side."""
    return _current_controller.wall_on_right()


def object_here() -> bool:
    """Check if there's an object in the current cell."""
    return _current_controller.object_here()


def carries_object() -> bool:
    """Check if the robot is carrying any objects."""
    return _current_controller.carries_object()


def is_facing_north() -> bool:
    """Check if the robot is facing north."""
    return _current_controller.is_facing_north()


def speed(speed_factor: int):
    """Set the speed from 1 (slow) to 10 (fast). 0 is superfast."""
    _current_world.robot.speed(speed_factor)

def print_state():
    """Print where the robot is and its heading"""
    _current_controller.print_state()