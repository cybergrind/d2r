"""Halbu's Repair All in Pandemonium Fortress: the Teleport staff's charges (and worn gear) back for gold.

The player, 2026-10-17: "we can start thinking on repairing teleport charges and getting some money, to travel more
efficiently". `wants`/`due` decide a visit; `repair` walks to Halbu, opens his Trade/Repair line (shop.py `menu_line`),
reads the quoted cost off the Repair All tooltip (OCR) and clicks only when the carried gold covers it. Tuning history:
history/repair.md.
"""

import re
import subprocess
import time
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.game.layout import GOLD_STAT
from inventory_tracking.game.records import Teleport, Wear, World
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.shop import (
    LINE,
    PANEL_SECONDS,
    WALK_SECONDS,
    WALKING,
    _close,
    _waypoint,
    known,
    menu_line,
    serving,
    walk_until,
    whereabouts,
)
from inventory_tracking.macros.waypoint import panel_point


__all__ = ['HALBU', 'REPAIR_BELOW', 'WEAR_BELOW', 'WEAR_CARRIED', 'back', 'due', 'repair', 'wants', 'worn_out']

HALBU = 257  # monstats *hcIdx
# Of the staff's maximum charges, for a visit of its own; a trade session tops it up anyway (loop.py `topped`)
REPAIR_BELOW = 0.2
WEAR_BELOW = 0.4  # of a worn item's durability, for a visit of its own (Enigma's Teleport leaves the staff full)
WEAR_CARRIED = 200_000  # carried for a durability-only repair: no quote to check its read cost against
RETRY_GAMES = 3  # games before a visit that raised nothing is tried again
HIS_SEEN = (0.1, 0.9, 0.42, 0.8)  # window fractions he is walked to be drawn within: his menu is high over him
# vendorpanellayouthd.json `button_repair_all` at (877, 1277), sprite 116 x 116: layout units, the button's middle
REPAIR_ALL = (877 + 116 / 2, 1277 + 116 / 2)
WAYPOINT_SEEN = (0.15, 0.85, 0.15, 0.8)  # window fractions the waypoint is walked to be drawn within (shop.py)
REPAIR_SECONDS = 2.0  # for the charges to show the repair
GOLD_SETTLE_SECONDS = 2.0  # for the gold stats to show it after the charges
LIFT: list[float] = []  # the lift that opened his panel last
QUOTED: list[int] = []  # the cost the game quoted at the last visit: none again before the carried gold covers it


# A vendor takes what the carried gold does not cover from the stash's (D2MOO SUnitNpc.cpp 1782-1795: STAT_GOLDBANK).
# The player, 2026-10-17: "you can repair only on collected gold in the inventory". STASH_TOUCHED turns repairs off.
GOLDBANK = 15  # itemstatcost.txt `goldbank`: the stash's gold
# The share of the carried gold a repair may cost (0.9 and 0.98 refused real repairs on 2026-10-17)
CARRIED_SHARE = 0.99
UNREAD_COVER, UNREAD_EXTRA = 2.0, 50_000  # an unread cost is safe with this many times the expected, and more, carried
QUOTE_DRIFT = 0.25  # the share a read cost may differ from the last quote by and be trusted
TOOLTIP_SECONDS = 0.6  # for the button's tooltip to show
TOOLTIP_BAND = (720, 90)  # screen pixels: the band read for the cost, across the pointer
TOOLTIP_ABOVE = 100  # its top over the pointer (the tooltip's line is 30 to 65 over it)
PAGE_MODES = ('7', '6', '13')  # tesseract page modes in turn: a line alone missed costs a block (6) read
# English data for tesseract: the system's has none
TESSDATA = Path(__file__).resolve().parents[2] / 'tmp' / 'item-ocr' / 'tessdata'
QUOTE_FILE = Path(__file__).resolve().parents[1] / 'runs' / 'alt-d' / 'repair-quote.txt'
STASH_TOUCHED = Path(__file__).resolve().parents[1] / 'runs' / 'alt-d' / 'repair-touched-stash.txt'


def quote() -> int | None:
    """The cost the game quoted last (QUOTE_FILE survives restarts), None none."""
    if not QUOTED:
        try:
            QUOTED[:] = [int(word) for word in QUOTE_FILE.read_text().split()[:2]]
        except OSError, ValueError:
            return None
    return QUOTED[0] if QUOTED else None


def per_charge() -> float | None:
    """The gold a charge cost at the last quote, None unknown."""
    quote()
    return QUOTED[0] / QUOTED[1] if len(QUOTED) > 1 and QUOTED[1] > 0 else None


def expected(missing: int) -> int | None:
    """The cost to expect for `missing` charges (it scales with them), else the last quote."""
    rate = per_charge()
    return round(rate * missing) if rate is not None and missing > 0 else quote()


def covered(expected_cost: int | None, coins: int | None) -> bool:
    """Whether an unread cost is safe to pay: the carried gold far over the expected one (OCR misses it daily)."""
    return expected_cost is not None and coins is not None and coins >= UNREAD_COVER * expected_cost + UNREAD_EXTRA


