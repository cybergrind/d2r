"""Replay real level fixtures (tests/inventory_tracking/fixtures/levels/) as snapshots."""

import json
from pathlib import Path

from inventory_tracking.levels.handler import Handler
from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.registry import handler_for


FIXTURES = Path(__file__).parents[1] / 'fixtures' / 'levels'


def replay(name) -> LevelSnapshot:
    data = json.loads((FIXTURES / f'{name}.json').read_text())
    location = Location(data['area_id'], 0, data['player']['x'], data['player']['y'])
    return LevelSnapshot(location, tuple(Room.from_row(room) for room in data['rooms']))


def handler_of(area: int) -> Handler:
    """The registered handler of a level the test knows has one."""
    handler = handler_for(area)
    assert handler is not None, area
    return handler
