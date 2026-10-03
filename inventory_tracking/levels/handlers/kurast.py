"""Kurast Bazaar and Upper Kurast: the gates, both temples, both sewer entrances and the waypoint.

Unconfirmed (from D2MOO DrlgOutPlace/DrlgOutJung and d2data, 2026-10-01; no evidence yet). Each
level has a gate in its north border (the level ahead) and one in its south border (the way
back), 'Burbs Waypoint', two sewer entrances into Sewers 1 (DS1 files 0 and 1) and two temples.
A temple preset is spawned once with file 0 and once with file 1; the files are named after the
level's vis slots (BurbsTemple2/3.ds1, MetroTemple2/3.ds1; levels.json Vis2/Vis3), so file 0
leads to Vis2 and file 1 to Vis3. Kurast Causeway (82) is one 48x16 'Bridge' preset covering
the whole level, so it has no handler.
"""

from inventory_tracking.levels.handler import Handler, PoiSpec, waypoint


def kurast(name, area, family, temple, ahead, temples, back):
    return Handler(
        name,
        frozenset({area}),
        (
            PoiSpec(ahead, rf'{family} Gate N', 'stairs'),
            PoiSpec(temples[0], temple, variants=(0,), warp=True),
            PoiSpec(temples[1], temple, variants=(1,), warp=True),
            PoiSpec('Sewers', rf'{family} Sewer', 'stairs', each=True),
            waypoint('Act 3 - Burbs'),
            PoiSpec(back, rf'{family} Gate S', 'previous'),
        ),
    )


HANDLERS = [
    kurast(
        'Kurast Bazaar',
        80,
        'Act 3 - Burbs',
        r'Act 3 - Burbs Temple',
        'Upper Kurast',
        ('Ruined Temple', 'Disused Fane'),
        'Lower Kurast',
    ),
    kurast(
        'Upper Kurast',
        81,
        'Act 3 - Metro',
        r'Act 3 - MetroTemple',
        'Kurast Causeway',
        ('Forgotten Reliquary', 'Forgotten Temple'),
        'Kurast Bazaar',
    ),
]
