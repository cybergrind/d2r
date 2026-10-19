"""River of Flame: the bridge's end into the Chaos Sanctum first, Hephasto at the Hellforge, the way back.

No warp joins River and Sanctum (levels.json Warp1 = -1): the mark is an open passage past the far
Bridge 2 (levels/exits.py `through`; runs/levels/evidence/107). It comes first (user, 2026-10-09:
repeated teleport steps must bring the character to the Chaos Sanctuary).
"""

import math
from dataclasses import dataclass, replace

from inventory_tracking.levels.handler import Handler, PoiSpec, instances
from inventory_tracking.levels.model import Guidance, LevelSnapshot, Poi, Room
from inventory_tracking.levels.presets import preset_name


CHAOS_SANCTUARY = 108
BRIDGE_START, BRIDGE = 'Act 4 - Bridge 1', 'Act 4 - Bridge 2'
BEYOND = 0.5  # tiles past the bridge's edge: on the Sanctum's side of the border


def centre(room: Room) -> tuple[float, float]:
    return room.x + room.width / 2, room.y + room.height / 2


def bridge_end(rooms) -> Poi | None:
    """Half a tile past the far edge of the Bridge 2 furthest from Bridge 1; None without both presets."""
    starts = [room for room, _ in instances(r for r in rooms if preset_name(r.preset) == BRIDGE_START)]
    spans = [room for room, _ in instances(r for r in rooms if preset_name(r.preset) == BRIDGE)]
    if len(starts) != 1 or not spans:
        return None
    start = centre(starts[0])
    far = max(spans, key=lambda room: math.dist(centre(room), start))
    dx, dy = centre(far)[0] - start[0], centre(far)[1] - start[1]
    x, y = centre(far)
    if abs(dx) >= abs(dy):
        x = far.x + far.width + BEYOND if dx > 0 else far.x - BEYOND
    else:
        y = far.y + far.height + BEYOND if dy > 0 else far.y - BEYOND
    return Poi('Chaos Sanctum', far, 'stairs', (x, y), CHAOS_SANCTUARY)


@dataclass(frozen=True)
class RiverOfFlame(Handler):
    def labels(self) -> frozenset[str]:
        return super().labels() | {'Chaos Sanctum'}

    def guide(self, snapshot: LevelSnapshot) -> Guidance:
        guidance = super().guide(snapshot)
        end = bridge_end(snapshot.rooms)
        if end is None:
            return replace(guidance, problems=(*guidance.problems, 'Chaos Sanctum: no bridge found'))
        return replace(guidance, pois=(end, *guidance.pois))


HANDLERS = [
    RiverOfFlame(
        'River of Flame',
        frozenset({107}),
        (
            PoiSpec('Hephasto', r'Act 4 - Lava Forge [WE]', 'target'),
            PoiSpec('City of the Damned', r'Act 4 - Lava Warp N', 'previous'),
        ),
    )
]
