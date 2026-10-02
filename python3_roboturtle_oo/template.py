"""
RoboTurtle - A Reeborg-like programming teaching tool built on Python turtle graphics.
"""

import sys
import json
import traceback

from typing import List, Dict, Any, Tuple

"""Dummy Turtle and Screen classes for when running headless.
   Needs to be a support file in the prototype.
"""

# ============================================================================
# Dummy Turtle class
# ============================================================================
class Turtle:
    def __init__(self, *args, **kwargs):
        self.pen_is_down = False
    def goto(*args, **kwargs): pass
    def forward(*args, **kwargs): pass
    def left(*args, **kwargs): pass
    def right(*args, **kwargs): pass
    def clearsceen(): pass
    def color(*args, **kwargs): pass
    def pencolor(*args, **kwargs): pass
    def fillcolor(*args, **kwargs): pass
    def begin_fill(*args, **kwargs): pass
    def end_fill(*args, **kwargs): pass
    def setheading(*args, **kwargs): pass 
    def circle(*args, **kwargs): pass
    def speed(*args, **kwargs): pass
    def heading(*args, **kwargs): pass
    def pendown(self, *args, **kwargs):
        self.pen_is_down = True
    def penup(self, *args, **kwargs):
        self.pen_is_down = False;
    def pensize(*args, **kwargs): pass
    def showturtle(*args, **kwargs): pass
    def hideturtle(*args, **kwargs): pass
    def tracer(*args, **kwargs): pass
    def write(*args, **kwargs): pass
    def shape(*args, **kwargs): pass
    def isdown(self, *args, **kwargs):
        return self.pen_is_down

# ============================================================================
# Dummy Screen class
# ============================================================================
class Screen:
    def setup(*args, **kwargs): pass
    def setworldcoordinates(*args, **kwargs): pass
    def title(*args, **kwargs): pass
    def tracer(*args, **kwargs): pass
    def update(*args, **kwargs): pass
    def clear(*args, **kwargs): pass

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
# TurtleSprite - The on-screen turtle (with inventory) used by each RoboTurtle
# ============================================================================


