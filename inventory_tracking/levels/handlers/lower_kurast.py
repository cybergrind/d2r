"""Lower Kurast: the super chest camps.

Lower Kurast's super chests don't sparkle; they sit in two shacks by a bonfire (user,
2026-09-30). Confirmed with Win+C dump 20260930T124726Z-e166c530 (fixture lower_kurast_camp),
taken inside one shack: the camp is 'Act 3 - Slums 16x16' DS1 variant 1 (Slums16x16_1.ds1),
with the fire, jungle torches and a jungle chest in each shack. Every variant-1 instance is
marked; a level may have none. The other Slums presets and variants seen had no fire.
"""

from inventory_tracking.levels.handler import Handler, PoiSpec


HANDLERS = [
    Handler(
        'Lower Kurast',
        frozenset({79}),
        (PoiSpec('Super chests', r'Act 3 - Slums 16x16', variants=(1,), each=True),),
        confirmed=True,
    )
]
