"""Replay real level fixtures (tests/inventory_tracking/fixtures/levels/) as snapshots."""

import json
from pathlib import Path

from inventory_tracking.levels.model import LevelSnapshot, Location, Room


FIXTURES = Path(__file__).parents[1] / 'fixtures' / 'levels'


def replay(name) -> LevelSnapshot:
    data = json.loads((FIXTURES / f'{name}.json').read_text())
    location = Location(data['area_id'], 0, data['player']['x'], data['player']['y'])
    return LevelSnapshot(location, tuple(Room.from_row(room) for room in data['rooms']))
