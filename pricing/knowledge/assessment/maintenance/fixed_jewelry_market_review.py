"""Offline comparison audit for explicitly reviewed fixed-stat unique jewelry items."""

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, date, datetime

from inventory_tracking.items.metadata import decode_stats, metadata
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.maintenance.fixed_market_review import MARKET
from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.definition_store import catalog
from pricing.knowledge.names import normalize_name
from pricing.knowledge.refresh import atomic_json


# Reviewed against native uniqueitems 122,269,119,273. Values here are game values;
# fixed-point encoding is applied using the native stat definition below.
SPECS = {
    "Atma's Scarab": {45: 75, 89: 3, 78: 5, 119: 20},
    'The Stone of Jordan': {9: 20, 77: 25, 50: 1, 51: 12, 127: 1},
    "The Cat's Eye": {96: 30, 93: 20, 31: 100, 32: 100, 2: 25},
    'The Mahim-Oak Curio': {0: 10, 1: 10, 2: 10, 3: 10, 31: 10, 119: 10, 39: 10, 41: 10, 43: 10, 45: 10, 16: 10},
}
OUTPUT = 'pricing/data/appraisal-fixed-jewelry-market-review.json'


def template_contract(name):
    if name not in SPECS:
        raise ValueError('Item is not a reviewed fixed jewelry identity')
    definition = catalog().named['unique', name]
    ranges = definition['roll_ranges']
    expected = {str(stat): value for stat, value in SPECS[name].items()}
    if set(ranges) != set(expected) or any(
        r['min'] != expected[k] or r['max'] != expected[k] for k, r in ranges.items()
    ):
        raise ValueError('Reviewed fixed jewelry definition changed')
    extra_raw = []
    if name == "Atma's Scarab":
        if definition.get('fixed_triggers') != (
            {'stat_id': 198, 'skill_id': 66, 'level': 2, 'chance': 5},
        ) or definition.get('fixed_poison_effect') != {
            'minimum_rate_raw': 102,
            'maximum_rate_raw': 102,
            'duration_frames': 100,
            'source_count': 1,
        }:
            raise ValueError('Reviewed fixed jewelry definition changed')
        extra_raw = [
            {'id': stat, 'layer': layer, 'raw': value}
            for stat, layer, value in ((57, 0, 102), (58, 0, 102), (59, 0, 100), (326, 0, 1), (198, 4226, 5))
        ]
    return native_jewelry_contract(name, SPECS[name], extra_raw=extra_raw)


def native_jewelry_contract(name, values, *, extra_raw=()):
    """Decode an explicitly reviewed jewelry configuration."""
    definition = catalog().named['unique', name]
    base = definition['base_definition']
    raw = [
        {'id': stat, 'layer': 0, 'raw': value << metadata()['stats'][str(stat)]['shift']}
        for stat, value in values.items()
    ]
    raw.extend(extra_raw)
    decoded, affixes, unresolved = decode_stats(raw, base=base)
    facts = normalize(
        {
            'item': {
                'name': name,
                'base_name': base['name'],
                'base_code': base['code'],
                'rarity': 'unique',
                'affixes': affixes,
                'identified': True,
                'ethereal': False,
                'sockets': 0,
                'socket_contents': 'empty',
                'socket_items': [],
            },
            'source': {
                'stat_capture_complete': True,
                'kind': 'reviewed_definition_template',
                'item_identity': {'table': 'unique', 'table_id': definition['game_definition']['*ID']},
            },
            'decoded_stats': decoded,
            'unresolved_stats': unresolved,
        }
    )
    contract, gaps = NamedHandler().contract(facts, 'jewelry')
    if contract is None or gaps:
        raise ValueError(f'Fixed jewelry comparison incomplete for {name}: {gaps}')
    return contract.to_dict()


