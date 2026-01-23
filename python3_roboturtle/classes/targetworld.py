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
    
    def __init__(self, grid_size, world_params):
        super().__init__(grid_size, world_params)
        if 'target' not in world_params:
            raise ValueError("TargetWorld requires 'target' in world_params")
        self.target = tuple(world_params['target'])
        target_icon = world_params.get('target_icon', 'flag')
        self.labelled_cells.append((self.target, target_icon))
    
    def at_goal(self):
        return self.robot_position == self.target
    
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