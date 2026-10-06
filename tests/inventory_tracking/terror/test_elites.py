"""Elite groups of a level: random ones against the level's range, fixed ones from its map pieces."""

from inventory_tracking.levels.model import Room
from inventory_tracking.terror.elites import Sighting, Table, fixed_groups, line, tally


TABLE = Table(
    levels={7: (7, 9), 83: (5, 7)},
    presets={
        (103, 0): (('unique', '', 40, 50),),
        (103, 1): (('unique', '', 10, 10), ('champion', '', 20, 20)),
        (654, 0): (('super', 'Toorc Icefist', 63, 88), ('super', 'Geleb Flamefinger', 62, 94)),
    },
    scripted={108: ('Infector of Souls',)},
    supers={27: 'Toorc Icefist', 28: 'Geleb Flamefinger', 38: 'Infector of Souls'},
)
PLAIN = Room(1, 100, 100, 8, 8)


def unique(unit_id, x, y, *, dead=False):
    return Sighting(unit_id, 'unique', 160, x, y, dead=dead)


def champion(unit_id, x, y, *, txt_id=160, dead=False):
    return Sighting(unit_id, 'champion', txt_id, x, y, dead=dead)


def test_fixed_groups_stand_where_their_piece_puts_them_once_per_piece():
    # A big piece comes as 8x8 chunks sharing its bounds: one piece, placed from the bounds' corner.
    chunks = [Room(654, 1160 + 8 * n, 360, 8, 8, 0, (1160, 360, 32, 32)) for n in range(3)]
    rooms = [PLAIN, Room(103, 200, 300, 8, 8, 0), *chunks]

    found = fixed_groups(83, rooms, TABLE)

    assert [(g.kind, g.name, g.x, g.y) for g in found] == [
        ('unique', '', 200 * 5 + 40, 300 * 5 + 50),
        ('super', 'Toorc Icefist', 1160 * 5 + 63, 360 * 5 + 88),
        ('super', 'Geleb Flamefinger', 1160 * 5 + 62, 360 * 5 + 94),
    ]


def test_a_piece_whose_file_is_not_read_yet_counts_as_its_first_file():
    assert [g.kind for g in fixed_groups(7, [Room(103, 200, 300, 8, 8)], TABLE)] == ['unique']


def test_scripted_bosses_are_fixed_groups_of_their_level():
    assert [(g.kind, g.name) for g in fixed_groups(108, [PLAIN], TABLE)] == [('super', 'Infector of Souls')]


def test_random_groups_count_uniques_one_each_and_champions_by_where_they_stood_together():
    seen = [
        unique(1, 1000, 1000, dead=True),
        unique(2, 3000, 1000),
        *(champion(10 + n, 2000 + 3 * n, 2000, dead=True) for n in range(3)),  # one group, all dead
        champion(20, 5000, 5000, dead=True),
        champion(21, 5003, 5000),  # one of two still alive: the group is
        champion(30, 5006, 5000, txt_id=161),  # another type next to them: its own group
    ]

    found = tally(7, [PLAIN], seen, TABLE)

    assert (found.killed, found.alive, found.expected) == (2, 3, (7, 9))
    assert (found.fixed_killed, found.fixed_alive, found.fixed_total) == (0, 0, 0)
    assert line(found) == 'Elites: 2 killed · 3 alive of 7-9'


def test_a_group_at_a_fixed_spot_and_every_super_unique_count_as_fixed_not_random():
    rooms = [Room(103, 200, 300, 8, 8, 0), Room(654, 400, 400, 8, 8, 0)]
    seen = [
        unique(1, 1045, 1552, dead=True),  # at the piece's unique pack
        unique(2, 1400, 1552),  # 72 tiles from it: a random one
        Sighting(3, 'super', 345, 2063, 2090, name='Toorc Icefist', dead=True),
        Sighting(4, 'super', 58, 9000, 9000, name='Bishibosh'),  # no piece names it: still fixed
    ]

    found = tally(83, rooms, seen, TABLE)

    assert (found.killed, found.alive, found.expected) == (0, 1, (5, 7))
    assert (found.fixed_killed, found.fixed_alive, found.fixed_total) == (2, 1, 4)  # Geleb not seen yet
    assert line(found) == 'Elites: 0 killed · 1 alive of 5-7 · fixed: 2 killed · 1 alive of 4'


def test_one_fixed_spot_takes_one_group_only():
    seen = [unique(1, 1045, 1552), unique(2, 1050, 1560)]

    found = tally(7, [Room(103, 200, 300, 8, 8, 0)], seen, TABLE)

    assert (found.alive, found.fixed_alive, found.fixed_total) == (1, 1, 1)


def test_no_line_where_nothing_is_expected_or_seen():
    assert line(tally(1, [PLAIN], [], TABLE)) is None
    assert line(tally(1, [PLAIN], [unique(1, 5, 5)], TABLE)) == 'Elites: 0 killed · 1 alive'
    assert line(tally(108, [PLAIN], [], TABLE)) == 'Elites: fixed: 0 killed of 1'
