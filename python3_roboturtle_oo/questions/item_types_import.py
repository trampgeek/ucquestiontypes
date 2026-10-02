import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "classes"))
from item_types import ITEM_TYPES
ITEM_NAMES = list(ITEM_TYPES)
