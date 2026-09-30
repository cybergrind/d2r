"""Discover level handlers (every module in levels/handlers/ exporting HANDLERS) and validate them.

Validation is offline, against the bundled preset table: no area has two handlers, every
area exists, every POI pattern matches at least one preset name, and every match stays
inside the declared family. The registry test runs it over all discovered handlers.
"""

import importlib
import pkgutil
from collections import defaultdict

from inventory_tracking.levels import handlers as handlers_package
from inventory_tracking.levels.handler import Handler
from inventory_tracking.levels.presets import LEVEL_NAMES, PRESET_NAMES


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
    problems.extend(f'area {a} has {len(n)} handlers: {", ".join(n)}' for a, n in sorted(by_area.items()) if len(n) > 1)
    return problems


HANDLERS = discover()
_BY_AREA = {area: handler for handler in HANDLERS for area in handler.areas}


def handler_for(area: int | None) -> Handler | None:
    return _BY_AREA.get(area) if area is not None else None
