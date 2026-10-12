"""Act 4 routes (levels/routes.md)."""

from inventory_tracking.routes.model import Route, enter, fight, leave, level, loot, use


ROUTES = [
    Route(
        'Izual',
        (103,),
        (level(104, enter('Plains of Despair', 105)), level(105, fight('Izual', 'Izual'), loot(), leave())),
    ),
    Route(
        'Diablo',
        (106, 107),
        (
            level(106, enter('River of Flame', 107)),
            level(107, enter('Chaos Sanctum', 108)),
            level(
                108,
                # user, 2026-10-12: west, north, east, then the star. A seal boss appears with its arm's last seal.
                use('Vizier seal 1'),
                use('Vizier seal 2'),
                fight('Grand Vizier of Chaos'),
                use('De Seis seal'),
                fight('Lord De Seis'),
                use('Infector seal 1'),
                use('Infector seal 2'),
                fight('Infector of Souls'),
                fight('Diablo', 'Diablo'),
                loot(),
                leave(),
            ),
        ),
    ),
]
