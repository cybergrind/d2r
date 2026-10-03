"""Offline review of Andariel material-roll evidence; never a replacement price contract.

Only an explicit single Ral insert proves unchanged strength, leech and ED here.
Unknown occupancy and unspecified jewels cannot certify those intrinsic rolls.
Missing ED is retained as missing, even when a total defense value is advertised.
"""

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

from pricing.knowledge.assessment.mechanics.socket_evidence import NATIVE_HASHES, reviewed_native
from pricing.knowledge.market import scope_status


ROOT = Path(__file__).resolve().parents[4]
MARKET = 'pricing/data/appraisal-market.jsonl'
RAW = 'pricing/raw/traderie/wpi-andariel-s-visage.json'
BOUNDS = {'437': (25, 30), '462': (8, 10), '425': (100, 150)}


def intrinsic_rolls(row):
    props = row.get('properties', {})
    if (
        (row.get('rarity'), row.get('name'), row.get('base_code')) != ('unique', "Andariel's Visage", 'usk')
        or type(row.get('ethereal')) is not bool
        or ('738' in props and props['738'] is not row['ethereal'])
        or row.get('base_upgrade') is not False
        or type(row.get('sockets')) is not int
        or row['sockets'] != 1
        or ('402' in props and (type(props['402']) is not int or props['402'] != 1))
        or row.get('socket_contents') != 'filled'
        or props.get('934') != 'Ral Rune'
    ):
        return None
    values = {}
    for key, (low, high) in BOUNDS.items():
        value = props.get(key)
        if value is None and key == '425':
            continue
        if type(value) is not int or not low <= value <= high:
            return None
        values[key] = value
    return values


def eligible(row):
    try:
        date.fromisoformat(row['observed_at'][:10])
    except KeyError, TypeError, ValueError:
        return False
    return (
        (row.get('rarity'), row.get('name')) == ('unique', "Andariel's Visage")
        and row.get('scope_status') == 'verified'
        and scope_status(row.get('properties', {})) == 'verified'
        and row.get('evidence_kind') == 'ask'
        and row.get('listing_status', {}).get('active') is True
        and row.get('listing_status', {}).get('selling') is True
        and row.get('listing_status', {}).get('completed') is False
        and row.get('unit_policy') == 'single_item'
        and type(row.get('amount')) is int
        and row['amount'] == 1
        and bool(row.get('seller_id'))
        and type(row.get('ask_ist')) in (int, float)
        and 0 < row['ask_ist'] < float('inf')
    )


def audit(rows):
    candidates = {}
    for row in rows:
        if eligible(row):
            previous = candidates.setdefault(row['id'], row)
            if previous != row:
                raise ValueError('Conflicting duplicate Andariel market observation')
    proven = []
    gaps = Counter()
    for row in candidates.values():
        rolls = intrinsic_rolls(row)
        if rolls is None:
            gaps['unknown_or_conflicting_variant_or_payload'] += 1
            continue
        if '425' not in rolls:
            gaps['missing_intrinsic_enhanced_defense'] += 1
        proven.append(
            {
                'id': row['id'],
                'seller_id': row['seller_id'],
                'observed_at': row['observed_at'],
                'ethereal': row['ethereal'],
                'sockets': 1,
                'insert': 'Ral Rune',
                'native_rolls': rolls,
                'source': row['source'],
            }
        )
    complete = [r for r in proven if set(r['native_rolls']) == set(BOUNDS)]
    cohorts = {}
    for row in complete:
        key = (row['ethereal'], *[row['native_rolls'][k] for k in BOUNDS])
        cohorts.setdefault(key, set()).add(row['seller_id'])
    # This review does not implement missing exact fixed modifiers or currency
    # comparisons, so even a larger future cohort must be re-evaluated explicitly.
    return {
        'eligible_asks': len(candidates),
        'verified_intrinsic_rows': len(proven),
        'verified_intrinsic_sellers': len({r['seller_id'] for r in proven}),
        'complete_material_roll_rows': len(complete),
        'complete_material_roll_sellers': len({r['seller_id'] for r in complete}),
        'exact_material_cohort_seller_counts': sorted(len(sellers) for sellers in cohorts.values()),
        'pricing_disposition': 'requires_exact_comparison_review'
        if any(len(sellers) >= 3 for sellers in cohorts.values())
        else 'insufficient_variant_evidence',
        'premium_threshold': None,
        'gaps': dict(gaps),
        'verified_native_observations': proven,
        'limitation': 'Material-roll review only; not exact comparison eligibility or completed trade qualification.',
    }


def main():
    if not reviewed_native(ROOT):
        raise ValueError('Native socket mechanics changed; review Ral effects before rebuilding')
    rows = [json.loads(line) for line in (ROOT / MARKET).read_text().splitlines()]
    paths = [
        MARKET,
        RAW,
        'pricing/data/wp-i-uniques-misc.json',
        'pricing/data/wp-a-builds.json',
        str(Path(__file__).relative_to(ROOT)),
        *[f'third-parties/d2data/json/{name}.json' for name in NATIVE_HASHES],
    ]
    document = {
        'schema_version': 1,
        'reviewed_at': date.today().isoformat(),
        'identity': "Andariel's Visage",
        'scope': 'SC / Non-Ladder / PC / RotW',
        'inputs': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        'reviewed_source_locators': [
            'pricing/data/wp-i-uniques-misc.json:/UQ-andariel-s-visage',
            'pricing/data/wp-a-builds.json:/poison-nova-necromancer/variants/1/merc/Helmet/0',
            'pricing/data/wp-a-builds.json:/blessed-hammer-paladin/variants/1/merc/Helmet/0',
        ],
        'material_stats': {
            'strength': '25-30; native roll, cannot be established from unspecified jewel totals',
            'life_steal': '8-10%; joint perfect strength/leech is a historical premium lead, not proven here',
            'enhanced_defense': '100-150%; secondary roll; no supported premium boundary',
            'ethereal': 'Mercenary variant distinction; never inferred from absent listing flag',
            'socket_payload': 'Ral and IAS/fire-resistance jewels are distinct variants; do not pool prices',
        },
        **audit(rows),
    }
    output = ROOT / 'pricing/data/appraisal-andariel-material-review.json'
    output.write_text(json.dumps(document, indent=2) + '\n')
    print(
        json.dumps(
            {
                k: document[k]
                for k in (
                    'eligible_asks',
                    'verified_intrinsic_rows',
                    'complete_material_roll_sellers',
                    'pricing_disposition',
                )
            }
        )
    )


if __name__ == '__main__':
    main()
