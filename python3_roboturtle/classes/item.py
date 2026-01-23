# ============================================================================
# Item Class
# ============================================================================

from turtle import Turtle #omitfrombuild

class Item:
    """Item that can be placed in the grid, displayed using UTF-8 characters."""

    # Map of item names to UTF-8 display characters
    ITEM_TYPES = {
        "star": "⭐",
        "key": "🔑",
        "leaf": "🍁",
        "house": "🏠",
        "home": "🏠",  # Synonym for house
        "flag": "🏁",
        "trash": "🗑",
        "box": "📦",
        "target": "🎯",
    }
    DEFAULT_SYMBOL = "📦"

    def __init__(self, item_type: str):
        self.item_type = item_type
        self.symbol = self.ITEM_TYPES.get(item_type, self.DEFAULT_SYMBOL)

    def draw(self, x: float, y: float, cell_size: float):
        """Draw the item using a UTF-8 character."""
        drawer = Turtle()
        drawer.hideturtle()
        drawer.speed(0)
        drawer.penup()
        drawer.goto(x, y - cell_size * 0.2)
        drawer.write(self.symbol, align="center", font=("Arial", int(cell_size * 0.45), "normal"))