"""Generate the testcases.json files for the two-turtle questions (run from the project dir)."""
import json

def swap(n, bay):
    blocked = [[[0, 1], [bay - 1, 1]], [[bay + 1, 1], [n - 1, 1]]]
    return {
        "world_class": "TargetWorld",
        "world_params": {"targets": [{"robot": "Alice", "location": [n - 1, 0]},
                                     {"robot": "Bob", "location": [0, 0]}],
                         "target_icon": "house_outline", "target_labels": False},
        "grid_size": [n, 2],
        "robots": [{"name": "Alice", "position": [0, 0], "heading": "east", "colour": "blue"},
                   {"name": "Bob", "position": [n - 1, 0], "heading": "west", "colour": "red"}],
        "blocked_cells": blocked,
        "items": [],
    }

def toss(width, height, wall_x, items, bob_y=0, icon="box", carried=None, houses=False):
    """items: list of (type, x, count) along row 0 on alice's side. Bob starts at the
       right edge, (width-1, bob_y), with the dump directly above him.
       carried: list of (type, count) that alice holds at the start instead.
       houses: draw house outlines at the two robots' start cells.
    """
    n = width - 1
    item_specs = [{"type": t, "position": [x, 0], "count": c} for t, x, c in items]
    item_specs += [{"type": t, "position": "inventory", "count": c, "robot": 0} for t, c in (carried or [])]
    params = {"item_dumps": [{"location": [n, bob_y + 1], "icon": icon}]}
    if houses:
        params["labelled_cells"] = [[[0, 0], "house_outline"], [[n, bob_y], "house_outline"]]
    return {
        "world_class": "PickUpItemsWorld",
        "world_params": params,
        "grid_size": [width, height],
        "robots": [{"name": "Alice", "position": [0, 0], "heading": "east", "colour": "blue"},
                   {"name": "Bob", "position": [n, bob_y], "heading": "west", "colour": "red"}],
        "walls": [[[wall_x, 0], [wall_x, height]]],
        "items": item_specs,
    }

def toss_basic(width, wall_x, carried):
    """Two rows high. Alice (carrying `carried`, a list of (type, count)) starts at home (0,0);
       Bob's home is (n,0) with the trash can directly above it at (n,1), separated from him
       by a wall. A vertical wall at wall_x splits the corridor. Both must finish at home.
    """
    n = width - 1
    return {
        "world_class": "PickUpItemsWorld",
        "world_params": {
            "targets": [{"robot": "Alice", "location": [0, 0]}, {"robot": "Bob", "location": [n, 0]}],
            "target_icon": "house_outline",
            "target_labels": False,
            "item_dumps": [{"location": [n, 1], "icon": "trash"}],
        },
        "grid_size": [width, 2],
        "robots": [{"name": "Alice", "position": [0, 0], "heading": "east", "colour": "blue"},
                   {"name": "Bob", "position": [n, 0], "heading": "west", "colour": "red"}],
        "walls": [[[wall_x, 0], [wall_x, 1]], [[n, 1], [n + 1, 1]]],   # row 1 is blocked, so the vertical wall only needs row 0
        "blocked_cells": [[[0, 1], [n - 1, 1]]],  # Whole top row, except the trash can cell
        "items": [{"type": t, "position": "inventory", "count": c, "robot": 0} for t, c in carried],
    }

def fmt(x, indent=0, width=100):
    """JSON-format x, keeping anything that fits on one line (within width) on one line."""
    flat = json.dumps(x)
    if indent + len(flat) <= width or not isinstance(x, (dict, list)):
        return flat
    pad = " " * (indent + 2)
    if isinstance(x, dict):
        body = [f'{pad}{json.dumps(k)}: {fmt(v, indent + 2)}' for k, v in x.items()]
        return "{\n" + ",\n".join(body) + "\n" + " " * indent + "}"
    body = [pad + fmt(v, indent + 2) for v in x]
    return "[\n" + ",\n".join(body) + "\n" + " " * indent + "]"

def dump(name, tests):
    """Write questions/<name>/testcases.json: the complete template parameters, ready to
       paste into the question. Compact layout; params_expanded.json has the same data
       fully expanded.
    """
    with open(f"questions/{name}/testcases.json", "w") as f:
        f.write(fmt({"testcases": tests}) + "\n")
    with open(f"questions/{name}/params_expanded.json", "w") as f:
        json.dump({"testcases": tests}, f, indent=2)
        f.write("\n")

dump("swap", [swap(7, 3), swap(5, 1), swap(9, 6), swap(6, 4)])

dump("toss", [
    toss_basic(8, 4, [("star", 3)]),
    toss_basic(10, 6, [("key", 1), ("leaf", 3)]),
    toss_basic(7, 3, [("key", 3)]),
    toss_basic(9, 5, [("star", 2), ("leaf", 1)]),
])

dump("toss_hard", [
    toss(8, 5, 4, [("star", 1, 1), ("star", 2, 1), ("star", 3, 1)], bob_y=2),
    toss(10, 6, 6, [("key", 0, 1), ("leaf", 1, 2), ("leaf", 3, 1), ("leaf", 5, 1)], bob_y=3, icon="trash"),
    toss(7, 4, 3, [("key", 1, 1), ("key", 2, 2)], bob_y=1),
    toss(9, 6, 5, [("star", 2, 2), ("leaf", 3, 1), ("star", 4, 1)], bob_y=4),
])
