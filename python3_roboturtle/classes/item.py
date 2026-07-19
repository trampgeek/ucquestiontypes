# ============================================================================
# Item Class
# ============================================================================

from turtle import Turtle #omitfrombuild
from item_types import ITEM_TYPES, DEFAULT_SYMBOL #omitfrombuild

class Item:
    """Item that can be placed in the grid, displayed using UTF-8 characters."""

    ITEM_TYPES = ITEM_TYPES  # See classes/item_types.py for the actual registry.

    def __init__(self, item_type: str):
        self.item_type = item_type
        self.symbol = self.ITEM_TYPES.get(item_type, self.ITEM_TYPES[DEFAULT_SYMBOL])

    def draw(self, x: float, y: float, cell_size: float):
        """Draw the item using a UTF-8 character."""
        drawer = Turtle()
        drawer.hideturtle()
        drawer.speed(0)
        drawer.penup()
        drawer.goto(x, y - cell_size * 0.2)
        drawer.write(self.symbol, align="center", font=("Arial", int(cell_size * 0.45), "normal"))