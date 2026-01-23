# ============================================================================
# RoboTurtle - The visual representation of the robot
# ============================================================================

from turtle import Turtle  #omitfrombuild

class RoboTurtle(Turtle):
    """A turtle subclass representing the robot with inventory."""
    
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