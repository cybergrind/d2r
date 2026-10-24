"""Gambling rings at Jamella to bring the gold under its cap (`gamble`), and when a town visit does it (`due`).

The player, 2026-10-21 ~09:45 (the carried gold sat at the cap, 950,000 = level 95 x 10k, so every visit walked to
Jamella, sold nothing and put the junk down by the stash, where its labels covered the stash): "for jamella and gold:
probably we need to implement gambling / go to jamella / gamble loop: buy desired items (rings for now) / when there is
no empty space - sell them (you don't need to go from gamble tab, you just right click to buy and sell) / if somethins
is valuable - keep it / repeat until we have <200k gold in both our and personal stash inventory / then we would be able
to sell items again without needing to turn off/on loot visibility". ~09:50: "this needs to be carefully analyzed when
we're doing it first time. probably we can set some higher budget at first (not 200k, but for example 3M, to test in
several times)". The shared stash's gold is never touched ("I don't want to touch this 9M of gold atm", 2026-10-17).

A session: walk to Jamella, open her Gamble line (the one under Trade), read her gamble stock (the same four vendor
grids as her trade stock, game/memory.py `stock`; a trade window is told by its key and scrolls), right click a ring
(plain right click buys one, as koolo's `BuyItem`), the ring arriving identified in the first free inventory cell. Rings
are bought until the inventory has no free cell or BATCH_MOST wait; then the batch is judged by the town's keep rules
(`keep_rules`: the identify worker's read, loot/api.py `town_verdicts`, the same decision a town visit makes) and the
junk ones sold from the gamble window (Ctrl + click, as shop.py `restock`'s sales and koolo's `SellItem` inside its
gamble chain). The kept ones stay carried for the next stash stop. No ring in her stock: her Refresh button.

Gold places (verified 2026-10-21): stat 14 `gold` is the carried gold, stat 15 `goldbank` the personal stash tab's
(08:57:22: "stat 15: 2500000", the Personal tab showing 2,500,000 in deposit-failed-085722.png while the Shared tab
showed 12,500,000 on 2026-10-19 07:53): the shared stash's gold is no stat of the character and is never read here. A
vendor takes what the carried gold does not cover from stat 15 (D2MOO SUnitNpc.cpp 1832-1837), and the player ruled that
fine (2026-10-21 ~10:10: "we can use gold for personal stash in gamble without widrawing it, just buy rings"): the
session spends the sum of both down to GAMBLE_FLOOR. Whether RotW can take the shared stash's gold too is unknown, so
each price must come out of stats 14 and 15: their sum falls by RING_PRICE within PRICE_DRIFT, else the session stops
and says so loudly (gold no stat shows paid it: the shared stash's, "I don't want to touch this 9M of gold atm").

Guards: the window must stay the gamble window (any other panel stops the session); no buy that would leave the sum
under GAMBLE_FLOOR or GOLD_RESERVE; each price out of stats 14 and 15, within PRICE_DRIFT; only a ring this session
bought and the keep rules call junk is sold, never one `protected` (engine.py) and never with the gold near its cap;
RINGS_MOST rings, SECONDS_MOST seconds and GAMBLE_SESSION_MOST gold a session at most; the player's KP_6 pause (a
cancel) and hand end it as any act. GAMBLE_DRY opens the window, reads the stock and logs the planned clicks, and buys
nothing.
"""

import json
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING

from inventory_tracking.common import LOG
from inventory_tracking.game.layout import GOLD_STAT
from inventory_tracking.game.records import Carried, Pack, Stocked
from inventory_tracking.game.stash import BANK_STAT
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import INVENTORY, cell_point
from inventory_tracking.macros.engine import Run, protected
from inventory_tracking.macros.shop import (
    JAMELLA,
    KEY,
    LINE,
    PANEL_SECONDS,
    SALE_MOST,
    SCROLL,
    SEEN,
    VENDOR,
    WALK_SECONDS,
    WALKING,
    _close,
    _note,
    _open_menu,
    gold_cap,
    serving,
    tab_point,
    walk_until,
    whereabouts,
)
from inventory_tracking.macros.waypoint import panel_point


if TYPE_CHECKING:
    from inventory_tracking.loot.assess import Assessor
    from inventory_tracking.loot.facts import ItemFacts
    from inventory_tracking.loot.value import Value


__all__ = [
    'ASSESSED',
    'CARRIED_FLOOR',
    'GAMBLE',
    'GAMBLE_DRY',
    'GAMBLE_FLOOR',
    'GAMBLE_SESSION_MOST',
    'NEAR_CAP',
    'NEAR_CAP_ONLY',
    'RING',
    'RING_PRICE',
    'Gambled',
    'Judge',
    'Judged',
    'due',
    'gamble',
    'keep_rules',
    'spendable',
]

