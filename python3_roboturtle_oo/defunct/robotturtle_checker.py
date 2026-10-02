"""
RoboTurtle Checker - Headless version for CodeRunner testing.

This module provides a non-graphical version of the RobotTurtle world
for automated checking of student code.
"""

import json
import sys
import traceback
import turtle
from collections import defaultdict
from typing import List, Tuple, Dict, Any, Optional


# Maximum number of robot operations allowed
MAX_OPERATIONS = 1000
DEFAULT_CELL_SIZE = 40  # Can be overridden in world_params.
ALL_CORRECT = "Final state is correct, well done!"

# ============================================================================
# Item System (Headless)
# ============================================================================

class Item:
    """Item that can be placed in the grid."""
    
    def __init__(self, item_type: str):
        self.item_type = item_type


# ============================================================================
# World (Headless)
# ============================================================================

class World:
    """Base class for a robot world with grid, walls, and items (no graphics)."""
    _registry = {}  # Register of known subclasses

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.__name__ != 'World':
            World._registry[cls.__name__] = cls

    @classmethod
    def create(cls, world_class_name, *args, **kwargs):
        """Instantiate a world of the given world class name."""
        if world_class_name not in World._registry:
            raise ValueError(f"Unknown world class: {world_class_name}")
        return World._registry[world_class_name](*args, **kwargs)
        
    
    def __init__(self, grid_size: Tuple[int, int], world_params: Dict = None):
        self.grid_width, self.grid_height = grid_size
        if world_params is None or 'cell_size' not in world_params:
            self.cell_size = DEFAULT_CELL_SIZE
        else:
            self.cell_size = world_params['cell_size']
        self.wall_segments = set()  # Set of unit wall segments for fast lookup
        self.blocked_cells = []
        self.items: Dict[Tuple[int, int], List[Item]] = defaultdict(list)
        self.robot_position: Tuple[int, int] = (0, 0)
        self.robot_heading: str = "north"
        self.robot_inventory: List[Item] = []
        self.operation_count: int = 0
        self.fail_messages = []

        # Add perimeter walls around the entire grid
        self._add_perimeter_walls()

    def add_wall(self, start: Tuple[int, int], end: Tuple[int, int]):
        """Add a wall segment from start to end coordinates.
        
        The wall is broken into unit segments for efficient checking.
        """
        x1, y1 = start
        x2, y2 = end
        
        # Break the wall into unit segments
        if x1 == x2:  # Vertical wall
            y_min, y_max = min(y1, y2), max(y1, y2)
            for y in range(y_min, y_max):
                self.wall_segments.add(((x1, y), (x1, y + 1)))
        else:  # Horizontal wall
            x_min, x_max = min(x1, x2), max(x1, x2)
            for x in range(x_min, x_max):
                self.wall_segments.add(((x, y1), (x + 1, y1)))

    def _add_perimeter_walls(self):
        """Add walls around the entire perimeter of the grid."""
        # Bottom wall
        self.add_wall((0, 0), (self.grid_width, 0))
        # Top wall
        self.add_wall((0, self.grid_height), (self.grid_width, self.grid_height))
        # Left wall
        self.add_wall((0, 0), (0, self.grid_height))
        # Right wall
        self.add_wall((self.grid_width, 0), (self.grid_width, self.grid_height))

    def add_blocked_cell(self, position: Tuple[int, int]):
        """Mark a cell as blocked (no-go zone)."""
        self.blocked_cells.append(position)
    
    def add_item(self, item_type: str, position: Tuple[int, int], count: int = 1):
        """Add items of a given type to a position."""
        for _ in range(count):
            self.items[position].append(Item(item_type))
    
    def set_robot_start(self, position: Tuple[int, int], heading: str = "north"):
        """Set the robot's starting position and heading."""
        self.robot_position = position
        self.robot_heading = heading
        self.robot_inventory = []
        self.operation_count = 0
    
    def is_wall_between(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> bool:
        """Check if there's a wall between two adjacent positions."""
        x1, y1 = pos1
        x2, y2 = pos2
        
        # Calculate the edge segment between the two cells
        if x2 > x1:  # Moving east
            edge = ((x2, y1), (x2, y1 + 1))
        elif x2 < x1:  # Moving west
            edge = ((x1, y1), (x1, y1 + 1))
        elif y2 > y1:  # Moving north
            edge = ((x1, y2), (x1 + 1, y2))
        else:  # Moving south
            edge = ((x1, y1), (x1 + 1, y1))
        
        return edge in self.wall_segments
    
    def check_final_state(self):
        """Check if the current world state satisfies the goal. Any errors
           must be appended to self.fail_messages.
           Override in subclasses.
        """
        return None
    
    def satisfies_goal(self):
        """True iff goal condition is satisfied. check_final_state must have been called"""
        return not self.fail_messages
    
    def fail_message(self) -> str:
        """Return an appropriate explanatory message if satisfies_goal is False.
        """
        return '\n'.join(self.fail_messages)
    
    def _check_operation_limit(self):
        """Check if operation limit has been exceeded."""
        self.operation_count += 1
        if self.operation_count > MAX_OPERATIONS:
            raise RuntimeError(
                f"Operation limit exceeded: your program executed more than {MAX_OPERATIONS} "
                f"robot operations. Check for infinite loops."
            )


class TargetWorld(World):
    """A world where the goal is to reach a specific target position."""
    
    def __init__(self, grid_size, world_params):
        super().__init__(grid_size, world_params)
        if 'target' not in world_params:
            raise ValueError("TargetWorld requires 'target' in world_params")
        self.target = tuple(world_params['target'])
    
    def draw_goal_marker(self):
        """Draw a chequered flag at the target cell."""
        cell_x, cell_y = self.target
        center_x = cell_x * self.cell_size + self.cell_size / 2
        center_y = cell_y * self.cell_size + self.cell_size / 2

        drawer = turtle.Turtle()
        drawer.hideturtle()
        drawer.speed(0)
        drawer.penup()
        drawer.goto(center_x, center_y - self.cell_size * 0.2)
        drawer.write("🏁", align="center", font=("Arial", int(self.cell_size * 0.5), "normal"))
    
    def check_final_state(self):
        """Check if the robot has reached the target position. If not,
           set self.fail_messages to an explanatory comment.
        """
        if self.robot_position != self.target:
            self.fail_messages.append(f"Robot did not reach the target. "
                f"Expected position: {self.target}, "
                f"Actual position: {self.robot_position}")
        return None


class PickUpItemsWorld(TargetWorld):
    """A subclass of TargetWorld in which all items in the
       grid except at those explicitly excluded cells are meant to have been
       collected and (optionally)
       put down again at a specified location. If there is a specified
       location for dumping items, it is automatically excluded from
       the search for items.
    """
    def __init__(self, grid_size, world_params):
        super().__init__(grid_size, world_params)
        exclude = world_params.get('exclude_cells', [])
        self.exclude = set(tuple(loc) for loc in exclude)
        self.item_dump = world_params.get('item_dump', None)
        if self.item_dump:
            self.exclude.append(self.item_dump.location)

    def check_final_state(self) -> bool:
        """Set self.fail_messages to a list of all faults in the final state
        """
        super().check_final_state()
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                if (x, y) not in self.exclude:
                    if self.items[(x, y)]:
                        self.fail_messages.append(f"Item(s) found at location ({x}, {y})")
        return None


# ============================================================================
# BotController (Headless)
# ============================================================================

class BotController:
    """Controller interface for commanding the robot (headless version)."""
    
    def __init__(self, world: World):
        self.world = world
    
    def move(self):
        """Move the robot forward one cell in its current direction."""
        self.world._check_operation_limit()
        
        x, y = self.world.robot_position
        heading = self.world.robot_heading
        
        new_pos = {
            "north": (x, y + 1),
            "east": (x + 1, y),
            "south": (x, y - 1),
            "west": (x - 1, y)
        }[heading]
        
        # Check for walls (including perimeter)
        if self.world.is_wall_between(self.world.robot_position, new_pos):
            raise RuntimeError(f"Cannot move: wall blocks path from {self.world.robot_position} to {new_pos}")
        
        # Check for blocked cells
        if new_pos in self.world.blocked_cells:
            raise RuntimeError(f"Cannot move: cell {new_pos} is blocked")
        
        # Move the robot
        self.world.robot_position = new_pos
    
    def turn_left(self):
        """Turn the robot 90 degrees to the left."""
        self.world._check_operation_limit()
        
        transitions = {
            "north": "west",
            "west": "south",
            "south": "east",
            "east": "north"
        }
        self.world.robot_heading = transitions[self.world.robot_heading]
    
    def turn_right(self):
        """Turn the robot 90 degrees to the right."""
        self.world._check_operation_limit()
        
        transitions = {
            "north": "east",
            "east": "south",
            "south": "west",
            "west": "north"
        }
        self.world.robot_heading = transitions[self.world.robot_heading]
    
    def take(self):
        """Pick up an item from the current cell."""
        self.world._check_operation_limit()
        
        pos = self.world.robot_position
        
        if pos not in self.world.items or len(self.world.items[pos]) == 0:
            raise RuntimeError(f"Cannot take: no items at position {pos}")
        
        # Remove one item from the cell
        item = self.world.items[pos].pop(0)
        
        # Add to robot inventory
        self.world.robot_inventory.append(item)
    
    def put(self):
        """Place an item from inventory into the current cell."""
        self.world._check_operation_limit()
        
        if len(self.world.robot_inventory) == 0:
            raise RuntimeError("Cannot put: robot has no items in inventory")
        
        # Remove item from inventory (FIFO - first in, first out)
        item = self.world.robot_inventory.pop(0)
        
        # Add to current cell
        pos = self.world.robot_position
        self.world.items[pos].append(item)
    
    def toss(self):
        """Toss an item from inventory into the cell directly in front of the robot."""
        self.world._check_operation_limit()
        
        if len(self.world.robot_inventory) == 0:
            raise RuntimeError("Cannot toss: robot has no items in inventory")
        
        # Calculate the position in front of the robot
        x, y = self.world.robot_position
        heading = self.world.robot_heading
        
        front_pos = {
            "north": (x, y + 1),
            "east": (x + 1, y),
            "south": (x, y - 1),
            "west": (x - 1, y)
        }[heading]
        
        # Check for walls (including perimeter)
        if self.world.is_wall_between(self.world.robot_position, front_pos):
            raise RuntimeError(f"Cannot toss: wall blocks path to {front_pos}")
        
        # Check for blocked cells
        if front_pos in self.world.blocked_cells:
            raise RuntimeError(f"Cannot toss: cell {front_pos} is blocked")
        
        # Remove item from inventory (FIFO)
        item = self.world.robot_inventory.pop(0)
        
        # Add to front cell
        self.world.items[front_pos].append(item)
    
    def build_wall(self):
        """Build a wall in front of the robot."""
        self.world._check_operation_limit()
        
        x, y = self.world.robot_position
        heading = self.world.robot_heading
        
        # Calculate the unit wall segment to add
        if heading == "north":
            wall = ((x, y + 1), (x + 1, y + 1))
        elif heading == "east":
            wall = ((x + 1, y), (x + 1, y + 1))
        elif heading == "south":
            wall = ((x, y), (x + 1, y))
        else:  # west
            wall = ((x, y), (x, y + 1))
        
        # Add the unit segment to the set
        self.world.wall_segments.add(wall)
    
    # Query methods
    def at_goal(self) -> bool:
        """Check if the robot is at the goal."""
        return self.world.satisfies_goal()
    
    def front_is_clear(self) -> bool:
        """Check if the cell in front is clear (no wall, not blocked)."""
        x, y = self.world.robot_position
        heading = self.world.robot_heading

        new_pos = {
            "north": (x, y + 1),
            "east": (x + 1, y),
            "south": (x, y - 1),
            "west": (x - 1, y)
        }[heading]

        # Check for walls (including perimeter)
        if self.world.is_wall_between(self.world.robot_position, new_pos):
            return False
        
        # Check for blocked cells
        if new_pos in self.world.blocked_cells:
            return False
        
        return True
    
    def right_is_clear(self) -> bool:
        """Check if the cell to the right is clear."""
        x, y = self.world.robot_position
        heading = self.world.robot_heading
        
        # Calculate position to the right without actually turning
        right_pos = {
            "north": (x + 1, y),      # Right of north is east
            "east": (x, y - 1),       # Right of east is south
            "south": (x - 1, y),      # Right of south is west
            "west": (x, y + 1)        # Right of west is north
        }[heading]
        
        new_x, new_y = right_pos
        
        # Check bounds
        if new_x < 0 or new_x >= self.world.grid_width or \
           new_y < 0 or new_y >= self.world.grid_height:
            return False
        
        # Check for walls
        if self.world.is_wall_between(self.world.robot_position, right_pos):
            return False
        
        # Check for blocked cells
        if right_pos in self.world.blocked_cells:
            return False
        
        return True
    
    def wall_in_front(self) -> bool:
        """Check if there's a wall directly in front."""
        x, y = self.world.robot_position
        heading = self.world.robot_heading
        
        new_pos = {
            "north": (x, y + 1),
            "east": (x + 1, y),
            "south": (x, y - 1),
            "west": (x - 1, y)
        }[heading]
        
        return self.world.is_wall_between(self.world.robot_position, new_pos)
    
    def wall_on_right(self) -> bool:
        """Check if there's a wall on the right side."""
        x, y = self.world.robot_position
        heading = self.world.robot_heading
        
        # Calculate position to the right without actually turning
        right_pos = {
            "north": (x + 1, y),      # Right of north is east
            "east": (x, y - 1),       # Right of east is south
            "south": (x - 1, y),      # Right of south is west
            "west": (x, y + 1)        # Right of west is north
        }[heading]
        
        return self.world.is_wall_between(self.world.robot_position, right_pos)
    
    def object_here(self) -> bool:
        """Check if there's an object in the current cell."""
        pos = self.world.robot_position
        return len(self.world.items[pos]) > 0
    
    def carries_object(self) -> bool:
        """Check if the robot is carrying any objects."""
        return len(self.world.robot_inventory) > 0
    
    def is_facing_north(self) -> bool:
        """Check if the robot is facing north."""
        return self.world.robot_heading == "north"


# ============================================================================
# World Loading
# ============================================================================

class NoWorldLoaded:
    """Sentinel object that raises an error when any method is called."""
    
    def __getattr__(self, name):
        raise RuntimeError("No world loaded.")
    
    def __call__(self, *args, **kwargs):
        raise RuntimeError("No world loaded.")


_current_world = None
_current_controller = NoWorldLoaded()


def load_world(data: Dict[str, Any]) -> World:
    """Load a world from a dictionary specification."""
    global _current_world, _current_controller
    
    if "grid_size" not in data:
        raise ValueError("World file must specify 'grid_size'")
    
    grid_size = tuple(data["grid_size"])
    
    # Determine world class
    world_class_name = data.get("world_class", "World")
    world_params = data.get("world_params", {})
    
    # Create world instance
    world = World.create(world_class_name, grid_size, world_params)
    
    # Add walls
    for wall in data.get("walls", []):
        start = tuple(wall[0])
        end = tuple(wall[1])
        # Validate wall is either horizontal or vertical
        if start[0] != end[0] and start[1] != end[1]:
            raise ValueError(f"Wall must be horizontal or vertical: {wall}")
        world.add_wall(start, end)
    
    # Add blocked cells
    for cell in data.get("blocked_cells", []):
        world.add_blocked_cell(tuple(cell))
    
    # Add items
    for item_data in data.get("items", []):
        world.add_item(
            item_data["type"],
            tuple(item_data["position"]),
            item_data.get("count", 1)
        )
    
    # Set robot start position
    robot_start = data.get("robot_start", {"position": [0, 0], "heading": "north"})
    world.set_robot_start(
        tuple(robot_start["position"]),
        robot_start.get("heading", "north")
    )
    
    # Set as current world and create controller
    _current_world = world
    _current_controller = BotController(world)
    
    return world


# ============================================================================
# Global command functions (API for student code)
# ============================================================================

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
    """Toss an item from inventory into the cell directly in front."""
    _current_controller.toss()


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

def speed(n: int):
    """Does nothing when checking."""
    return


# ============================================================================
# Checker Function
# ============================================================================

def run_tests(testcases: List[Dict[str, Any]], student_code: str) -> str:
    """
    Run student code against all test cases.
    
    Args:
        testcases: List of test case specifications
        student_code: The student's Python code as a string
    
    Returns:
        Success message if all tests pass, error message otherwise
    """
    for i, testcase in enumerate(testcases):
        try:
            # Load the world for this test case
            load_world(testcase)
            
            # Create a namespace with the global functions
            namespace = {
                'move': move,
                'turn_left': turn_left,
                'turn_right': turn_right,
                'take': take,
                'put': put,
                'toss': toss,
                'build_wall': build_wall,
                'at_goal': at_goal,
                'front_is_clear': front_is_clear,
                'right_is_clear': right_is_clear,
                'wall_in_front': wall_in_front,
                'wall_on_right': wall_on_right,
                'object_here': object_here,
                'carries_object': carries_object,
                'is_facing_north': is_facing_north,
                'speed': speed,
            }
            
            # Execute the student's code
            try:
                exec(student_code, namespace)
            except SyntaxError as e:
                return f"Syntax error in your code at line {e.lineno}: {e.msg}"
            except RuntimeError as e:
                # Extract line number from traceback
                tb = traceback.extract_tb(sys.exc_info()[2])
                # Find the last frame that's in the student's code (not in this module)
                student_frame = None
                for frame in tb:
                    if frame.filename == "<string>":
                        student_frame = frame
                
                error_msg = str(e)
                if student_frame:
                    return f"Error at line {student_frame.lineno}: {error_msg}"
                else:
                    return f"Error: {error_msg}"
            except Exception as e:
                # Extract line number from traceback
                tb = traceback.extract_tb(sys.exc_info()[2])
                student_frame = None
                for frame in tb:
                    if frame.filename == "<string>":
                        student_frame = frame
                
                error_type = type(e).__name__
                error_msg = str(e)
                if student_frame:
                    return f"{error_type} at line {student_frame.lineno}: {error_msg}"
                else:
                    return f"{error_type}: {error_msg}"
            
            # Check if goal is satisfied
            if not _current_world.satisfies_goal():
                return _current_world.unsatisfied_goal_message()
        
        except Exception as e:
            return f"Test setup error: {str(e)}"
    
    # All tests passed
    return ALL_CORRECT

__student_code = """{{ STUDENT_ANSWER | e('py') }}"""

__testcases = json.loads("""{{testcases | json_encode}}""")

output = run_tests(__testcases, __student_code)
fraction = 1 if output == ALL_CORRECT else 0
result = {'fraction': fraction, 'prologuehtml': f"<h3>{output}</h3>"}
print(json.dumps(result))