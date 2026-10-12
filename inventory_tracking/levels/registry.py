"""Discover level handlers (every module in levels/handlers/ exporting HANDLERS) and validate them.

Validation is offline, against the bundled preset table: no area has two handlers, every
area exists, every POI pattern matches at least one preset name, every match stays inside the
declared family, and a POI on an object has that object once in every layout of every preset it
matches (an `each` POI: in at least one layout). The registry test runs it over all discovered handlers.
"""

import importlib
import pkgutil
from collections import defaultdict

from inventory_tracking.levels import handlers as handlers_package
from inventory_tracking.levels.handler import Handler
from inventory_tracking.levels.presets import LEVEL_NAMES, PRESET_NAMES, object_spots, object_variants


def discover(package=handlers_package) -> tuple[Handler, ...]:
    found = []
    for module in sorted(pkgutil.iter_modules(package.__path__), key=lambda m: m.name):
        found.extend(importlib.import_module(f'{package.__name__}.{module.name}').HANDLERS)
    return tuple(found)


def validate(handlers) -> list[str]:
    problems = []
    by_area = defaultdict(list)
    for handler in handlers:
        for area in sorted(handler.areas):
            by_area[area].append(handler.name)
            if area not in LEVEL_NAMES:
                problems.append(f'{handler.name}: area {area} is not in the levels table')
        for spec in handler.pois:
            names = [name for name in PRESET_NAMES.values() if spec.matches(name)]
            if not names:
                problems.append(f'{handler.name}: {spec.label} pattern {spec.pattern!r} matches no preset')
            if spec.family is not None:
                problems.extend(
                    f'{handler.name}: {spec.label} matches {name!r} outside family {spec.family!r}'
                    for name in names
                    if not name.startswith(spec.family)
                )
            if spec.thing:
                problems.extend(f'{handler.name}: {spec.label} {problem}' for problem in unplaced(spec))
    problems.extend(f'area {a} has {len(n)} handlers: {", ".join(n)}' for a, n in sorted(by_area.items()) if len(n) > 1)
    return problems


def unplaced(spec) -> list[str]:
    """Where the object table has no single spot for a POI on an object."""
    layouts = [
        (name, variant, len(object_spots(preset, variant, spec.thing)))
        for preset, name in PRESET_NAMES.items()
        if spec.matches(name)
        for variant in range(max(object_variants(preset), 1))
        if not spec.variants or variant in spec.variants
    ]
    if spec.each:
        return [] if any(count for _, _, count in layouts) else [f'object {spec.thing} is in no matching layout']
    return [
        f'object {spec.thing} is {count} times in {name!r} layout {variant}'
        for name, variant, count in layouts
        if count != 1
    ]


HANDLERS = discover()
_BY_AREA = {area: handler for handler in HANDLERS for area in handler.areas}


def handler_for(area: int | None) -> Handler | None:
    return _BY_AREA.get(area) if area is not None else None
