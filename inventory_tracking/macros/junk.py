"""The KP_6 loop's items identified, appraised, and the junk among them sold for the staff's repair
(routes/lower-kurast-loop-plan.md §15).

The player, 2026-10-17: "probably we need to steer into picking items with +skill, identifying them, appraising,
selling [bad ones] and repairing on these money ... remember, that we shouldn't sell our own equipment or valuable
items". The staff's Teleport charges are bought by Halbu's repair, on carried gold only (macros/repair.py).

- The pickup takes the candidates (macros/pickmode.py `candidate`): magic and rare items that can roll skills, shown
  by the loot filter.
- At the end of a game in Pandemonium Fortress, before the stash, the loop's unidentified items are identified with
  the Tome of Identify (`identify`: a right click on the tome, a click on the item, checked in memory).
- The service's identify watcher appraises each item the moment it is identified (identify/service.py
  `IdentifyWorker`, `verdict_for`); `junk` keeps the ones it calls `vendor`, the verdict with no reason to keep
  (no value watch, no build use, no trade tier, no estimate). Any other verdict, none in time, or an item still
  unidentified is kept: it goes to the stash as before.
- Junk is never stashed and is sold at Jamella's next visit (macros/shop.py `restock`), with the full stacks' items.

What is sold is only ever the loop's own items (macros/cube.py `loot`: neither the player's, read at the loop's
first look, nor the cube, the tomes, the keys), of the kinds taken only to be identified (macros/pickmode.py
`sellable`: charms and white Void bases too, never a jewel, ring, rune or gem), never set, unique or crafted,
identified, with the `vendor` verdict for that unit. Items' unit ids change from game to game, so junk is kept by
class and cell (`Cell`), as the loop's items are (macros/loop.py `mine`), and dropped once nothing of its class lies
there.
"""

from collections.abc import Callable, Iterable, Mapping, Sequence

from inventory_tracking.common import LOG
from inventory_tracking.items.metadata import item_base
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import INVENTORY, PANEL_SECONDS, cell_point, loot, open_inventory
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.pickmode import WHITE, sellable
from inventory_tracking.macros.world import IDENTIFY_TOME, Carried, Pack


__all__ = ['JUNK_QUALITIES', 'MAGIC', 'VENDOR', 'identify', 'junk', 'junk_of', 'named', 'unidentified']

Cell = tuple[int, int, int]  # an item's class and top-left inventory cell
MAGIC, RARE = 4, 6  # ItemData quality (loot/shown.py RARITIES)
# The qualities sold as junk once appraised `vendor`: magic, rare, set, unique and crafted (the player, 11:10 on
# 2026-10-18: "we should sell junk rings and other junk items; imporant!: do not sell own equipment or valuable items"),
# never a set or unique charm (macros/pickmode.py `sellable`); a white or superior one only as a Void base
SET, UNIQUE, CRAFTED = 5, 7, 8
JUNK_QUALITIES = frozenset((MAGIC, RARE, SET, UNIQUE, CRAFTED, *WHITE))
VENDOR = 'vendor'  # identify/service.py `verdict_for`: no reason to keep it (the module text)
IDENTIFY_SECONDS = 1.0  # for an item's identified flag to turn on after the click
CURSOR_SETTLE = 0.15  # seconds after the right click on the tome, before the click on the item


QUALITIES = {4: 'magic', 5: 'set', 6: 'rare', 7: 'unique', 8: 'crafted'}


def named(item: Carried) -> str:
    """The item's quality and base, and its class: 'magic Demonhide Gloves (380)', for the log and tools/trade.py."""
    base = item_base(item.txt)
    name = base['name'] if base is not None else 'item'
    return f'{QUALITIES.get(item.quality, "white")} {name} ({item.txt})'


def unidentified(pack: Pack, own: frozenset[Cell]) -> list[Carried]:
    """The loop's items in the inventory that are not identified yet (magic and better)."""
    return [item for item in loot(pack, own) if not item.identified and item.quality >= MAGIC]


