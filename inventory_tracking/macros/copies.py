"""The best copy of a unique or set item first: the loop sells one the appraisal calls `vendor` only when the player
already owns a copy at least as good ("loop should keep the best copy first", the player, 2026-10-18).

Kept, and stashed like a keeper: the first copy, one no owned copy rolls at least as well as, and one whose owned
copies cannot be told (no identify read, unreadable collection). Owned copies come read-only from the collection
database, less the playing character's inventory and cube (items in transit); the item's own read from the identify
watcher's `identified/` files. Notes: history/copies.md.
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
    offline_characters,
    online_only,
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
TRANSIT = ('inventory', 'cube')  # the playing character's containers that hold the loop's items
SHOWN = 3  # the better stats told in the log


@dataclass(frozen=True)
class Appraisal:
    """The appraisal's verdict on an item and its identify read (None when not found)."""

    verdict: str
    observation: Observation | None = None


# Retired when TOWN_DECIDES is on (loot/keep.py, M6, 2026-10-20); delete after the 30-cycle check (loot/api.py
# `town_verdicts` keeps the first and the best copy). Until then the visit's old chain and loot/today.py use it
def keep_copy(item: Carried, appraisal: Appraisal, owned: Sequence[Observation] | None) -> str | None:
    """Why the set or unique `vendor` item is kept; None when an owned copy (`owned`; None: cannot be told) rolls at
    least as well, or for any other item or verdict (the verdict decides)."""
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
    """The reads of the owned copies of `observation`'s item; None when the collection cannot be read or the item has
    no match rule."""
    kind = match_kind(observation)
    if kind is None or not database.exists():
        return None
    _, condition, params = kind
    online, online_params = online_only(offline_characters())  # offline characters own nothing (appraisal/owned.py)
    try:
        with closing(connect_readonly(database)) as db:
            playing = db.execute('SELECT name FROM characters ORDER BY last_seen DESC LIMIT 1').fetchone()
            sql = (
                'SELECT p.*, i.* FROM placements p JOIN items i ON i.fingerprint = p.fingerprint '
                f'WHERE p.gone_at IS NULL AND {condition} '
                f'AND NOT (p.owner = ? AND p.container IN ({", ".join("?" for _ in TRANSIT)})){online} ORDER BY p.id'
            )
            found = db.execute(sql, [*params, playing['name'] if playing else '', *TRANSIT, *online_params]).fetchall()
            rows = [(_row_item(row), _row_placement(row)) for row in found]
    except (sqlite3.Error, ValueError) as error:
        LOG.info('Macro: copies: the collection cannot be read: %s', error)
        return None
    return [record.observation for record, _ in without_self(observation, rows) if same_item(observation, record)]


READ_UNITS: dict[Path, int | None] = {}  # each identify read's unit id by file, read once


def reads(directory: Path, units: Iterable[int]) -> dict[int, Observation]:
    """The identify reads of `units` in the service's run directory, by unit id."""
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


# Retired when TOWN_DECIDES is on (loot/keep.py, M6, 2026-10-20); delete after the 30-cycle check. Until then the
# visit's old chain uses it
def sold(
    junk: Sequence[Carried],
    directory: Path | None,
    owned: Callable[[Observation], list[Observation] | None] = owned_copies,
) -> list[Carried]:
    """The loop's `junk` less the set and unique copies kept (`keep_copy`), each logged; the stash stop takes the kept
    as keepers. `directory`: the service's run directory, None outside the service (junk returned as is). Never
    raises: on a failure the set and unique items are kept."""
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
    except Exception as error:  # never into the visit
        LOG.info('Macro: copies: %s: the %d set and unique items kept', error, len(candidates))
        kept = {item.unit_id for item in candidates}
    return [item for item in junk if item.unit_id not in kept]
