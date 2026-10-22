"""Gambling rings at Jamella (macros/gamble.py; the player, 2026-10-21 ~09:45: "gamble loop: buy desired items (rings
for now) / when there is no empty space - sell them ... / if somethins is valuable - keep it / repeat until we have
<200k gold")."""

import logging
from collections.abc import Callable, Sequence
from dataclasses import replace

import pytest

from inventory_tracking.game.records import Carried, Monster, Pack, Stocked
from inventory_tracking.macros import gamble
from inventory_tracking.macros.actuator import Cancelled
from inventory_tracking.macros.cube import CUBE_CLASS
from inventory_tracking.macros.gamble import RING, RING_PRICE, Gambled, Judged, due, keep_rules, spendable
from inventory_tracking.macros.routines import screen_fraction
from inventory_tracking.macros.shop import JAMELLA, LINE, TRADE_ABOVE
from inventory_tracking.macros.waypoint import panel_point
from tests.inventory_tracking.macros.fakes import WINDOW, Event, Game, character_of, player, world


FORTRESS = 103
JAMELLA_AT = (5083.5, 5058.5)
CAP = 950_000  # level 95
AMULET = 535  # items metadata `amu`
MAGIC, UNIQUE = 4, 7
SALE = 3_000  # what a junk ring brings back
# Her gamble stock: two rings and an amulet on the first tab (the 14 items of 00:37 on 2026-10-17 had none on Misc)
STOCK = (Stocked(RING, 0, 0, 0, 501), Stocked(RING, 0, 1, 0, 502), Stocked(AMULET, 0, 2, 0, 503))


@pytest.fixture(autouse=True)
def first_runs_floor(monkeypatch):
    """The cases' gold sums were written at the first runs' floor (3M); the live floor is 200,000 since 2026-10-21
    ~15:20 (gamble.py GAMBLE_FLOOR, `test_the_live_floor_is_the_players_200k`)."""
    from inventory_tracking.macros import gamble as gamble_module

    monkeypatch.setattr(gamble_module, 'GAMBLE_FLOOR', 3_000_000)
    monkeypatch.setattr(gamble_module, 'CARRIED_FLOOR', 0)  # the carried floor of ~16:45 has its own tests


@pytest.fixture(autouse=True)
def gamble_lifts_apart(monkeypatch, tmp_path):
    monkeypatch.setattr(gamble, 'LIFTS_FILE', tmp_path / 'gamble-lifts.json')
    monkeypatch.setattr(gamble, 'GAMBLE_DRY', False)
    monkeypatch.setattr(gamble, 'GAMBLE', True)


