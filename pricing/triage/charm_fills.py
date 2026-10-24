"""Shimmering charms (magic charms with the all-resistances prefix) priced by what they sold for.

The player, 2026-10-24: "definitive valuation based on real deals (not just ask)". The evidence is Traderie's Recent
Trades (accepted and completed offers, SC/NL/PC/RotW), built into pricing/data/charm-evidence.json by
`uv run --offline python -m pricing.tools.build_charm_evidence`. A facet is a charm size, its all-res roll and its
one companion affix with its value (`facet`); the triage (engine.py `assess`) takes the facet's sale-backed band over
the asks.

A facet with fewer than MIN_FILLS priced trades is priced by its comparable-or-worse trades instead: the same size,
all res no higher than the item's, and the same companion at no higher value or no companion at all (a floor, never a
better copy's price). Pure but for
the evidence file's read (`evidence`).
"""

import json
from collections.abc import Mapping
from functools import cache
from pathlib import Path
from typing import Any


__all__ = ['EVIDENCE_FILE', 'MIN_FILLS', 'band', 'evidence', 'facet', 'facet_key', 'reason', 'shape']

EVIDENCE_FILE = Path(__file__).resolve().parents[1] / 'data' / 'charm-evidence.json'
SIZES = {'small charm': 'sc', 'large charm': 'lc', 'grand charm': 'gc'}
ALL_RES = '441'  # Traderie '+{{value}} to All Resistances'
SINGLE_RES = ('401', '426', '427', '428')  # poison, cold, fire, lightning: the drop's four halves of ALL_RES
# Not an affix: rarity, platform, mode, ladder and game version, and the required level a listing may state
IGNORED = frozenset(('797', '798', '799', '800', '1854', '796'))
MIN_FILLS = 3  # priced trades a band needs
LIQUID_FILLS = 10  # priced trades in the band's last LIQUID_DAYS that make it liquid
LIQUID_DAYS = 30


def shape(name: str, properties: Mapping[Any, Any]) -> tuple[str, int, str | None, Any] | None:
    """(size, all res, companion property or None, its value) of a shimmering charm; None for any other item: not a
    charm, no all-res roll, a single resistance beside it, or more than one companion."""
    size = SIZES.get(str(name).casefold())
    if size is None:
        return None
    found = {str(key): value for key, value in properties.items() if str(key) not in IGNORED}
    res = found.pop(ALL_RES, None)
    singles = [found.pop(key, None) for key in SINGLE_RES]
    if res is None and len(set(singles)) == 1:
        res = singles[0]  # a read with the four resistances alone
    if type(res) is not int or res < 1 or any(value not in (None, res) for value in singles):
        return None
    if len(found) > 1:
        return None
    if not found:
        return size, res, None, None
    [(companion, value)] = found.items()
    return size, res, companion, value


def facet_key(size: str, res: int, companion: str | None, value: Any) -> str:
    """'sc/5/418:20', 'lc/8/plain'."""
    return f'{size}/{res}/{"plain" if companion is None else f"{companion}:{value}"}'


def facet(item: Mapping[str, Any]) -> tuple[str, int, str | None, Any] | None:
    """`shape` of a triage item (pricing/triage/adapters.py `from_drop`): a magic charm, one at a time."""
    if item.get('category') != 'magic' or item.get('quantity', 1) != 1:
        return None
    return shape(str(item.get('name', '')), item.get('properties') or {})


@cache
def evidence(path: Path = EVIDENCE_FILE) -> Mapping[str, Any]:
    """The built evidence ({'facets': {key: record}, 'sources': ...}); empty when the file is missing."""
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return {'facets': {}}


def _comparable(key: str, size: str, res: int, companion: str | None, value: Any) -> bool:
    """A facet's trades price the item as a floor: the same size, no higher all res, and either no companion (a plain
    charm is worse than one with a suffix) or the same companion at no higher value."""
    their_size, their_res, rest = key.split('/')
    if their_size != size or int(their_res) > res:
        return False
    if rest == 'plain' or companion is None:
        return rest == 'plain'
    prop, _, theirs = rest.partition(':')
    try:
        return prop == companion and float(theirs) <= float(value)
    except TypeError, ValueError:
        return False


def band(item: Mapping[str, Any], facets: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    """The sale-backed band of the item's facet, or of its comparable-or-worse trades; None when neither has
    MIN_FILLS priced trades (the asks stay the triage's)."""
    found = facet(item)
    if found is None:
        return None
    known: Mapping[str, Any] = evidence()['facets'] if facets is None else facets
    key = facet_key(*found)
    exact = known.get(key)
    if exact is not None and len(_paid(exact)) >= MIN_FILLS:
        return _band(item, key, _trades(exact), None)
    pooled = [trade for other, record in known.items() if _comparable(other, *found) for trade in _trades(record)]
    if len([t for t in pooled if t.get('ist') is not None]) < MIN_FILLS:
        return None
    _, res, companion, value = found
    label = f'≤{res} all res' + ('' if companion is None else f', {companion} ≤{value:g}')
    return _band(item, key, pooled, label)


def _trades(record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return list(record.get('trades') or ())


def _paid(record: Mapping[str, Any]) -> list[float]:
    return [t['ist'] for t in _trades(record) if t.get('ist') is not None]


def _q1(values: list[float]) -> float:
    import statistics

    return values[0] if len(values) < 2 else statistics.quantiles(values, n=4, method='inclusive')[0]


def _band(item: Mapping[str, Any], key: str, trades: list[Mapping[str, Any]], comparison: str | None) -> dict[str, Any]:
    import statistics
    from datetime import date, timedelta

    priced = [t for t in trades if t.get('ist') is not None]
    paid = sorted(t['ist'] for t in priced)
    dates = sorted(t['date'] for t in priced)
    newest = date.fromisoformat(dates[-1])
    recent = sum(date.fromisoformat(d) > newest - timedelta(days=LIQUID_DAYS) for d in dates)
    found: dict[str, Any] = {
        'category': 'family',
        'name': str(item.get('name', '')).casefold(),
        'bucket': f'fills:{key}' + (f'|comparable:{comparison}' if comparison else ''),
        'quantity': 1,
        'price_unit': 'per item',
        'q1_ist': round(_q1(paid), 3),
        'median_ist': round(statistics.median(paid), 3),
        'min_ist': round(paid[0], 3),
        'max_ist': round(paid[-1], 3),
        'fills': len(paid),
        'sellers': len({t.get('seller') for t in priced}),
        'buyers': len({t.get('buyer') for t in priced}),
        'oldest_fill': dates[0],
        'newest_fill': dates[-1],
        'observed_at': dates[-1],
        'liquidity': 'liquid' if recent >= LIQUID_FILLS else 'thin',
        'evidence_kind': 'fills',
    }
    if comparison:
        found['fill_comparison'] = comparison
    return found


def reason(found: Mapping[str, Any]) -> str:
    """'sold 1.2-2.5 Ist (q1-median, 14 trades 2026-10-01..10-24)'."""
    span = f'{found["oldest_fill"]}..{found["newest_fill"][5:]}'
    text = f'sold {found["q1_ist"]:.3g}-{found["median_ist"]:.3g} Ist (q1-median, {found["fills"]} trades {span})'
    return text + (f' · comparable-or-worse {found["fill_comparison"]}' if found.get('fill_comparison') else '')