# The switch: gamble at a town visit when `due` (the player, 2026-10-21 ~09:45: "probably we need to implement
# gambling"). False: today (no gamble; the junk put down at the cap)
GAMBLE = True
# The first live runs plan and log the clicks without making them (the coordinator for the player, 2026-10-21 ~09:50:
# "this needs to be carefully analyzed when we're doing it first time"): the window is opened and read, the first buy
# and the sell gesture logged, nothing bought. False once a dry session's log is checked: checked 2026-10-21 13:35:27
# (her stock read, tab 0, the Ring at (9, 0) for ~50,000, budget 450,000); the player: "we have topped up gold and no
# gamble session has occured"
GAMBLE_DRY = False
# The rings are judged by the one assessment entry point at GAMBLE (loot/assess.py `live().assess_all`, design.md §10.4
# step 3; the player, 2026-10-23: "I want to have one place that decides pickups/value"): the town's rules, as before.
# Gate (2026-10-23): the same sell/keep per ring on the recorded rings (tests/inventory_tracking/macros/
# test_gamble_assessed.py). `_sell`'s guards stay (engine.py `protected`, D3). While on, a ring the old call
# (loot/api.py `town_verdicts` over BOOK) judges otherwise logs one shadow line. False: the old call alone
ASSESSED = True
# Gold the session leaves, counted as the carried gold (stat 14) plus the personal stash's (stat 15); the shared stash's
# is no part of it. 3M for the first runs ("probably we can set some higher budget at first (not 200k, but for example
# 3M, to test in several times)", 2026-10-21 ~09:50); the target is the sum under 200,000 (the player, ~10:10, on "<200k
# gold in both our and personal stash inventory"), once the first sessions' logs are checked: checked 2026-10-21 (3
# sessions, 13 rings, every price from stats 14 and 15 once WAIT_GOLD_MOVE was in), the player ~15:20: "yes, lower it to
# 200k"
GAMBLE_FLOOR = 200_000
GAMBLE_SESSION_MOST = 500_000  # gold one session spends at most: short sessions, several of them, to analyse
RING = 537  # items metadata class of `rin` (Ring; d2data misc.json code `rin`, the same numbering as shop.py KEY 558)
# A ring's gamble price: misc.json `rin` `gamble cost` 50000 (pricing/raw/d2data-misc.json); rings and amulets cost it
# flat whatever the level (D2MOO Items.cpp 2526-2529, less the reduced-prices stat). Checked against each purchase
RING_PRICE = 50_000
# A price off RING_PRICE by more than this share (stats 14 and 15 together) stops the session: a misread, a new formula,
# or gold no stat shows paid it (the shared stash's)
PRICE_DRIFT = 0.2
# The carried and personal stash gold never gambled below, whatever the floor: keys, scrolls and a repair (the staff's
# ~11k; a vendor takes a repair's shortfall from the personal stash too, D2MOO SUnitNpc.cpp 1782-1795)
GOLD_RESERVE = 50_000
# A session at a visit that does not need it for the cap: this much over the floor (a short walk for a few rings is
# not worth it; "identify-in-a-batch only when room runs out", the player's lazy-batch mindset, 2026-10-20)
DUE_SPEND = 250_000
# Gambling only near the gold's cap (the player, 2026-10-23: "Only near gold cap"): a session only once the carried
# gold (stat 14 alone; the stashes' gold never counts toward it, and the shared stash's is never spent) is within
# NEAR_CAP of the cap (level x 10k, shop.py `gold_cap`). Before, a visit gambled at DUE_SPEND spendable wherever the
# gold stood: five sessions on 2026-10-22, each at ~470-550k carried of the 960k cap (probe.log 20:54-23:44), 0 rings
# kept.
# False: as before (DUE_SPEND far from the cap too)
NEAR_CAP_ONLY = True
# The margin: the carried gold rose ~280-330k an hour on 2026-10-22 (260k after the 22:15 session -> 475k at 23:01;
# 261k after that one -> 496k at 23:44) with a room trip every ~6.6 min of loop time, ~35-40k a visit to visit. 150k
# is about four visits' gold: a visit missed (a stop, a long level, an act boss's gold) still does not reach the cap,
# where gold is left on the ground and her sales stop (SALE_MOST 35k). The session then spends GAMBLE_SESSION_MOST
# (500k) from ~810k+, so the sessions come about once in 1.5 h, not every ~40 min; a wider margin would not make them
# rarer (the session's most sets that), a narrower one risks the cap
NEAR_CAP = 150_000
# The carried gold never gambled below: the game takes a price from the carried gold first, then the personal stash's
# (16:41:52 on 2026-10-21: carried 9,142 + personal stash 35,858 paid ring 5), and repairs use only the carried gold
# while potions keep 100k carried (shop.POTIONS_RESERVE). The 16:41 session left 8,309 carried. The player, 2026-10-21
# ~16:45, asked: "Keep 200k carried": gambling stops when the carried gold would go under it (the personal stash's gold
# is then not spent by gambling)
CARRIED_FLOOR = 200_000
# Window heights from her drawn point up to the middle of her menu's Gamble line, the line under Trade: Trade's middle
# is learned at 0.2296 (menu-lifts.json, 405), the lines LINE apart, the edge between them at 0.218 (history/shop.md);
# a click at 0.2174 opened Gamble (00:36:58 on 2026-10-17)
GAMBLE_ABOVE = 0.207
LIFTS_FILE = Path(__file__).resolve().parents[1] / 'runs' / 'alt-d' / 'gamble-lifts.json'  # the Gamble lifts that took
HITS_KEPT = 40
# vendorpanellayouthd.json `button_refresh` at (877, 1277) (read 2026-10-21; Repair All's place, its sprite 116 x 116):
# "VendorPanelMessage:RefreshAll", a new gamble stock (koolo clicks it when an item is not in the window)
REFRESH = (877 + 116 / 2, 1277 + 116 / 2)
REFRESHES_MOST = 3  # refreshes in a row that show no ring, at most
RINGS_MOST = 12  # rings bought a session, at most
SECONDS_MOST = 120.0  # a session's seconds at most (one ring ~2-3 s with its sale)
BATCH_MOST = 8  # rings bought before they are judged and the junk sold, at most (the free cells end a batch first)
KEPT_MOST = 4  # rings kept a session, at most: each keeps a cell until the next stash stop
STOCK_SECONDS = 2.0  # for her gamble stock to be read after its window shows (shop.py STOCK_SECONDS)
BOUGHT_SECONDS = 1.5  # for a ring bought to show in the inventory
SOLD_SECONDS = 1.5  # for a ring sold to leave it
GOLD_SECONDS = 1.0  # for the carried gold to settle after a purchase or a sale
GOLD_SETTLE = 0.25
# A ring's price came off the carried gold more than GOLD_SECONDS after the ring showed (14:26:09 on 2026-10-21: buy 2
# read "for 0 gold", gambling stopped as if the shared stash had paid; the next read, at the sale of ring 1, took the
# price: "sold ... for -42916"): the reads are waited on to move from the gold before the click. False: as before
GOLD_MOVE_SECONDS = 3.0
WAIT_GOLD_MOVE = True
TAB_SETTLE = 0.4
REFRESH_SECONDS = 1.5  # for the stock to change after a Refresh click
PANELS = frozenset(('inventory', 'npc_interact', 'npc_shop'))  # her gamble window's panels; any other stops it
PREFIX = 'Macro: gamble:'