def audit(observations, as_of):
    rows = []
    for name in SPECS:
        contract = template_contract(name)
        candidates = [r for r in observations if normalize_name(r.get('name')) == normalize_name(name)]
        compared = evaluate(contract, candidates)
        price = price_from_comparables(compared, today=as_of)
        if price.get('unavailable_reason') == 'unclassified':
            raise ValueError('Unclassified fixed jewelry price cannot be reviewed')
        rows.append(
            {
                'name': name,
                'quality': 'unique',
                'base_code': contract['base_code'],
                'contract': contract,
                'unit_quantity': 1,
                'disposition': 'estimate' if price['estimate_ist'] is not None else 'evidence_unavailable',
                'price': price,
                'cached_observations': len(candidates),
                'accepted_observations': [
                    {k: r.get(k) for k in ('listing_id', 'seller_id', 'source', 'observed_at')}
                    for r in compared['accepted']
                ],
                'rejection_counts': dict(Counter(reason for r in compared['rejected'] for reason in r['reasons'])),
            }
        )
    return rows


def review_inputs(root, observations, names):
    # Pin all appraisal/decoder code so changes to transitive comparison logic
    # invalidate this audit, as well as the definition and market generations.
    paths = {
        MARKET,
        'pricing/data/appraisal-market-manifest.json',
        'pricing/data/appraisal-definitions.json',
        'pricing/data/appraisal-properties.json',
        'inventory_tracking/items/data/item_metadata.json',
        'third-parties/d2data/json/uniqueitems.json',
        'pricing/data/wp-f-ladder.json',
    }
    for directory in ('pricing/knowledge', 'inventory_tracking/items'):
        paths.update(
            p.relative_to(root).as_posix()
            for p in (root / directory).rglob('*')
            if p.is_file() and p.suffix in ('.py', '.json')
        )
    manifest = json.loads((root / 'pricing/data/appraisal-market-manifest.json').read_text())
    for row in observations:
        if normalize_name(row.get('name')) not in {normalize_name(n) for n in names}:
            continue
        source = row.get('source')
        if not isinstance(source, str) or not source.startswith('pricing/raw/'):
            raise ValueError('Fixed jewelry audit requires preserved raw evidence')
        path = (root / source).resolve()
        hashes = {r.get('sha256') for r in manifest['files'] if r.get('path') == source}
        if (
            not path.is_relative_to(root.resolve())
            or not path.is_file()
            or len(hashes) != 1
            or hashlib.sha256(path.read_bytes()).hexdigest() not in hashes
        ):
            raise ValueError('Fixed jewelry audit raw evidence is stale')
        paths.add(source)
    return {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in sorted(paths)}


def build_review(root, as_of):
    observations = [json.loads(line) for line in (root / MARKET).read_text().splitlines()]
    return {
        'schema_version': 1,
        'scope': 'reviewed_fixed_unique_jewelry_identities',
        'as_of': as_of.isoformat(),
        'inputs': review_inputs(root, observations, SPECS),
        'rows': audit(observations, as_of),
    }


def apply_reviews(rows, review, root):
    if review is None:
        return
    try:
        as_of = date.fromisoformat(review['as_of'])
        expected = build_review(root, as_of)
    except (KeyError, TypeError, ValueError, OSError) as error:
        raise ValueError('Fixed jewelry review cannot be verified') from error
    if review != expected:
        raise ValueError('Fixed jewelry review is stale, altered or incomplete')
    indexed = {record['name']: (index, record) for index, record in enumerate(review['rows'])}
    for row in rows:
        if (
            row.get('kind') != 'identity'
            or row.get('category') != 'unique'
            or row.get('name') not in indexed
            or row['dimensions']['discovery']['state'] != 'reviewed'
        ):
            continue
        index, record = indexed[row['name']]
        native = catalog().named['unique', row['name']]['game_definition']['*ID']
        if row.get('catalog_ids') != [f'unique{native}']:
            continue
        outcome = record['price'].get('unavailable_reason', 'supported dated asks')
        row['dimensions']['market'] = {
            'state': 'reviewed',
            'disposition': record['disposition'],
            'unit_quantity': 1,
            'reason': f'Reviewed fixed unique jewelry comparison: {outcome}; one identified native item.',
            'sources': [{'artifact': 'fixed_jewelry_market_reviews', 'locator': f'/rows/{index}'}],
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', type=date.fromisoformat, default=datetime.now(UTC).date())
    args = parser.parse_args()
    review = build_review(ROOT, args.as_of)
    atomic_json(ROOT / OUTPUT, review)
    print(
        json.dumps(
            [
                {k: r[k] for k in ('name', 'disposition', 'cached_observations', 'rejection_counts', 'price')}
                for r in review['rows']
            ]
        )
    )


if __name__ == '__main__':
    main()
