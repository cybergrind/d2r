"""Review cached Guardian variants and native ED without inventing dates or prices."""

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

from pricing.knowledge.market import scope_status


ROOT = Path(__file__).resolve().parents[4]
MARKET = 'pricing/data/appraisal-market.jsonl'
# Reviewed helm/armor effects in the pinned native gem table; jewels are not scalars.
ED_EFFECTS = {'Ral Rune': 0, 'Perfect Topaz': 0, 'Cham Rune': 0, 'El Rune': 0, 'Zod Rune': 0, 'Pul Rune': 30}
NATIVE_HASHES = {
    'armor': 'ad8d490abd48b336ac22f605904202fe5132460f91e3b307d9006753b9cb0271',
    'uniqueitems': 'e6f28489942a6145d99190728071c0e7557313239517bb03c627d3d41bbad8e7',
    'gems': '8471e44185164052f2fe3564ad00519055450641c84e4a7830894d82be945670',
}


def material_review(row):
    props = row.get('properties', {})
    if (
        (row.get('rarity'), row.get('name')) != ('unique', 'Guardian Angel')
        or row.get('base_code') not in ('xlt', 'ult')
        or type(row.get('ethereal')) is not bool
        or row.get('base_upgrade') is not (row.get('base_code') == 'ult')
        or ('738' in props and props['738'] is not row['ethereal'])
        or ('1216' in props and props['1216'] is not row['base_upgrade'])
    ):
        return {'status': 'unknown_or_conflicting_variant'}
    sockets = row.get('sockets')
    contents = row.get('socket_contents')
    if (
        type(sockets) is not int
        or sockets not in (0, 1)
        or ('402' in props and (type(props['402']) is not int or props['402'] != sockets))
    ):
        return {'status': 'unknown_socket_payload'}
    insert = props.get('934')
    if contents == 'empty' and insert is None:
        contribution = 0
    elif sockets == 1 and contents == 'filled' and isinstance(insert, str) and insert in ED_EFFECTS:
        contribution = ED_EFFECTS[insert]
    else:
        return {'status': 'unknown_socket_payload'}
    total = props.get('425')
    if total is None:
        return {'status': 'missing_enhanced_defense'}
    if type(total) is not int or not 180 <= total - contribution <= 200:
        return {'status': 'conflicting_enhanced_defense'}
    return {'status': 'verified_native_ed', 'native_ed': total - contribution, 'socket_ed': contribution}


def dated_ask(row):
    try:
        date.fromisoformat(row['observed_at'][:10])
    except KeyError, TypeError, ValueError:
        return False
    return (
        row.get('evidence_kind') == 'ask'
        and row.get('listing_status') == {'active': True, 'selling': True, 'completed': False}
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
        if (row.get('rarity'), row.get('name')) != ('unique', 'Guardian Angel'):
            continue
        previous = candidates.setdefault(row['id'], row)
        if previous != row:
            raise ValueError('Conflicting duplicate Guardian observation')
    observations = []
    for row in candidates.values():
        scoped = row.get('scope_status') == 'verified' and scope_status(row.get('properties', {})) == 'verified'
        review = material_review(row) if scoped else {'status': 'unverified_scope'}
        observations.append(
            {
                'id': row['id'],
                'source': row.get('source'),
                'seller_id': row.get('seller_id'),
                'observed_at': row.get('observed_at'),
                'dated_eligible_ask': scoped and dated_ask(row),
                'base_code': row.get('base_code'),
                'ethereal': row.get('ethereal'),
                'sockets': row.get('sockets'),
                'socket_contents': row.get('socket_contents'),
                'insert': row.get('properties', {}).get('934'),
                **review,
            }
        )
    eligible = sum(r['dated_eligible_ask'] for r in observations)
    return {
        'cached_observations': len(observations),
        'dated_eligible_asks': eligible,
        'material_statuses': dict(Counter(r['status'] for r in observations)),
        'pricing_disposition': 'no_dated_comparable_evidence' if not eligible else 'requires_exact_comparison_review',
        'premium_threshold': None,
        'observations': observations,
        'limitation': 'Material evidence review; not a new trade qualification or a numerical price.',
    }


def main():
    paths = [MARKET, 'pricing/raw/traderie/guardian-angel.json', str(Path(__file__).relative_to(ROOT))]
    for name, expected in NATIVE_HASHES.items():
        path = f'third-parties/d2data/json/{name}.json'
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise ValueError('Guardian native mechanics changed; review ranges and inserts')
        paths.append(path)
    rows = [json.loads(line) for line in (ROOT / MARKET).read_text().splitlines()]
    result = {
        'schema_version': 1,
        'reviewed_at': date.today().isoformat(),
        'identity': 'Guardian Angel',
        'scope': 'SC / Non-Ladder / PC / RotW',
        'inputs': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        **audit(rows),
    }
    (ROOT / 'pricing/data/appraisal-guardian-material-review.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('inputs', 'observations')}))


if __name__ == '__main__':
    main()
