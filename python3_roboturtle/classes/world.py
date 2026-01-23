"""
#============================================================================
# World - Manages the grid, walls, items, and rendering
# ============================================================================
"""
from collections import defaultdict

# dummy imports to let VS Code do type checking
from turtle import Turtle, Screen  #omitfrombuild
from roboturtle import RoboTurtle #omitfrombuild
from botcontroller import BotController  #omitfrombuild
from item import Item  #omitfrombuild

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