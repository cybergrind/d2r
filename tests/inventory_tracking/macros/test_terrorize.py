"""A Worldstone Shard used in town (macros/terrorize.py): which shard, the take-out and the right click against a small
scripted stash, and what is said. Offline: which click the game takes is the player's in-game test
(rca/2026-10-20/act-terrorize-findings.md §6)."""

import threading
from dataclasses import dataclass, field, replace

import pytest

from inventory_tracking.game.records import Carried, Pack, StashView
from inventory_tracking.loot.storage import MATERIALS_TAB
from inventory_tracking.macros import terrorize
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import INVENTORY, cell_point, rune_slot
from inventory_tracking.macros.stash import tab_point
from inventory_tracking.macros.terrorize import SHARD_FLOOR, choose_shard
from inventory_tracking.macros.waypoint import panel_point
from tests.inventory_tracking.macros.fakes import world


WESTERN, EASTERN, SOUTHERN, DEEP, NORTHERN = 674, 675, 676, 677, 678
FORTRESS = 103
WINDOW = (0, 0, 3840, 2160)
ACT4 = (104, 105, 106, 107, 108)


def view(**counts: int) -> StashView:
    names = {'western': WESTERN, 'eastern': EASTERN, 'southern': SOUTHERN, 'deep': DEEP, 'northern': NORTHERN}
    return StashView((), tuple(sorted((names[name], count) for name, count in counts.items())))


def test_the_most_held_shard_at_90_or_more_is_chosen_ties_to_the_cheaper():
    assert choose_shard(view(western=95, deep=97)) == DEEP
    assert choose_shard(view(western=97, eastern=97)) == WESTERN  # a tie: the cheaper
    assert choose_shard(view(northern=99, deep=99)) == DEEP
    assert choose_shard(view(western=SHARD_FLOOR - 1, deep=12)) is None  # 89 is under the floor
    assert choose_shard(view(western=SHARD_FLOOR)) == WESTERN
    assert choose_shard(None) is None  # the stash unread: no choice
    assert choose_shard(view()) is None


def test_an_act_asked_for_takes_only_its_shard():
    # The Act 4 kind: only the Deep shard terrorizes Act 4 (misc.txt xa4 calc1 4)
    assert choose_shard(view(western=99, deep=93), act=4) == DEEP
    assert choose_shard(view(western=99, deep=60), act=4) is None
    assert terrorize.SHARDS[DEEP] == 4


@dataclass
class Stash:
    """The game as the shard's clicks see it: the carried items, the Materials stacks, the pointer, open panels.
    `take`: what a click on a stack does (CTRL: one to the inventory, CURSOR: one onto the pointer, None: nothing);
    `use`: what a right click on a shard does ('consumed', 'back' onto its stack, None nothing)."""

    stacks: dict[int, int]
    items: list[Carried] = field(default_factory=list)
    pointer: Carried | None = None
    take: str | None = terrorize.CTRL
    use: str | None = 'consumed'
    panels: tuple[str, ...] = ('stash', 'inventory')
    tab: int = 0
    at: tuple[float, float] = (0.0, 0.0)
    clicks: list[tuple[str, tuple[str, ...], tuple[float, float]]] = field(default_factory=list)
    said: list[str] = field(default_factory=list)
    listed: frozenset[int] = frozenset()
    used: list[int] = field(default_factory=list)
    next_unit: int = 500

    def pack(self) -> Pack:
        return Pack(tuple(self.items), pointer=self.pointer.unit_id if self.pointer is not None else None)

    def near(self, point: tuple[float, float]) -> bool:
        return abs(point[0] - self.at[0]) < 0.01 and abs(point[1] - self.at[1]) < 0.02

    def slot_of(self) -> int | None:
        return next(
            (txt for txt in self.stacks if (slot := rune_slot(txt)) and self.near(panel_point(WINDOW, *slot))), None
        )

    def item_at(self) -> Carried | None:
        return next((i for i in self.items if self.near(cell_point(WINDOW, INVENTORY, (i.x, i.y), i.size))), None)

    def free(self) -> tuple[int, int]:
        spot = self.pack().inventory.first_spot((1, 1))
        assert spot is not None
        return spot

    def click(self, *holding: str) -> None:
        self.clicks.append(('left', holding, self.at))
        if self.near(panel_point(WINDOW, *tab_point(MATERIALS_TAB))):
            self.tab = MATERIALS_TAB
            return
        txt = self.slot_of()
        if txt is not None and self.tab == MATERIALS_TAB:
            if self.pointer is not None and self.pointer.txt == txt:  # put back onto its stack
                self.stacks[txt] += 1
                self.pointer = None
            elif holding == ('Control_L',) and self.take == terrorize.CTRL:
                self.items.append(Carried(self.next_unit, txt, *self.free(), (1, 1)))
                self.stacks[txt] -= 1
            elif not holding and self.take == terrorize.CURSOR:
                self.pointer = Carried(self.next_unit, txt, 0, 0, (1, 1))
                self.stacks[txt] -= 1
            return
        if self.pointer is not None and not holding:
            for y in range(4):
                for x in range(10):
                    if self.near(cell_point(WINDOW, INVENTORY, (x, y))):
                        self.items.append(replace(self.pointer, x=x, y=y))
                        self.pointer = None
                        return

    def tap(self, *names: str) -> None:
        self.clicks.append(('tap', names, self.at))
        item = self.item_at()
        if names == ('Button3',) and item is not None and item.txt in terrorize.SHARDS:
            if self.use is not None:
                self.items.remove(item)
            if self.use == 'consumed':
                self.used.append(item.txt)
                self.listed = frozenset(ACT4)
            elif self.use == 'back':
                self.stacks[item.txt] += 1


