# ============================================================================
# World Loading
# ============================================================================

from world import World  #omitfrombuild
from item import Item  #omitfrombuild
from botcontroller import BotController  #omitfrombuild
import json  #omitfrombuild

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