class TurtleSprite(Turtle):
    """A turtle subclass that carries an item inventory."""
    
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
OUTLINE_HOUSE = "house_outline"  # A target_icon / label name: a faint line-drawn house.
OUTLINE_COLOUR = "#c4c4c4"
HEADING_ANGLES = {"north": 90, "east": 0, "south": 270, "west": 180}
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
        self.robots = []        # The RoboTurtle instances created so far by the student's code.
        self.robot_specs = []   # Start specs (position, heading, colour, inventory), one per robot.
        self.speed_setting = 3  # Mid-range speed. User can change if they like.
        self.fail_messages = []  # A list of errors in the final state. Empty if goal satisfied.
        self.world_params = world_params
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
                    if char_name == OUTLINE_HOUSE:
                        self.draw_house_outline(drawer, centre_x, centre_y)
                        continue
                    drawer.goto(centre_x, centre_y - self.cell_size * 0.2)
                    icon = Item.ITEM_TYPES.get(char_name, 'box')
                    drawer.write(icon, align="center", font=("Arial", int(self.cell_size * 0.5), "normal"))
    
    def draw_house_outline(self, drawer, cx, cy):
        """Draw a faint grey outline of a house (roof, walls and door) centred on
           (cx, cy) - unobtrusive enough for a turtle to sit on top of it.
        """
        s = self.cell_size
        drawer.color(OUTLINE_COLOUR)
        drawer.pensize(2)
        # Walls and roof as one continuous outline, then the door.
        outline = [(-0.28, -0.30), (-0.28, 0.08), (-0.36, 0.08), (0, 0.38),
                   (0.36, 0.08), (0.28, 0.08), (0.28, -0.30), (-0.28, -0.30)]
        door = [(-0.07, -0.30), (-0.07, -0.08), (0.07, -0.08), (0.07, -0.30)]
        for points in (outline, door):
            drawer.penup()
            drawer.goto(cx + points[0][0] * s, cy + points[0][1] * s)
            drawer.pendown()
            for dx, dy in points[1:]:
                drawer.goto(cx + dx * s, cy + dy * s)
            drawer.penup()

    def draw_grid(self, restore_tracer=True):
        """Draw the grid, walls, items, and labels. Animation (tracer) is switched
           back on at the end unless restore_tracer is False, in which case the caller
           must do it - used by the loader so the robots are drawn before animation starts.
        """
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
        
        self.draw_robot_names()
        self.screen.update()

        # Re-enable animation after initial grid drawing
        if restore_tracer:
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


    def create_sprites(self):
        """Create and show a turtle for every robot spec, at its start cell, so
           the student can see the initial state. Called after the grid is drawn.
        """
        for spec in self.robot_specs:
            spec["robot"] = None  # Set to the RoboTurtle once the student creates it.
            spec["sprite"] = self.create_turtle(tuple(spec["position"]),
                                                spec.get("heading", "north"), spec["colour"])
            for item in spec.get("inventory", []):
                spec["sprite"].add_item_to_inventory(item)

    def claim_robot_spec(self, name):
        """Return the (unclaimed) spec of the robot with the given name, marking it
           as claimed by the RoboTurtle being constructed.
        """
        names = [spec["name"] for spec in self.robot_specs]
        if name is None:
            if len(names) != 1 or self.robot_specs[0]["named"]:
                raise RuntimeError("You must say which robot you want: "
                                   f"RoboTurtle(name) with name one of {names}")
            name = names[0]
        if name not in names:
            raise RuntimeError(f"There is no robot called {name!r} in this world. "
                               f"The robots are: {names}")
        spec = self.robot_specs[names.index(name)]
        if spec["robot"] is not None:
            raise RuntimeError(f"A RoboTurtle called {name!r} has already been created.")
        return spec

    def create_turtle(self, position, heading, colour):
        """Create and position a TurtleSprite and return it."""
        turtle = TurtleSprite()
        turtle.hideturtle()  # Hide initially to avoid showing movement to start position
        turtle.speed(0)  # Need to race to the start point
        turtle.color(colour)
        turtle.penup()
        turtle.goto(*self.cell_centre(position))
        turtle.setheading(HEADING_ANGLES[heading])
        turtle.showturtle()
        turtle.speed(self.speed_setting)
        self.screen.update()
        return turtle

    def draw_robot_names(self):
        """Label each robot's start cell with the robot's name, if there are several
           robots or the world explicitly names them.
        """
        if not self.names_shown():
            return
        drawer = Turtle()
        drawer.hideturtle()
        drawer.speed(0)
        drawer.penup()
        shared = self.labelled_target_cells()
        for spec in self.robot_specs:
            cell = tuple(spec["position"])
            x, y = self.cell_centre(cell)
            if cell in shared:
                # The cell also has a target label in its bottom right corner, so go bottom left.
                drawer.goto(x - self.cell_size * 0.5 + 3, y - self.cell_size * 0.40)
                align = "left"
            else:
                drawer.goto(x, y - self.cell_size * 0.40)
                align = "center"
            drawer.color(spec["colour"])
            drawer.write(spec["name"], align=align, font=("Arial", 10, "bold"))

    def labelled_target_cells(self):
        """The set of cells that get a target-name label. Overridden by TargetWorld."""
        return set()

    def names_shown(self):
        """True if robot (and target) name labels should be drawn."""
        return len(self.robot_specs) > 1 or any(spec["named"] for spec in self.robot_specs)

    def spec_for(self, name, index):
        """Return the robot spec with the given name or, if name is None, the index'th spec
           (used to infer which robot a per-robot goal belongs to from its order).
        """
        if name is None:
            if index >= len(self.robot_specs):
                raise ValueError(f"World has a goal for robot number {index + 1} but only "
                                 f"{len(self.robot_specs)} robot(s)")
            return self.robot_specs[index]
        for spec in self.robot_specs:
            if spec["name"] == name:
                return spec
        raise ValueError(f"World has a goal for unknown robot {name!r}")

    def set_speed(self, n):
        """Set the speed of all current and future robots."""
        self.speed_setting = n
        # Changing speed with animation on can make Skulpt drop a turtle from the
        # display, so do it with animation off and then switch animation back on.
        self.screen.tracer(0)
        for spec in self.robot_specs:
            if "sprite" in spec:
                spec["sprite"].speed(n)
        self.screen.update()
        self.screen.tracer(1)

    def other_robot_at(self, cell, me):
        """Return a robot other than 'me' at the given cell, or None."""
        for robot in self.robots:
            if robot is not me and robot.cell == cell:
                return robot
        return None

    def note_cell_erased(self):
        """Item display updates wipe path segments, so every robot must redraw its last few."""
        for robot in self.robots:
            robot.redraw_last = True

    def redraw_world(self):
        """Redraw grid and walls and then restore all the robots."""
        self.screen.tracer(0)  # Disable animation for redraw
        self.screen.clear()
        self.draw_grid()
        for spec in self.robot_specs:
            robot = spec["robot"]
            cell = robot.cell if robot else tuple(spec["position"])
            heading = robot.heading if robot else spec.get("heading", "north")
            spec["sprite"].showturtle()
            spec["sprite"].penup()
            spec["sprite"].goto(*self.cell_centre(cell))
            spec["sprite"].setheading(HEADING_ANGLES[heading])
        self.screen.update()
        self.screen.tracer(1)  # Re-enable animation

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
        missing = [spec["name"] for spec in self.robot_specs if spec["robot"] is None]
        if missing:
            self.fail_messages.append(f"Your code never created a RoboTurtle for: {missing}")
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
    
    target_required = True  # Subclasses may set False to make targets optional.

    def __init__(self, grid_size, world_params):
        super().__init__(grid_size, world_params)
        has_target = 'target' in world_params or 'targets' in world_params
        if not has_target and self.target_required:
            raise ValueError("TargetWorld requires 'target' in world_params")
        # 'targets' (one per robot, matched by index) is optional; 'target' is robot 0's.
        # 'targets' is a list with one entry per robot. Each is either a cell, [x, y]
        # (the robot is inferred from the entry's position in the list), or
        # {"robot": name, "location": [x, y]}. 'target' is a single target for robot 0.
        if 'targets' in world_params:
            raw_targets = world_params['targets']
        else:
            raw_targets = [world_params['target']] if has_target else []
        self.target_entries = []  # (robot name or None, cell) pairs
        for entry in raw_targets:
            if isinstance(entry, dict):
                self.target_entries.append((entry['robot'], tuple(entry['location'])))
            else:
                self.target_entries.append((None, tuple(entry)))
        self.target = self.target_entries[0][1] if self.target_entries else None
        self.label_targets = world_params.get('target_labels', True)  # Name each target's robot?
        target_icon = world_params.get('target_icon', 'flag')
        for _, cell in self.target_entries:
            self.labelled_cells.append((cell, target_icon))

    def labelled_target_cells(self):
        """Cells that get a "→name" label (when names are shown)."""
        if not self.label_targets:
            return set()
        return {cell for _, cell in self.target_entries}

    def draw_robot_names(self):
        """Extend parent to also label each target with the name of its robot."""
        super().draw_robot_names()
        if not self.names_shown() or not self.label_targets:
            return
        drawer = Turtle()
        drawer.hideturtle()
        drawer.speed(0)
        drawer.penup()
        for i, (name, cell) in enumerate(self.target_entries):
            spec = self.spec_for(name, i)
            x, y = self.cell_centre(cell)
            drawer.goto(x + self.cell_size * 0.5 - 3, y - self.cell_size * 0.40)  # Bottom right corner
            drawer.color(spec["colour"])
            drawer.write("→" + spec["name"], align="right", font=("Arial", 10, "bold"))
    
    def check_final_state(self):
        """Check if the robot has reached the target position. If not,
           set self.fail_messages to an explanatory comment.
        """
        super().check_final_state()
        for i, (name, target) in enumerate(self.target_entries):
            spec = self.spec_for(name, i)
            robot = spec["robot"]
            if robot is not None and robot.cell != target:
                who = f"Robot {spec['name']!r}" if len(self.robot_specs) > 1 else "Robot"
                self.fail_messages.append(f"{who} did not reach the target. "
                    f"Expected position: {target}, "
                    f"Actual position: {robot.cell}")
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

    target_required = False  # Targets are optional - the item dumps define the goal.

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
           ANY_TYPE) currently placed anywhere in the world or in the starting
           inventory of any robot.
        """
        in_world = [item for item_list in self.items.values() for item in item_list]
        carried = [item for spec in self.robot_specs for item in spec.get("inventory", [])]
        return sum(
            1
            for item in in_world + carried
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
        # 'paths' is a list of path specs, one per robot; 'path' is robot 0's only.
        # Each entry is either a list of segments (robot inferred from its position in
        # the list) or {"robot": name, "path": segments}.
        if 'paths' in world_params:
            path_specs = world_params['paths']
        elif 'path' in world_params:
            path_specs = [world_params['path']]
        else:
            raise ValueError("PathWorld requires 'path' (or 'paths') inside world_params")
        self.required_paths = []  # (robot name or None, cells) pairs
        for entry in path_specs:
            if isinstance(entry, dict):
                if 'robot' not in entry or 'path' not in entry:
                    raise ValueError("Each dict entry in 'paths' needs both 'robot' and 'path' keys")
                self.required_paths.append((entry['robot'], self.expand_path(entry['path'])))
            else:
                self.required_paths.append((None, self.expand_path(entry)))
        self.required_path = self.required_paths[0][1]

    def expand_path(self, path_segments):
        """Expand a list of [start, end] segments into a list of cell locations."""
        cells = []
        for start, end in path_segments:
            x0, y0 = start
            x1, y1 = end
            if x0 != x1 and y0 != y1:
                raise RuntimeError("Path segments must be horizontal or vertical")
            dx = (x1 > x0) - (x1 < x0)
            dy = (y1 > y0) - (y1 < y0)
            for i in range(abs(x1 - x0) + abs(y1 - y0) + 1):
                cell = (x0 + i * dx, y0 + i * dy)
                # Skip if a new segment starts where the last one finished.
                if not (cells and cells[-1] == cell):
                    cells.append(cell)
        return cells

    def check_final_state(self):
        """Set self.fail_messages to a list of all faults in the final state
        """
        super().check_final_state()
        for i, (name, required) in enumerate(self.required_paths):
            spec = self.spec_for(name, i)
            robot = spec["robot"]
            if robot is not None and robot.path != required:
                who = f"Robot {spec['name']!r}" if len(self.robot_specs) > 1 else "Roboturtle"
                self.fail_messages.append(f"{who} has not followed the required path")


# ============================================================================
# RoboTurtle - the student-facing, object-oriented robot.
# Each instance has its own turtle, position, heading, path and inventory.
# ============================================================================



HEADING_DELTAS = {"north": (0, 1), "east": (1, 0), "south": (0, -1), "west": (-1, 0)}
LEFT_OF = {"north": "west", "west": "south", "south": "east", "east": "north"}
RIGHT_OF = {"north": "east", "east": "south", "south": "west", "west": "north"}
HEADING_ANGLES = {"north": 90, "east": 0, "south": 270, "west": 180}


class RoboTurtle:
    """A robot in the current world. The world shows each robot, labelled with
       its name, at its starting position; RoboTurtle(name) takes control of
       the robot with that name. The name may be omitted only if the world
       has just one robot.
    """

    def __init__(self, name=None):
        world = _current_world
        if world is None:
            raise RuntimeError("No world loaded.")
        spec = world.claim_robot_spec(name)
        self.world = world
        self.name = spec["name"]
        self.cell = tuple(spec["position"])
        self.heading = spec.get("heading", "north")
        self.colour = spec["colour"]
        self.path = [self.cell]
        self.redraw_last = False  # True to redraw path over previous cell.
        self.turtle = spec["sprite"]
        spec["robot"] = self
        world.robots.append(self)

    # ---- geometry helpers (no state change) ----
    def _cell_ahead(self):
        dx, dy = HEADING_DELTAS[self.heading]
        return (self.cell[0] + dx, self.cell[1] + dy)

    def _cell_right(self):
        dx, dy = HEADING_DELTAS[RIGHT_OF[self.heading]]
        return (self.cell[0] + dx, self.cell[1] + dy)

    def _in_grid(self, cell):
        return 0 <= cell[0] < self.world.grid_width and 0 <= cell[1] < self.world.grid_height

    # ---- commands ----
    def move(self):
        """Move the robot forward one cell in its current direction."""
        new_pos = self._cell_ahead()
        if self.world.is_wall_between(self.cell, new_pos):
            raise RuntimeError(f"Cannot move: wall blocks path from {self.cell} to {new_pos}")
        if new_pos in self.world.blocked_cells:
            raise RuntimeError(f"Cannot move: cell {new_pos} is blocked")
        if self.world.other_robot_at(new_pos, self) is not None:
            raise RuntimeError(f"Cannot move: another robot is at {new_pos}")

        self.cell = new_pos
        screen_x, screen_y = self.world.cell_centre(new_pos)
        self.turtle.color(self.colour)
        self.turtle.pendown()
        self.turtle.goto(screen_x, screen_y)
        self.turtle.penup()
        self.path.append(new_pos)

        # Horrible hack to redraw the last 3 segments of the path in the event that
        # it got obliterated by a previous cell erasure operation from picking up items.
        # It seems this can't be done while the live turtle is in the obliterated
        # cell.
        if self.redraw_last:
            worker = Turtle()
            previous_cells = self.path[-3:]
            worker.speed(0)
            worker.hideturtle()
            worker.color(self.colour)
            worker.penup()
            worker.goto(self.world.cell_centre(previous_cells[0]))
            worker.pendown()
            for cell in previous_cells[1:]:
                worker.goto(self.world.cell_centre(cell))
            self.redraw_last = False

    def turn_left(self):
        """Turn the robot 90 degrees to the left."""
        self.heading = LEFT_OF[self.heading]
        self.turtle.left(90)

    def turn_right(self):
        """Turn the robot 90 degrees to the right."""
        self.heading = RIGHT_OF[self.heading]
        self.turtle.right(90)

    def take(self) -> str:
        """Pick up an item from the current cell. Returns the item's type name."""
        pos = self.cell
        if pos not in self.world.items or len(self.world.items[pos]) == 0:
            raise RuntimeError(f"Cannot take: no items at position {pos}")
        item = self.world.items[pos].pop(0)
        if len(self.world.items[pos]) == 0:
            del self.world.items[pos]
        self.turtle.add_item_to_inventory(item)
        self.world.update_item_display(pos)
        self.world.note_cell_erased()
        return item.item_type

    def put(self) -> str:
        """Place an item from inventory into the current cell. Returns the item's type name."""
        if not self.turtle.has_item():
            raise RuntimeError("Cannot put: robot has no items in inventory")
        item = self.turtle.inventory.pop(0)
        pos = self.cell
        if pos not in self.world.items:
            self.world.items[pos] = []
        self.world.items[pos].append(item)
        self.world.update_item_display(pos)
        self.world.note_cell_erased()
        return item.item_type

    def toss(self) -> str:
        """Toss an item from inventory into the cell directly in front of the robot.
           Returns the item's type name.
        """
        if not self.turtle.has_item():
            raise RuntimeError("Cannot toss: robot has no items in inventory")
        front_pos = self._cell_ahead()
        if not self._in_grid(front_pos):
            raise RuntimeError("Cannot toss: out of bounds")
        if front_pos in self.world.blocked_cells:
            raise RuntimeError(f"Cannot toss: cell {front_pos} is blocked")
        item = self.turtle.inventory.pop(0)
        if front_pos not in self.world.items:
            self.world.items[front_pos] = []
        self.world.items[front_pos].append(item)
        self.world.update_item_display(front_pos, False)
        self.world.note_cell_erased()
        return item.item_type

    def build_wall(self):
        """Build a wall in front of the robot."""
        x, y = self.cell
        if self.heading == "north":
            wall = ((x, y + 1), (x + 1, y + 1))
        elif self.heading == "east":
            wall = ((x + 1, y), (x + 1, y + 1))
        elif self.heading == "south":
            wall = ((x, y), (x + 1, y))
        else:  # west
            wall = ((x, y), (x, y + 1))
        self.world.wall_segments.add(wall)
        self.world.redraw_world()

    def speed(self, speed_factor: int):
        """Set this robot's speed from 1 (slow) to 10 (fast). 0 is superfast."""
        self.turtle.speed(speed_factor)

    def get_turtle(self):
        """Not-for-general-use method to get the underlying Turtle"""
        return self.turtle

    # ---- queries ----
    def at_goal(self) -> bool:
        """Check if the world's goal (as defined by the world subclass) is satisfied."""
        return self.world.at_goal()

    def front_is_clear(self) -> bool:
        """Check if the cell in front is clear (no wall, not blocked, no other robot)."""
        new_pos = self._cell_ahead()
        return not (self.world.is_wall_between(self.cell, new_pos)
                    or new_pos in self.world.blocked_cells
                    or self.world.other_robot_at(new_pos, self) is not None)

    def right_is_clear(self) -> bool:
        """Check if the cell to the right is clear."""
        right_pos = self._cell_right()
        return (self._in_grid(right_pos)
                and not self.world.is_wall_between(self.cell, right_pos)
                and right_pos not in self.world.blocked_cells)

    def wall_in_front(self) -> bool:
        """Check if there's a wall directly in front."""
        return self.world.is_wall_between(self.cell, self._cell_ahead())

    def wall_on_right(self) -> bool:
        """Check if there's a wall on the right side."""
        return self.world.is_wall_between(self.cell, self._cell_right())

    def object_here(self) -> bool:
        """Check if there's an object in the current cell."""
        return self.cell in self.world.items and len(self.world.items[self.cell]) > 0

    def carries_object(self) -> bool:
        """Check if the robot is carrying any objects."""
        return self.turtle.has_item()

    def inventory(self) -> list:
        """Return a list of the type names of items in the robot's inventory,
           ordered by when they were picked up, most recently picked up last.
        """
        return [item.item_type for item in self.turtle.inventory]

    def is_facing_north(self) -> bool:
        """Check if the robot is facing north."""
        return self.heading == "north"

    def position(self) -> tuple:
        """Return the robot's current grid coordinates as an (x, y) tuple."""
        return self.cell

    def target_cell(self):
        """Return the target cell's (x, y) tuple, or None if no target is defined."""
        return getattr(self.world, 'target', None)

    def facing(self) -> str:
        """Return the robot's heading as 'N', 'S', 'E', or 'W'."""
        return {'north': 'N', 'south': 'S', 'east': 'E', 'west': 'W'}[self.heading]

    def print_state(self):
        """Print robot position and heading"""
        print(f"RoboTurtle is at {self.cell} heading {self.heading}")

    def send_text(self, s: str):
        """Display the given text string in the world's text output area.
           The text is prefixed with this robot's name and a colon and space.
           Requires 'expected_texts' to have been set in this test's world_params.
        """
        if not isinstance(s, str):
            raise RuntimeError('"send_text" must take a string as a parameter. '
                                f'But I got {type(s).__name__}.')
        self.world.send_text(f"{self.name}: {s}")


