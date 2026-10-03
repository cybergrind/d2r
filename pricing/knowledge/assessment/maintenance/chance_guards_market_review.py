"""Offline Chance Guards variant census; no implicit ethereal defaults or price pooling."""

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

from pricing.knowledge.assessment.maintenance.trade_waterwalk_evidence import exclusion
from pricing.knowledge.assessment.mechanics.socket_evidence import reviewed_native


ROOT = Path(__file__).resolve().parents[4]
MARKET = 'pricing/data/appraisal-market.jsonl'
# Verified armor.json mgl/xmg/umg; original intrinsic ED uses max+1,
# whereas upgrades reroll their base. Flat15 is applied after percentage defense.
BASES = {'mgl': ('Normal', (10,)), 'xmg': ('Exceptional', tuple(range(37, 45))), 'umg': ('Elite', tuple(range(59, 68)))}


def possibilities(row):
    """Conservative legal variants. A singleton is proof, multiple means unresolved.

    Original ethereal candidates deliberately include the full base range and
    max+1, so uncertainty about operation order cannot establish a false proof.
    """
    props = row.get('properties', {})
    if (
        (row.get('rarity'), row.get('name')) != ('unique', 'Chance Guards')
        or type(row.get('sockets')) is not int
        or row['sockets'] != 0
        or row.get('socket_contents') != 'empty'
        or ('402' in props and (type(props['402']) is not int or props['402'] != 0))
        or props.get('934') is not None
        or ('399' in props and (type(props['399']) is not int or props['399'] != 15))
    ):
        return []
    ed, defense = props.get('425'), props.get('1855')
    if ed is not None and (type(ed) is not int or not 20 <= ed <= 30):
        return []
    if defense is not None and (type(defense) is not int or defense <= 0):
        return []
    result = []
    for code, (tier, bases) in BASES.items():
        upgraded = code != 'mgl'
        if row.get('base_code') not in (None, code) or props.get('930') not in (None, tier):
            continue
        if any(value is not None and value is not upgraded for value in (row.get('base_upgrade'), props.get('1216'))):
            continue
        for ethereal in (False, True):
            if any(value is not None and value is not ethereal for value in (row.get('ethereal'), props.get('738'))):
                continue
            raw_bases = (8, 9, 10) if ethereal and code == 'mgl' else bases
            totals = {
                (base * 3 // 2 if ethereal else base) * (100 + percent) // 100 + 15
                for base in raw_bases
                for percent in ((ed,) if ed is not None else range(20, 31))
            }
            if defense is None or defense in totals:
                result.append((code, ethereal))
    return result


def audit(rows):
    unique = {}
    for row in rows:
        if (row.get('rarity'), row.get('name')) == ('unique', 'Chance Guards'):
            if not isinstance(row.get('id'), str) or not row['id']:
                raise ValueError('Chance Guards observation needs an ID')
            if unique.setdefault(row['id'], row) != row:
                raise ValueError('Conflicting Chance Guards observation')
    records = []
    for row in unique.values():
        reason = exclusion(row)
        variants = possibilities(row) if not reason else []
        mf = row.get('properties', {}).get('461')
        if not reason and (type(mf) is not int or not 25 <= mf <= 40):
            reason = 'invalid_or_missing_magic_find'
        status = reason or (
            'proven_variant'
            if len(variants) == 1
            else 'ambiguous_variant'
            if variants
            else 'conflicting_or_missing_variant'
        )
        records.append(
            {
                'id': row['id'],
                'seller_id': row.get('seller_id'),
                'status': status,
                'variants': variants,
                'magic_find': mf,
                'enhanced_defense': row.get('properties', {}).get('425'),
                'total_defense': row.get('properties', {}).get('1855'),
            }
        )
    return {
        'observations': records,
        'statuses': dict(Counter(r['status'] for r in records)),
        'proven_sellers': sorted({r['seller_id'] for r in records if r['status'] == 'proven_variant'}),
        'trade_threshold': None,
        'limitation': 'Variant research only; exact roll cohorts and independent sellers still gate pricing.',
    }


def main():
    if not reviewed_native(ROOT):
        raise ValueError('Native tables changed; review Chance Guards defense arithmetic')
    rows = [json.loads(line) for line in (ROOT / MARKET).read_text().splitlines()]
    paths = [
        MARKET,
        str(Path(__file__).relative_to(ROOT)),
        'pricing/knowledge/assessment/maintenance/trade_waterwalk_evidence.py',
        'pricing/knowledge/assessment/maintenance/trade_war_traveler_evidence.py',
        'pricing/knowledge/market.py',
        'third-parties/d2data/json/armor.json',
        'third-parties/d2data/json/uniqueitems.json',
        'pricing/data/wp-f-ladder.json',
    ]
    paths += sorted({r['source'] for r in rows if r.get('name') == 'Chance Guards'})
    result = {
        'schema_version': 1,
        'reviewed_at': date.today().isoformat(),
        'scope': 'SC / Non-Ladder / PC / RotW',
        'inputs': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        **audit(rows),
    }
    (ROOT / 'pricing/data/appraisal-chance-guards-material-review.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('inputs', 'observations')}))


if __name__ == '__main__':
    main()
