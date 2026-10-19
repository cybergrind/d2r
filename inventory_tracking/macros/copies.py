"""The best copy of a unique or set item first: the loop sells one the appraisal calls `vendor` only when the player
already owns a copy at least as good.

The player, 16:50 on 2026-10-18: "loop should keep the best copy first" (the loop had sold a Maelstrom, set rings, a
Skin of the Flayed One the appraisal called junk), with the standing rule of 2026-10-04: cleanup never drops the last
copy of a unique or set, only the surplus. So a set or unique item of the loop's junk (macros/junk.py `junk_of`) is
kept, and stashed like any keeper, when

- no copy is owned (the first copy),
- every owned copy rolls worse, or better on some stats and worse on others (none at least as good: appraisal/owned.py
  `overall`, `AT_LEAST_AS_GOOD`), or
- what is owned cannot be told: its identify read is not found, or the collection cannot be read (the safe side).

The worse stashed copy stays where it is: the stash's cleanup is the player's ("very carefully").

What is owned (`owned_copies`): the collection database (collection/store.py), read only. The stash watcher captures
the character's stash, inventory, cube, equipment and mercenary and the shared stash each time the stash closes
(collection/watch.py), so the loop's own stash stops keep it current; the mules are as of their last capture (Win+S, or
a stash closed on them). The character that played last (`characters.last_seen`) is the loop's: its inventory and cube
are left out, they hold the loop's items in transit (at 16:54 on 2026-10-18 a junk Cathan's Seal lay in the cube as
captured, sold a minute later). Not covered: a character never captured, and an item moved on a mule since its last
capture. Copies matched as appraisal/owned.py matches them: the same unique or set row, ethereal or not; rolls compared
on the variable stats both share.

The item's own read: the identify watcher keeps each item it reads in the service's run directory
(identify/service.py `_assess`, corpus/store.py `persist`: `identified/<id>.json`, with its unit id); an item carried
from an earlier game has a new unit id and no read (kept). Two copies in one visit: the best rolled is judged first and
counts as owned for the next.
"""

import json
import sqlite3
from collections.abc import Callable, Iterable, Sequence
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from inventory_tracking.appraisal.owned import (
    AT_LEAST_AS_GOOD,
    compare_rolls,
    connect_readonly,
    match_kind,
    overall,
    perfection,
    same_item,
    variable_rolls,
    without_self,
)
from inventory_tracking.collection.store import DEFAULT_DATABASE, _row_item, _row_placement
from inventory_tracking.common import LOG
from inventory_tracking.game.records import Carried
from inventory_tracking.macros.junk import VENDOR, named
from inventory_tracking.macros.pickmode import SET, UNIQUE


__all__ = ['Appraisal', 'keep_copy', 'owned_copies', 'reads', 'sold']

Observation = dict[str, Any]
TRANSIT = ('inventory', 'cube')  # the playing character's containers that hold the loop's items (the module text)
SHOWN = 3  # the better stats told in the log


@dataclass(frozen=True)
class Appraisal:
    """What the appraisal said of an item: its verdict (identify/service.py `verdict_for`) and its identify read (the
    decoded observation), None when not found."""

    verdict: str
    observation: Observation | None = None


def keep_copy(item: Carried, appraisal: Appraisal, owned: Sequence[Observation] | None) -> str | None:
    """Why the set or unique `item` the appraisal calls `vendor` is kept (the module text), None when it is sold: an
    owned copy (`owned`, the reads of the copies of the same item; None when they cannot be told) rolls at least as
    well. Any other item or verdict: None (nothing to say: the verdict decides)."""
    if item.quality not in (SET, UNIQUE) or appraisal.verdict != VENDOR:
        return None
    if appraisal.observation is None:
        return 'its identify read is not found: what is owned cannot be told'
    if owned is None:
        return 'the collection cannot be read: what is owned cannot be told'
    if not owned:
        return 'the first copy'
    new = variable_rolls(appraisal.observation)
    compared = [compare_rolls(new, variable_rolls(copy)) for copy in owned]
    relation = overall([relation for relation, _, _ in compared])
    if relation in AT_LEAST_AS_GOOD:
        return None
    better = sorted({stat for _, stats, _ in compared for stat in stats})
    told = f': {", ".join(better[:SHOWN])}' if better else ''
    if relation == 'better':
        return f'rolls better than the {len(owned)} owned{told}'
    return f'none of the {len(owned)} owned rolls as well on every stat{told}'


