"""Exhaustive pricing audits for reviewed unique jewelry roll combinations."""

import argparse
import json
from collections import Counter
from datetime import UTC, date, datetime
from itertools import product

from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
from pricing.knowledge.assessment.maintenance.fixed_jewelry_market_review import native_jewelry_contract, review_inputs
from pricing.knowledge.assessment.maintenance.fixed_market_review import MARKET
from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.definition_store import catalog
from pricing.knowledge.names import normalize_name
from pricing.knowledge.refresh import atomic_json


NAME = "Mara's Kaleidoscope"
OUTPUT = 'pricing/data/appraisal-variable-jewelry-market-review.json'
# Each axis describes correlated native stats, bounds, native property slot/name,
# and a readable discriminator. Separate axes roll independently.
SPECS = {
    NAME: ({127: 2, 0: 5, 1: 5, 2: 5, 3: 5}, (((39, 41, 43, 45), 20, 30, 2, 'res-all', 'all_resistance'),)),
    'Dwarf Star': (
        {79: 100, 11: 40, 28: 15, 7: 40, 142: 15},
        (((35,), 12, 15, 5, 'red-mag', 'magic_damage_reduction'),),
    ),
    'Nagelring': (
        {35: 3, 78: 3},
        (
            ((19,), 50, 75, 3, 'att', 'attack_rating'),
            ((80,), 15, 30, 4, 'mag%', 'magic_find'),
        ),
    ),
}


def template_contract(roll, *, name=NAME):
    if name not in SPECS:
        raise ValueError('Unreviewed variable jewelry identity')
    fixed, axes = SPECS[name]
    rolls = (roll,) if len(axes) == 1 else roll
    if not isinstance(rolls, tuple) or len(rolls) != len(axes):
        raise ValueError('Jewelry roll dimensions differ from reviewed axes')
    definition = catalog().named['unique', name]
    expected = {str(stat): (value, value) for stat, value in fixed.items()}
    values = dict(fixed)
    native = definition['game_definition']
    for value, (stats, lower, upper, slot, prop, label) in zip(rolls, axes, strict=True):
        if type(value) is not int or not lower <= value <= upper:
            raise ValueError(f'{name} {label.replace("_", " ")} roll must be an integer from {lower} to {upper}')
        expected.update({str(stat): (lower, upper) for stat in stats})
        values.update(dict.fromkeys(stats, value))
        if (native.get(f'prop{slot}'), native.get(f'min{slot}'), native.get(f'max{slot}')) != (prop, lower, upper):
            raise ValueError('Jewelry definition changed; roll correlation requires review')
    actual = {k: (r['min'], r['max']) for k, r in definition['roll_ranges'].items()}
    if actual != expected:
        raise ValueError('Jewelry definition changed; roll inventory requires review')
    return native_jewelry_contract(name, values)


def audit(observations, as_of, *, name=NAME):
    candidates = [r for r in observations if normalize_name(r.get('name')) == normalize_name(name)]
    rows = []
    _, axes = SPECS[name]
    for rolls in product(*(range(axis[1], axis[2] + 1) for axis in axes)):
        contract = template_contract(rolls[0] if len(axes) == 1 else rolls, name=name)
        compared = evaluate(contract, candidates)
        price = price_from_comparables(compared, today=as_of)
        if price.get('unavailable_reason') == 'unclassified':
            raise ValueError('Unclassified variable jewelry comparison result')
        rows.append(
            {
                'name': name,
                **{axis[-1]: value for axis, value in zip(axes, rolls, strict=True)},
                'contract': contract,
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


def build_review(root, as_of):
    observations = [json.loads(line) for line in (root / MARKET).read_text().splitlines()]
    return {
        'schema_version': 1,
        'scope': 'reviewed_unique_jewelry_roll_partitions',
        'as_of': as_of.isoformat(),
        'inputs': review_inputs(root, observations, SPECS),
        'rows': [row for name in SPECS for row in audit(observations, as_of, name=name)],
    }


def apply_reviews(rows, review, root):
    if review is None:
        return
    try:
        expected = build_review(root, date.fromisoformat(review['as_of']))
    except (ValueError, KeyError, TypeError, OSError) as error:
        raise ValueError('Variable jewelry market review cannot be verified') from error
    if review != expected:
        raise ValueError('Variable jewelry market review is stale, altered or missing roll outcomes')
    for row in rows:
        name = row.get('name')
        if name not in SPECS:
            continue
        native_id = catalog().named['unique', name]['game_definition']['*ID']
        if (row.get('kind'), row.get('name'), row.get('category'), row.get('catalog_ids')) != (
            'identity',
            name,
            'unique',
            [f'unique{native_id}'],
        ) or row['dimensions']['discovery']['state'] != 'reviewed':
            continue
        row['dimensions']['market'] = {
            'state': 'reviewed',
            'disposition': 'reviewed_roll_partition',
            'unit_quantity': 1,
            'reason': (
                'All eleven correlated resistance rolls have separate reviewed price dispositions.'
                if name == NAME
                else 'All four magic damage reduction rolls have separate reviewed price dispositions.'
                if name == 'Dwarf Star'
                else 'All 416 independent attack-rating and magic-find combinations have reviewed price dispositions.'
            ),
            'sources': [{'artifact': 'variable_jewelry_market_reviews', 'locator': '/rows'}],
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
                {
                    k: v
                    for k, v in r.items()
                    if k
                    in (
                        'name',
                        'all_resistance',
                        'magic_damage_reduction',
                        'attack_rating',
                        'magic_find',
                        'disposition',
                        'price',
                    )
                }
                for r in review['rows']
            ]
        )
    )


if __name__ == '__main__':
    main()