# ============================================================================
# World Loading
# ============================================================================


class NoWorldLoaded:
    """Sentinel object that raises an error when any method is called."""
    
    def __getattr__(self, name):
        raise RuntimeError("No world loaded. Call roboturtle.load() first.")
    
    def __call__(self, *args, **kwargs):
        raise RuntimeError("No world loaded. Call roboturtle.load() first.")

# The world most recently loaded; RoboTurtle() instances are created in it.

_current_world = None


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
    global _current_world
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
    # Robot start specs. Robots themselves are created by the student's code,
    # one RoboTurtle(name) per spec. 'robot_start' (single robot) is still accepted.
    starts = data.get("robots", [data.get("robot_start", {"position": [0, 0], "heading": "north"})])
    default_colours = ['blue', 'red', 'green', 'orange', 'purple']
    for i, start in enumerate(starts):
        spec = dict(start)
        spec["named"] = "name" in spec  # Explicitly named in the world, so label it on screen.
        spec.setdefault("colour", default_colours[i % len(default_colours)])
        spec.setdefault("name", f"robot{i + 1}" if len(starts) > 1 else "robot")
        spec["inventory"] = []
        world.robot_specs.append(spec)

    # Add items, either to world or a robot's starting inventory.
    for item_data in data.get("items", []):
        item_type = item_data['type']
        position = item_data['position']
        count = item_data.get("count", 1)
        if str(position).lower() == 'inventory':
            robot_index = item_data.get("robot", 0)
            for i in range(count):
                world.robot_specs[robot_index]["inventory"].append(Item(item_type))
        else:
            world.add_item_to_cell(
                Item(item_type),
                tuple(position),
                count
            )

    # Let the world snapshot/derive anything it needs now that it's fully populated.
    world.on_world_loaded()

    # Draw the world, then show the robots at their start positions.
    world.create_sprites()
    world.draw_grid(restore_tracer=False)
    world.screen.update()
    world.screen.tracer(1)

    
    # Set as current world and create controller
    _current_world = world
    
    return world