@dataclass(frozen=True)
class Judged:
    """The keep rules' word on a ring bought: sold or kept, its title, why (`sell: ...` or `keep: ...` with the rule
    id), its stats as the game words them."""

    unit_id: int
    sell: bool
    title: str
    why: str
    stats: str = ''


Judge = Callable[[Sequence[Carried]], Mapping[int, Judged]]


@dataclass
class Gambled:
    """What a session did: rings bought, kept (titles), sold; gold spent on rings and brought back by sales; the
    carried and personal stash gold before and after; why it ended; its seconds; whether it was a dry run."""

    bought: int = 0
    kept: list[str] = field(default_factory=list)
    sold: int = 0
    paid: int = 0
    back: int = 0
    carried: tuple[int | None, int | None] = (None, None)
    bank: tuple[int | None, int | None] = (None, None)
    stop: str = ''
    seconds: float = 0.0
    dry: bool = False

    def said(self) -> str:
        kept = f' ({", ".join(self.kept)})' if self.kept else ''
        return (
            f'{self.bought} rings bought, {len(self.kept)} kept{kept}, {self.sold} sold; gold paid {self.paid}, back '
            f'{self.back}, spent {self.paid - self.back}; carried {self.carried[0]} -> {self.carried[1]}, personal '
            f'stash {self.bank[0]} -> {self.bank[1]}; {self.seconds:.1f} s; stop: {self.stop}'
            f'{" (dry run: nothing bought)" if self.dry else ""}'
        )


def _stat(run: Run, stat: int) -> int | None:
    """A stat of the character's (0 when the stats were read without it: the game lists no zero stat), None unread."""
    loot = run.reads.loot()
    return dict(loot.stats).get(stat, 0) if loot is not None and loot.stats else None


def carried_gold(run: Run) -> int | None:
    return _stat(run, GOLD_STAT)


def bank_gold(run: Run) -> int | None:
    """The personal stash tab's gold (stat 15); the shared stash's is not the character's stat."""
    return _stat(run, BANK_STAT)


def least() -> int:
    """The sum of the carried and personal stash gold a session leaves at least."""
    return max(GAMBLE_FLOOR, GOLD_RESERVE)


