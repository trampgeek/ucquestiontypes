""" The TargetWorld class - a class in which the only goal is for RoboTurtle
    to finish at a specified target position.
"""
from turtle import Turtle  #omitfrombuild
from world import World  #omitfrombuild
from item import Item   #omitfrombuild
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