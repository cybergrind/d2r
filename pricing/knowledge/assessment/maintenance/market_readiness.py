"""Audit market evidence prerequisites, not modifier equivalence or prices.

Run offline with --as-of YYYY-MM-DD for a reproducible research queue.
"""

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path

from pricing.knowledge.assessment.adapters.capture import bases_by_code
from pricing.knowledge.assessment.comparables import SCOPE_PROPERTIES, publication_rows
from pricing.knowledge.assessment.handlers.socket_fillers import filler_effects
from pricing.knowledge.assessment.mechanics.socket_effects import BOOLEAN_SOCKET_STATS
from pricing.knowledge.assessment.observations import superseded_rows
from pricing.knowledge.assessment.registry import FAMILIES
from pricing.knowledge.market import scope_status, valid_positive


ROOT = Path(__file__).resolve().parents[4]
NAMED = {'unique': 'unique', 'uniques': 'unique', 'set': 'set', 'sets': 'set'}
ITEM_CATEGORIES = {*NAMED, 'base', 'misc', 'charms', 'crafted', 'runewords'}
RARITIES = {'unique', 'set', 'normal', 'superior', 'low quality', 'magic', 'rare', 'crafted', 'runeword'}


def policy(category, quality):
    if category in NAMED:
        return 'named'
    if category == 'runewords':
        return 'runeword'
    if category == 'crafted' or quality in ('magic', 'rare', 'crafted'):
        return 'affixed'
    return 'base' if quality in ('normal', 'superior', 'low quality') else 'unclassified'


def supported_payload(row, sockets):
    """Check explicit payload structure; captured contribution checks run later."""
    base = bases_by_code().get(row.get('base_code'), {})
    family = next((f.name for f in FAMILIES if base.get('type') in f.types), None)
    effects = filler_effects(family)
    payload = row.get('properties', {}).get('934')
    if not isinstance(payload, str):
        return False
    names = [name.strip() for name in payload.split(',')]
    if not 1 <= len(names) <= sockets or any(name not in effects for name in names):
        return False
    bonuses = Counter()
    for name in names:
        bonuses.update(effects[name])
    return all(bonuses[stat] <= 1 for stat in BOOLEAN_SOCKET_STATS)


def gaps(row, today):
    result = []
    expected = NAMED.get(row.get('category')) or {'runewords': 'runeword', 'crafted': 'crafted'}.get(
        row.get('category')
    )
    if row.get('rarity') not in RARITIES or (expected and row.get('rarity') != expected):
        result.append('rarity')
    if not row.get('base_code'):
        result.append('base_code')
    if type(row.get('ethereal')) is not bool:
        result.append('ethereal')
    sockets = row.get('sockets')
    if (
        type(sockets) not in (int, float)
        or not math.isfinite(sockets)
        or sockets != int(sockets)
        or not 0 <= sockets <= 6
    ):
        result.append('sockets')
    contents = row.get('socket_contents')
    if row.get('category') == 'runewords':
        if row.get('base_rarity') not in ('normal', 'superior', 'low quality'):
            result.append('base_rarity')
        if contents != 'filled' or 'sockets' in result or not sockets:
            result.append('socket_contents')
    elif contents == 'filled':
        if 'sockets' in result or not supported_payload(row, sockets):
            result.append('filled_socket_comparison')
    elif contents != 'empty':
        result.append('socket_contents')
    if row.get('mechanics_conflicts'):
        result.append('mechanics_conflict')
    if row.get('evidence_kind') != 'ask':
        result.append('not_ask')
    if row.get('unit_policy') != 'single_item':
        result.append('unit')
    if not row.get('seller_id'):
        result.append('seller')
    if not valid_positive(row.get('ask_ist')):
        result.append('price')
    _, excluded = publication_rows([row], today)
    result.extend(excluded)
    return result


def audit(rows, *, today, all_items=False):
    rows = list(rows)
    superseded = superseded_rows(rows)
    seen = set()
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        category = row.get('category')
        quality = NAMED.get(category)
        if all_items and category in ITEM_CATEGORIES:
            quality = quality or row.get('rarity') or 'unknown'
        if quality is None or not row.get('name') or i in superseded:
            continue
        identity = (row.get('listing_id'), row.get('observed_at'))
        if row.get('listing_id'):
            if identity in seen:
                continue
            seen.add(identity)
        properties = row.get('properties', {})
        if row.get('scope_status') != 'verified' or (
            SCOPE_PROPERTIES & properties.keys() and scope_status(properties) != 'verified'
        ):
            continue
        groups[quality, row['name'], policy(category, quality)].append(row)
    items = []
    totals = defaultdict(Counter)
    for (quality, name, selected_policy), candidates in sorted(groups.items()):
        counts, examples, ready = Counter(), defaultdict(list), 0
        for row in candidates:
            missing = gaps(row, today)
            ready += not missing
            counts.update(missing)
            for key in missing:
                if len(examples[key]) < 2:
                    examples[key].append({k: row.get(k) for k in ('listing_id', 'source')})
        items.append(
            {
                **({'policy': selected_policy} if all_items else {}),
                'quality': quality,
                'name': name,
                'scoped_observations': len(candidates),
                'structurally_ready': ready,
                'gaps': dict(sorted(counts.items())),
                'examples': dict(examples),
            }
        )
        totals[selected_policy].update(scoped_observations=len(candidates), structurally_ready=ready, identities=1)
    return {
        'schema_version': 1,
        **({'by_policy': {key: dict(value) for key, value in sorted(totals.items())}} if all_items else {}),
        'as_of': today.isoformat(),
        'limitation': (
            'Structural prerequisites only. Ready rows may still lack required rolls, match no captured variant, '
            'fail captured socket-contribution checks, or fail independent-seller/dispersion gates. '
            'No tier or price is inferred.'
        ),
        'items': items,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', type=date.fromisoformat, default=datetime.now(UTC).date())
    parser.add_argument('--all-items', action='store_true', help='Include base, magic, rare, crafted and runeword rows')
    args = parser.parse_args()
    path = ROOT / 'pricing/data/appraisal-market.jsonl'
    with path.open() as stream:
        result = audit((json.loads(line) for line in stream), today=args.as_of, all_items=args.all_items)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
