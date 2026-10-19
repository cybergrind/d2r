"""Kurast Bazaar and Upper Kurast: the gates, both temples, both sewer entrances and the waypoint.

Temple file 0 leads to Vis2, file 1 to Vis3: the files are named after the slots (BurbsTemple2/3.ds1).
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
