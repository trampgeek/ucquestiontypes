"""A subclass of TargetWorld in which all items in the
    grid except at those explicitly excluded cells are meant to have been
    collected and (optionally)
    put down again at a specified location. If there is a specified
    location for dumping items, it is automatically excluded from
    the search for items.
"""
from targetworld import TargetWorld  #omitfrombuild

class PickUpItemsWorld(TargetWorld):

    def __init__(self, grid_size, world_params):
        super().__init__(grid_size, world_params)
        exclude = world_params.get('exclude_cells', [])
        self.exclude = set(tuple(loc) for loc in exclude)
        self.item_dump = world_params.get('item_dump', None)
        if self.item_dump:
            dump_location = tuple(self.item_dump['location'])
            self.exclude.add(dump_location)
            self.labelled_cells.append((dump_location, "trash"))
        self.fail_messages = []

    def check_final_state(self):
        """Set self.fail_messages to a list of all faults in the final state
        """
        super().check_final_state()
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                if (x, y) not in self.exclude:
                    if self.items[(x, y)]:
                        self.fail_messages.append(f"Item(s) found at location ({x}, {y})")
        item_dump = self.world_params.get('item_dump', None)
        if item_dump:
            got = len(self.items[tuple(item_dump['location'])])
            expected = item_dump['num_items']
            if got != expected:
                self.fail_messages.append(f"Expected {expected} items at dump location but got {got}.")

        return None