# ============================================================================
# BotController - The command interface for students
# ============================================================================

from world import World   #omitfrombuild
from turtle import Turtle  #omitfrombuild

global _current_world  #omitfrombuild

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