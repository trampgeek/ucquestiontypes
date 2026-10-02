"""
RoboTurtle - A Reeborg-like programming teaching tool built on Python turtle graphics.
"""

import turtle
import json
from collections import defaultdict


# ============================================================================
# Item System
# ============================================================================

class Item:
    """Item that can be placed in the grid, displayed using UTF-8 characters."""

    # Map of item names to UTF-8 display characters
    ITEM_SYMBOLS = {
        "star": "⭐",
        "key": "🔑",
        "leaf": "🍁"
    }
    DEFAULT_SYMBOL = "📦"

    def __init__(self, item_type: str):
        self.item_type = item_type
        self.symbol = self.ITEM_SYMBOLS.get(item_type, self.DEFAULT_SYMBOL)

    def draw(self, x: float, y: float, cell_size: float):
        """Draw the item using a UTF-8 character."""
        drawer = turtle.Turtle()
        drawer.hideturtle()
        drawer.speed(0)
        drawer.penup()
        drawer.goto(x, y - cell_size * 0.2)
        drawer.write(self.symbol, align="center", font=("Arial", int(cell_size * 0.6), "normal"))


# Item factory - now just creates Item instances with different types
ITEM_TYPES = {
    "star": lambda: Item("star"),
    "key": lambda: Item("key"),
    "leaf": lambda: Item("leaf")
}


# ============================================================================
# RoboTurtle - The visual representation of the robot
# ============================================================================

class RoboTurtle(turtle.Turtle):
    """A turtle subclass representing the robot with inventory."""
    
    def __init__(self):
        super().__init__()
        self.shape("turtle")
        self.inventory = []
    
    def add_item(self, item: Item):
        """Add an item to the robot's inventory."""
        self.inventory.append(item)
    
    def remove_item(self, item_type: str):
        """Remove and return an item of the specified type from inventory."""
        for i, item in enumerate(self.inventory):
            if item.item_type == item_type:
                return self.inventory.pop(i)
        return None
    
    def has_item(self, item_type = None) -> bool:
        """Check if robot has an item. If item_type is None, check if any item."""
        if item_type is None:
            return len(self.inventory) > 0
        return any(item.item_type == item_type for item in self.inventory)
    
    def get_inventory_count(self) -> int:
        """Return the number of items in inventory."""
        return len(self.inventory)


# ============================================================================
# World - Manages the grid, walls, items, and rendering
# ============================================================================