def worn_out(wear: Wear | None) -> bool:
    """Whether a worn item is under WEAR_BELOW of its durability (never with STASH_TOUCHED)."""
    return not STASH_TOUCHED.exists() and wear is not None and wear.share < WEAR_BELOW


def worn_text(wear: Wear | None) -> str:
    return f'{wear.durability}/{wear.maximum} (class {wear.txt})' if wear is not None else '?'


def affordable(coins: int | None) -> bool:
    """Whether the carried gold covers the cost last quoted (none quoted: a visit tells)."""
    cost = quote()
    return cost is None or (coins is not None and cost <= coins * CARRIED_SHARE)


def wants(staff: Teleport | None) -> bool:
    """Whether the staff's charges are low enough for a repair (never with STASH_TOUCHED)."""
    return (
        not STASH_TOUCHED.exists()
        and staff is not None
        and staff.maximum > 0
        and staff.charges < staff.maximum * REPAIR_BELOW
    )


def due(
    staff: Teleport | None, wear: Wear | None, coins: int | None, *, top_up: bool = False, waited: bool = True
) -> bool:
    """Whether Halbu is visited: charges low or missing in a `top_up`, and affordable; a worn item with WEAR_CARRIED;
    or his line unlearned. Never before `waited`."""
    charged = (wants(staff) or top_up) and affordable(coins)
    mends = worn_out(wear) and coins is not None and coins >= WEAR_CARRIED
    return (charged or mends or ((staff is not None or wear is not None) and unknown())) and waited


def lifts() -> tuple[float, ...]:
    """The lifts over his drawn point his Trade/Repair line is tried at: the learned one and half a LINE either side
    (a wide scan once spent 34 s), else from 0.22 up (he is taller than Jamella)."""
    learned_lift = known(HALBU)
    if learned_lift:
        near = (learned_lift, learned_lift + LINE / 2, learned_lift - LINE / 2)
        return tuple(dict.fromkeys(round(lift, 4) for lift in near))
    scan = tuple(0.22 + step * LINE / 2 for step in range(10))
    return tuple(dict.fromkeys(round(lift, 4) for lift in scan))


def unknown() -> bool:
    """Whether his line is still to be learned."""
    return known(HALBU) is None


def gold(run: Run, stat: int = GOLD_STAT) -> int | None:
    """The carried gold (`GOLDBANK`: the stash's), None unread."""
    loot = run.reads.loot()
    if loot is None or not loot.stats:
        return None
    return dict(loot.stats).get(stat)