class Actuator:
    def __init__(self, game: Stash) -> None:
        self.game = game
        self.keys = self

    def focused_window_rect(self) -> tuple[int, int, int, int]:
        return WINDOW

    def move(self, x: float, y: float, *, scatter=(6, 4), quick=False) -> None:
        self.game.at = (x, y)

    def click(self, *holding: str) -> None:
        self.game.click(*holding)

    def tap(self, *names: str) -> None:
        self.game.tap(*names)


class Reads:
    def __init__(self, game: Stash) -> None:
        self.game = game

    def carried(self) -> Pack:
        return self.game.pack()

    def stash_view(self) -> StashView:
        return StashView((), tuple(sorted(self.game.stacks.items())))


class Pace:
    def __init__(self, run: Run) -> None:
        self.run = run

    def sleep(self, seconds: float) -> None:
        self.run.now += seconds


class Run:
    def __init__(self, game: Stash, area: int = FORTRESS) -> None:
        self.game, self.area, self.now = game, area, 0.0
        self.actuator, self.reads, self.pace = Actuator(game), Reads(game), Pace(self)
        self.cancelled = threading.Event()

    def clock(self) -> float:
        return self.now

    def world(self):
        return replace(world(self.area), open_panels=self.game.panels)

    def say(self, text: str) -> None:
        self.game.said.append(text)


@pytest.fixture
def clicks_on(monkeypatch):
    monkeypatch.setattr(terrorize, 'CLICKS', True)
    monkeypatch.setattr(terrorize, 'close', lambda run, panels: None)
    monkeypatch.setattr(terrorize, 'open_inventory', lambda run, key: None)


def use(game: Stash, **kwargs) -> terrorize.Used | None:
    run = Run(game)
    terrorized = kwargs.pop('terrorized', lambda area: area in game.listed)
    return terrorize.terrorize(run, 'i', terrorized=terrorized, **kwargs)  # pyrefly: ignore[bad-argument-type] the fake run


def test_with_the_clicks_off_the_request_chooses_and_says_and_clicks_nothing(caplog, monkeypatch):
    monkeypatch.setattr(terrorize, 'CLICKS', False)
    game = Stash({DEEP: 97, WESTERN: 40})
    with caplog.at_level('INFO'):
        assert use(game) is None
    assert game.clicks == []
    assert game.stacks == {DEEP: 97, WESTERN: 40}
    assert 'Macro: terrorize: Deep Worldstone Shard chosen for act 4 (stack 97;' in caplog.text
    assert 'the clicks are off' in caplog.text


def test_no_shard_at_the_floor_uses_nothing_and_says_so(caplog, clicks_on):
    game = Stash({DEEP: 89})
    with caplog.at_level('INFO'):
        assert use(game) is None
    assert game.clicks == []
    assert f'Macro: terrorize: no shard for any act at {SHARD_FLOOR} or more' in caplog.text