class World:
    """Base class for a robot world with grid, walls, and items."""
    _registry = {}  # Registry of known World subclasses
    
    @classmethod
    def __init_subclass__(cls, **kwargs):
        """Automatically register World subclasses."""
        super().__init_subclass__(**kwargs)
        if cls.__name__ != 'World':
            World._registry[cls.__name__] = cls
    
    @classmethod
    def create(cls, world_class_name, *args, **kwargs):
        """Factory method to instantiate a world of the given class name."""
        if world_class_name not in World._registry:
            raise ValueError(f"Unknown world class: {world_class_name}")
        return World._registry[world_class_name](*args, **kwargs)
    
    def __init__(self, grid_size, world_params=None):
        if world_params is None:
            world_params = {}
        self.grid_width, self.grid_height = grid_size
        self.cell_size = world_params.get('cell_size', 40)
        self.wall_segments = set()  # Set of unit wall segments for O(1) lookup
        self.blocked_cells = []
        self.items = defaultdict(list)  # position -> list of items
        self.robot = None
        self.robot_position = (0, 0)
        self.robot_heading: str = "north"  # north, east, south, west
        
        # Set up the screen
        self.screen = turtle.Screen()
        self.screen.title("RoboTurtle World")
        
        # Calculate screen size with margins for labels
        margin = 60
        screen_width = self.grid_width * cell_size + 2 * margin
        screen_height = self.grid_height * cell_size + 2 * margin
        self.screen.setup(width=int(screen_width * 0.7), height=int(screen_height * 0.7))
        self.screen.setworldcoordinates(-margin, -margin, 
                                       self.grid_width * cell_size + margin,
                                       self.grid_height * cell_size + margin)
        self.screen.tracer(0)  # Disable auto-update for faster drawing
        
    def add_wall(self, start, end):
        """Add a wall segment from start to end coordinates.
        
        The wall is broken into unit segments for efficient O(1) checking.
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
    
    def add_blocked_cell(self, position):
        """Mark a cell as blocked (no-go zone)."""
        self.blocked_cells.append(position)
    
    def add_item(self, item_type: str, position, count: int = 1):
        """Add items of a given type to a position."""
        if item_type not in ITEM_TYPES:
            raise ValueError(f"Unknown item type: {item_type}")
        
        for _ in range(count):
            self.items[position].append(ITEM_TYPES[item_type]())
    
    def draw_grid(self):
        """Draw the grid, walls, items, and labels."""
        drawer = turtle.Turtle()
        drawer.hideturtle()
        drawer.speed(0)
        drawer.penup()
        
        # Draw grid lines
        drawer.color("lightgray")
        drawer.pensize(1)
        
        # Vertical lines
        for x in range(self.grid_width + 1):
            drawer.penup()
            drawer.goto(x * self.cell_size, 0)
            drawer.pendown()
            drawer.goto(x * self.cell_size, self.grid_height * self.cell_size)
        
        # Horizontal lines
        for y in range(self.grid_height + 1):
            drawer.penup()
            drawer.goto(0, y * self.cell_size)
            drawer.pendown()
            drawer.goto(self.grid_width * self.cell_size, y * self.cell_size)
        
        # Draw axis labels
        drawer.penup()
        drawer.color("black")
        
        # X-axis labels (bottom)
        for x in range(self.grid_width):
            drawer.goto(x * self.cell_size + self.cell_size / 2, -30)
            drawer.write(str(x), align="center", font=("Arial", 10, "normal"))
        
        # Y-axis labels (left)
        for y in range(self.grid_height):
            drawer.goto(-30, y * self.cell_size + self.cell_size / 2 - 5)
            drawer.write(str(y), align="center", font=("Arial", 10, "normal"))
        
        # Draw blocked cells
        drawer.fillcolor("darkblue")
        for cell_x, cell_y in self.blocked_cells:
            drawer.penup()
            drawer.goto(cell_x * self.cell_size, cell_y * self.cell_size)
            drawer.pendown()
            drawer.begin_fill()
            for _ in range(4):
                drawer.forward(self.cell_size)
                drawer.left(90)
            drawer.end_fill()
        
        # Draw goal marker (if this is a subclass that defines one)
        self.draw_goal_marker()
        
        # Draw walls
        drawer.color("darkred")
        drawer.pensize(4)
        for (x1, y1), (x2, y2) in self.wall_segments:
            drawer.penup()
            drawer.goto(x1 * self.cell_size, y1 * self.cell_size)
            drawer.pendown()
            drawer.goto(x2 * self.cell_size, y2 * self.cell_size)
        
        # Draw items
        for position, item_list in self.items.items():
            if len(item_list) > 0:
                cell_x, cell_y = position
                center_x = cell_x * self.cell_size + self.cell_size / 2
                center_y = cell_y * self.cell_size + self.cell_size / 2
                
                # Draw the first item (they're all the same type in a cell)
                item_list[0].draw(center_x, center_y, self.cell_size)
                
                # If multiple items, draw count
                if len(item_list) > 1:
                    drawer.penup()
                    drawer.goto(center_x + self.cell_size * 0.25, 
                               center_y + self.cell_size * 0.15)
                    drawer.color("black")
                    drawer.write(str(len(item_list)), 
                               align="left", 
                               font=("Arial", 8, "normal"))
        
        self.screen.update()
        
        # Re-enable animation after initial grid drawing
        self.screen.tracer(1)
    
    def draw_goal_marker(self):
        """Draw a goal marker. Override in subclasses. Base class does nothing."""
        pass
    
    def create_robot(self, position, heading: str = "north"):
        """Create and position the robot."""
        self.robot = RoboTurtle()
        self.robot.hideturtle()  # Hide initially to avoid showing movement to start position
        self.robot.speed(0)  # Need to race to the start point
        self.robot_position = position
        self.robot_heading = heading
        
        # Position the robot at the center of the cell
        cell_x, cell_y = position
        screen_x = cell_x * self.cell_size + self.cell_size / 2
        screen_y = cell_y * self.cell_size + self.cell_size / 2
        
        self.robot.penup()
        self.robot.goto(screen_x, screen_y)
        
        # Set heading
        heading_angles = {"north": 90, "east": 0, "south": 270, "west": 180}
        self.robot.setheading(heading_angles[heading])
        
        # Now show the turtle at the correct position
        self.robot.showturtle()
        self.robot.speed(1)   # Slow movements. User can speed it up if they want.
        
        self.screen.update()
    
    def update_item_display(self, position):
        """Update the display of items at a specific position without redrawing the world."""
        cell_x, cell_y = position
        center_x = cell_x * self.cell_size + self.cell_size / 2
        center_y = cell_y * self.cell_size + self.cell_size / 2
        
        # Clear the area with a white rectangle
        eraser = turtle.Turtle()
        eraser.hideturtle()
        eraser.speed(0)
        eraser.penup()
        
        # Draw white rectangle to clear the cell
        rect_size = self.cell_size * 0.9
        eraser.goto(center_x - rect_size/2, center_y - rect_size/2)
        eraser.color("white")
        eraser.fillcolor("white")
        eraser.begin_fill()
        for _ in range(4):
            eraser.forward(rect_size)
            eraser.left(90)
        eraser.end_fill()
        
        # Redraw the item if any remain
        if position in self.items and len(self.items[position]) > 0:
            item_list = self.items[position]
            item_list[0].draw(center_x, center_y, self.cell_size)
            
            # Draw count if multiple items
            if len(item_list) > 1:
                counter = turtle.Turtle()
                counter.hideturtle()
                counter.speed(0)
                counter.penup()
                counter.goto(center_x + self.cell_size * 0.25, 
                           center_y + self.cell_size * 0.15)
                counter.color("black")
                counter.write(str(len(item_list)), 
                           align="left", 
                           font=("Arial", 8, "normal"))
    
    def bot_controller(self) -> 'BotController':
        """Return a controller for commanding the robot."""
        if self.robot is None:
            raise RuntimeError("Robot has not been created. Call create_robot() first.")
        return BotController(self)
    
    def is_wall_between(self, pos1, pos2) -> bool:
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
        
        # Simple set lookup - O(1)
        return edge in self.wall_segments
    
    def satisfies_goal(self) -> bool:
        """Check if the current world state satisfies the goal. Override in subclasses."""
        return True
    
    def unsatisfied_goal_message(self) -> str:
        """Return an appropriate explanatory message if satisfies_goal is False.
        Override in subclasses.
        """
        return ''


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
    
    def satisfies_goal(self) -> bool:
        """Check if the robot has reached the target position."""
        return self.robot_position == self.target
    
    def unsatisfied_goal_message(self) -> str:
        """Return what's wrong."""
        return (f"Robot did not reach the target. "
                f"Expected position: {self.target}, "
                f"Actual position: {self.robot_position}")


