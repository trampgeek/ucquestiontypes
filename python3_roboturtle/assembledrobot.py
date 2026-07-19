"""
The assembled RoboTurtle and all its support classes, ready
for inclusion in both the CodeRunner question template and the
prototypeextra.html file that needs to execute the same code
using Skulpt.
"""

# ============================================================================
# Item type registry - the single source of truth for item type names and
# their emoji symbols. Kept separate from item.py (and dependency-free, no
# turtle import) so build tooling can load it directly, e.g. to keep
# editor.html's item pickers in sync without duplicating this list by hand.
# ============================================================================

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
    "banana": "🍌",
    "apple": "🍎",
}

DEFAULT_SYMBOL = "box"  # Name (not emoji) of the item type used as a fallback for unknown types.


# ============================================================================
# Item Class
# ============================================================================


class Item:
    """Item that can be placed in the grid, displayed using UTF-8 characters."""

    ITEM_TYPES = ITEM_TYPES  # See classes/item_types.py for the actual registry.

    def __init__(self, item_type: str):
        self.item_type = item_type
        self.symbol = self.ITEM_TYPES.get(item_type, self.ITEM_TYPES[DEFAULT_SYMBOL])

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
TEXT_BAR_HEIGHT = 40           # Height, in pixels, of the optional text output bar.
TEXT_LABEL_WIDTH = 70          # Width of the shaded "Text:" label cell.
TEXT_LABEL_COLOUR = "#c9d6e3"

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

        # Optional text output area (send_text()), available to any World subclass.
        # Enabled by the mere presence of 'expected_texts' in world_params (may be an
        # empty list, e.g. to assert that no text should be sent).
        self.text_output_enabled = 'expected_texts' in world_params
        self.expected_texts = world_params.get('expected_texts', [])
        self.sent_texts = []    # All texts sent, in order - checked against expected_texts.
        self.current_text = ''  # Most recently sent text - the only one displayed.

        # Set up the screen
        self.screen = Screen()
        #self.screen.title("RoboTurtle World")  # THIS CLOBBERS THE WINDOW/TAB TITLE!
        
        # Calculate screen size with margins for labels
        margin = 60
        self.margin = margin
        extra = self.extra_bottom_height()
        screen_width = self.grid_width * self.cell_size + 2 * margin
        screen_height = self.grid_height * self.cell_size + 2 * margin + extra
        self.screen.setup(width=int(screen_width * 0.7), height=int(screen_height * 0.7))
        self.screen.setworldcoordinates(-margin, -margin - extra,
                                       self.grid_width * self.cell_size + margin,
                                       self.grid_height * self.cell_size + margin)
        self.screen.tracer(0)  # Disable auto-update for faster drawing

        # Add perimeter walls around the entire grid
        self._add_perimeter_walls()

    def at_goal(self):
        """True if the goal, as defined by check_final_state(), is currently
           satisfied. Subclasses define the goal by overriding
           check_final_state() (extending, not replacing, the base
           implementation) rather than by overriding at_goal() itself.
        """
        self.check_final_state()
        is_at_goal = not self.fail_messages
        self.fail_messages = []
        return is_at_goal

    def extra_bottom_height(self):
        """Extra vertical space (in world-coordinate/pixel units) reserved below
           the grid's own margin, for the optional text output bar. Called during
           __init__, before the screen/world-coordinates are set up.
        """
        return TEXT_BAR_HEIGHT if self.text_output_enabled else 0


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

    def on_world_loaded(self):
        """Hook called once by worldloader.load_world(), after walls, the robot,
           and all items have been placed but before the world is first drawn
           and before any student code runs. Default no-op; overridden by
           PickUpItemsWorld to snapshot initial item counts for auto-derived
           dump counts.
        """
        pass

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

        if self.text_output_enabled:
            self.draw_text_bar()


    def draw_text_bar(self):
        """(Re)draw the text output bar below the grid, showing only the
           most recently sent text. No-op if text output isn't enabled.
        """
        if not self.text_output_enabled:
            return
        bar_top = -self.margin
        bar_bottom = bar_top - TEXT_BAR_HEIGHT
        bar_right = self.grid_width * self.cell_size

        drawer = Turtle()
        drawer.hideturtle()
        drawer.speed(0)

        # Clear the whole bar, then paint the shaded "Text:" label cell.
        self._fill_rect(drawer, 0, bar_bottom, bar_right, bar_top, "white")
        self._fill_rect(drawer, 0, bar_bottom, TEXT_LABEL_WIDTH, bar_top, TEXT_LABEL_COLOUR)

        drawer.penup()
        drawer.color("black")
        drawer.goto(TEXT_LABEL_WIDTH / 2, (bar_top + bar_bottom) / 2 - 7)
        drawer.write("Text:", align="center", font=("Arial", 14, "bold"))

        # Monospace font for the message itself, sized up slightly so its
        # smaller x-height still reads at roughly the same effective size
        # as the "Text:" label and the grid's axis labels.
        drawer.goto(TEXT_LABEL_WIDTH + 10, (bar_top + bar_bottom) / 2 - 7)
        drawer.write(self.current_text, align="left", font=("Courier New", 15, "normal"))

        self._stroke_rect(drawer, 0, bar_bottom, bar_right, bar_top, "gray")

        self.screen.update()

    def _stroke_rect(self, drawer, x0, y0, x1, y1, colour):
        """Draw an unfilled outline of the axis-aligned rectangle (x0,y0)-(x1,y1)."""
        drawer.penup()
        drawer.goto(x0, y0)
        drawer.color(colour)
        drawer.pendown()
        drawer.goto(x1, y0)
        drawer.goto(x1, y1)
        drawer.goto(x0, y1)
        drawer.goto(x0, y0)
        drawer.penup()

    def _fill_rect(self, drawer, x0, y0, x1, y1, colour):
        """Fill the axis-aligned rectangle (x0,y0)-(x1,y1) with the given colour."""
        drawer.penup()
        drawer.goto(x0, y0)
        drawer.color(colour)
        drawer.fillcolor(colour)
        drawer.pendown()
        drawer.begin_fill()
        drawer.goto(x1, y0)
        drawer.goto(x1, y1)
        drawer.goto(x0, y1)
        drawer.goto(x0, y0)
        drawer.end_fill()
        drawer.penup()

    def send_text(self, s: str):
        """Record a sent text message and update the display to show it.
           Only the most recent message is ever shown.
        """
        if not self.text_output_enabled:
            raise RuntimeError("send_text() requires 'expected_texts' to be set "
                                "in this test's world_params")
        if not isinstance(s, str):
            raise RuntimeError('"send_text" must take a string as a parameter. '
                                f'But I got {type(s).__name__}.')
        self.sent_texts.append(s)
        self.current_text = s
        self.draw_text_bar()


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
           Subclasses should extend (not replace) this, via super().check_final_state(),
           so the text-output check below still runs.
        """
        self.fail_messages = []
        if self.text_output_enabled and self.sent_texts != self.expected_texts:
            if len(self.expected_texts) == 1:
                if len(self.sent_texts) > 1:
                    self.fail_messages.append(
                        "I expected just a single text message to be sent, "
                        "but multiple were received."
                    )
                else:
                    actual = repr(self.sent_texts[0]) if self.sent_texts else "(none sent)"
                    self.fail_messages.append(
                        "Text message sent did not match that expected.\n"
                        f"Expected: {self.expected_texts[0]!r}\n"
                        f"Actual:   {actual}"
                    )
            else:
                self.fail_messages.append(
                    "Text messages sent did not match those expected.\n"
                    f"Expected: {self.expected_texts}\n"
                    f"Actual:   {self.sent_texts}"
                )
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

"""A subclass of TargetWorld in which all items in the grid, except those at
    explicitly excluded cells or item-dump locations, are meant to have been
    collected and (optionally) redeposited at one or more dump locations.
