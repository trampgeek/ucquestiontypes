# ============================================================================
# RoboTurtle - the student-facing, object-oriented robot.
# Each instance has its own turtle, position, heading, path and inventory.
# ============================================================================

from world import World  #omitfrombuild
from turtle import Turtle  #omitfrombuild

global _current_world  #omitfrombuild

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