def owned_copies(observation: Observation, database: Path = DEFAULT_DATABASE) -> list[Observation] | None:
    """The reads of the owned copies of the item read as `observation` (the module text), [] with none; None when the
    collection cannot be read or the item has no match rule."""
    kind = match_kind(observation)
    if kind is None or not database.exists():
        return None
    _, condition, params = kind
    try:
        with closing(connect_readonly(database)) as db:
            playing = db.execute('SELECT name FROM characters ORDER BY last_seen DESC LIMIT 1').fetchone()
            sql = (
                'SELECT p.*, i.* FROM placements p JOIN items i ON i.fingerprint = p.fingerprint '
                f'WHERE p.gone_at IS NULL AND {condition} '
                f'AND NOT (p.owner = ? AND p.container IN ({", ".join("?" for _ in TRANSIT)})) ORDER BY p.id'
            )
            found = db.execute(sql, [*params, playing['name'] if playing else '', *TRANSIT]).fetchall()
            rows = [(_row_item(row), _row_placement(row)) for row in found]
    except (sqlite3.Error, ValueError) as error:
        LOG.info('Macro: copies: the collection cannot be read: %s', error)
        return None
    return [record.observation for record, _ in without_self(observation, rows) if same_item(observation, record)]


READ_UNITS: dict[Path, int | None] = {}  # each identify read's unit id by file (read once: `reads`)


def reads(directory: Path, units: Iterable[int]) -> dict[int, Observation]:
    """The identify reads of `units` in the service's run directory `directory` (the module text), by unit id."""
    wanted, found = set(units), {}
    for path in sorted((directory / 'identified').glob('*.json')):
        if path not in READ_UNITS or READ_UNITS[path] in wanted:
            try:
                observation = json.loads(path.read_text())['observation']
                unit = int(observation['source']['unit_id'])
            except OSError, ValueError, KeyError, TypeError:
                observation, unit = None, None
            READ_UNITS[path] = unit
            if observation is not None and unit in wanted:
                found[unit] = observation
    return found


def alike(one: Observation, other: Observation) -> bool:
    """Whether two reads are copies of the same set or unique item (appraisal/owned.py `match_kind`)."""
    a, b = one['item'], other['item']
    rows = [(o.get('source', {}).get('item_identity') or {}).get('table_id') for o in (one, other)]
    return (
        (a.get('rarity'), a.get('name'), a.get('ethereal')) == (b.get('rarity'), b.get('name'), b.get('ethereal'))
        and (None in rows or rows[0] == rows[1])
    )  # fmt: skip


def title(item: Carried, observation: Observation | None) -> str:
    """'Maelstrom (Yew Wand)' from the read, else the class (junk.py `named`)."""
    read = observation['item'] if observation is not None else {}
    if not read.get('name'):
        return named(item)
    return f'{read["name"]} ({read["base_name"]})' if read.get('base_name') else read['name']


def sold(
    junk: Sequence[Carried],
    directory: Path | None,
    owned: Callable[[Observation], list[Observation] | None] = owned_copies,
) -> list[Carried]:
    """The loop's `junk` less the set and unique copies kept (`keep_copy`), each told: the kept are no junk, so the
    stash stop takes them as keepers. `directory`: the service's run directory (macros/visitlog.py
    `session_directory`), None outside the service (a test, the CLI): no reads there, the junk as it is. Never raises:
    on a failure the set and unique items are kept."""
    candidates = [item for item in junk if item.quality in (SET, UNIQUE)]
    if not candidates or directory is None:
        return list(junk)
    try:
        found = reads(directory, (item.unit_id for item in candidates))

        def rolled(item: Carried) -> float:
            observation = found.get(item.unit_id)
            return (perfection(variable_rolls(observation)) or 0.0) if observation is not None else 1.0

        kept: set[int] = set()
        held: list[Observation] = []  # the copies kept in this visit: owned for the next of the same item
        for item in sorted(candidates, key=rolled, reverse=True):
            observation = found.get(item.unit_id)
            copies = owned(observation) if observation is not None else None
            if copies is not None and observation is not None:
                copies = [*copies, *(copy for copy in held if alike(copy, observation))]
            reason = keep_copy(item, Appraisal(VENDOR, observation), copies)
            if reason is None:
                LOG.info('Macro: copies: sell %s: an owned copy rolls at least as well', title(item, observation))
                continue
            LOG.info('Macro: copies: keep %s: %s', title(item, observation), reason)
            kept.add(item.unit_id)
            if observation is not None:
                held.append(observation)
    except Exception as error:  # never into the visit: the safe side
        LOG.info('Macro: copies: %s: the %d set and unique items kept', error, len(candidates))
        kept = {item.unit_id for item in candidates}
    return [item for item in junk if item.unit_id not in kept]
