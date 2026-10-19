"""The Teleport staff's charges back by a repair at Halbu (the KP_6 loop's leg in Pandemonium Fortress).

The player, 2026-10-17: "we can start thinking on repairing teleport charges and getting some money, to travel more
efficiently". A repair refills a charged item's charges and costs gold; the loop's level run spares the staff (travel.py
`LOOPED`: Blade Warp first, Teleport where it does not reach, the last charges kept), so more charges are faster runs.

When: in Pandemonium Fortress before the way to the chests, the staff under REPAIR_BELOW of its maximum charges
(`wants`); not again for RETRY_GAMES games after a visit that did not raise them (no gold, a click off).

The steps (`repair`): Halbu (monstats *hcIdx 257, shop/capture.py VENDORS) walked to and his menu opened as Jamella's
is (shop.py, `serving`); his Trade/Repair line clicked at each of `lifts` until his vendor panel shows (his menu has a
line fewer than hers, Gamble: the line is not where hers is, so a lift a line lower is tried first); the panel's Repair
All button clicked (the game's vendorpanellayouthd.json, read 2026-10-17: `button_repair_all` at (877, 1277) in the left
panel, its sprite 116 x 116 a frame); the charges read again; his windows closed. The gold before and after is said.
"""

import re
import subprocess
import time
from pathlib import Path

from inventory_tracking.common import LOG
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
from inventory_tracking.macros.world import GOLD_STAT, Teleport, Wear, World


__all__ = ['HALBU', 'REPAIR_BELOW', 'WEAR_BELOW', 'WEAR_CARRIED', 'back', 'due', 'repair', 'wants', 'worn_out']

HALBU = 257
# Of the staff's maximum charges, for a visit of its own: with Teleport in the loop's moves (~7.5 charges a stay) the
# visits at half cost 3.9 s a cycle (15:28-15:43 on 2026-10-17); a trade session tops it up anyway (macros/loop.py
# `topped`), so a visit of its own waits for under 30% (21 of 69: ~1.5 stays over the 10 kept, travel.py LOW_CHARGES)
# 0.3 → 0.2 at 17:25: each errand is a whole session (loop.py `errand`); 14 of 69 still keeps a stay over the 10
REPAIR_BELOW = 0.2
# Of a worn item's durability, for a visit of its own: Teleport of the character's own (Enigma, 22:26 on 2026-10-17)
# leaves the staff's charges full, and their repairs had been what mended the rest of the gear on the way. Enigma read
# 33 of 60 then; at none an item gives nothing (its Teleport gone with it)
WEAR_BELOW = 0.4
# A repair for durability alone has no cost to expect (the quotes are the charges', `expected`): only a cost read off
# the tooltip is paid, and only with this much carried, so that a digit lost to the OCR cannot reach the stash's gold
WEAR_CARRIED = 200_000
RETRY_GAMES = 3  # with Teleport in the moves the charges run out in about three games (16:32 on 2026-10-17)
HIS_SEEN = (0.1, 0.9, 0.42, 0.8)  # window fractions he is walked to be drawn within: his menu is high over him
REPAIR_ALL = (877 + 116 / 2, 1277 + 116 / 2)  # layout units in the left panel: the Repair All button's middle
WAYPOINT_SEEN = (0.15, 0.85, 0.15, 0.8)  # window fractions the waypoint is walked to be drawn within (shop.py)
REPAIR_SECONDS = 2.0  # for the charges to show the repair
GOLD_SETTLE_SECONDS = 2.0  # for the gold stats to show it after the charges
LIFT: list[float] = []  # the lift that opened his panel last
QUOTED: list[int] = []  # the cost the game quoted at the last visit: none again before the carried gold covers it


# A vendor takes what the carried gold does not cover from the stash's (D2MOO SUnitNpc.cpp 1782-1795: STAT_GOLDBANK),
# so the game's quoted cost is read before the click (`quoted`); the player, 2026-10-17: "you can repair only on
# collected gold in the inventory". STASH_TOUCHED turns repairs off if the stash's gold ever moves.
GOLDBANK = 15  # itemstatcost.txt `goldbank`: the stash's gold
# The share of the carried gold a repair may cost: under it the vendor takes nothing from the stash's. 0.9 refused
# 101,803 with 107,753 carried (12:41:43 on 2026-10-17), 0.98 102,206 with 104,270 (13:12:13); a misread cost is caught
# by the quote's gold a charge, and a last digit read wrong is under the 1% left
CARRIED_SHARE = 0.99
UNREAD_COVER, UNREAD_EXTRA = 2.0, 50_000  # an unread cost is safe with this many times the expected, and more, carried
QUOTE_DRIFT = 0.25  # the share a read cost may differ from the last quote by and be trusted
TOOLTIP_SECONDS = 0.6  # for the button's tooltip to show
TOOLTIP_BAND = (720, 90)  # screen pixels: the band read for the cost, across the pointer
TOOLTIP_ABOVE = 100  # its top over the pointer (the tooltip's line is 30 to 65 over it)
# tesseract's page modes tried in turn: a line (7) read nothing of "Repair all equipment: 101803" at 12:39:19 on
# 2026-10-17, where a block (6) read the number in all twelve pictures kept that day, and 13 (a raw line) too
PAGE_MODES = ('7', '6', '13')
# English data for tesseract: the system's has none (/usr/share/tessdata held afr and osd on 2026-10-17)
TESSDATA = Path(__file__).resolve().parents[2] / 'tmp' / 'item-ocr' / 'tessdata'
QUOTE_FILE = Path(__file__).resolve().parents[1] / 'runs' / 'alt-d' / 'repair-quote.txt'
STASH_TOUCHED = Path(__file__).resolve().parents[1] / 'runs' / 'alt-d' / 'repair-touched-stash.txt'