class GambleGame(Game):
    """The fortress with Jamella: her Gamble line (the one under Trade) opens her gamble window, a plain right click on
    a ring there buys it (a new ring into the first free inventory cell, identified, its price off the carried gold and
    the rest off the personal stash's, as the game does), a new ring takes its stock cell (`rings_left` of them), her
    Refresh button brings two rings again, a Ctrl + click sells (Game's `sell_at`)."""

    def __init__(self, *, carried: int, bank: int, free: int = 20) -> None:
        jamella = Monster(77, JAMELLA, 1, *JAMELLA_AT, 0xFFFFFFFF)
        super().__init__(world(FORTRESS, player=player(FORTRESS, x=JAMELLA_AT[0] - 3.0, y=JAMELLA_AT[1]),
                               monsters=(jamella,)))  # fmt: skip
        self.vendor = jamella
        self.gamble_stock: tuple[Stocked, ...] = STOCK
        self.gambling = False
        # The cube and the player's charms fill all but `free` of the 40 cells
        taken = [Carried(1, CUBE_CLASS, 0, 0, (2, 2))]
        cells = [(x, y) for x in range(10) for y in range(4) if not (x < 2 and y < 2)]
        for n, (x, y) in enumerate(cells[: len(cells) - free]):
            taken.append(Carried(10 + n, 603, x, y, (1, 1)))
        self.pack = Pack(tuple(taken), ('...',) * 4, keys=12, portals=20)
        self.loot = replace(self.loot, stats=((12, 95), (14, carried), (15, bank)))
        self.sale_price = SALE
        self.qualities: list[int] = []  # each ring bought's quality in turn (magic when none is left)
        self.rings_left = 99  # rings her stock holds yet after a purchase
        self.on_buy: Callable[[int], None] = lambda n: None  # called with the count bought after each purchase
        self.bought: list[int] = []  # the unit ids that came
        self.refreshed = 0
        self.unseen = False  # a purchase paid from gold no stat shows (the shared stash's): stats 14 and 15 unchanged
        self.sales_at: list[int] = []  # the rings carried at each Ctrl + click

    def gold(self) -> tuple[int, int]:
        stats = dict(self.loot.stats)
        return stats.get(14, 0), stats.get(15, 0)

    def set_gold(self, carried: int, bank: int) -> None:
        stats = dict(self.loot.stats)
        stats[14], stats[15] = carried, bank
        self.loot = replace(self.loot, stats=tuple(stats.items()))

    def vendor_click(self, x: float, y: float) -> None:
        if self.vendor is not None and 'npc_shop' in self.world.open_panels and self.gambling:
            refresh = panel_point(WINDOW, *gamble.REFRESH)
            if abs(refresh[0] - x) < 0.02 and abs(refresh[1] - y) < 0.03:
                self.refreshed += 1
                self.next_unit += 10
                self.gamble_stock = (Stocked(RING, 0, 0, 0, self.next_unit), Stocked(RING, 0, 1, 0, self.next_unit + 1),
                                     Stocked(AMULET, 0, 2, 0, self.next_unit + 2))  # fmt: skip
                self.stock = self.gamble_stock
            return
        if self.vendor is not None and 'npc_shop' not in self.world.open_panels:
            drawn = screen_fraction(character_of(self.world), self.vendor.x, self.vendor.y, WINDOW[2] / WINDOW[3])
            if abs(drawn[0] - x) < 0.05 and abs(drawn[1] - (TRADE_ABOVE - LINE) - y) < LINE / 2:
                self.world = replace(self.world, open_panels=('inventory', 'npc_interact', 'npc_shop'))
                self.shop_opened = self.clock.now
                self.gambling, self.stock = True, self.gamble_stock
                return
        super().vendor_click(x, y)

    def act(self, event: Event) -> None:
        w = self.world
        if event[0] == 'click' and self.keys.ctrl:
            self.sales_at.append(len(self.rings()))
        if 'npc_shop' not in w.open_panels:
            self.gambling = False
        if event[0] == 'key' and event[1] == 'Escape':
            self.gambling = False
        if event[0] == 'button' and event[1] == 3 and self.gambling and 'npc_shop' in w.open_panels:
            if 'Shift_L' not in event[3]:
                self.buy(self.stock_cell(*event[2]))
            return
        super().act(event)

    def buy(self, cell: tuple[int, int]) -> None:
        assert self.pack is not None
        ring = next((s for s in self.stock if s.txt == RING and (s.x, s.y) == cell), None)
        free = next(((x, y) for x in range(10) for y in range(4) if self.pack.inventory[y][x] == '.'), None)
        carried, bank = self.gold()
        if ring is None or free is None or carried + bank < RING_PRICE:
            return
        paid = min(carried, RING_PRICE)
        if not self.unseen:
            self.set_gold(carried - paid, bank - (RING_PRICE - paid))  # the shortfall from the stash (D2MOO)
        self.next_unit += 1
        quality = self.qualities.pop(0) if self.qualities else MAGIC
        came = Carried(self.next_unit, RING, *free, (1, 1), quality=quality)
        self.pack = replace(self.pack, items=(*self.pack.items, came))
        self.bought.append(came.unit_id)
        self.rings_left -= 1
        self.next_unit += 1
        after = Stocked(RING if self.rings_left > 0 else AMULET, ring.tab, ring.x, ring.y, self.next_unit)
        self.gamble_stock = tuple(after if s is ring else s for s in self.stock)
        self.stock = self.gamble_stock
        self.on_buy(len(self.bought))

    def rings(self) -> list[Carried]:
        assert self.pack is not None
        return [i for i in self.pack.items if i.txt == RING]


def by_quality(rings: Sequence[Carried]) -> dict[int, Judged]:
    """The test's keep rules: a magic ring is junk, a unique kept."""
    return {
        r.unit_id: Judged(r.unit_id, r.quality == MAGIC, 'magic Ring' if r.quality == MAGIC else 'unique Ring',
                          'sell: K8 worthless' if r.quality == MAGIC else 'keep: K4 first copy', '+10 to Strength')
        for r in rings
    }  # fmt: skip