def quoted(run: Run, rect) -> int | None:
    """The cost on the Repair All tooltip (ui.json strThisShouldBeIn104) by tesseract, only the tooltip's band (wider
    reads noise); None unread. The pointer is on the button."""
    run.pace.sleep(TOOLTIP_SECONDS)
    pointer = run.actuator.keys.pointer()
    if pointer is None:
        return None
    left, top = max(rect[0], pointer[0] - TOOLTIP_BAND[0] // 2), max(rect[1], pointer[1] - TOOLTIP_ABOVE)
    path = Path(__file__).resolve().parents[1] / 'runs' / 'alt-d' / f'repair-{time.strftime("%H%M%S")}.png'
    try:
        size = f'{TOOLTIP_BAND[0]}x{TOOLTIP_BAND[1]}'
        subprocess.run(['grim', '-g', f'{left},{top} {size}', str(path)], timeout=3, check=True, capture_output=True)
        text = ''
        for psm in PAGE_MODES:
            text = subprocess.run(
                ['tesseract', str(path), 'stdout', '--psm', psm, '--tessdata-dir', str(TESSDATA)],
                timeout=10,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            if cost_of(text) is not None:
                break
    except (OSError, subprocess.SubprocessError) as error:
        LOG.info('Macro: repair: the cost not read: %s', error)
        return None
    LOG.info('Macro: repair: the tooltip read %r (%s)', ' '.join(text.split())[:120], path.name)
    return cost_of(text)


# Letters the game's font makes of digits within a word of digits ("1Q1677", "5@548" on 2026-10-17)
LOOKALIKES = str.maketrans(
    {
        'O': '0',
        'Q': '0',
        'D': '0',
        'o': '0',
        '@': '0',
        'Ø': '0',
        'ø': '0',
        'I': '1',
        'l': '1',
        '|': '1',
        'S': '5',
        'B': '8',
    }
)


def cost_of(text: str) -> int | None:
    """The tooltip text's last number of four digits and more, LOOKALIKES read as digits; None with none."""
    text = ' '.join(
        word.translate(LOOKALIKES) if sum(c.isdigit() for c in word) >= 2 else word for word in text.split()
    )
    numbers = re.findall(r'\d[\d,.]{3,}', text)
    digits = re.sub(r'\D', '', numbers[-1]) if numbers else ''
    return int(digits) if digits else None


def repair(run: Run, fix: bool = True) -> bool:
    """Halbu's Repair All (mouse mode); whether charges or durability rose. Not `fix`: only learn his line."""
    if run.pad is not None:
        raise Abort('the repair needs mouse mode')
    before = run.reads.teleport()
    worn = run.reads.wear()
    coins = gold(run)
    rect = run.actuator.keys.focused_window_rect()
    if (before is None and worn is None) or rect is None:
        raise Abort('no staff with Teleport charges and no worn item read, or no game window')
    aspect = rect[2] / rect[3]
    charges = f'{before.charges}/{before.maximum}' if before is not None else '?'
    run.say(f'Repair: the staff at {charges} charges, the most worn item {worn_text(worn)}, {coins} gold')
    bank = gold(run, GOLDBANK)
    with serving(HALBU):

        def place(world: World) -> tuple[float, float] | None:
            return whereabouts(world)  # his usual place when out of the units' reach (shop.py USUAL)

        walk_until(run, place, HIS_SEEN, 'Halbu')  # low enough on the screen for his menu over him
        run.seen(lambda w: w.player is not None and w.player.mode not in WALKING, WALK_SECONDS)
        try:
            try:
                menu_line(
                    run, aspect, 'Trade/Repair', lifts(),
                    lambda _lift: run.seen(lambda w: 'npc_shop' in w.open_panels, PANEL_SECONDS) is not None,
                    picture=True,
                )  # fmt: skip
            except Abort:
                raise Abort("Halbu's vendor panel did not open at any line tried") from None
            if not fix:
                LOG.info('Macro: repair: his panel opened; repairs are off: nothing clicked in it')
                return False
            run.actuator.move(*panel_point(rect, *REPAIR_ALL), scatter=(10, 10))
            missing = before.maximum - before.charges if before is not None else 0
            cost, last = quoted(run, rect), expected(missing) if missing else None
            if cost is not None and last is not None and abs(cost - last) > QUOTE_DRIFT * last:
                # A misread lowering the cost would pass the check below and spend the stash's gold
                LOG.info('Macro: repair: the read cost %d is far from the %d expected for %d charges: not trusted',
                         cost, last, missing)  # fmt: skip
                cost = None
            if cost is not None and missing:
                QUOTED[:] = [cost, missing]
                QUOTE_FILE.write_text(f'{cost} {missing}')
            if cost is not None and not missing and (coins is None or coins < WEAR_CARRIED):
                LOG.info('Macro: repair: %d for the durability alone, %s carried: not under the %d it needs',
                         cost, coins, WEAR_CARRIED)  # fmt: skip
                return False
            if cost is None and missing and covered(last, coins):
                LOG.info('Macro: repair: the cost unread; %s expected for %d charges, %s carried: repaired', last,
                         missing, coins)  # fmt: skip
                cost = last
            if cost is None or coins is None or cost > coins * CARRIED_SHARE:
                LOG.info('Macro: repair: the cost %s is not within %.0f%% of the carried %s gold: no repair',
                         cost, 100 * CARRIED_SHARE, coins)  # fmt: skip
                return False
            run.actuator.click()

            def rose(_: World) -> bool:
                now = run.reads.teleport()
                if before is not None and now is not None and now.charges > before.charges:
                    return True
                mended = run.reads.wear()
                return worn is not None and (mended is None or mended.share > worn.share)

            took = run.seen(rose, REPAIR_SECONDS) is not None
            if took and coins is not None:
                # The gold lands after the charges, in steps: most of the cost gone before the stash's check
                least = coins - (1 - QUOTE_DRIFT) * cost
                run.seen(lambda _w: (gold(run) or coins) <= least, GOLD_SETTLE_SECONDS)
        finally:
            _close(run)
    after = run.reads.teleport()
    mended = run.reads.wear()
    left, banked = gold(run), gold(run, GOLDBANK)
    if took and coins is not None and left == coins:
        LOG.warning('Macro: repair: the carried gold did not move (%s)', coins)
    if bank is not None and banked is not None and banked < bank:
        STASH_TOUCHED.write_text(f'{bank} -> {banked}\n')
        LOG.error('Macro: repair: the stash gold went %d -> %d: repairs are off for good (%s)', bank, banked,
                  STASH_TOUCHED)  # fmt: skip
    LOG.info(
        'Macro: repair: the staff %s -> %s charges (of %s), the most worn item %s -> %s, gold %s -> %s',
        before.charges if before is not None else None, after.charges if after is not None else None,
        before.maximum if before is not None else None, worn_text(worn), worn_text(mended), coins, left,
    )  # fmt: skip
    run.say(f'Repair: {after.charges if after is not None else "?"} charges, {left} gold')
    return took


def back(run: Run) -> None:
    """Walk back toward the waypoint: from beside Halbu no aim reaches it."""
    try:
        walk_until(run, _waypoint(run), WAYPOINT_SEEN, 'the waypoint')
    except Abort as stop:
        LOG.info('Macro: repair: back toward the waypoint: %s', stop)
