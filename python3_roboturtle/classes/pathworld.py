""" The PathWorld class"""

from world import World #omitfrombuild

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
