# ============================================================================
# World Loading
# ============================================================================

from world import World  #omitfrombuild
from item import Item  #omitfrombuild
import json  #omitfrombuild

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