def quote() -> int | None:
    """The cost the game quoted last (QUOTE_FILE: kept across restarts of the service), None none."""
    if not QUOTED:
        try:
            QUOTED[:] = [int(word) for word in QUOTE_FILE.read_text().split()[:2]]
        except OSError, ValueError:
            return None
    return QUOTED[0] if QUOTED else None


def per_charge() -> float | None:
    """The gold a charge cost at the last quote (QUOTE_FILE's second word: the charges it was for), None unknown."""
    quote()
    return QUOTED[0] / QUOTED[1] if len(QUOTED) > 1 and QUOTED[1] > 0 else None


def expected(missing: int) -> int | None:
    """The cost to look for with `missing` charges to refill: the last quote's gold a charge times them, else the
    last quote (the cost is the charges': 62,918 for 37 at 12:08:37 on 2026-10-17, 101,677 for 60 at 12:04:09)."""
    rate = per_charge()
    return round(rate * missing) if rate is not None and missing > 0 else quote()


def covered(expected_cost: int | None, coins: int | None) -> bool:
    """Whether an unread cost is safe to pay: the carried gold far over any cost the charges missing can come to
    (UNREAD_COVER times the expected and UNREAD_EXTRA more), so the vendor takes none of the stash's (it takes only what
    the carried gold does not cover; the check after a repair still turns repairs off if the stash's gold moved). OCR
    read "Tae ee" from a clear "Repair all equipment: 47449" at 16:25:12 on 2026-10-17, eight such misses that day."""
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
    """Whether Halbu is visited: the staff's charges low (`wants`) or, in a visit, any missing (`top_up`: town.py
    `tops_up`) with the carried gold covering the cost; a worn item low on durability (its repair of its own, the
    staff's charges full: Teleport of the character's own) with WEAR_CARRIED carried; his line not learned yet
    (`unknown`: his panel only opened, no gold spent); none for RETRY_GAMES games after a visit that raised nothing
    (`waited`)."""
    charged = (wants(staff) or top_up) and affordable(coins)
    mends = worn_out(wear) and coins is not None and coins >= WEAR_CARRIED
    return (charged or mends or ((staff is not None or wear is not None) and unknown())) and waited


def lifts() -> tuple[float, ...]:
    """The lifts over his drawn point (as his menu opened) his Trade/Repair line is clicked at: the learned one, then
    from 0.22 up by half a line (LINE). He is taller than Jamella, and his menu with him: none of four clicks 0.184 to
    0.218 over him took (01:50 on 2026-10-17)."""
    learned_lift = known(HALBU)
    if learned_lift:
        # Learned: it and half a line either side only. Ten lifts all failed at 16:31:30-16:32:02 on 2026-10-17 (34 s,
        # the menu open each time, the character two units from him); the learned one had taken all day
        near = (learned_lift, learned_lift + LINE / 2, learned_lift - LINE / 2)
        return tuple(dict.fromkeys(round(lift, 4) for lift in near))
    scan = tuple(0.22 + step * LINE / 2 for step in range(10))
    return tuple(dict.fromkeys(round(lift, 4) for lift in scan))


def unknown() -> bool:
    """Whether his line is still to be learned (a visit that only opens his panel, while repairs are off)."""
    return known(HALBU) is None


def gold(run: Run, stat: int = GOLD_STAT) -> int | None:
    """The gold the character carries (the player's stat 14; `GOLDBANK`, 15: the stash's), None unread."""
    loot = run.loot() if run.loot is not None else None
    if loot is None or not loot.stats:
        return None
    return dict(loot.stats).get(stat)