def spendable(carried: int | None, bank: int | None) -> int:
    """The gold a session may spend, carried and personal stash's alike: down to `least` of their sum and the carried
    gold down to CARRIED_FLOOR, GAMBLE_SESSION_MOST at most; 0 with a count unread."""
    if carried is None or bank is None:
        return 0
    carried_most = carried - CARRIED_FLOOR if CARRIED_FLOOR else carried + bank  # 0: the old sum alone
    return max(0, min(GAMBLE_SESSION_MOST, carried + bank - least(), carried_most))


def due(carried: int | None, bank: int | None, cap: int | None) -> str | None:
    """Why a town visit gambles now, None when it does not: GAMBLE on and a ring's worth `spendable` with the carried
    gold within NEAR_CAP of its cap (NEAR_CAP_ONLY); off, with it too near its cap for a sale (shop.py `restock` sells
    nothing past cap - SALE_MOST), or DUE_SPEND spendable."""
    if not GAMBLE or carried is None or cap is None:
        return None
    budget = spendable(carried, bank)
    if NEAR_CAP_ONLY:
        if carried + NEAR_CAP <= cap or budget < RING_PRICE:
            return None
        return f'carried gold {carried} within {NEAR_CAP} of the cap {cap}: {budget} to spend'
    capped = carried + SALE_MOST > cap
    if budget < RING_PRICE or (not capped and budget < DUE_SPEND):
        return None
    return f'carried gold {carried} of the cap {cap}, personal stash {bank}: {budget} to spend'


# -- The Gamble line --------------------------------------------------------------------------------------------


def hits() -> list[float]:
    try:
        kept = json.loads(LIFTS_FILE.read_text())
    except OSError, ValueError:
        return []
    return [float(lift) for lift in kept] if isinstance(kept, list) else []


def lifts() -> tuple[float, ...]:
    """The lifts the Gamble line is tried at, in turn: the middle of those that took, GAMBLE_ABOVE, a quarter line
    higher and lower (never as high as Trade's edge)."""
    took = hits()
    first = round((min(took) + max(took)) / 2, 4) if took else GAMBLE_ABOVE
    tried = (first, GAMBLE_ABOVE, GAMBLE_ABOVE + LINE / 4, GAMBLE_ABOVE - LINE / 4)
    return tuple(dict.fromkeys(round(lift, 4) for lift in tried))


def _learned(lift: float) -> None:
    """Kept apart from her Trade lifts (shop.py LIFTS_FILE, `menu_line` learns under the vendor alone)."""
    try:
        LIFTS_FILE.write_text(json.dumps([*hits(), round(lift, 4)][-HITS_KEPT:]))
    except OSError as error:
        LOG.info('%s the lift not kept: %s', PREFIX, error)


def _stock(run: Run) -> tuple[Stocked, ...] | None:
    """Her gamble stock once read (within STOCK_SECONDS), None when the window is her trade window (a key or a scroll
    in it) or nothing was read."""
    assert run.stock is not None
    found: list[tuple[Stocked, ...]] = [()]

    def read(_w) -> bool:
        assert run.stock is not None
        found[0] = run.stock(JAMELLA)
        return any(item.txt == RING for item in found[0]) or any(item.txt in (KEY, SCROLL) for item in found[0])

    began = run.clock()
    run.seen(read, STOCK_SECONDS)
    stock = found[0]
    LOG.info('%s her stock read %.2fs after the window: %d items by tab %s, rings %s', PREFIX, run.clock() - began,
             len(stock), dict(sorted(Counter(item.tab for item in stock).items())), _rings(stock))  # fmt: skip
    if not stock or any(item.txt in (KEY, SCROLL) for item in stock):
        return None
    return stock


def _rings(stock: Sequence[Stocked]) -> list[tuple[int, int, int, int]]:
    """The rings in her stock as (tab, x, y, unit), for the log."""
    return [(item.tab, item.x, item.y, item.unit_id) for item in stock if item.txt == RING]


def _open_gamble(run: Run, aspect: float) -> tuple[Stocked, ...]:
    """Her gamble window's stock: her menu opened (shop.py `_open_menu`) and its Gamble line clicked at each of
    `lifts` until a vendor window without a key or a scroll opens; the lift that took is kept. `Abort` with none."""
    for tried, lift in enumerate(lifts()):
        drawn = _open_menu(run, aspect)
        run.actuator.move(drawn[0], drawn[1] - lift, scatter=(6, 1))
        _note(run, aspect, f'the Gamble line clicked {lift:.4f} over Jamella')
        run.actuator.click()
        shown = run.seen(lambda w: 'npc_shop' in w.open_panels, PANEL_SECONDS)
        stock = _stock(run) if shown is not None else None
        if stock is not None:
            _learned(lift)
            return stock
        LOG.info('%s the Gamble line missed %.4f over her (try %d): %s', PREFIX, lift, tried + 1,
                 'no window' if shown is None else 'not her gamble window')  # fmt: skip
        _close(run)
    raise Abort('her gamble window did not open at any line tried')


# -- The session ------------------------------------------------------------------------------------------------


