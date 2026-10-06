"""Copies of an assessed item already in the collection, and whether its rolls are better.

"The same item" is the same unique/set (definition id), the same runeword, the same
normal/superior base (ethereal and socket count included), or a magic/rare/crafted
item on the same base with the same kinds of stats (a +1 Lightning skiller grand
charm with life matches another one with life). Only open placements count.

Rolls are compared stat by stat on every variable stat both items share, using the
roll range the decoder annotated (`roll_range`/`roll_quality_range`, with its
`better` direction). The result is read-only evidence for Alt+D and the identify
summary; nothing here writes the collection.
"""

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Literal

from inventory_tracking.collection.fingerprint import fingerprint
from inventory_tracking.collection.models import ItemRecord, Location
from inventory_tracking.collection.store import _row_item, _row_placement


Relation = Literal['better', 'worse', 'equal', 'mixed', 'same']
# 'same': nothing variable to compare (fixed-stat unique, plain base): an exact duplicate kind.
AT_LEAST_AS_GOOD = frozenset(('worse', 'equal', 'same'))
SHOWN_COPIES = 3


def multiple_copy_use(result: dict[str, Any]) -> bool:
    """Charms fill multiple inventory cells; jewels are consumed in socket setups."""
    item = result.get('extraction', {}).get('item', {})
    return item.get('base_name', item.get('name')) in {
        'Small Charm',
        'Large Charm',
        'Grand Charm',
        'Jewel',
        'Colossal Jewel',
    }


def stat_key(row: dict[str, Any]) -> str | None:
    stats = [row['memory_stat']] if row.get('memory_stat') else row.get('memory_stats', [])
    keys = [f'{s["id"]}:{s["layer"]}' for s in stats if 'id' in s and 'layer' in s]
    return '+'.join(keys) or row.get('name')


def stat_keys(observation: dict[str, Any]) -> frozenset[str]:
    return frozenset(
        key
        for row in observation.get('decoded_stats', [])
        if row.get('status') == 'decoded' and row.get('presentation') != 'internal' and (key := stat_key(row))
    )


