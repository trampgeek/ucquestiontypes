"""
The assembled RoboTurtle and all its support classes, ready
for inclusion in both the CodeRunner question template and the
prototypeextra.html file that needs to execute the same code
using Skulpt.
"""

# ============================================================================
# Item Class
# ============================================================================


class Item:
    """Item that can be placed in the grid, displayed using UTF-8 characters."""

    # Map of item names to UTF-8 display characters
    ITEM_TYPES = {
        "star": "⭐",
        "key": "🔑",
        "leaf": "🍁",
        "house": "🏠",
        "home": "🏠",  # Synonym for house
        "flag": "🏁",
        "trash": "🗑",
        "box": "📦",
        "target": "🎯",
    }
    DEFAULT_SYMBOL = "📦"

    def __init__(self, item_type: str):
        self.item_type = item_type
        self.symbol = self.ITEM_TYPES.get(item_type, self.DEFAULT_SYMBOL)

    def draw(self, x: float, y: float, cell_size: float):
        """Draw the item using a UTF-8 character."""
        drawer = Turtle()
        drawer.hideturtle()
        drawer.speed(0)
        drawer.penup()
        drawer.goto(x, y - cell_size * 0.2)
        drawer.write(self.symbol, align="center", font=("Arial", int(cell_size * 0.45), "normal"))

# ============================================================================
# RoboTurtle - The visual representation of the robot
# ============================================================================


class RoboTurtle(Turtle):
    """A turtle subclass representing the robot with inventory."""
    
    def __init__(self):
        super().__init__()
        self.shape("turtle")
        self.inventory = []
    
    def add_item_to_inventory(self, item):
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

"""
#============================================================================
# World - Manages the grid, walls, items, and rendering
# ============================================================================
"""
from collections import defaultdict

# dummy imports to let VS Code do type checking