# ============================================================================
# Global functions. The OO version has only speed(); everything else is a
# method of RoboTurtle.
# ============================================================================


def speed(speed_factor: int):
    """Set the speed of all robots from 1 (slow) to 10 (fast). 0 is superfast."""
    _current_world.set_speed(speed_factor)




# ============================================================================
# Checker Function
# ============================================================================


def run_tests(testcases: List[Dict[str, Any]], student_code: str, disabled_functions: List) -> str:
    """
    Run student code against all test cases.
    
    Args:
        testcases: List of test case specifications
        student_code: The student's Python code as a string
        disabled_functions: functions to be removed from the namespace for this question
    
    Returns:
        An error message string - empty if no errors.
    """
    for i, testcase in enumerate(testcases):
        try:
            # Load the world for this test case
            load_world(testcase)
            
            # Create a namespace with the RoboTurtle class
            namespace = {
                'RoboTurtle': RoboTurtle,
                'speed': speed,
                'print': lambda *args, **kwargs: None,
            }

            for func in disabled_functions:
                del namespace[func];
            
            # Execute the student's code
            try:
                exec(student_code, namespace)
                # Check if goal is satisfied (fail message will be empty)
                errors = _current_world.fail_message().strip()
            except SyntaxError as e:
                errors = f"Syntax error in your code at line {e.lineno}: {e.msg}"
            except Exception as e:
                # Extract line number from traceback
                tb = traceback.extract_tb(sys.exc_info()[2])
                # Find the last frame that's in the student's code (not in this module)
                student_frame = None
                for frame in tb:
                    if frame.filename == "<string>":
                        student_frame = frame

                error_type = type(e).__name__
                error_msg = str(e)
                if student_frame:
                    errors = f"{error_type} at line {student_frame.lineno}: {error_msg}"
                else:
                    errors = f"{error_type}: {error_msg}"

            if errors:
                return f"Test {i+1} failed as follows:\n{errors}"
        
        except Exception as e:
            return f"Test setup error: {str(e)}"
    
    # All tests passed
    return ''

