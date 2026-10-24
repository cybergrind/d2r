"""Regenerate loot/data/base-floor.json: the plain white and superior bases the offline triage prices clearly under the
loop's worth-the-cells floor (loot/base_floor.py), one key per base, quality, ethereal flag, sockets and ED grade.

Asymmetric (the player, 2026-10-23: "we absolutely MUST NOT trash good items"): a key is written only when the
triage's band fits the facts exactly (the sockets, the ethereal flag and the quality in its bucket; the ED relaxed only
for an ordinary ED under 15, every ordinary roll of it junk), has at least SELLERS sellers, says `vendor` or `slow`,
names no demand row (a runeword or merc base the guides recommend for exactly these facts) and no own use, and both its
decision price and its median are clearly under the floor (CLEARLY). A keep key: any band prices it at or above the
floor, thin or pooled (base_floor.py PLAIN_BY_RULES takes it whatever the rules say).

Prices are the repo's (pricing/triage on the KB's bands, never the web). The KB is a build input only.
Run: uv run --offline python -m inventory_tracking.loot.build_base_floor
"""

import argparse
import datetime
from collections.abc import Iterator, Mapping
from typing import Any

from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot import base_floor
from inventory_tracking.reports import publish


__all__ = ['CLEARLY', 'SELLERS', 'build', 'judge', 'junk_record', 'keep_record', 'main']

# "Clearly under" the floor: the median at most this share of it (a band at 0.99 Ist is no clear junk)
CLEARLY = 0.9
SELLERS = 3  # the triage's own least for a band (pricing/triage/bands.py: fewer is liquidity 'none')
ORDINARY_EDS = (0, 14)  # a superior's ordinary ED rolls, the worst and the best: both must be junk
PERFECT_ED = 15
ED_PROPERTY = {'weapons': '510', 'armor': '425'}  # the categories priced (pricing/knowledge/base_evidence.py)


def _item(base: Mapping[str, Any], rarity: str, ethereal: bool, sockets: int, ed: int) -> dict[str, Any]:
    """The triage's item for a clean, empty base of these facts (pricing/knowledge/base_evidence.py `plain_item`)."""
    from pricing.api import plain_base_item

    return plain_base_item(base, rarity, ethereal, sockets, ed)


def junk_record(result: Mapping[str, Any], *, rarity: str, ethereal: bool, sockets: int, perfect: bool) -> dict | None:
    """The table's record when the triage `result` prices these facts clearly under the floor (the module text),
    None when the loop keeps them. Pure."""
    band = result.get('band') or {}
    price, median = result.get('decision_ist'), band.get('median_ist')
    if result.get('verdict') not in base_floor.SELLS_OVER or price is None or median is None:
        return None
    if result.get('demand') or result.get('own_use') or band.get('evidence_kind') != 'asks':
        return None
    if (band.get('sellers') or 0) < SELLERS or band.get('liquidity') not in ('liquid', 'thin'):
        return None
    relaxed = set(band.get('relaxed_facets') or ())
    if relaxed - {'base_ed'} or (relaxed and perfect):
        return None
    bucket = str(band.get('bucket') or result.get('bucket') or '')
    exact = (f'"sockets":{sockets}', f'"ethereal":{"true" if ethereal else "false"}', f'"rarity":"{rarity}"')
    if not all(part in bucket for part in exact):
        return None
    if max(price, median) > CLEARLY * base_floor.FLOOR_IST:
        return None
    return {
        'q1': round(band.get('q1_ist') or price, 3),
        'median': round(median, 3),
        'sellers': band['sellers'],
        'observed': band.get('observed_at'),
        'verdict': result['verdict'],
    }


def keep_record(result: Mapping[str, Any]) -> dict | None:
    """The table's keep record when the triage `result` prices these facts at or above the floor by any band, thin or
    pooled, names a demand row for them (a runeword or merc base a guide recommends for exactly these facts) or says
    `check` (a guide-listed base with too few sellers): "we absolutely MUST NOT trash good items" (the player,
    2026-10-23). None else. Pure."""
    band = result.get('band') or {}
    prices = [price for price in (result.get('decision_ist'), band.get('median_ist')) if price is not None]
    demand = [row.get('runeword') or row.get('original_label') or row.get('kind') for row in result.get('demand') or ()]
    if result.get('verdict') == 'check':
        demand.append('guide-listed, check')  # the triage's own doubt (a guide's base with too few sellers): kept
    if not demand and (not prices or max(prices) < base_floor.FLOOR_IST):
        return None
    return {
        'q1': round(band.get('q1_ist') or min(prices), 3) if prices else None,
        'median': round(band.get('median_ist') or max(prices), 3) if prices else None,
        'sellers': band.get('sellers'),
        'observed': band.get('observed_at'),
        'verdict': result.get('verdict'),
        **({'demand': sorted({str(name) for name in demand})[:3]} if demand else {}),
    }


def judge(
    tables: Any, base: Mapping[str, Any], rarity: str, ethereal: bool, sockets: int, perfect: bool
) -> tuple[str, dict] | None:
    """('junk', record) when every ED roll of the key is junk (`junk_record`, ORDINARY_EDS for an ordinary superior),
    ('keep', record) when any is priced at or above the floor (`keep_record`), None else."""
    from pricing.api import triage_assess as assess

    eds = (0,) if rarity == 'normal' else (PERFECT_ED,) if perfect else ORDINARY_EDS
    results = [assess(_item(base, rarity, ethereal, sockets, ed), tables) for ed in eds]
    kept = [record for result in results if (record := keep_record(result)) is not None]
    if kept:
        return 'keep', max(kept, key=lambda record: record['median'] or 0)
    facts = {'rarity': rarity, 'ethereal': ethereal, 'sockets': sockets, 'perfect': perfect}
    junk = [junk_record(result, **facts) for result in results]
    if all(record is not None for record in junk):
        return 'junk', max((record for record in junk if record is not None), key=lambda record: record['median'])
    return None


def _facts(bases: Mapping[str, Mapping[str, Any]]) -> Iterator[tuple[Mapping[str, Any], str, bool, int, bool]]:
    for base in bases.values():
        if base.get('category') not in ED_PROPERTY:
            continue
        for rarity in ('normal', 'superior'):
            for ethereal in (False, True):
                for sockets in range(int(base.get('max_sockets') or 0) + 1):
                    for perfect in (False, True) if rarity == 'superior' else (False,):
                        yield base, rarity, ethereal, sockets, perfect


def build(tables: Any, bases: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    found: dict[str, dict[str, dict]] = {'junk': {}, 'keep': {}}
    for base, rarity, ethereal, sockets, perfect in _facts(bases):
        judged = judge(tables, base, rarity, ethereal, sockets, perfect)
        if judged is not None:
            kind, record = judged
            named = base_floor.key(base['code'], rarity, ethereal=ethereal, sockets=sockets, perfect=perfect)
            found[kind][named] = record
    return {
        'built': datetime.date.today().isoformat(),
        'source': 'pricing/triage (offline KB bands, Traderie asks SC/NL/PC/RotW), loot/build_base_floor.py',
        'floor_ist': base_floor.FLOOR_IST,
        'junk': dict(sorted(found['junk'].items())),
        'keep': dict(sorted(found['keep'].items())),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.parse_args(argv)
    from pricing.api import triage_tables

    report = build(triage_tables.load(), metadata()['bases'])
    publish(base_floor.TABLE, report)
    print(f'{len(report["junk"])} junk and {len(report["keep"])} keep keys -> {base_floor.TABLE}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
