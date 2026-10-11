"""The situations: a pack, what brings it back, and what a fight should achieve there.

Every monster is a monstats Id looked up in the table (table.py, revivers.json): no id is written
here. Places are units from the character's starting place, +x and +y along the world's axes; a
pack stands 8 to 19 units out (the player engages at 12 to 14 at the median, combat/policy.py), the
blades fly REACH = 22.1 units. Three settings, each a Hell area the table lists for its reviver:

- Catacombs Level 1: Dark Shaman and Dark Ones (a fallen has 1,406 points, a shaman 2,548: a blade
  takes 1,700, a cast's five on one monster 2,380 out and as much again on the way back);
- Tal Rasha's Tomb: Unraveler and Burning Dead (3,574 and 7,990 points);
- Flayer Jungle: Flayer Shaman and Flayers.

Life: the plain Hell scenarios have the area's own life. The `terror_` ones have the life of the
level a Terror Zone lifts the monsters to (`terror_life`: the game's config and monlvl). The
`tough_` ones have TOUGH times the plain life, which is ASSUMED: it stands for what the tables here
do not give (a Herald's life, a game of several players, blades that a resistant monster takes less
of than the fitted 1,700), and shows where today's aim stops ending the fight at all.

`within`, `raised` and `casts` are what is wanted of a fight; the reference fight of harness.py meets
each (test_scenarios.py), so none asks for more than the geometry allows.
"""

import json
from pathlib import Path

from inventory_tracking.combat.mechanics.tables import area_level, tables
from inventory_tracking.combat.policy import REACH

from .harness import Body, Raiser, Scenario, body, tougher, wall, walls
from .table import raised, reviver


def area_of(row: dict, name: str) -> int:
    return next(a['area'] for a in row['areas'] if a['name'] == name)


SHAMAN = reviver('fallenshaman4')
FALLEN = raised('FallenShaman')['fallen4']
CATACOMBS = area_of(SHAMAN, 'Catacombs Level 1')
UNRAVELER = reviver('unraveler3')
BURNING_DEAD = raised('GreaterMummy')['skeleton4']
TOMB = area_of(UNRAVELER, "Tal Rasha's Tomb")
FLAYER_SHAMAN = reviver('fetishshaman3')
FLAYER = raised('FetishShaman')['fetish3']
JUNGLE = area_of(FLAYER_SHAMAN, 'Flayer Jungle')


TERROR = Path(__file__).parents[4] / 'terror_zones' / 'data' / 'desecratedzones-game.json'
CHARACTER_LEVEL = 93  # ASSUMED: the level inventory_tracking/terror/plan.md notes for the character (2026-10-02)
TOUGH = 5.0  # ASSUMED life factor of the `tough_` scenarios


def terror_life(area: int, character: int = CHARACTER_LEVEL) -> float:
    """How many times the area's own life a terrorized monster has on Hell: the config's `boost_level`
    above the character within its bounds (desecratedzones, rotw hell defaults), by monlvl HP(H)."""
    rule = json.loads(TERROR.read_text())['desecrated_zones'][0]['game_difficulties']['rotw']['hell']['defaults']
    level = max(rule['bound_incl_min'], min(character + rule['boost_level'], rule['bound_incl_max']))
    points = tables()['monlvl']
    return int(points[str(level)]['HP(H)']) / int(points[str(area_level(area))]['HP(H)'])


def raiser(unit: int, row: dict, raises, *, close: bool = False) -> Raiser:
    """The reviver `unit` with its table row's range and rate; `close` for one that raises from beside the corpse."""
    return Raiser(unit, row['raise_close'] if close else row['raise_range'], row['raise_frames'], frozenset(raises))


def pack(txt: int, area: int, *places: tuple[float, float], first: int = 1, elite: bool = False) -> tuple[Body, ...]:
    return tuple(body(first + n, txt, at, area, elite=elite) for n, at in enumerate(places))


def units(bodies) -> list[int]:
    return [b.unit for b in bodies]


def fallen(*places, **options) -> tuple[Body, ...]:
    return pack(FALLEN, CATACOMBS, *places, **options)


def shaman(unit: int, at, **options) -> Body:
    return body(unit, SHAMAN['txt'], at, CATACOMBS, **options)


def catacombs(name: str, minions, shamans, *, others=(), raises=None, **wanted) -> Scenario:
    """Dark Shamans raising `minions` and each other (table.py: a shaman raises shamans too)."""
    raisers = tuple(
        raiser(s.unit, SHAMAN, (units(minions) if raises is None else raises) + [o.unit for o in shamans if o != s])
        for s in shamans
    )
    return Scenario(name, CATACOMBS, (*minions, *others, *shamans), raisers, **wanted)


ROW = ((9.0, 0.0), (12.0, 0.0), (15.0, 0.0), (18.0, 0.0))  # four monsters on one line: one cast takes them all
KNOT = ((9.0, -2.0), (11.0, 1.0), (13.0, -1.0), (10.0, 3.0))  # four in a loose knot