DEFAULT_CELL_SIZE = 65
FILL_COLOUR = "#4CBB17"

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
        self.cell_size = world_params.get('cell_size', DEFAULT_CELL_SIZE)
        self.wall_segments = set()  # Set of unit wall segments for O(1) lookup
        self.blocked_cells = []
        self.items = defaultdict(list)  # position (tuple) -> list of items
        self.robot = None
        self.robot_position = (0, 0)
        self.robot_heading: str = "north"  # north, east, south, west
        self.fail_messages = []  # A list of errors in the final state. Empty if goal satisfied.
        self.world_params = world_params
        self.path = [] # A list of the cells that the turtle moves into.
        self.labelled_cells = [] # A list of [location, utf8_char] pairs of labelled cells.
        if world_params and 'labelled_cells' in world_params:
            self.labelled_cells = world_params['labelled_cells']  

        # Set up the screen
        self.screen = Screen()
        self.screen.title("RoboTurtle World")
        
        # Calculate screen size with margins for labels
        margin = 60
        screen_width = self.grid_width * self.cell_size + 2 * margin
        screen_height = self.grid_height * self.cell_size + 2 * margin
        self.screen.setup(width=int(screen_width * 0.7), height=int(screen_height * 0.7))
        self.screen.setworldcoordinates(-margin, -margin,
                                       self.grid_width * self.cell_size + margin,
                                       self.grid_height * self.cell_size + margin)
        self.screen.tracer(0)  # Disable auto-update for faster drawing

        # Add perimeter walls around the entire grid
        self._add_perimeter_walls()

    def at_goal(self):
        """True if Robot is at its target position. Subclasses must implement."""
        return False


    def cell_centre(self, cell):
        """Return the x, y coords of the centre of the given cell"""
        x, y = cell
        return x * self.cell_size + self.cell_size / 2, y * self.cell_size + self.cell_size / 2

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

    def add_blocked_cell(self, position):
        """Mark a cell as blocked (no-go zone)."""
        self.blocked_cells.append(position)
    
    def add_item_to_cell(self, item, position: tuple, count: int = 1):
        """Add items to a cell at a given position."""       
        for _ in range(count):
            self.items[position].append(item)

    def draw_fixed_icons(self, location_of_interest=None):
        """Put the appropriate special character into each labelled cell if location_of_interest is None
           or just the marker(s) at the specified location_of_interest if given.
        """
        if self.labelled_cells:
            drawer = Turtle()
            drawer.hideturtle()
            drawer.speed(0)
            drawer.penup()
            for location, char_name in self.labelled_cells:
                if location_of_interest is None or location_of_interest == location:
                    centre_x, centre_y = self.cell_centre(location)
                    drawer.goto(centre_x, centre_y - self.cell_size * 0.2)
                    icon = Item.ITEM_TYPES.get(char_name, 'box')
                    drawer.write(icon, align="center", font=("Arial", int(self.cell_size * 0.5), "normal"))
    
    def draw_grid(self):
        """Draw the grid, walls, items, and labels."""
        drawer = Turtle()
        drawer.hideturtle()
        drawer.speed(0)
        drawer.penup()
        
        # Draw grid lines
        drawer.color("gray")
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
            drawer.write(str(x), align="center", font=("Arial", 12, "normal"))
        
        # Y-axis labels (left)
        for y in range(self.grid_height):
            drawer.goto(-30, y * self.cell_size + self.cell_size / 2 - 6)
            drawer.write(str(y), align="center", font=("Arial", 12, "normal"))
        
        # Draw blocked cells
        drawer.color(FILL_COLOUR)
        drawer.fillcolor(FILL_COLOUR)
        for cell_x, cell_y in self.blocked_cells:
            drawer.penup()
            drawer.goto(cell_x * self.cell_size, cell_y * self.cell_size)
            drawer.pendown()
            drawer.begin_fill()
            for _ in range(4):
                drawer.forward(self.cell_size)
                drawer.left(90)
            drawer.end_fill()
        
        # Draw fixed labelled cells.
        self.draw_fixed_icons()
        
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
                centre_x, centre_y = self.cell_centre(position)

                # Draw the first item (they're all the same type in a cell)
                item_list[0].draw(centre_x, centre_y, self.cell_size)
                
                # If multiple items, draw count
                self.write_item_count(item_list, centre_x, centre_y, drawer)
        
        self.screen.update()
        
        # Re-enable animation after initial grid drawing
        self.screen.tracer(1)
    
    
    def create_robot(self, position, heading: str = "north"):
        """Create and position the robot."""
        self.robot = RoboTurtle()
        self.robot.hideturtle()  # Hide initially to avoid showing movement to start position
        self.robot.speed(0)  # Need to race to the start point
        self.robot_position = tuple(position)
        self.robot_heading = heading
        
        # Position the robot at the center of the cell
        screen_x, screen_y = self.cell_centre(position)
        
        self.robot.penup()
        self.robot.goto(screen_x, screen_y)
        
        # Set heading
        heading_angles = {"north": 90, "east": 0, "south": 270, "west": 180}
        self.robot.setheading(heading_angles[heading])
        
        # Now show the turtle at the correct position
        self.robot.showturtle()
        self.robot.speed(3)   # Mid-range speed. User can change if they like.
        
        self.screen.update()
    
    def update_item_display(self, position, redraw_path_segment=True):
        """Update the display of items at a specific position without redrawing the world."""
        centre_x, centre_y = self.cell_centre(position)
        
        # Clear the area with a white rectangle
        worker = Turtle()
        worker.hideturtle()
        worker.speed(0)
        worker.penup()
        
        # Draw white rectangle to clear the cell
        rect_size = self.cell_size * 0.9
        worker.goto(centre_x - rect_size / 2, centre_y - rect_size / 2)
        worker.color("white")
        worker.fillcolor("white")
        worker.begin_fill()
        for _ in range(4):
            worker.forward(rect_size)
            worker.left(90)
        worker.end_fill()

        
        # Redraw the item if any remain
        if position in self.items and len(self.items[position]) > 0:
            item_list = self.items[position]
            item_list[0].draw(centre_x, centre_y, self.cell_size)
            
            # Draw count if multiple items
            self.write_item_count(item_list, centre_x, centre_y, worker)


    def write_item_count(self, item_list, centre_x, centre_y, turtle):
        if len(item_list) > 1:
            turtle.penup()
            turtle.goto(centre_x + self.cell_size * 0.22, 
                        centre_y + self.cell_size * 0.25)
            turtle.color("black")
            turtle.write(str(len(item_list)), 
                        align="left", 
                        font=("Arial", 10, "normal"))
        
     
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
    
    def check_final_state(self):
        """Check if the current world state satisfies the goal. Any errors
           must be appended to self.fail_messages.
           Override in subclasses.
        """
        self.fail_messages = []
        return 

    def fail_message(self) -> str:
        """Return the empty string if the goal is satisfies or an explanatory string otherwise.
        """
        self.check_final_state()
        return '\n'.join(self.fail_messages)