"""

DEFAULT_DUMP_ICON = "trash"
ANY_TYPE = "Any"

class PickUpItemsWorld(TargetWorld):

    def __init__(self, grid_size, world_params):
        super().__init__(grid_size, world_params)
        exclude = world_params.get('exclude_cells', [])
        self.exclude = set(tuple(loc) for loc in exclude)

        dump_specs = world_params.get('item_dumps', None)
        if dump_specs is None:
            # Backward compatibility: map the old singular 'item_dump' format
            # ({'location': [...], 'num_items': N}) to a single-entry item_dumps list.
            legacy_dump = world_params.get('item_dump', None)
            dump_specs = [{
                'location': legacy_dump['location'],
                'type': ANY_TYPE,
                'icon': DEFAULT_DUMP_ICON,
                'count': legacy_dump.get('num_items', None),
            }] if legacy_dump is not None else []

        self.item_dumps = []
        for dump_spec in dump_specs:
            location = tuple(dump_spec['location'])
            dump = {
                'location': location,
                'type': dump_spec.get('type', ANY_TYPE),
                'icon': dump_spec.get('icon', DEFAULT_DUMP_ICON),
                'count': dump_spec.get('count', None),  # None => auto-derive in on_world_loaded()
            }
            self.item_dumps.append(dump)
            self.exclude.add(location)
            self.labelled_cells.append((location, dump['icon']))

        self.fail_messages = []

    def on_world_loaded(self):
        """Auto-derive the count for any dump that didn't specify one explicitly,
           from how many matching items exist anywhere in the world right now
           (called once, after items are placed, before the student's code runs).
        """
        super().on_world_loaded()
        for dump in self.item_dumps:
            if dump['count'] is None:
                dump['count'] = self._count_matching_items(dump['type'])

    def _count_matching_items(self, item_type):
        """Count all items of the given type (or all items, if item_type is
           ANY_TYPE) currently placed anywhere in the world.
        """
        return sum(
            1
            for item_list in self.items.values()
            for item in item_list
            if item_type == ANY_TYPE or item.item_type == item_type
        )

    def check_final_state(self):
        """Set self.fail_messages to a list of all faults in the final state.
        """
        super().check_final_state()

        for x in range(self.grid_width):
            for y in range(self.grid_height):
                if (x, y) not in self.exclude:
                    if self.items[(x, y)]:
                        self.fail_messages.append(f"Item(s) found at location ({x}, {y})")

        for dump in self.item_dumps:
            location = dump['location']
            expected_type = dump['type']
            expected_count = dump['count']
            actual_items = self.items[location]

            if expected_type != ANY_TYPE:
                wrong_types = [item.item_type for item in actual_items if item.item_type != expected_type]
                if wrong_types:
                    self.fail_messages.append(
                        f"Dump at {location} should contain only '{expected_type}' items "
                        f"but also found: {wrong_types}"
                    )

            got = len(actual_items)
            if got != expected_count:
                self.fail_messages.append(
                    f"Expected {expected_count} item(s) at dump location {location} but got {got}."
                )

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
    
    def take(self) -> str:
        """Pick up an item from the current cell. Returns the item's type name."""
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

        return item.item_type
    
    def put(self) -> str:
        """Place an item from inventory into the current cell. Returns the item's type name."""
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

        return item.item_type

    def toss(self) -> str:
        """Toss an item from inventory into the cell directly in front of the robot.
           Returns the item's type name.
        """
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

        return item.item_type
    
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

    def inventory(self) -> list:
        """Return a list of the type names of items in the robot's inventory,
           ordered by when they were picked up, most recently picked up last.
        """
        return [item.item_type for item in self.world.robot.inventory]
    
    def is_facing_north(self) -> bool:
        """Check if the robot is facing north."""
        return self.world.robot_heading == "north"
    
    def position(self) -> tuple:
        """Return the robot's current grid coordinates as an (x, y) tuple."""
        return self.world.robot_position

    def target_cell(self):
        """Return the target cell's (x, y) tuple, or None if no target is defined."""
        return getattr(self.world, 'target', None)

    def facing(self) -> str:
        """Return the robot's heading as 'N', 'S', 'E', or 'W'."""
        return {'north': 'N', 'south': 'S', 'east': 'E', 'west': 'W'}[self.world.robot_heading]

    def print_state(self):
        """Print robot position and heading"""
        print(f"Robot is at {self.world.robot_position} heading {self.world.robot_heading}")

    def send_text(self, s: str):
        """Display the given text string in the world's text output area.
           Requires 'expected_texts' to have been set in this test's world_params.
        """
        self.world.send_text(s)

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

    # Let the world snapshot/derive anything it needs now that it's fully populated.
    world.on_world_loaded()

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


def take() -> str:
    """Pick up an item from the current cell. Returns the item's type name."""
    return _current_controller.take()


def put() -> str:
    """Place an item from inventory into the current cell. Returns the item's type name."""
    return _current_controller.put()


def toss() -> str:
    """Toss an item from inventory into the cell directly in front of the robot.
       Returns the item's type name.
    """
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


def inventory() -> list:
    """Return a list of the type names of items in the robot's inventory,
       ordered by when they were picked up, most recently picked up last.
    """
    return _current_controller.inventory()


def is_facing_north() -> bool:
    """Check if the robot is facing north."""
    return _current_controller.is_facing_north()


def speed(speed_factor: int):
    """Set the speed from 1 (slow) to 10 (fast). 0 is superfast."""
    _current_world.robot.speed(speed_factor)

def position() -> tuple:
    """Return the robot's current grid coordinates as an (x, y) tuple."""
    return _current_controller.position()


def target_cell():
    """Return the target cell's (x, y) tuple, or None if no target is defined."""
    return _current_controller.target_cell()


def facing() -> str:
    """Return the robot's current heading as 'N', 'S', 'E', or 'W'."""
    return _current_controller.facing()


def print_state():
    """Print where the robot is and its heading"""
    _current_controller.print_state()


def send_text(s: str):
    """Display the given text string in the world's text output area."""
    _current_controller.send_text(s)