def test_out_of_town_it_is_refused():
    with pytest.raises(Abort, match='used in town'):
        terrorize.terrorize(Run(Stash({DEEP: 97}), area=107), 'i')  # pyrefly: ignore[bad-argument-type] the fake run


def test_one_shard_out_by_ctrl_click_then_a_right_click_on_its_cell_terrorizes_the_act(caplog, clicks_on):
    game = Stash({DEEP: 97, WESTERN: 95}, items=[Carried(7, 529, 0, 0, (1, 1))])  # a potion in the first cell
    with caplog.at_level('INFO'):
        used = use(game)
    assert used is not None
    assert used.confirmed
    assert (used.shard, used.act, used.before, used.after, used.listed) == (DEEP, 4, 97, 96, True)
    assert game.used == [DEEP]
    assert game.stacks == {DEEP: 96, WESTERN: 95}  # one shard, the other stacks untouched
    # The right click on the shard's cell, never another
    (right,) = [click for click in game.clicks if click[0] == 'tap']
    assert right[1] == ('Button3',)
    assert right[2] == pytest.approx(cell_point(WINDOW, INVENTORY, (1, 0)))
    assert 'Macro: terrorize: Deep Worldstone Shard used for act 4 (stack 97 -> 96); the act read terrorized' in (
        caplog.text
    )


def test_one_shard_by_the_pointer_is_put_on_a_free_cell_then_used(clicks_on, monkeypatch):
    monkeypatch.setattr(terrorize, 'TAKE_OUT', terrorize.CURSOR)
    game = Stash({DEEP: 93}, take=terrorize.CURSOR)
    used = use(game)
    assert used is not None
    assert used.confirmed
    assert game.stacks == {DEEP: 92}
    assert game.pointer is None


def test_a_click_that_takes_no_shard_out_makes_no_right_click(caplog, clicks_on):
    game = Stash({DEEP: 97}, take=None)
    with caplog.at_level('INFO'):
        assert use(game) is None
    assert all(click[0] != 'tap' for click in game.clicks)
    assert game.stacks == {DEEP: 97}
    assert 'put no shard in the inventory' in caplog.text


def test_a_right_click_that_puts_it_back_on_its_stack_is_not_confirmed(clicks_on):
    game = Stash({DEEP: 97}, use='back')
    used = use(game)
    assert used is not None
    assert used.gone
    assert not used.confirmed  # the stack is not one lower: not used
    assert game.stacks == {DEEP: 97}


def test_a_right_click_that_does_nothing_leaves_the_shard_carried_and_said(caplog, clicks_on):
    game = Stash({DEEP: 97}, use=None)
    with caplog.at_level('INFO'):
        used = use(game)
    assert used is not None
    assert not used.gone
    assert [item.txt for item in game.items] == [DEEP]
    assert 'did not use it: it stays carried' in caplog.text


def test_a_use_the_client_does_not_list_is_said_not_read_terrorized(caplog, clicks_on):
    game = Stash({DEEP: 97})
    with caplog.at_level('INFO'):
        used = use(game, terrorized=lambda area: False)
    assert used is not None
    assert used.confirmed
    assert used.listed is False
    assert 'the act not read terrorized' in caplog.text


def test_the_act_kinds_use_with_no_inventory_key_terrorizes_with_the_stash_open(clicks_on):
    # Session 20261020T184216Z-86b2d9c3, game 1 (21:42:42): the act kind (actloop.py `use_shard`) passes no inventory
    # key; "no inventory key read" stopped the shard and left the game. The right click is made with the stash open
    # (USE_WITH_STASH_OPEN): the key opens nothing
    assert terrorize.USE_WITH_STASH_OPEN
    game = Stash({DEEP: 97})
    run = Run(game)
    used = terrorize.terrorize(run, None, 4, lambda area: area in game.listed)  # pyrefly: ignore[bad-argument-type] the fake run
    assert used is not None
    assert used.confirmed
    assert game.used == [DEEP]


def test_with_the_stash_closed_first_the_use_needs_the_inventory_key(clicks_on, monkeypatch):
    monkeypatch.setattr(terrorize, 'USE_WITH_STASH_OPEN', False)
    with pytest.raises(Abort, match='no inventory key read'):
        terrorize.terrorize(Run(Stash({DEEP: 97})), None, 4)  # pyrefly: ignore[bad-argument-type] the fake run