""" The TargetWorld class - a class in which the only goal is for RoboTurtle
    to finish at a specified target position.
"""
class TargetWorld(World):
    """A world where the goal is to reach a specific target position."""

    @classmethod
    def __init_subclass__(cls, **kwargs):
        """Need to register our subclasses, so pass the subclass registration up to our parent."""
        super().__init_subclass__(**kwargs)
    
    def __init__(self, grid_size, world_params):
        super().__init__(grid_size, world_params)
        if 'target' not in world_params:
            raise ValueError("TargetWorld requires 'target' in world_params")
        self.target = tuple(world_params['target'])
        target_icon = world_params.get('target_icon', 'flag')
        self.labelled_cells.append((self.target, target_icon))
    
    def at_goal(self):
        return self.robot_position == self.target
    
    def check_final_state(self):
        """Check if the robot has reached the target position. If not,
           set self.fail_messages to an explanatory comment.
        """
        super().check_final_state()
        if self.robot_position != self.target:
            self.fail_messages.append(f"Robot did not reach the target. "
                f"Expected position: {self.target}, "
                f"Actual position: {self.robot_position}")
        return None
    
    def update_item_display(self, position, redraw_path_segment=True):
        """Extend parent to redraw the chequered flag if necessary"""
        super().update_item_display(position, redraw_path_segment)
        self.draw_fixed_icons(position)

"""A subclass of TargetWorld in which all items in the
    grid except at those explicitly excluded cells are meant to have been
    collected and (optionally)
    put down again at a specified location. If there is a specified
    location for dumping items, it is automatically excluded from
    the search for items.
"""

class PickUpItemsWorld(TargetWorld):

    def __init__(self, grid_size, world_params):
        super().__init__(grid_size, world_params)
        exclude = world_params.get('exclude_cells', [])
        self.exclude = set(tuple(loc) for loc in exclude)
        self.item_dump = world_params.get('item_dump', None)
        if self.item_dump:
            dump_location = tuple(self.item_dump['location'])
            self.exclude.add(dump_location)
            self.labelled_cells.append((dump_location, "trash"))
        self.fail_messages = []

    def check_final_state(self):
        """Set self.fail_messages to a list of all faults in the final state
        """
        super().check_final_state()
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                if (x, y) not in self.exclude:
                    if self.items[(x, y)]:
                        self.fail_messages.append(f"Item(s) found at location ({x}, {y})")
        item_dump = self.world_params.get('item_dump', None)
        if item_dump:
            got = len(self.items[tuple(item_dump['location'])])
            expected = item_dump['num_items']
            if got != expected:
                self.fail_messages.append(f"Expected {expected} items at dump location but got {got}.")

        return None
    
""" The PathWorld class"""


class PathWorld(World):
    """A subclass of World in which the turtle is required to follow a specified
       path.
    """
    def __init__(self, grid_size, world_params):
        super().__init__(grid_size, world_params)
        path_segments = world_params['path']

        # Expand the list of path segments into a list of cell locations
        self.required_path = []
        for start, end in path_segments:
            x0, y0 = start
            x1, y1 = end
            if x0 != x1 and y0 != y1:
                raise RuntimeError("Path segments must be horizontal or vertical")
            if x0 == x1:  # Vertical
                dy = 1 if y0 <= y1 else -1
                y = y0
                for i in range(abs(y1 - y0) + 1):
                    self.add_path_cell((x0, y))
                    y += dy
                    i += 1
            else:  # Horizontal
                dx = 1 if x0 <= x1 else -1
                x = x0
                for i in range(abs(x1 - x0) + 1):
                    self.add_path_cell((x, y0))
                    x += dx
                    i += 1

    def at_goal(self):
        """True if robot is at the end of the required path, regardless of how 
           it got there.
        """
        return self.robot_position == self.required_path[-1]

    def add_path_cell(self, cell):
        """Add the given cell to the path unless it's already the last
           cell (to handle the case of a new segment starting where the
           last one finished).
        """
        if not (self.required_path and self.required_path[-1] == cell):
            self.required_path.append(cell)

    def check_final_state(self):
        """Set self.fail_messages to a list of all faults in the final state
        """
        super().check_final_state()
        if self.required_path != self.path:
            self.fail_messages.append("Roboturtle has not followed the required path")


# ============================================================================
# BotController - The command interface for students
# ============================================================================



