"""Arcane Sanctuary: the Summoner sits at the end of one of four arms.

Confirmed 2026-09-30 by two Win+C dumps (fixtures arcane_summoner_s / _w): the room was
preset 527 in one game and 525 in another; the Summoner was found in it in game.

The mark is where he stands, not the room's middle (user, 2026-10-11: the mark "is far too away to
damage him"). In that game (15:43, the arm at the north end, preset 527 'Summoner S' at tile
(5084, 1000) as in the fixture) the teleport step stopped at (25458.5, 5037.5), 11 from the room's
middle with no footing nearer, and he stood at (25440.7, 5020.9), 25 away with the blades reaching
22: at (20.7, 20.9) units from the preset's origin. The layout file (Act2/Arcane/SummS.ds1, read from
the install that day) has its one monster at (20, 20); the other three files have theirs at the
places below; E was seen in game too ((20.5, 35.5), 15:57 that day). UNCONFIRMED in game: W and N.

The mark is a stand beside him, not his spot (user, 2026-10-11: "for all boss farms ... teleport not in
boss and his group, but slightly offset the point"). In the four takes of that day (three of S, one
of E) he stands in the south-east corner of a platform of 20 x 20 units, the same in both files;
two ramps lead from that corner down to a landing 16 south and 10 east of him, and a pack stood in
the hall below it in two takes. From the landing he is 18 away with a clear line, and of that pack
16 of 18 and 10 of 16 were in reach with one, none and 4 nearer than 10 units. The mark is the tile
there, `STAND` from his spot: its own middle is a unit short of footing, and the hop lands on the
footing beside it. W and N take the same offset by the files' likeness, unseen.
"""

from inventory_tracking.levels.handler import target


SUMMONER_AT = {
    'Act 2 - Arcane Summoner W': (35, 20),
    'Act 2 - Arcane Summoner E': (20, 35),
    'Act 2 - Arcane Summoner S': (20, 20),
    'Act 2 - Arcane Summoner N': (20, 30),
}

STAND = (10, 15)  # world units from his spot to the mark

HANDLERS = [
    target(
        'Arcane Sanctuary',
        areas={74},
        label='Summoner',
        preset=r'Act 2 - Arcane Summoner [NSEW]',
        at_in={name: (x + STAND[0], y + STAND[1]) for name, (x, y) in SUMMONER_AT.items()},
        confirmed=True,
    )
]