def _free(pack: Pack) -> int:
    return sum(row.count('.') for row in pack.inventory)


def _golds(run: Run) -> tuple[int | None, int | None]:
    return carried_gold(run), bank_gold(run)


def _settled(run: Run, moved_from: tuple[int | None, int | None] | None = None) -> tuple[int | None, int | None]:
    """The carried and personal stash gold once two reads GOLD_SETTLE apart agree (within GOLD_SECONDS): a price's
    two parts land apart. With `moved_from` (WAIT_GOLD_MOVE), first waited up to GOLD_MOVE_SECONDS for the reads to
    leave those values: a purchase's gold can show late."""
    if WAIT_GOLD_MOVE and moved_from is not None:
        began = run.clock()
        while _golds(run) == moved_from and run.clock() - began < GOLD_MOVE_SECONDS:
            run.pace.sleep(GOLD_SETTLE)
    last, began = _golds(run), run.clock()
    while run.clock() - began < GOLD_SECONDS:
        run.pace.sleep(GOLD_SETTLE)
        now = _golds(run)
        if now == last:
            return now
        last = now
    return last


def _sum(golds: tuple[int | None, int | None]) -> int | None:
    return None if golds[0] is None or golds[1] is None else golds[0] + golds[1]


class Session:
    """One gamble session at her open window (`gamble`): `run` buys, judges and sells until a stop."""

    def __init__(self, run: Run, rect, judge: Judge, stock: tuple[Stocked, ...], dry: bool) -> None:
        self.run, self.rect, self.judge, self.stock, self.dry = run, rect, judge, stock, dry
        self.began = run.clock()
        self.done = Gambled(dry=dry)
        self.tab: int | None = None  # the tab shown, once clicked
        self.batch: list[Carried] = []  # rings bought, not judged yet
        self.mine: set[int] = set()  # every unit this session bought: the only ones it may sell
        self.refreshes = 0  # refreshes in a row with no ring

    def go(self) -> str:
        """Buy, judge and sell until a stop; the stop's reason. The batch left is judged and its junk sold first."""
        while True:
            why = self._stop()
            if why is not None:
                break
            ring = self._ring()
            if ring is None:
                why = 'no ring in her stock after refreshes'
                break
            pack = self._pack()
            if not pack.inventory.has_room((1, 1)) or len(self.batch) >= BATCH_MOST:
                self._settle()
                pack = self._pack()
                if not pack.inventory.has_room((1, 1)):
                    why = 'no free inventory cell after the sales'
                    break
                continue
            if self.dry:
                self._plan(ring, pack)
                why = 'dry run'
                break
            why = self._buy(ring, pack)
            if why is not None:
                break
        if self.batch and not self._unexpected():
            self._settle()
        return why

    def _pack(self) -> Pack:
        assert self.run.carried is not None
        pack = self.run.carried()
        if pack is None:
            raise Abort('the inventory is not read')
        return pack

    def _unexpected(self) -> str | None:
        panels = set(self.run.world().open_panels)
        if 'npc_shop' not in panels:
            return f'her window closed (panels {sorted(panels)})'
        if panels - PANELS:
            return f'a panel opened: {", ".join(sorted(panels - PANELS))}'
        return None

    def _stop(self) -> str | None:
        """Why the session buys no more, None when it may buy a ring."""
        if why := self._unexpected():
            return why
        if self.run.clock() - self.began >= SECONDS_MOST:
            return f'{SECONDS_MOST:g} s'
        if self.done.bought >= RINGS_MOST:
            return f'{RINGS_MOST} rings'
        if len(self.done.kept) >= KEPT_MOST:
            return f'{KEPT_MOST} rings kept'
        carried, bank = carried_gold(self.run), bank_gold(self.run)
        if carried is None or bank is None:
            return 'the gold is not read'
        if self.done.paid - self.done.back + RING_PRICE > GAMBLE_SESSION_MOST:
            return f'the session spent {self.done.paid - self.done.back} of {GAMBLE_SESSION_MOST}'
        if carried + bank - RING_PRICE < least():
            return f'carried {carried} + personal stash {bank} would go under the floor {least()}'
        if CARRIED_FLOOR and carried - RING_PRICE < CARRIED_FLOOR:
            return f'carried {carried} would go under the carried floor {CARRIED_FLOOR}'
        return None

    def _ring(self) -> Stocked | None:
        """A ring in her stock, her Refresh clicked while none shows (REFRESHES_MOST in a row)."""
        assert self.run.stock is not None
        while True:
            self.stock = self.run.stock(JAMELLA) or self.stock
            ring = next((item for item in self.stock if item.txt == RING), None)
            if ring is not None:
                self.refreshes = 0
                return ring
            if self.refreshes >= REFRESHES_MOST or self.dry:
                return None
            self.refreshes += 1
            before = {item.unit_id for item in self.stock}
            self.run.actuator.move(*panel_point(self.rect, *REFRESH), scatter=(10, 10))
            LOG.info('%s no ring in her stock (%d items): Refresh clicked (%d)', PREFIX, len(self.stock),
                     self.refreshes)  # fmt: skip
            self.run.actuator.click()
            self.run.seen(lambda _w, b=before: self._changed(b), REFRESH_SECONDS)

    def _changed(self, before: set[int]) -> bool:
        """Whether her stock holds an item not in `before` (a refresh took)."""
        assert self.run.stock is not None
        return bool({item.unit_id for item in self.run.stock(JAMELLA)} - before)

    def _show_tab(self, tab: int) -> None:
        if self.tab == tab:
            return
        self.run.actuator.move(*panel_point(self.rect, *tab_point(tab)), scatter=(15, 5))
        self.run.actuator.click()
        self.run.pace.sleep(TAB_SETTLE)
        self.tab = tab

    def _plan(self, ring: Stocked, pack: Pack) -> None:
        """GAMBLE_DRY: the clicks a session would make, logged, none made."""
        point = cell_point(self.rect, VENDOR, (ring.x, ring.y))
        tab = panel_point(self.rect, *tab_point(ring.tab))
        LOG.info('%s dry: would click her tab %d at (%.4f, %.4f), then right click the Ring at her (%d, %d) (unit %d) '
                 'at (%.4f, %.4f) for ~%d gold; carried %s, personal stash %s, budget %d, %d cells free; junk sold by '
                 'Ctrl + click on its inventory cell; Refresh at (%.4f, %.4f)', PREFIX, ring.tab, *tab, ring.x, ring.y,
                 ring.unit_id, *point, RING_PRICE, carried_gold(self.run), bank_gold(self.run),
                 spendable(carried_gold(self.run), bank_gold(self.run)), _free(pack),
                 *panel_point(self.rect, *REFRESH))  # fmt: skip

    def _buy(self, ring: Stocked, pack: Pack) -> str | None:
        """Right click `ring`, checked by a new ring in the inventory and its price out of the carried and personal
        stash gold (`_unread_price`); why the session stops, None when it goes on."""
        run = self.run
        self._show_tab(ring.tab)
        had = {item.unit_id for item in pack.items}
        gold, bank = carried_gold(run), bank_gold(run)
        point = cell_point(self.rect, VENDOR, (ring.x, ring.y))
        number = self.done.bought + 1
        LOG.info('%s buy %d: the Ring at her (%d, %d) tab %d (unit %d), right click at (%.4f, %.4f); carried %s, '
                 'personal stash %s, %d cells free', PREFIX, number, ring.x, ring.y, ring.tab, ring.unit_id, *point,
                 gold, bank, _free(pack))  # fmt: skip
        run.actuator.move(*point, scatter=(5, 5))
        run.actuator.tap('Button3')
        found: list[Carried] = []

        def came(_w) -> bool:
            assert run.carried is not None
            now = run.carried()
            found[:] = [i for i in (now.items if now is not None else ()) if i.unit_id not in had]
            return bool(found)

        if run.seen(came, BOUGHT_SECONDS) is None:
            return f'buy {number}: nothing came into the inventory'
        after, bank_after = _settled(run, (gold, bank))
        before_sum, after_sum = _sum((gold, bank)), _sum((after, bank_after))
        paid = before_sum - after_sum if before_sum is not None and after_sum is not None else None
        new = found[0]
        self.mine.add(new.unit_id)
        self.done.bought += 1
        self.done.paid += paid or 0
        LOG.info('%s bought %d: unit %d (class %d, quality %d) at (%d, %d) for %s gold (expected %d); carried %s, '
                 'personal stash %s, %d cells free', PREFIX, number, new.unit_id, new.txt, new.quality, new.x, new.y,
                 paid, RING_PRICE, after, bank_after, _free(self._pack()))  # fmt: skip
        if len(found) > 1 or new.txt != RING:
            return f'buy {number}: {len(found)} items came, class {new.txt}: not a ring alone'
        self.batch.append(new)
        if paid is None or abs(paid - RING_PRICE) > PRICE_DRIFT * RING_PRICE:
            return self._unread_price(number, paid, (gold, bank), (after, bank_after))
        return None

    def _unread_price(self, number: int, paid: int | None, before: tuple, after: tuple) -> str:
        """A price stats 14 and 15 do not show: said loudly (the log's warning, the card), the session's stop."""
        why = (
            f'buy {number}: the price was not from the carried or the personal stash gold: they fell by {paid}, a ring '
            f'costs {RING_PRICE} (carried {before[0]} -> {after[0]}, personal stash {before[1]} -> {after[1]})'
        )
        LOG.warning("%s %s: gold no stat shows may have paid it (the shared stash's?): gambling stopped", PREFIX, why)
        self.run.say(f'Gamble stopped: ring {number} not paid from carried or personal stash gold (shared stash?)')
        return why

    def _settle(self) -> None:
        """The batch judged by the keep rules; the junk sold, the rest kept (no read: kept)."""
        batch, self.batch = self.batch, []
        try:
            verdicts = self.judge(batch)
        except Exception as error:  # the reads or the KB failing: nothing sold (S8)
            LOG.info('%s the keep rules failed (%s: %s): %d rings kept', PREFIX, type(error).__name__, error,
                     len(batch))  # fmt: skip
            verdicts = {}
        for ring in batch:
            verdict = verdicts.get(ring.unit_id)
            if verdict is None:
                LOG.info('%s judged: Ring unit %d at (%d, %d): keep: no appraisal (S8)', PREFIX, ring.unit_id, ring.x,
                         ring.y)  # fmt: skip
                self.done.kept.append(f'ring {ring.unit_id} (no appraisal)')
                continue
            LOG.info('%s judged: %s (unit %d at (%d, %d)): %s; stats: %s', PREFIX, verdict.title, ring.unit_id,
                     ring.x, ring.y, verdict.why, verdict.stats or '-')  # fmt: skip
            if not verdict.sell or not self._sell(ring, verdict.title):
                self.done.kept.append(verdict.title)

    def _sell(self, ring: Carried, title: str) -> bool:
        """Sell `ring` (this session's, still where it came) by a Ctrl + click; whether it went. `Abort` when another
        item left the inventory."""
        run = self.run
        if ring.unit_id not in self.mine:
            LOG.info('%s %s (unit %d) is not one this session bought: never sold', PREFIX, title, ring.unit_id)
            return False
        if why := protected(run, ring):
            LOG.info('%s %s (unit %d) is %s: never sold', PREFIX, title, ring.unit_id, why)
            return False
        gold, cap = carried_gold(run), gold_cap(run)
        if gold is None or cap is None or gold + SALE_MOST > cap:
            LOG.info('%s %s kept: carried %s of the cap %s, no sale over it', PREFIX, title, gold, cap)
            return False
        now = self._pack()
        if all((i.unit_id, i.x, i.y) != (ring.unit_id, ring.x, ring.y) for i in now.items):
            LOG.info('%s %s (unit %d) is no longer at (%d, %d): not sold', PREFIX, title, ring.unit_id, ring.x, ring.y)
            return False
        others = {i.unit_id for i in now.items} - {ring.unit_id}
        run.actuator.move(*cell_point(self.rect, INVENTORY, (ring.x, ring.y), ring.size), scatter=(5, 5))
        run.actuator.click('Control_L')

        def gone(_w) -> bool:
            assert run.carried is not None
            pack = run.carried()
            return pack is not None and all(i.unit_id != ring.unit_id for i in pack.items)

        took = run.seen(gone, SOLD_SECONDS) is not None
        after = _settled(run, (gold, bank_gold(run)))[0] if took else carried_gold(run)
        back = after - gold if took and after is not None else 0
        self.done.back += back
        self.done.sold += int(took)
        left = self._pack()
        LOG.info('%s %s %s (unit %d) at (%d, %d)%s; carried %s, %d cells free', PREFIX,
                 'sold' if took else 'could not sell', title, ring.unit_id, ring.x, ring.y,
                 f' for {back} gold' if took else '', after, _free(left))  # fmt: skip
        if others - {i.unit_id for i in left.items}:
            raise Abort(f'an item other than the ring sold left the inventory at ({ring.x}, {ring.y})')
        return took