def buys(play: Game) -> list[Event]:
    return [e for e in play.keys.events if e[0] == 'button' and e[1] == 3 and 'Shift_L' not in e[3]]


def test_a_session_gambles_down_to_the_floor_and_never_takes_the_stashs_gold(monkeypatch):
    monkeypatch.setattr(gamble, 'GAMBLE_FLOOR', 3_200_000)
    monkeypatch.setattr(gamble, 'RINGS_MOST', 50)
    play = GambleGame(carried=950_000, bank=2_500_000, free=6)

    done = gamble.gamble(play.run(), by_quality)

    carried, bank = play.gold()
    assert bank == 2_500_000  # the personal stash's gold untouched
    assert carried + bank >= 3_200_000  # never under the floor
    assert carried + bank - RING_PRICE < 3_200_000  # and no ring's worth over it left
    assert done.bought == len(play.bought) >= 5
    assert done.sold == done.bought  # every magic ring sold
    assert not play.rings()
    assert done.paid == RING_PRICE * done.bought
    assert done.back == SALE * done.sold
    assert 'under the floor' in done.stop
    assert play.world.open_panels == ()
    assert gamble.hits() == [gamble.GAMBLE_ABOVE]  # the Gamble line's lift kept apart from her Trade line's


def test_a_session_spends_its_most_and_no_more(monkeypatch):
    monkeypatch.setattr(gamble, 'GAMBLE_SESSION_MOST', 160_000)
    play = GambleGame(carried=950_000, bank=2_500_000)

    done = gamble.gamble(play.run(), by_quality)

    assert done.paid - done.back <= 160_000
    assert done.bought == 3  # 3 x (50,000 - 3,000) = 141,000; a fourth would pass 160,000
    assert 'the session spent' in done.stop


def test_the_players_pause_ends_the_session_at_once():
    play = GambleGame(carried=950_000, bank=2_500_000, free=8)
    play.qualities = [MAGIC, UNIQUE, MAGIC]
    run = play.run()
    play.on_buy = lambda n: run.cancelled.set() if n == 3 else None  # three rings, then the player's KP_6 pause

    with pytest.raises(Cancelled):
        gamble.gamble(run, by_quality)

    assert len(play.bought) == 3


def test_the_unique_stays_carried_and_is_named_kept(monkeypatch):
    monkeypatch.setattr(gamble, 'RINGS_MOST', 3)
    play = GambleGame(carried=950_000, bank=2_500_000, free=8)
    play.qualities = [MAGIC, UNIQUE, MAGIC]

    done = gamble.gamble(play.run(), by_quality)

    assert done.bought == 3
    assert done.sold == 2
    assert done.kept == ['unique Ring']
    assert [r.quality for r in play.rings()] == [UNIQUE]


def test_rings_are_bought_until_no_cell_is_free_then_the_junk_is_sold(monkeypatch):
    monkeypatch.setattr(gamble, 'RINGS_MOST', 5)
    play = GambleGame(carried=950_000, bank=2_500_000, free=2)

    done = gamble.gamble(play.run(), by_quality)

    assert done.bought == 5
    assert done.sold == 5
    assert play.sales_at[:2] == [2, 1]  # the first sales once both free cells held a ring
    assert not play.rings()


def test_another_panel_stops_the_session():
    play = GambleGame(carried=950_000, bank=2_500_000)

    def opened(n: int) -> None:
        if n == 2:
            play.world = replace(play.world, open_panels=(*play.world.open_panels, 'stash'))

    play.on_buy = opened

    done = gamble.gamble(play.run(), by_quality)

    assert done.bought == 2
    assert 'a panel opened: stash' in done.stop
    assert done.sold == 0  # nothing more clicked in a window that is not hers alone


def test_no_buy_under_the_floor():
    # 3,040,000 in all: a ring would leave 2,990,000, under the 3M floor
    play = GambleGame(carried=540_000, bank=2_500_000)

    done = gamble.gamble(play.run(), by_quality)

    assert done.bought == 0
    assert not buys(play)
    assert play.gold() == (540_000, 2_500_000)
    assert 'under a ring' in done.stop


