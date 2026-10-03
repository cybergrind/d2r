"""Index rule identity selectors once; preserve source order and wildcard rules."""

from itertools import product


FIELDS = ('category', 'name', 'family')


def compile_index(rows, *, patterns=False):
    index = {}
    for position, row in enumerate(rows):
        if patterns and not row.get('pattern'):
            continue
        selectors = row | row['pattern'] if patterns else row
        key = tuple(str(selectors[field]).casefold() if field in selectors else None for field in FIELDS)
        index.setdefault(key, []).append((position, row))
    return index


def candidates(item, index):
    keys = product(*((None, str(item.get(field, '')).casefold()) for field in FIELDS))
    selected = [entry for key in keys for entry in index.get(key, ())]
    return [row for _, row in sorted(selected, key=lambda entry: entry[0])]