PAIR = catacombs(
    'two_shamans_cover_each_other',
    fallen((9.0, 0.0), (11.0, 1.0), (12.0, -1.0)),
    (shaman(8, (14.0, 7.0)), shaman(9, (14.0, -7.0))),
    within=4.0,
    raised=2,
    why='each shaman raises the other and the pack; no line from the start takes both',
)
UNRAVELER_ASIDE = Scenario(
    'unraveler_off_the_line_of_its_skeletons',
    TOMB,
    (*pack(BURNING_DEAD, TOMB, *ROW, (10.0, 2.5)), body(9, UNRAVELER['txt'], (-3.0, 18.0), TOMB)),
    (raiser(9, UNRAVELER, [1, 2, 3, 4, 5]),),
    within=5.0,
    raised=2,
    why='the Unraveler raises from 31 units; it stands in reach, off the line, with two casts of life',
)
CHAMPIONS = Scenario(
    'unique_unraveler_behind_a_champion_pack',
    TOMB,
    (*pack(BURNING_DEAD, TOMB, *ROW[:3], elite=True), body(9, UNRAVELER['txt'], (5.0, 17.0), TOMB, elite=True)),
    (raiser(9, UNRAVELER, [1, 2, 3]),),
    within=6.0,
    raised=2,
    why='an Unraveler raises champions: the elite weight is on both sides and cannot tell them apart',
)

SCENARIOS: tuple[Scenario, ...] = (
    catacombs(
        'shaman_behind_its_pack_in_line',
        fallen((8.0, 0.0), (11.0, 1.0), (14.0, -1.0), (12.0, 2.0)),
        (shaman(9, (19.0, 0.5)),),
        within=3.0,
        raised=2,
        why='the blades pass through the pack: the line through the minions takes the shaman behind them',
    ),
    catacombs(
        'shaman_in_the_open_off_the_line',
        fallen(*ROW, (10.0, 2.0)),
        (shaman(9, (4.0, 15.0)),),
        within=3.0,
        raised=2,
        why='the rich line is the row; the shaman stands 75 degrees off it, in reach, alone',
    ),
    Scenario(
        'shaman_behind_a_wall',
        CATACOMBS,
        (*fallen(*KNOT), shaman(9, (16.0, 12.0))),
        (raiser(9, SHAMAN, [1, 2, 3, 4]),),
        blocked=wall(10.0, 8.0, 14.0, 9.5),
        within=6.0,
        raised=4,
        why='a wall stands between the character and the shaman; a few steps aside there is a shot',
    ),
    Scenario(
        'shaman_in_a_closed_cell',
        CATACOMBS,
        (*fallen(*KNOT), shaman(9, (18.0, 12.0))),
        (raiser(9, SHAMAN, [1, 2, 3, 4]),),
        blocked=walls(
            wall(13.0, 7.0, 23.0, 8.5),
            wall(13.0, 15.5, 23.0, 17.0),
            wall(13.0, 7.0, 14.5, 17.0),
            wall(21.5, 7.0, 23.0, 17.0),
        ),
        raised=8,
        casts=12,
        why='the shaman is shut in (a closed door): no spot has a shot, so the pack cannot be killed for good',
    ),
    PAIR,
    catacombs(
        'two_shamans_on_one_line',
        fallen((9.0, 3.0), (11.0, -3.0)),
        (shaman(8, (12.0, 0.0)), shaman(9, (17.0, 0.0))),
        within=3.0,
        raised=2,
        why='the control for the pair: one cast takes both shamans',
    ),
    catacombs(
        'shaman_out_of_reach',
        fallen(*KNOT),
        (shaman(9, (27.0, 3.0)),),
        within=6.0,
        raised=4,
        why=f'the shaman stands 27 units out, past the blades ({REACH:.1f}), its pack within its 30',
    ),
    catacombs(
        'line_with_the_shaman_or_the_richer_line',
        fallen(*ROW, (6.0, 6.0), (9.0, 9.0)),
        (shaman(9, (13.0, 13.0)),),
        within=3.0,
        raised=2,
        why='four minions on one line, two minions and the shaman on another',
    ),
    catacombs(
        'champion_fallen_before_a_plain_shaman',
        fallen((6.0, 6.0), (9.0, 9.0)),
        (shaman(9, (4.0, 15.0)),),
        others=fallen(*ROW[:3], first=5, elite=True),
        raises=[1, 2],
        within=4.0,
        raised=2,
        why='the control for the elites: a shaman never raises a champion, so the champions first costs little',
    ),
    UNRAVELER_ASIDE,
    CHAMPIONS,
    Scenario(
        'unraveler_raises_from_out_of_reach',
        TOMB,
        (*pack(BURNING_DEAD, TOMB, *KNOT), body(9, UNRAVELER['txt'], (-8.0, 27.0), TOMB)),
        (raiser(9, UNRAVELER, [1, 2, 3, 4]),),
        within=8.0,
        raised=4,
        why='the Unraveler stands 28 units out and raises the corpses 25 to 31 units from it',
    ),
    Scenario(
        'flayer_shaman_among_its_flayers',
        JUNGLE,
        (
            *pack(FLAYER, JUNGLE, (9.0, 0.0), (11.0, 1.0), (13.0, -1.0)),
            body(9, FLAYER_SHAMAN['txt'], (12.0, 3.0), JUNGLE),
        ),
        (raiser(9, FLAYER_SHAMAN, [1, 2, 3], close=True),),
        within=3.0,
        raised=2,
        why='a Flayer Shaman raises from beside the corpse, so it stands in the pack and the pack line takes it',
    ),
    tougher(CHAMPIONS, 'terror_unique_unraveler_behind_a_champion_pack', terror_life(TOMB), within=7.0, raised=2),
    tougher(PAIR, 'terror_two_shamans_cover_each_other', terror_life(CATACOMBS), within=5.0, raised=2),
    tougher(UNRAVELER_ASIDE, 'tough_unraveler_off_the_line_of_its_skeletons', TOUGH, within=9.0, raised=2),
    tougher(PAIR, 'tough_two_shamans_cover_each_other', TOUGH, within=6.0, raised=2),
)

BY_NAME = {scenario.name: scenario for scenario in SCENARIOS}
