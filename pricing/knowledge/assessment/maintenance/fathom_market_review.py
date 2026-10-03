"""Bounded native cold-damage research for cached Death's Fathom asks."""

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

from pricing.knowledge.assessment.maintenance.trade_waterwalk_evidence import exclusion
from pricing.knowledge.assessment.mechanics.socket_evidence import NATIVE_HASHES, reviewed_native


ROOT = Path(__file__).resolve().parents[4]
MARKET = 'pricing/data/appraisal-market.jsonl'
COLD_FACETS = {'Rainbow Facet: Cold Death', 'Rainbow Facet: Cold Level-Up'}


def cold_review(row):
    props = row.get('properties', {})
    sockets, contents, insert = row.get('sockets'), row.get('socket_contents'), props.get('934')
    if (
        (row.get('rarity'), row.get('name'), row.get('base_code')) != ('unique', "Death's Fathom", 'obf')
        or (sockets is not None and (type(sockets) is not int or sockets not in (0, 1)))
        or ('402' in props and (type(props['402']) is not int or props['402'] not in (0, 1)))
        or (sockets is not None and '402' in props and sockets != props['402'])
        or ((contents == 'filled' or insert is not None) and (sockets == 0 or props.get('402') == 0))
        or (contents == 'empty' and insert is not None)
        or ('1216' in props and props['1216'] is not False)
        or props.get('930') not in (None, 'Elite')
    ):
        return {'status': 'conflicting_variant'}
    total = props.get('747')
    if total is None:
        return {'status': 'missing_cold_skill_damage'}
    if type(total) is not int or not 15 <= total <= 35:
        return {'status': 'invalid_cold_total'}
    if contents == 'empty' or sockets == 0 or props.get('402') == 0:
        if total > 30:
            return {'status': 'invalid_cold_total'}
        return {'status': 'verified_empty_cold', 'native_cold_range': [total, total]}
    if contents == 'filled' and isinstance(insert, str) and insert in COLD_FACETS:
        low, high = max(15, total - 5), min(30, total - 3)
        if low > high:
            return {'status': 'invalid_cold_total'}
        return {
            'status': 'bounded_cold_facet',
            'native_cold_range': [low, high],
            'facet_cold_range': [total - high, total - low],
        }
    return {'status': 'unknown_socket_contribution'}


def audit(rows):
    unique = {}
    for row in rows:
        if (row.get('rarity'), row.get('name')) != ('unique', "Death's Fathom"):
            continue
        if not isinstance(row.get('id'), str) or not row['id']:
            raise ValueError('Fathom observation needs an ID')
        if unique.setdefault(row['id'], row) != row:
            raise ValueError('Conflicting Fathom observation')
    records = []
    for row in unique.values():
        reason = exclusion(row)
        review = {'status': reason} if reason else cold_review(row)
        records.append(
            {
                'id': row['id'],
                'seller_id': row.get('seller_id'),
                'observed_at': row.get('observed_at'),
                'ethereal': row.get('ethereal'),
                'properties': row.get('properties'),
                **review,
            }
        )
    return {
        'observations': records,
        'statuses': dict(Counter(r['status'] for r in records)),
        'native_perfect_sellers': sorted({r['seller_id'] for r in records if r.get('native_cold_range') == [30, 30]}),
        'trade_threshold': None,
        'limitation': (
            'Native cold bounds only. Ethereal status, resistances, facet pierce/trigger '
            'and exact comparable pricing remain separate.'
        ),
    }


def main():
    if not reviewed_native(ROOT):
        raise ValueError('Native tables changed; review Fathom and facet bounds')
    native = json.loads((ROOT / 'third-parties/d2data/json/uniqueitems.json').read_bytes())
    if any(
        native[key].get(field) != value
        for key, field, value in (
            ('354', 'prop2', 'extra-cold'),
            ('354', 'min2', 15),
            ('354', 'max2', 30),
            ('393', 'prop3', 'extra-cold'),
            ('393', 'min3', 3),
            ('393', 'max3', 5),
            ('397', 'prop3', 'extra-cold'),
            ('397', 'min3', 3),
            ('397', 'max3', 5),
        )
    ):
        raise ValueError('Fathom native cold definitions conflict')
    rows = [json.loads(line) for line in (ROOT / MARKET).read_text().splitlines()]
    paths = [
        MARKET,
        str(Path(__file__).relative_to(ROOT)),
        'pricing/knowledge/assessment/maintenance/trade_waterwalk_evidence.py',
        'pricing/knowledge/assessment/maintenance/trade_war_traveler_evidence.py',
        'pricing/knowledge/market.py',
        'pricing/data/wp-f-ladder.json',
        *[f'third-parties/d2data/json/{name}.json' for name in NATIVE_HASHES],
    ]
    paths += sorted({r['source'] for r in rows if r.get('name') == "Death's Fathom"})
    result = {
        'schema_version': 1,
        'reviewed_at': date.today().isoformat(),
        'scope': 'SC / Non-Ladder / PC / RotW',
        'inputs': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        **audit(rows),
    }
    (ROOT / 'pricing/data/appraisal-fathom-material-review.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('inputs', 'observations')}))


if __name__ == '__main__':
    main()