def gamble(run: Run, judge: Judge) -> Gambled:
    """One gamble session at Jamella (mouse mode, in her town): walk to her, open her gamble window, buy rings, judge
    them (`judge`, live `keep_rules`), sell the junk, until a stop (`Session._stop`); her window closed after. A session
    with nothing to spend opens nothing. `Abort` when a step does not take."""
    if run.pad is not None:
        raise Abort('gambling needs mouse mode')
    if run.carried is None or run.stock is None:
        raise Abort('the gamble cannot be read')
    rect = run.actuator.keys.focused_window_rect()
    if rect is None:
        raise Abort('no game window')
    dry = GAMBLE_DRY
    carried, bank, cap = carried_gold(run), bank_gold(run), gold_cap(run)
    budget = spendable(carried, bank)
    LOG.info('%s session: carried %s (cap %s), personal stash %s, floor %d (reserve %d), %d to spend (session most '
             '%d)%s', PREFIX, carried, cap, bank, GAMBLE_FLOOR, GOLD_RESERVE, budget, GAMBLE_SESSION_MOST,
             ', dry' if dry else '')  # fmt: skip
    began = run.clock()
    done = Gambled(carried=(carried, carried), bank=(bank, bank), dry=dry)
    if budget < RING_PRICE:
        done.stop = f'{budget} to spend, under a ring'
        LOG.info('%s session done: %s', PREFIX, done.said())
        return done
    aspect = rect[2] / rect[3]
    with serving(JAMELLA):
        walk_until(run, whereabouts, SEEN, 'Jamella')
        run.seen(lambda w: w.player is not None and w.player.mode not in WALKING, WALK_SECONDS)
        try:
            session = Session(run, rect, judge, _open_gamble(run, aspect), dry)
            stop = session.go()
        finally:
            _close(run)
    done = session.done
    done.stop = stop
    done.carried = (carried, carried_gold(run))
    done.bank = (bank, bank_gold(run))
    done.seconds = run.clock() - began
    LOG.info('%s session done: %s', PREFIX, done.said())
    run.say(f'Gamble: {done.bought} rings, {len(done.kept)} kept, gold {done.carried[1]}')
    return done