# ============================================================================
# BotController - The command interface for students
# ============================================================================

class BotController:
    """Controller interface for commanding the robot."""
    
    def __init__(self, world: World):
        self.world = world
    
    def move(self):
        """Move the robot forward one cell in its current direction."""
        # Calculate new position
        x, y = self.world.robot_position
        heading = self.world.robot_heading
        
        new_pos = {
            "north": (x, y + 1),
            "east": (x + 1, y),
            "south": (x, y - 1),
            "west": (x - 1, y)
        }[heading]
        
        new_x, new_y = new_pos
        
        # Check bounds
        if new_x < 0 or new_x >= self.world.grid_width or \
           new_y < 0 or new_y >= self.world.grid_height:
            raise RuntimeError(f"Cannot move: out of bounds (attempted to move to {new_pos})")
        
        # Check for walls
        if self.world.is_wall_between(self.world.robot_position, new_pos):
            raise RuntimeError(f"Cannot move: wall blocks path from {self.world.robot_position} to {new_pos}")
        
        # Check for blocked cells
        if new_pos in self.world.blocked_cells:
            raise RuntimeError(f"Cannot move: cell {new_pos} is blocked")
        
        # Move the robot
        self.world.robot_position = new_pos
        screen_x = new_x * self.world.cell_size + self.world.cell_size / 2
        screen_y = new_y * self.world.cell_size + self.world.cell_size / 2
        self.world.robot.goto(screen_x, screen_y)
    
    def turn_left(self):
        """Turn the robot 90 degrees to the left."""
        transitions = {
            "north": "west",
            "west": "south",
            "south": "east",
            "east": "north"
        }
        self.world.robot_heading = transitions[self.world.robot_heading]
        self.world.robot.left(90)
    
    def turn_right(self):
        """Turn the robot 90 degrees to the right."""
        transitions = {
            "north": "east",
            "east": "south",
            "south": "west",
            "west": "north"
        }
        self.world.robot_heading = transitions[self.world.robot_heading]
        self.world.robot.right(90)
    
    def take(self):
        """Pick up an item from the current cell."""
        pos = self.world.robot_position
        
        if pos not in self.world.items or len(self.world.items[pos]) == 0:
            raise RuntimeError(f"Cannot take: no items at position {pos}")
        
        # Remove one item from the cell
        item = self.world.items[pos].pop(0)
        if len(self.world.items[pos]) == 0:
            del self.world.items[pos]
        
        # Add to robot inventory
        self.world.robot.add_item(item)
        
        # Update just the item display at this position
        self.world.update_item_display(pos)
    
    def put(self):
        """Place an item from inventory into the current cell."""
        if not self.world.robot.has_item():
            raise RuntimeError("Cannot put: robot has no items in inventory")
        
        # Remove item from inventory (just take the first one)
        item = self.world.robot.inventory.pop(0)
        
        # Add to current cell
        pos = self.world.robot_position
        if pos not in self.world.items:
            self.world.items[pos] = []
        self.world.items[pos].append(item)
        
        # Update just the item display at this position
        self.world.update_item_display(pos)
    
    def toss(self):
        """Toss an item from inventory into the cell directly in front of the robot."""
        if not self.world.robot.has_item():
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

        front_x, front_y = front_pos

        # Check if front cell is valid (in bounds)
        if front_x < 0 or front_x >= self.world.grid_width or \
           front_y < 0 or front_y >= self.world.grid_height:
            raise RuntimeError(f"Cannot toss: target cell {front_pos} is out of bounds")

        # Check for walls
        if self.world.is_wall_between(self.world.robot_position, front_pos):
            raise RuntimeError(f"Cannot toss: wall blocks path to {front_pos}")

        # Check for blocked cells
        if front_pos in self.world.blocked_cells:
            raise RuntimeError(f"Cannot toss: cell {front_pos} is blocked")

        # Remove item from inventory (least-recently-picked-up, which is first in list)
        item = self.world.robot.inventory.pop(0)

        # Add to front cell
        if front_pos not in self.world.items:
            self.world.items[front_pos] = []
        self.world.items[front_pos].append(item)

        # Update the display at the front position
        self.world.update_item_display(front_pos)
    
    def build_wall(self):
        """Build a wall in front of the robot."""
        # Determine where the wall would be placed
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
        
        # Save robot state
        robot_pos = self.world.robot_position
        robot_heading = self.world.robot_heading
        heading_angles = {"north": 90, "east": 0, "south": 270, "west": 180}
        
        # Redraw the world
        self.world.screen.tracer(0)  # Disable animation for redraw
        self.world.screen.clear()
        self.world.draw_grid()
        
        # Restore robot
        self.world.robot.showturtle()
        self.world.robot.penup()
        self.world.robot.goto(robot_pos[0] * self.world.cell_size + self.world.cell_size / 2,
                             robot_pos[1] * self.world.cell_size + self.world.cell_size / 2)
        self.world.robot.setheading(heading_angles[robot_heading])
        self.world.screen.update()
        self.world.screen.tracer(1)  # Re-enable animation

    def get_turtle(self):
        """Not-for-general use method to get the underlying Turtle"""
        return self.world.robot
    
    # Query methods
    def at_goal(self) -> bool:
        """Check if the robot is at the goal."""
        return self.world.satisfies_goal()
    
    def front_is_clear(self) -> bool:
        """Check if the cell in front is clear (no wall, in bounds, not blocked)."""
        x, y = self.world.robot_position
        heading = self.world.robot_heading
        
        new_pos = {
            "north": (x, y + 1),
            "east": (x + 1, y),
            "south": (x, y - 1),
            "west": (x - 1, y)
        }[heading]
        
        new_x, new_y = new_pos
        
        # Check bounds
        if new_x < 0 or new_x >= self.world.grid_width or \
           new_y < 0 or new_y >= self.world.grid_height:
            return False
        
        # Check for walls
        if self.world.is_wall_between(self.world.robot_position, new_pos):
            return False
        
        # Check for blocked cells
        if new_pos in self.world.blocked_cells:
            return False
        
        return True
    
    def right_is_clear(self) -> bool:
        """Check if the cell to the right is clear."""
        # Temporarily turn right, check, turn back
        old_heading = self.world.robot_heading
        self.turn_right()
        result = self.front_is_clear()
        self.turn_left()
        return result
    
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
        old_heading = self.world.robot_heading
        self.turn_right()
        result = self.wall_in_front()
        self.turn_left()
        return result
    
    def object_here(self) -> bool:
        """Check if there's an object in the current cell."""
        pos = self.world.robot_position
        return pos in self.world.items and len(self.world.items[pos]) > 0
    
    def carries_object(self) -> bool:
        """Check if the robot is carrying any objects."""
        return self.world.robot.has_item()
    
    def is_facing_north(self) -> bool:
        """Check if the robot is facing north."""
        return self.world.robot_heading == "north"


