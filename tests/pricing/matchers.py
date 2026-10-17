"""dirty-equals matchers keep the object they were last compared with (`_other`, for their repr after a failure). A
matcher that lives in module data, such as an item-bank case's expectations, so keeps a piece of every result it was
compared with for the rest of the run: 31,751 item-bank cases held one appraisal each, 1-2 MB a test, 17 GB in all."""

import dataclasses
from typing import Any

from dirty_equals import DirtyEquals


def forget_comparisons(value: Any) -> None:
    """Every matcher reachable from `value` (through containers, dataclasses and other matchers) back to how it was
    built, remembering no compared object."""
    stack, seen = [value], set()
    while stack:
        current = stack.pop()
        if id(current) in seen or isinstance(current, (str, bytes, int, float, type(None))):
            continue
        seen.add(id(current))
        if isinstance(current, DirtyEquals):
            current._other = None
            current._was_equal = None
            stack.extend(current._repr_args)
            stack.extend(current._repr_kwargs.values())
            stack.extend(getattr(current, '__dict__', {}).values())
        elif isinstance(current, dict):
            stack.extend(current.values())
        elif isinstance(current, (list, tuple, set, frozenset)):
            stack.extend(current)
        elif dataclasses.is_dataclass(current) and not isinstance(current, type):
            stack.extend(getattr(current, field.name) for field in dataclasses.fields(current))