def quoted(run: Run, rect) -> int | None:
    """The cost the game shows on the Repair All button's tooltip ("Repair all equipment: %d", strings ui.json
    strThisShouldBeIn104), read by OCR (tesseract) from a picture of the button's surroundings, kept beside the runs
    for a look; None unread. The pointer is on the button."""
    run.pace.sleep(TOOLTIP_SECONDS)
    pointer = run.actuator.keys.pointer()
    if pointer is None:
        return None
    # Only the band the tooltip is drawn in, over the button: a wider picture (1400 x 330, the stash's items and the
    # panel's art in it) read as noise at 10:31:02 on 2026-10-17 ("REPAIR ALL' ... no number"); this band read the cost
    # in all ten pictures kept from the night
    left, top = max(rect[0], pointer[0] - TOOLTIP_BAND[0] // 2), max(rect[1], pointer[1] - TOOLTIP_ABOVE)
    path = Path(__file__).resolve().parents[1] / 'runs' / 'alt-d' / f'repair-{time.strftime("%H%M%S")}.png'
    try:
        size = f'{TOOLTIP_BAND[0]}x{TOOLTIP_BAND[1]}'
        subprocess.run(['grim', '-g', f'{left},{top} {size}', str(path)], timeout=3, check=True, capture_output=True)
        text = ''
        for psm in PAGE_MODES:  # one line first; a block when it reads no cost (repair-123918.png: '' as a line)
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
    # "Repair all equipment: N": the band holds only the tooltip, its words read loosely ("REPAIRTALE etl 111469",
    # "Berar ant cum e: 119636"), its number well: the last one of four digits and more. A misread one is caught by
    # the quote's drift (`repair`, QUOTE_DRIFT)
    LOG.info('Macro: repair: the tooltip read %r (%s)', ' '.join(text.split())[:120], path.name)
    return cost_of(text)


# Letters the game's font makes of digits, in a word that holds digits: its 0 is read as Q or O ("1Q1677" for 101677,
# 11:54:16 and 11:59:59 on 2026-10-17, repair-115959.png)
# its slashed 0 as @ ("5@548" for 50548, 13:24:09, repair-132409.png)
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
    """The cost in the tooltip band's text: its last number of four digits and more, the font's look-alike letters
    within a word of digits read as the digits (LOOKALIKES); None with none."""
    text = ' '.join(
        word.translate(LOOKALIKES) if sum(c.isdigit() for c in word) >= 2 else word for word in text.split()
    )
    numbers = re.findall(r'\d[\d,.]{3,}', text)
    digits = re.sub(r'\D', '', numbers[-1]) if numbers else ''
    return int(digits) if digits else None


def repair(run: Run, fix: bool = True) -> bool:
    """Halbu's Repair All (the module text); whether the staff's charges or the most worn item's durability rose. Mouse
    mode only. Not `fix`: his panel only opened and closed again, to learn his line (`unknown`)."""
    if run.pad is not None:
        raise Abort('the repair needs mouse mode')
    before = run.teleport() if run.teleport is not None else None
    worn = run.wear() if run.wear is not None else None
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
            # Only with the game's own cost within the carried gold: a vendor takes the rest from the stash's (the
            # player, 2026-10-17: "you can repair only on collected gold in the inventory")
            missing = before.maximum - before.charges if before is not None else 0
            # No charge missing: the durability's cost, which no quote of charges tells (`WEAR_CARRIED`)
            cost, last = quoted(run, rect), expected(missing) if missing else None
            if cost is not None and last is not None and abs(cost - last) > QUOTE_DRIFT * last:
                # A misread that lowers the cost would pass the check below and spend the stash's gold for the rest:
                # a read that far from the cost expected for the charges missing is not trusted
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
                now = run.teleport() if run.teleport is not None else None
                if before is not None and now is not None and now.charges > before.charges:
                    return True
                mended = run.wear() if run.wear is not None else None
                return worn is not None and (mended is None or mended.share > worn.share)

            took = run.seen(rose, REPAIR_SECONDS) is not None
            if took and coins is not None:
                # The gold stats land after the charges: read at once, the carried gold had not moved (208,801 ->
                # 208,801 for a 69,696 repair, 12:09:40 on 2026-10-17), and the stash's check would see nothing. Nor
                # at its first move: 165,932 -> 165,323 for a 61,006 repair (18:44:57), 104,317 a game later. Waited
                # for most of the cost to be gone, the stash's check after it
                least = coins - (1 - QUOTE_DRIFT) * cost
                run.seen(lambda _w: (gold(run) or coins) <= least, GOLD_SETTLE_SECONDS)
        finally:
            _close(run)
    after = run.teleport() if run.teleport is not None else None
    mended = run.wear() if run.wear is not None else None
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
    """Back toward the waypoint after a visit to Halbu, whatever came of it (macros/loop.py's leg), as from Jamella
    (shop.py `restock`): from beside him it is 37 units off, listed in sight and drawn where no aim reaches it ("the
    waypoint is not under the pointer at any aim", 12:39:25 on 2026-10-17: a recovery), and the walk from there ran
    out of clicks at 12:10:04."""
    try:
        walk_until(run, _waypoint(run), WAYPOINT_SEEN, 'the waypoint')
    except Abort as stop:
        LOG.info('Macro: repair: back toward the waypoint: %s', stop)