class BotController:
    """Controller interface for commanding the robot."""
    
    def __init__(self, world: World):
        self.world = world
        self.redraw_last = False # True to redraw path over previous cell.
    
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

        # Check for walls (including perimeter)
        if self.world.is_wall_between(self.world.robot_position, new_pos):
            raise RuntimeError(f"Cannot move: wall blocks path from {self.world.robot_position} to {new_pos}")

        # Check for blocked cells
        if new_pos in self.world.blocked_cells:
            raise RuntimeError(f"Cannot move: cell {new_pos} is blocked")

        # Move the robot
        self.world.robot_position = new_pos
        screen_x, screen_y = self.world.cell_centre(new_pos)
        self.world.robot.color('blue')
        self.world.robot.pendown()
        self.world.robot.goto(screen_x, screen_y)
        self.world.robot.penup()
        self.world.path.append(new_pos)

        # Horrible hack to redraw the last 3 segments of the path in the event that
        # it got obliterated by a previous cell erasure operation from picking up items. 
        # It seems this can't be done while the live turtle is in the obliterated
        # cell.
        if self.redraw_last:
            worker = Turtle()
            previous_cells = self.world.path[-3:]
            worker.speed(0)
            worker.hideturtle()
            worker.color('blue')
            worker.penup()
            worker.goto(self.world.cell_centre(previous_cells[0]))
            worker.pendown()
            for cell in previous_cells[1:]:
                worker.goto(self.world.cell_centre(cell))
            self.redraw_last = False
    
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
        self.world.robot.add_item_to_inventory(item)
        
        # Update just the item display at this position
        self.world.update_item_display(pos)
        self.redraw_last = True
    
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
        self.redraw_last = True
    
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

        # Check for tossing outside the grid.
        x, y = front_pos
        if x < 0 or x >= _current_world.grid_width or y < 0 or y >= _current_world.grid_height:
            raise RuntimeError("Cannot toss: out of bounds")

        # Check for blocked cells
        if front_pos in self.world.blocked_cells:
            raise RuntimeError(f"Cannot toss: cell {front_pos} is blocked")

        # Remove item from inventory (least-recently-picked-up, which is first in list)
        item = self.world.robot.inventory.pop(0)

        # Add to front cell
        if front_pos not in self.world.items:
            self.world.items[front_pos] = []
        self.world.items[front_pos].append(item)

        # Update the display at the front position (but don't redraw the path segment)
        self.world.update_item_display(front_pos, False)
        self.redraw_last = True
    
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
        screen_pos = self.world.cell_centre(robot_pos)
        self.world.robot.goto(*screen_pos)
        self.world.robot.setheading(heading_angles[robot_heading])
        self.world.screen.update()
        self.world.screen.tracer(1)  # Re-enable animation

    def get_turtle(self):
        """Not-for-general-use method to get the underlying Turtle"""
        return self.world.robot
    
    # Query methods
    def at_goal(self) -> bool:
        """Check if the robot is at its target position,
           as defined by the relevant world subclass.
        """
        return self.world.at_goal()
    
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
        return pos in self.world.items and len(self.world.items[pos]) > 0
    
    def carries_object(self) -> bool:
        """Check if the robot is carrying any objects."""
        return self.world.robot.has_item()
    
    def is_facing_north(self) -> bool:
        """Check if the robot is facing north."""
        return self.world.robot_heading == "north"
    
    def print_state(self):
        """Print robot position and heading"""
        print(f"Robot is at {self.world.robot_position} heading {self.world.robot_heading}")

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
    for cell0, cell1 in data.get("blocked_cells", []):
        # Expand rectangular area into a list of blocked cells.
        x0, y0 = cell0
        x1, y1 = cell1
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                world.add_blocked_cell((x, y))
    # Create robot
    robot_start = data.get("robot_start", {"position": [0, 0], "heading": "north"})
    start_pos = robot_start["position"]
    world.create_robot(
        tuple(start_pos),
        robot_start.get("heading", "north")
    )
    world.path.append(tuple(start_pos))

    # Add items, either to world or Robot inventory.
    for item_data in data.get("items", []):
        item_type = item_data['type']
        position = item_data['position']
        count = item_data.get("count", 1)
        if str(position).lower() == 'inventory':
            for i in range(count):
                world.robot.add_item_to_inventory(Item(item_type))
        else:
            world.add_item_to_cell(
                Item(item_type),
                tuple(position),
                count
            )
    
    # Draw the world
    world.draw_grid()

    
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