# -- The keep rules, live ---------------------------------------------------------------------------------------


def _stats(observation: Mapping | None) -> str:
    """An identify read's stat lines, as the game words them, for the log."""
    rows = observation.get('decoded_stats', ()) if observation is not None else ()
    return '; '.join(str(row.get('text')) for row in rows if isinstance(row, Mapping) and row.get('text'))


def keep_rules(appraise: Callable[[list[int]], object] | None, assessor: Callable[[], Assessor] | None = None) -> Judge:
    """The live judge: the identify worker's read and KB lookup of the rings now (`appraise`, runner.py
    `MacroRunner.appraise`, noted into loot/shadow.py BOOK), then the one entry point at GAMBLE (`assessor`, live
    loot/assess.py `live`: the town visit's decision, keep.py `decide` under the town's guards, the owned copies from
    the collection). A ring with no read is kept (S8)."""

    def judge(rings: Sequence[Carried]) -> dict[int, Judged]:
        # here: the loot layers import the macros (loot/value.py `CollectionCopies`)
        from inventory_tracking.loot.assess import Outcome, Site, carried_facts, live, shadow
        from inventory_tracking.loot.facts import Owner
        from inventory_tracking.loot.shadow import BOOK

        began = time.monotonic()
        if appraise is not None and rings:
            appraise([ring.unit_id for ring in rings])
        judging = (assessor or live)()
        reads = {ring.unit_id: (entry.observation if (entry := BOOK.get(ring.unit_id)) is not None else None)
                 for ring in rings}  # fmt: skip
        if not ASSESSED:
            old = _town_judged(rings, judging.copies.copies)
            LOG.info('%s %d rings judged in %.2f s', PREFIX, len(rings), time.monotonic() - began)
            return {unit: replace(judged, stats=_stats(reads.get(unit))) for unit, judged in old.items()}
        found = judging.assess_all([carried_facts(ring, Owner.LOOP, BOOK) for ring in rings], Site.GAMBLE)
        try:  # the shadow: never in the way of the entry point's decision
            old = _town_judged(rings, judging.copies.copies)
        except Exception as error:
            LOG.info('%s the old keep rules failed (%s: %s): no shadow', PREFIX, type(error).__name__, error)
            old = {}
        LOG.info('%s %d rings judged in %.2f s', PREFIX, len(rings), time.monotonic() - began)
        judged = {}
        for assessment in found:
            unit, sold = assessment.facts.unit_id, assessment.outcome == Outcome.VENDOR
            was = old.get(unit)
            shadow(('gamble', unit), Site.GAMBLE, assessment.facts.title(), 'sell' if sold else 'keep',
                   'sell' if was is not None and was.sell else 'keep', new_decides=True)  # fmt: skip
            why = f'{"sell" if sold else "keep"}: {assessment.why} [rule {assessment.rule}]'
            judged[unit] = Judged(unit, sold, assessment.facts.title(), why, _stats(reads.get(unit)))
        return judged

    return judge


def _town_judged(
    rings: Sequence[Carried], copies: Callable[[ItemFacts], Sequence[ItemFacts] | None]
) -> dict[int, Judged]:
    """The rings judged by loot/api.py `town_verdicts` over BOOK (`keep_rules` before the entry point). Legacy until
    ASSESSED is proven: the switch-off path and the shadow."""
    from inventory_tracking.loot import api as loot_api
    from inventory_tracking.loot.facts import Owner, from_carried
    from inventory_tracking.loot.shadow import BOOK
    from inventory_tracking.loot.value import appraise_result

    items: list[tuple[ItemFacts, Value | None]] = []
    for ring in rings:
        entry = BOOK.get(ring.unit_id)
        facts = from_carried(ring, owner=Owner.LOOP, observation=entry.observation if entry is not None else None)
        items.append((facts, appraise_result(facts, entry.result, entry.verdict) if entry is not None else None))
    return {
        verdict.facts.unit_id: Judged(
            verdict.facts.unit_id,
            verdict.sold,
            verdict.facts.title(),
            f'{verdict.said()} [rule {verdict.decision.rule if verdict.decision is not None else "-"}]',
        )
        for verdict in loot_api.town_verdicts(items, copies)
    }