# ============================================================================
# World Loading
# ============================================================================

class NoWorldLoaded:
    """Sentinel object that raises an error when any method is called."""
    
    def __getattr__(self, name):
        raise RuntimeError("No world loaded. Call roboturtle.load() first.")
    
    def __call__(self, *args, **kwargs):
        raise RuntimeError("No world loaded. Call roboturtle.load() first.")

# Global world instance for simple function-based interface

_current_world = None
_current_controller = NoWorldLoaded()


def load(filename: str) -> World:
    """Load a world from a JSON file and set it as the current world."""
    with open(filename, 'r') as f:
        s = f.read()
    return load_string(s)
    

def load_string(s:str) -> dict:
    """Load a world from the given json string and return it as a world dictionary."""
    data = json.loads(s)
    return load_world(data)


def load_world(data) -> World:
    """Given a world specification as a dictionary, extract all required data"""
    global _current_world, _current_controller
    if "grid_size" not in data:
        raise ValueError("World file must specify 'grid_size'")
    
    grid_size = tuple(data["grid_size"])
    
    # Determine world class
    world_class_name = data.get("world_class", "World")
    world_params = data.get("world_params", {})
    
    # Create world instance using factory method
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
    
    # Draw the world
    world.draw_grid()
    
    # Create robot
    robot_start = data.get("robot_start", {"position": [0, 0], "heading": "north"})
    world.create_robot(
        tuple(robot_start["position"]),
        robot_start.get("heading", "north")
    )
    
    # Set as current world and create controller
    _current_world = world
    _current_controller = BotController(world)
    
    return world


# ============================================================================
# Global command functions (Reeborg-style interface)
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
    """Remove an item from inventory without placing it."""

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
