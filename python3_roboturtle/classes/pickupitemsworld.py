"""A subclass of TargetWorld in which all items in the grid, except those at
    explicitly excluded cells or item-dump locations, are meant to have been
    collected and (optionally) redeposited at one or more dump locations.
"""
from targetworld import TargetWorld  #omitfrombuild

DEFAULT_DUMP_ICON = "trash"
ANY_TYPE = "Any"

class PickUpItemsWorld(TargetWorld):

    def __init__(self, grid_size, world_params):
        super().__init__(grid_size, world_params)
        exclude = world_params.get('exclude_cells', [])
        self.exclude = set(tuple(loc) for loc in exclude)

        dump_specs = world_params.get('item_dumps', None)
        if dump_specs is None:
            # Backward compatibility: map the old singular 'item_dump' format
            # ({'location': [...], 'num_items': N}) to a single-entry item_dumps list.
            legacy_dump = world_params.get('item_dump', None)
            dump_specs = [{
                'location': legacy_dump['location'],
                'type': ANY_TYPE,
                'icon': DEFAULT_DUMP_ICON,
                'count': legacy_dump.get('num_items', None),
            }] if legacy_dump is not None else []

        self.item_dumps = []
        for dump_spec in dump_specs:
            location = tuple(dump_spec['location'])
            dump = {
                'location': location,
                'type': dump_spec.get('type', ANY_TYPE),
                'icon': dump_spec.get('icon', DEFAULT_DUMP_ICON),
                'count': dump_spec.get('count', None),  # None => auto-derive in on_world_loaded()
            }
            self.item_dumps.append(dump)
            self.exclude.add(location)
            self.labelled_cells.append((location, dump['icon']))

        self.fail_messages = []

    def on_world_loaded(self):
        """Auto-derive the count for any dump that didn't specify one explicitly,
           from how many matching items exist anywhere in the world right now
           (called once, after items are placed, before the student's code runs).
        """
        super().on_world_loaded()
        for dump in self.item_dumps:
            if dump['count'] is None:
                dump['count'] = self._count_matching_items(dump['type'])

    def _count_matching_items(self, item_type):
        """Count all items of the given type (or all items, if item_type is
           ANY_TYPE) currently placed anywhere in the world.
        """
        return sum(
            1
            for item_list in self.items.values()
            for item in item_list
            if item_type == ANY_TYPE or item.item_type == item_type
        )

    def check_final_state(self):
        """Set self.fail_messages to a list of all faults in the final state.
        """
        super().check_final_state()

        for x in range(self.grid_width):
            for y in range(self.grid_height):
                if (x, y) not in self.exclude:
                    if self.items[(x, y)]:
                        self.fail_messages.append(f"Item(s) found at location ({x}, {y})")

        for dump in self.item_dumps:
            location = dump['location']
            expected_type = dump['type']
            expected_count = dump['count']
            actual_items = self.items[location]

            if expected_type != ANY_TYPE:
                wrong_types = [item.item_type for item in actual_items if item.item_type != expected_type]
                if wrong_types:
                    self.fail_messages.append(
                        f"Dump at {location} should contain only '{expected_type}' items "
                        f"but also found: {wrong_types}"
                    )

            got = len(actual_items)
            if got != expected_count:
                self.fail_messages.append(
                    f"Expected {expected_count} item(s) at dump location {location} but got {got}."
                )

        return None