def variable_rolls(observation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Stat key → {value, fraction, row} for every decoded stat with a real roll range."""
    rolls = {}
    for row in observation.get('decoded_stats', []):
        bounds = row.get('roll_quality_range') or row.get('roll_range')
        value = row.get('value')
        key = stat_key(row)
        if row.get('status') != 'decoded' or not bounds or not isinstance(value, int | float) or key is None:
            continue
        low, high = bounds['min'], bounds['max']
        if low >= high:
            continue
        better = (row.get('roll_range') or {}).get('better', 'higher')
        fraction = (value - low) / (high - low) if better == 'higher' else (high - value) / (high - low)
        rolls[key] = {'value': value, 'fraction': max(0.0, min(1.0, fraction)), 'better': better, 'row': row}
    return rolls


def perfection(rolls: dict[str, dict[str, Any]]) -> float | None:
    """Mean roll position over the variable stats, 0 (all minimum) to 1 (all perfect)."""
    if not rolls:
        return None
    return sum(r['fraction'] for r in rolls.values()) / len(rolls)


def short_stat(row: dict[str, Any]) -> str:
    # Local import: identify.service imports this module's callers.
    from inventory_tracking.identify.service import compact_stat

    return compact_stat(row.get('text') or row.get('name') or '?')


def compare_rolls(
    new: dict[str, dict[str, Any]], old: dict[str, dict[str, Any]]
) -> tuple[Relation, list[str], list[str]]:
    """(relation, stats the new item rolls better, stats it rolls worse) against one owned copy."""
    better, worse = [], []
    for key in new.keys() & old.keys():
        n, o = new[key], old[key]
        if n['value'] == o['value']:
            continue
        higher_is_better = n['better'] == 'higher'
        diff = f'{short_stat(n["row"])} vs {o["value"]}'
        (better if (n['value'] > o['value']) == higher_is_better else worse).append(diff)
    if not new.keys() & old.keys():
        relation: Relation = 'same'
    elif better and worse:
        relation = 'mixed'
    elif better:
        relation = 'better'
    elif worse:
        relation = 'worse'
    else:
        relation = 'equal'
    return relation, sorted(better), sorted(worse)


def overall(relations: list[Relation]) -> Relation:
    """Better only when it beats every copy; worse/equal/same when any copy is at least as good."""
    if not relations:
        return 'same'
    if all(r == 'better' for r in relations):
        return 'better'
    at_least_as_good: tuple[Relation, ...] = ('same', 'equal', 'worse')
    return next((r for r in at_least_as_good if r in relations), 'mixed')


def match_kind(observation: dict[str, Any]) -> tuple[str, str, list[Any]] | None:
    """(kind label, SQL condition, parameters) selecting candidate copies; None when not comparable."""
    item = observation['item']
    ethereal = item.get('ethereal')
    if item.get('runeword'):
        return f'{item["runeword"]} runeword', 'i.runeword = ? AND i.ethereal IS ?', [item['runeword'], ethereal]
    rarity = item.get('rarity')
    if item.get('identified') is False:
        return None
    if rarity in ('unique', 'set'):
        return (
            f'{rarity} {item["name"]}',
            'i.rarity = ? AND i.name = ? AND i.ethereal IS ? AND i.identified IS NOT 0',
            [
                rarity,
                item['name'],
                ethereal,
            ],
        )
    if rarity in ('magic', 'rare', 'crafted'):
        rarities = ['magic'] if rarity == 'magic' else ['rare', 'crafted']
        marks = ', '.join('?' for _ in rarities)
        return (
            f'{rarity} {item["base_name"]} with the same stats',
            f'i.base_code = ? AND i.rarity IN ({marks}) AND i.identified IS NOT 0 AND i.runeword IS NULL',
            [item['base_code'], *rarities],
        )
    if rarity in ('normal', 'superior'):
        return (
            f'{"ethereal " if ethereal else ""}{item["base_name"]}'
            + (f' ({item["sockets"]} os)' if item.get('sockets') else ''),
            "i.base_code = ? AND i.rarity IN ('normal', 'superior') AND i.runeword IS NULL "
            'AND i.ethereal IS ? AND i.sockets IS ?',
            [item['base_code'], ethereal, item.get('sockets')],
        )
    return None


def same_item(observation: dict[str, Any], record: ItemRecord) -> bool:
    item = observation['item']
    if item.get('rarity') in ('unique', 'set') and not item.get('runeword'):
        mine = (observation.get('source', {}).get('item_identity') or {}).get('table_id')
        theirs = (record.observation.get('source', {}).get('item_identity') or {}).get('table_id')
        return mine is None or theirs is None or mine == theirs
    if item.get('rarity') in ('magic', 'rare', 'crafted') and not item.get('runeword'):
        return stat_keys(observation) == stat_keys(record.observation)
    return True


def is_self(observation: dict[str, Any], own_fingerprint: str, placement) -> bool:
    """The assessed item itself when it already lies in a collected container (Alt+D in the stash)."""
    if placement.fingerprint != own_fingerprint:
        return False
    try:
        here = Location.from_source(observation['source'], placement.location.owner)
    except KeyError, ValueError:
        return False
    location = placement.location
    return (here.container, here.x, here.y) == (location.container, location.x, location.y)


def same_unit(observation: dict[str, Any], record: ItemRecord) -> bool:
    """The collection last saw this fingerprint on the very unit now assessed."""
    mine = observation.get('source', {}).get('unit_id')
    return mine is not None and mine == record.observation.get('source', {}).get('unit_id')


def without_self(observation: dict[str, Any], rows: list) -> list:
    """Drop the assessed item's own placement: the cell it lies in, else the one it was moved from.

    A capture (closing the stash) records the item where it lay; carried elsewhere
    afterwards, that placement stays open until the next capture and is still this item.
    """
    own_fingerprint = fingerprint(observation)
    for index, (_, placement) in enumerate(rows):
        if is_self(observation, own_fingerprint, placement):
            return rows[:index] + rows[index + 1 :]
    for index, (record, placement) in enumerate(rows):
        if placement.fingerprint == own_fingerprint and same_unit(observation, record):
            return rows[:index] + rows[index + 1 :]
    return rows


def connect_readonly(database: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f'file:{database}?mode=ro', uri=True, timeout=2)
    connection.row_factory = sqlite3.Row
    return connection


def owned_copies(observation: dict[str, Any], database: Path | str) -> dict[str, Any] | None:
    """Owned copies of the same item and how this one compares; None without a collection or a match rule."""
    database = Path(database)
    kind = match_kind(observation)
    if kind is None or not database.exists():
        return None
    label, condition, params = kind
    own_fingerprint = fingerprint(observation)
    sql = (
        'SELECT p.*, i.* FROM placements p JOIN items i ON i.fingerprint = p.fingerprint '
        f'WHERE p.gone_at IS NULL AND {condition} ORDER BY p.id'
    )
    with closing(connect_readonly(database)) as db:
        rows = [(_row_item(r), _row_placement(r)) for r in db.execute(sql, params)]
    new_rolls = variable_rolls(observation)
    copies = []
    relations: list[Relation] = []
    for record, placement in without_self(observation, rows):
        if not same_item(observation, record):
            continue
        old_rolls = variable_rolls(record.observation)
        old_perfection = perfection(old_rolls)
        relation, better, worse = compare_rolls(new_rolls, old_rolls)
        relations.append(relation)
        copies.append(
            {
                'name': record.name,
                'location': placement.location.label,
                'identical': record.fingerprint == own_fingerprint,
                'perfection': None if old_perfection is None else round(old_perfection, 3),
                'relation': relation,
                'better': better,
                'worse': worse,
            }
        )
    new_perfection = perfection(new_rolls)
    return {
        'kind': label,
        'count': len(copies),
        'relation': overall(relations) if relations else None,
        'perfection': None if new_perfection is None else round(new_perfection, 3),
        'copies': copies,
    }


def percent(value: float | None) -> str:
    return '' if value is None else f' ({round(value * 100)}% rolls)'


RELATION_TEXT = {
    'better': 'this one beats every copy',
    'worse': 'an owned copy rolls better',
    'equal': 'an owned copy rolls the same',
    'mixed': 'better on some stats, worse on others',
    'same': 'already owned (no variable rolls)',
}


def owned_summary(owned: dict[str, Any] | None) -> str | None:
    """One short clause for the identify summary: 'owned 2: better than every owned copy'."""
    if not owned or not owned['count']:
        return None
    return f'owned {owned["count"]}: {RELATION_TEXT[owned["relation"]]}'


def owned_lines(owned: dict[str, Any] | None, *, comparison_only: bool = False) -> list[str]:
    """Alt+D section: the count, the overall relation, then the closest copies with stat differences."""
    if owned is None:
        return []
    if not owned['count']:
        return [f'Owned: none ({owned["kind"]})']
    lines = [f'Owned: {owned["count"]} x {owned["kind"]}']
    if not comparison_only:
        lines[0] += f' — {RELATION_TEXT[owned["relation"]]}'
    if not comparison_only and owned['perfection'] is not None:
        lines[0] += f'; rolls {round(owned["perfection"] * 100)}% of max'
    ranked = sorted(owned['copies'], key=lambda c: -(c['perfection'] or 0))
    for copy in ranked[:SHOWN_COPIES]:
        parts = [f'  {copy["location"]}{percent(copy["perfection"])}']
        if copy['identical']:
            parts.append('identical')
        elif copy['relation'] != 'same':
            parts.append(copy['relation'])
        if copy['better']:
            parts.append('new better: ' + ', '.join(copy['better']))
        if copy['worse']:
            parts.append('new worse: ' + ', '.join(copy['worse']))
        lines.append(' — '.join(parts))
    if len(ranked) > SHOWN_COPIES:
        lines.append(f'  +{len(ranked) - SHOWN_COPIES} more copies')
    return lines
