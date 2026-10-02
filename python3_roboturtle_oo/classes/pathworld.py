""" The PathWorld class"""

from world import World #omitfrombuild

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
