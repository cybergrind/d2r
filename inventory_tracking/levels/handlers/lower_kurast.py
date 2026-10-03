"""Lower Kurast: the super chest camps.

Lower Kurast's super chests don't sparkle; they sit in two shacks by a bonfire (user,
2026-09-30). Confirmed with Win+C dump 20260930T124726Z-e166c530 (fixture lower_kurast_camp),
taken inside one shack: the camp is 'Act 3 - Slums 16x16' DS1 variant 1 (Slums16x16_1.ds1),
with the fire, jungle torches and a jungle chest in each shack. Every variant-1 instance is
marked; a level may have none. The other Slums presets and variants seen had no fire.

Exits (2026-10-01): D2MOO DRLGOUTJUNG_BuildLowerKurast puts 'Slums Gate N' in the north border
(toward Kurast Bazaar) and 'Slums Gate S' (16x8) in the south border (toward the Flayer Jungle);
the waypoint is 'Burbs Waypoint' in every Kurast level. Both fixtures hold one of each.
"""

from inventory_tracking.levels.handler import Handler, PoiSpec, waypoint


HANDLERS = [
    Handler(
        'Lower Kurast',
        frozenset({79}),
        (
            PoiSpec('Super chests', r'Act 3 - Slums 16x16', variants=(1,), each=True),
            PoiSpec('Kurast Bazaar', r'Act 3 - Slums Gate N', 'stairs'),
            waypoint('Act 3 - Burbs'),
            PoiSpec('Flayer Jungle', r'Act 3 - Slums Gate S', 'previous'),
        ),
        confirmed=True,
    )
]