def test_the_personal_stashs_gold_pays_what_the_carried_gold_does_not(monkeypatch):
    # The player, 2026-10-21 ~10:10: "we can use gold for personal stash in gamble without widrawing it, just buy rings"
    monkeypatch.setattr(gamble, 'GAMBLE_FLOOR', 2_400_000)
    play = GambleGame(carried=60_000, bank=2_500_000)

    done = gamble.gamble(play.run(), by_quality)

    carried, bank = play.gold()
    assert done.bought >= 3  # past the carried 60,000
    assert bank < 2_500_000
    assert carried + bank >= 2_400_000
    assert 'under the floor' in done.stop


def test_a_reserve_is_left_with_no_floor(monkeypatch):
    monkeypatch.setattr(gamble, 'GAMBLE_FLOOR', 0)
    play = GambleGame(carried=20_000, bank=150_000)

    done = gamble.gamble(play.run(), by_quality)

    carried, bank = play.gold()
    assert done.bought == 2  # 170,000 -> 70,000 (+ the sales); a third would leave under 50,000
    assert carried + bank >= gamble.GOLD_RESERVE


def test_a_price_no_read_gold_paid_stops_the_session_loudly(caplog):
    # Paid from gold neither stat 14 nor stat 15 shows: the shared stash's ("I don't want to touch this 9M of gold")
    play = GambleGame(carried=950_000, bank=2_500_000)
    play.unseen = True

    with caplog.at_level(logging.INFO):
        done = gamble.gamble(play.run(), by_quality)

    assert done.bought == 1
    assert 'not from the carried or the personal stash' in done.stop
    assert any(r.levelno == logging.WARNING and 'shared stash' in r.message for r in caplog.records)
    assert any('shared stash' in said for said in play.said)


def test_the_dry_run_opens_her_gamble_window_and_buys_nothing(monkeypatch, caplog):
    monkeypatch.setattr(gamble, 'GAMBLE_DRY', True)
    play = GambleGame(carried=950_000, bank=2_500_000)

    with caplog.at_level(logging.INFO):
        done = gamble.gamble(play.run(), by_quality)

    assert done.dry
    assert done.bought == 0
    assert not buys(play)
    assert play.gold() == (950_000, 2_500_000)
    planned = [r.message for r in caplog.records if 'dry: would click her tab 0' in r.message]
    assert planned
    assert 'right click the Ring' in planned[0]
    assert play.world.open_panels == ()


def test_no_ring_in_her_stock_refreshes_it(monkeypatch):
    monkeypatch.setattr(gamble, 'RINGS_MOST', 3)
    play = GambleGame(carried=950_000, bank=2_500_000)
    play.gamble_stock = (Stocked(RING, 0, 0, 0, 501), Stocked(AMULET, 0, 2, 0, 503))
    play.rings_left = 0  # each ring bought leaves an amulet in its cell

    def again(n: int) -> None:
        play.rings_left = 0

    play.on_buy = again

    done = gamble.gamble(play.run(), by_quality)

    assert play.refreshed >= 1
    assert done.bought == 3


def test_the_gamble_line_is_learned_apart_from_her_trade_line():
    play = GambleGame(carried=950_000, bank=2_500_000)
    play.gamble_stock = ()  # nothing read: the window is not taken for hers, each lift tried

    with pytest.raises(Exception, match='gamble window did not open'):
        gamble.gamble(play.run(), by_quality)

    assert gamble.hits() == []


def test_the_switch_off_is_today_and_on_it_is_due_at_the_cap(monkeypatch):
    assert due(940_000, 2_500_000, CAP) is not None  # a sale would pass the cap
    assert due(800_000, 2_300_000, CAP) is None  # sales still go, 100,000 over the floor
    assert due(800_000, 2_500_000, CAP) is not None  # 300,000 over the floor: a session's worth
    assert due(940_000, 2_000_000, CAP) is None  # 2.94M: nothing over the 3M floor
    assert due(940_000, None, CAP) is None  # the stash's gold unread
    monkeypatch.setattr(gamble, 'GAMBLE', False)
    assert due(950_000, 2_500_000, CAP) is None