def count_python_lines(code):
    """Support function to return (roughly) the count of lines of code"""
    lines = code.split('\n')
    count = 0
    
    for line in lines:
        trimmed = line.strip()
        if trimmed == '' or trimmed.startswith('#'):
            continue
        
        # Skip lines containing triple quotes (docstrings)
        if '"""' in trimmed or "'''" in trimmed:
            continue

        count += 1
    
    return count


__student_code = """{{ STUDENT_ANSWER | e('py') }}"""
__testcases = json.loads("""{{testcases | json_encode}}""")
__maxlines = int("""{{maxnumlines |default('0') | e('py')}}""")
__disabled_functions__ = json.loads("""{{disabledfunctions | default([]) | json_encode}}""")
line_count = count_python_lines(__student_code)
if __maxlines > 0 and line_count > __maxlines:
    result = {'fraction': 0, 'prologuehtml': f"Sorry - at most {__maxlines} lines of code are allowed. You have {line_count}"}
else:
    output = run_tests(__testcases, __student_code, __disabled_functions__)
    if output.strip() == '':
        result = {'fraction': 1, 'prologuehtml': f"<h3>All tests passed - well done! 😊</h3>"}
    else:
        errors = output.replace('\n', '<br>')
        result = {'fraction': 0, 'prologuehtml': f"<h3>Oops, looks like that didn't work.</h3><p>{errors}</p>"}

print(json.dumps(result))
