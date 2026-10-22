"""A drop in a pile whose label no aim finds (macros/pile.py; rca/2026-10-21/targeting-findings.md §4.1).

09:19:21-26 on 2026-10-21: a Magic Sun Spirit among 12 drops, three tries, 26 aims, the potions' labels under every
one. Here the fake game lays the labels out as boxes (classic pixels from each drop's ground): the potions' labels stack
up the drop's column, its own is pushed to the side where no aim of the pickup looks; with Show Items off every drop is
its picture on its own ground.
"""

import pytest

from inventory_tracking.game.records import HEALING, VALUABLE, Drop, Loot, Teleport
from inventory_tracking.game.view import Viewport
from inventory_tracking.levels.model import Level, Room
from inventory_tracking.macros import pickup, pile
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.pickup import pick_up
from tests.inventory_tracking.macros.fakes import KEYS, SHOW_ITEMS_KEY, SLOTS, WINDOW, Game, world


HERE = Room(1, 996, 996, 8, 8)
EAST = tuple(Room(2 + i, 1004 + 8 * i, 996, 8, 8) for i in range(4))
LEVEL = Level(101, (HERE, *EAST), ())
FULL = (606, 606, 531, 531) * 4
SPIRIT = Drop(70, 5004.0, 5002.0, 'Magic Sun Spirit', VALUABLE, (2, 2))
POTIONS = tuple(Drop(80 + i, 5004.0 + (1, -1, 2, -2, 0, 1)[i], 5002.0 + (1, 1, -1, 2, 2, -2)[i], 'potion', HEALING)
                for i in range(6))  # fmt: skip
SIDE = (60.0, -70.0, 130.0, -56.0)  # the Sun Spirit's label: pushed right of the column, where no pickup aim looks
PICTURE = (-10.0, -14.0, 10.0, 4.0)  # a drop's own picture on its ground, the labels hidden


class Pile(Game):
    """Labels as boxes (left, top, right, bottom; classic pixels from the drop's ground), the first drop of the list
    whose box holds the pointer on top; with Show Items off each drop's picture (`picture`) on its ground."""

    def __init__(self, *drops: Drop) -> None:
        super().__init__(world(area=101, slots=SLOTS, show_items=True))
        self.staff = Teleport(10, 20, True)
        self.loot = Loot(tuple(drops), FULL, 1000, 1000)
        self.boxes: dict[int, tuple[float, float, float, float]] = {}
        self.picture = PICTURE

    def drop_under_pointer(self) -> Drop | None:
        fx, fy = self.keys.fraction()
        aspect = WINDOW[2] / WINDOW[3]
        me = self.character
        for drop in self.loot.drops:
            gx, gy = Viewport(aspect).ground((me.x, me.y), drop.x, drop.y)
            across, down = (fx - gx) * aspect * 600, (fy - gy) * 600
            box = self.picture if self.world.show_items is False else self.boxes.get(drop.unit_id, (-30, -32, 30, -16))
            if box[0] <= across <= box[2] and box[1] <= down <= box[3]:
                return drop
        return None


def keys(_world, skills):
    return {skill: KEYS[skill] for skill in skills}


def nothing():
    raise AssertionError('there was something to pick up')


def sun_spirit_pile() -> Pile:
    """The potions first in the list (their labels drawn over the Sun Spirit's), each label 18 pixels above the one
    below it, up the column from the Sun Spirit's own aim (0, -24)."""
    play = Pile(*POTIONS, SPIRIT)
    for i, potion in enumerate(POTIONS):
        # each potion's label drawn over the column above the Sun Spirit: its box moved by where the potion lies
        dx, dy = potion.x - SPIRIT.x, potion.y - SPIRIT.y
        across, down = (dx - dy) * 16, (dx + dy) * 8
        top = -32 - 18 * i
        play.boxes[potion.unit_id] = (-60 - across, top - down, 60 - across, top + 16 - down)
    play.boxes[SPIRIT.unit_id] = SIDE
    return play


@pytest.fixture(autouse=True)
def fresh_sweep(monkeypatch):
    monkeypatch.setattr(pile, 'SWEPT', {})


def test_the_pickup_aims_alone_never_find_the_pushed_label(monkeypatch):
    # Before: 2026-10-21 09:19:21-26, three tries and the Sun Spirit left on the ground
    monkeypatch.setattr(pile, 'PILE_LABELS_OFF', False)
    monkeypatch.setattr(pile, 'PILE_SWEEP', False)
    play = sun_spirit_pile()
    run = play.run()
    run.show_items_key = SHOW_ITEMS_KEY
    with pytest.raises(Abort):
        pick_up(run, LEVEL, keys, nothing)
    assert play.picked == []


def test_a_pile_drop_no_label_aim_finds_is_clicked_by_its_picture_with_the_labels_hidden():
    play = sun_spirit_pile()
    run = play.run()
    run.show_items_key = SHOW_ITEMS_KEY

    assert pick_up(run, LEVEL, keys, nothing)

    assert play.picked == ['Magic Sun Spirit']  # never a potion
    assert play.world.show_items is True  # the labels shown again for the level run (routines.show_items_on)
    assert [e for e in play.keys.events if e[0] == 'key' and e[1] == SHOW_ITEMS_KEY]  # hidden by its key


def test_with_no_show_items_key_the_labels_are_swept_and_the_pushed_label_found():
    play = sun_spirit_pile()
    run = play.run()
    run.show_items_key = None

    assert pick_up(run, LEVEL, keys, nothing)

    assert play.picked == ['Magic Sun Spirit']
    assert play.world.show_items is True  # never touched


def test_the_labels_come_back_on_when_the_look_with_them_hidden_is_cut_short(monkeypatch):
    play = sun_spirit_pile()
    run = play.run()
    run.show_items_key = SHOW_ITEMS_KEY

    def cut(*_args, **_kwargs):
        raise Abort('priced act expired: look again before continuing')

    monkeypatch.setattr(pile, 'look_hidden', cut)
    with pytest.raises(Abort, match='priced act expired'):
        pile.pile_take(run, SPIRIT, {SPIRIT.unit_id: SPIRIT}, 6, [], pickup.click)
    assert play.world.show_items is True


def test_a_sweep_cut_short_goes_on_where_it_left_off():
    play = sun_spirit_pile()
    play.boxes[SPIRIT.unit_id] = (300.0, 300.0, 301.0, 301.0)  # nowhere
    run = play.run()
    run.show_items_key = None
    path = pile.sweep_path(6)
    steps = iter(range(10))

    original = run.hovered
    assert original is not None

    def hovered():
        if next(steps, None) is None:
            raise Abort('priced act expired: look again before continuing')
        return original()

    run.hovered = hovered
    with pytest.raises(Abort):
        pile.sweep(run, SPIRIT, {SPIRIT.unit_id: SPIRIT}, 6, [], pickup.click)
    assert 0 < pile.SWEPT[SPIRIT.unit_id] < len(path)


def test_the_sweep_never_clicks_an_unwanted_label_and_covers_the_columns():
    path = pile.sweep_path(11)
    assert {across for across, _ in path} == set(pile.SWEEP_COLUMNS)
    assert min(down for _, down in path) <= -64 - 10 * 11 + pile.SWEEP_STEP
    play = sun_spirit_pile()
    play.boxes[SPIRIT.unit_id] = (300.0, 300.0, 301.0, 301.0)  # nowhere
    run = play.run()
    assert pile.sweep(run, SPIRIT, {SPIRIT.unit_id: SPIRIT}, 6, [], pickup.click) is None
    assert play.picked == []
    assert not [e for e in play.keys.events if e[0] == 'click']