def identify(run: Run, inventory_key: str, items: Iterable[Carried]) -> list[Carried]:
    """Identify `items` with the Tome of Identify, one by one, each checked by its flag in memory; the ones identified.
    Stops at the first that does not take, or when the tome is empty. Mouse mode only; the panels closed after."""
    if run.pad is not None:
        raise Abort('identifying needs mouse mode')
    pack = run.carried() if run.carried is not None else None
    rect = run.actuator.keys.focused_window_rect()
    tome = next((item for item in pack.items if item.txt == IDENTIFY_TOME), None) if pack is not None else None
    items = list(items)
    why = (
        'the inventory is not read' if pack is None
        else 'no Tome of Identify' if tome is None
        else 'the tome is empty' if not pack.identifies
        else 'no game window' if rect is None
        else None
    )  # fmt: skip
    if why is not None or pack is None or tome is None or rect is None:
        LOG.info('Macro: identify: %s: %d items stay unidentified', why, len(items))
        return []
    done: list[Carried] = []
    try:
        open_inventory(run, inventory_key)
        for item in items[: pack.identifies]:
            run.actuator.move(*cell_point(rect, INVENTORY, (tome.x, tome.y), tome.size), scatter=(5, 5))
            run.actuator.tap('Button3')  # the tome's right click: the pointer identifies the next item clicked
            run.pace.sleep(CURSOR_SETTLE)
            run.actuator.move(*cell_point(rect, INVENTORY, (item.x, item.y), item.size), scatter=(5, 5))
            run.actuator.click()

            def known(_w, i=item) -> bool:
                p = run.carried() if run.carried is not None else None
                return p is not None and any(c.unit_id == i.unit_id and c.identified for c in p.items)

            if run.seen(known, IDENTIFY_SECONDS) is None:
                LOG.info('Macro: identify: the item %d at (%d, %d) did not take', item.txt, item.x, item.y)
                break
            done.append(item)
    finally:
        if 'inventory' in run.world().open_panels:
            run.actuator.tap('Escape')
            run.seen(lambda w: 'inventory' not in w.open_panels, PANEL_SECONDS)
            run.actuator.rebase()
    LOG.info('Macro: identify: %d of %d items identified', len(done), len(items))
    return done


def junk(pack: Pack, own: frozenset[Cell], verdicts: Mapping[int, str], said: Callable[[str], None]) -> set[Cell]:
    """The cells of the loop's items the appraisal calls junk (the module text), each said with its verdict."""
    found = set()
    for item in loot(pack, own):
        if not item.identified or item.quality not in JUNK_QUALITIES or item.unit_id not in verdicts:
            continue
        base = item_base(item.txt)
        if not sellable(base['type'] if base is not None else None, item.quality, item.txt):
            continue  # a sure valuable (a jewel, a ring, a rune...): kept whatever the appraisal says
        verdict = verdicts[item.unit_id]
        said(f'appraised {named(item)} at ({item.x}, {item.y}): {verdict}')
        if verdict == VENDOR:
            found.add((item.txt, item.x, item.y))
    return found


def junk_of(items: Sequence[Carried], appraise: Callable[[list[int]], Mapping[int, str]]) -> list[Carried]:
    """The junk among the loop's `items` (the inventory's and the cube's; never the player's): identified, of a kind
    it may sell (`sellable`), magic or rare or a white Void base, appraised `vendor` now (`appraise`: the identify
    watcher's verdicts by unit id, read again for an item carried from another game). An item with no verdict is
    kept."""
    found = []
    for item in items:
        base = item_base(item.txt)
        if (
            item.identified
            and item.quality in JUNK_QUALITIES
            and sellable(base['type'] if base else None, item.quality, item.txt)
        ):
            found.append(item)
    verdicts = appraise([item.unit_id for item in found]) if found else {}
    return [item for item in found if verdicts.get(item.unit_id) == VENDOR]
