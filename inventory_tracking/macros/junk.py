"""The KP_6 loop's items identified, appraised, and the junk sold to fund the staff's repair
(routes/lower-kurast-loop-plan.md §15; Teleport charges come with Halbu's repair, repair.py).

The player, 2026-10-17: "... remember, that we shouldn't sell our own equipment or valuable items".

Unidentified loop items are identified with the Tome in Pandemonium Fortress (`identify`); the identify watcher
appraises each (identify/service.py `verdict_for`). Only `vendor` verdicts are junk; anything else, or no verdict, is
stashed. Junk is sold at Jamella's (shop.py `restock`). Only the loop's own items (cube.py `loot`) of `sellable` kinds
are ever sold. Unit ids change per game, so junk is kept by class and cell (`Cell`).
"""

from collections.abc import Callable, Iterable, Mapping, Sequence

from inventory_tracking.common import LOG
from inventory_tracking.game.layout import IDENTIFY_TOME
from inventory_tracking.game.records import Carried, Pack
from inventory_tracking.items.metadata import item_base
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import INVENTORY, PANEL_SECONDS, cell_point, loot, open_inventory
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.pickmode import WHITE, sellable


__all__ = ['JUNK_QUALITIES', 'MAGIC', 'VENDOR', 'identify', 'junk', 'junk_of', 'named', 'unidentified']

Cell = tuple[int, int, int]  # an item's class and top-left inventory cell
MAGIC, RARE = 4, 6  # ItemData quality (loot/shown.py RARITIES)
# Qualities sold once appraised `vendor`; whites only as Void bases (`sellable`). The player, 2026-10-18: "we should
# sell junk rings and other junk items; imporant!: do not sell own equipment or valuable items"
SET, UNIQUE, CRAFTED = 5, 7, 8
JUNK_QUALITIES = frozenset((MAGIC, RARE, SET, UNIQUE, CRAFTED, *WHITE))
VENDOR = 'vendor'  # identify/service.py `verdict_for`: no reason to keep it
IDENTIFY_SECONDS = 1.0  # for an item's identified flag to turn on after the click
CURSOR_SETTLE = 0.15  # seconds after the right click on the tome, before the click on the item


QUALITIES = {4: 'magic', 5: 'set', 6: 'rare', 7: 'unique', 8: 'crafted'}


def named(item: Carried) -> str:
    """'magic Demonhide Gloves (380)': quality, base and class, for the log and tools/trade.py."""
    base = item_base(item.txt)
    name = base['name'] if base is not None else 'item'
    return f'{QUALITIES.get(item.quality, "white")} {name} ({item.txt})'


def unidentified(pack: Pack, own: frozenset[Cell]) -> list[Carried]:
    """The loop's unidentified magic-or-better items."""
    return [item for item in loot(pack, own) if not item.identified and item.quality >= MAGIC]


def identify(run: Run, inventory_key: str, items: Iterable[Carried]) -> list[Carried]:
    """Identify `items` with the Tome, each checked in memory; returns those identified. Stops at the first that does
    not take or when the tome is empty. Mouse mode only; panels closed after."""
    if run.pad is not None:
        raise Abort('identifying needs mouse mode')
    pack = run.reads.carried()
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
            run.actuator.tap('Button3')  # the tome's right click arms the pointer
            run.pace.sleep(CURSOR_SETTLE)
            run.actuator.move(*cell_point(rect, INVENTORY, (item.x, item.y), item.size), scatter=(5, 5))
            run.actuator.click()

            def known(_w, i=item) -> bool:
                p = run.reads.carried()
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
    """Cells of the loop's items appraised junk, each verdict said."""
    found = set()
    for item in loot(pack, own):
        if not item.identified or item.quality not in JUNK_QUALITIES or item.unit_id not in verdicts:
            continue
        base = item_base(item.txt)
        if not sellable(base['type'] if base is not None else None, item.quality, item.txt):
            continue  # a sure valuable (jewel, ring, rune...)
        verdict = verdicts[item.unit_id]
        said(f'appraised {named(item)} at ({item.x}, {item.y}): {verdict}')
        if verdict == VENDOR:
            found.add((item.txt, item.x, item.y))
    return found


def junk_of(items: Sequence[Carried], appraise: Callable[[list[int]], Mapping[int, str]]) -> list[Carried]:
    """The junk among the loop's `items`: identified, `sellable`, of JUNK_QUALITIES, appraised `vendor` now
    (`appraise`: verdicts by unit id). No verdict: kept."""
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
