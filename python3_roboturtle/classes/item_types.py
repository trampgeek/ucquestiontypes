# ============================================================================
# Item type registry - the single source of truth for item type names and
# their emoji symbols. Kept separate from item.py (and dependency-free, no
# turtle import) so build tooling can load it directly, e.g. to keep
# editor.html's item pickers in sync without duplicating this list by hand.
# ============================================================================

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
    "banana": "🍌",
    "apple": "🍎",
}

DEFAULT_SYMBOL = "box"  # Name (not emoji) of the item type used as a fallback for unknown types.