def test_the_budget_is_the_floor_the_reserve_and_the_session_most(monkeypatch):
    assert spendable(950_000, 2_500_000) == 450_000  # down to the 3M floor on the sum
    assert spendable(950_000, 9_000_000) == 500_000  # the session's most
    assert spendable(100_000, 3_100_000) == 200_000  # the personal stash's gold spent too
    assert spendable(None, 2_500_000) == 0
    monkeypatch.setattr(gamble, 'GAMBLE_FLOOR', 0)
    assert spendable(30_000, 100_000) == 130_000 - gamble.GOLD_RESERVE


def test_a_ring_with_no_appraisal_is_kept_by_the_live_rules():
    ring = Carried(4242, RING, 3, 1, (1, 1), quality=MAGIC)
    asked: list[list[int]] = []

    verdicts = keep_rules(asked.append)([ring])

    assert asked == [[4242]]
    assert not verdicts[4242].sell
    assert 'no appraisal' in verdicts[4242].why


def test_the_summary_says_what_the_session_did():
    done = Gambled(bought=3, kept=['unique Ring'], sold=2, paid=150_000, back=6_000, carried=(950_000, 806_000),
                   bank=(2_500_000, 2_500_000), stop='3 rings', seconds=12.5)  # fmt: skip
    said = done.said()
    assert '3 rings bought, 1 kept (unique Ring), 2 sold' in said
    assert 'spent 144000' in said
    assert 'stop: 3 rings' in said


class LateGold(GambleGame):
    """Her prices come off the carried gold `lag` seconds after the ring shows (14:26:09 on 2026-10-21)."""

    lag = 1.2

    def __init__(self, *args, **kwargs) -> None:
        self.pending: list[tuple[float, int, int]] = []
        super().__init__(*args, **kwargs)

    @property
    def loot(self):
        while self.pending and self.pending[0][0] <= self.clock.now:
            _, carried, bank = self.pending.pop(0)
            stats = dict(self._loot.stats)
            stats[14], stats[15] = carried, bank
            self._loot = replace(self._loot, stats=tuple(stats.items()))
        return self._loot

    @loot.setter
    def loot(self, value) -> None:
        self._loot = value

    def set_gold(self, carried: int, bank: int) -> None:
        if not hasattr(self, 'clock'):
            super().set_gold(carried, bank)
            return
        self.pending.append((self.clock.now + self.lag, carried, bank))


@pytest.mark.parametrize('wait', [True, False])
def test_a_price_that_shows_late_is_waited_for_not_taken_for_the_shared_stashs(monkeypatch, wait):
    # 14:26:09 on 2026-10-21: buy 2 read "for 0 gold" and gambling stopped; the price came off at the next read
    monkeypatch.setattr(gamble, 'WAIT_GOLD_MOVE', wait)
    play = LateGold(carried=950_000, bank=2_500_000)

    done = gamble.gamble(play.run(), by_quality)

    if not wait:
        assert done.bought == 1
        assert 'not from the carried or the personal stash' in done.stop
        return
    assert done.bought >= 2
    assert 'not from the carried or the personal stash' not in (done.stop or '')
    assert done.paid == done.bought * RING_PRICE


def test_the_live_floor_is_the_players_200k():
    # the player, 2026-10-21 ~15:20: "yes, lower it to 200k"
    import ast
    from pathlib import Path

    tree = ast.parse(Path(gamble.__file__).read_text(encoding='utf-8'))
    floor = next(
        n.value
        for n in tree.body
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'GAMBLE_FLOOR'
    )
    assert ast.literal_eval(floor) == 200_000


def test_the_carried_gold_is_never_gambled_under_the_carried_floor(monkeypatch):
    # the player, 2026-10-21 ~16:45: "Keep 200k carried" (16:41: the session left 8,309 carried)
    monkeypatch.setattr(gamble, 'CARRIED_FLOOR', 200_000)
    monkeypatch.setattr(gamble, 'GAMBLE_FLOOR', 200_000)
    assert gamble.spendable(189_142, 2_500_000) == 0
    assert gamble.spendable(537_961, 2_500_000) == 337_961
    assert gamble.spendable(950_000, 0) == 500_000  # the session's most


def test_the_live_carried_floor_is_the_players_200k():
    import ast
    from pathlib import Path

    tree = ast.parse(Path(gamble.__file__).read_text(encoding='utf-8'))
    floor = next(
        n.value
        for n in tree.body
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'CARRIED_FLOOR'
    )
    assert ast.literal_eval(floor) == 200_000
