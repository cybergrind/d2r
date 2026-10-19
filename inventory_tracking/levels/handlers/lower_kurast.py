"""Lower Kurast: the super chest camps, the gates and the waypoint.

A camp is 'Slums 16x16' variant 1 (fixture lower_kurast_camp); a level may have none. One mark per
`PlaceUniqueChest` spot, so the route opens them one by one (routes/lower-kurast-plan.md).
"""

from inventory_tracking.levels.handler import Handler, PoiSpec, waypoint
from inventory_tracking.levels.model import UNIQUE_CHEST


HANDLERS = [
    Handler(
        'Lower Kurast',
        frozenset({79}),
        (
            PoiSpec('Super chests', r'Act 3 - Slums 16x16', variants=(1,), each=True, thing=UNIQUE_CHEST),
            PoiSpec('Kurast Bazaar', r'Act 3 - Slums Gate N', 'stairs'),
            waypoint('Act 3 - Burbs'),
            PoiSpec('Flayer Jungle', r'Act 3 - Slums Gate S', 'previous'),
        ),
        confirmed=True,
    )
]
