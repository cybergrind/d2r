"""Review Windforce mana steal separately from socket payload and asking prices."""

import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from pricing.knowledge.assessment.maintenance.guardian_market_review import dated_ask
from pricing.knowledge.market import scope_status


ROOT = Path(__file__).resolve().parents[4]
MARKET = 'pricing/data/appraisal-market.jsonl'
# Reviewed weapon effects only. Other payloads remain unknown, not zero.
MANA_EFFECTS = {'Ort Rune': 0, 'Vex Rune': 7, 'Perfect Skull': 3}


def material_review(row):
    props = row.get('properties', {})
    if (
        (row.get('rarity'), row.get('name')) != ('unique', 'Windforce')
        or row.get('base_code') != '6lw'
        or row.get('ethereal') is not False
        or ('738' in props and props['738'] is not False)
        or ('1216' in props and props['1216'] is not False)
    ):
        return {'status': 'unknown_or_conflicting_variant'}
    sockets = row.get('sockets')
    contents = row.get('socket_contents')
    insert = props.get('934')
    if (
        type(sockets) is not int
        or sockets not in (0, 1)
        or ('402' in props and (type(props['402']) is not int or props['402'] != sockets))
    ):
        return {'status': 'unknown_socket_payload'}
    if contents == 'empty' and (insert is None or insert == '' or insert == []):
        contribution = 0
    elif sockets == 1 and contents == 'filled' and isinstance(insert, str) and insert in MANA_EFFECTS:
        contribution = MANA_EFFECTS[insert]
    else:
        return {'status': 'unknown_socket_payload'}
    total = props.get('463')
    if total is None:
        return {'status': 'missing_mana_steal'}
    if type(total) is not int or not 6 <= total - contribution <= 8:
        return {'status': 'conflicting_mana_steal'}
    return {
        'status': 'verified_native_mana_steal',
        'native_mana_steal': total - contribution,
        'socket_mana_steal': contribution,
    }


def audit(rows):
    unique = {}
    for row in rows:
        if (row.get('rarity'), row.get('name')) != ('unique', 'Windforce'):
            continue
        if unique.setdefault(row['id'], row) != row:
            raise ValueError('Conflicting duplicate Windforce observation')
    observations = []
    for row in unique.values():
        scoped = row.get('scope_status') == 'verified' and scope_status(row.get('properties', {})) == 'verified'
        review = material_review(row) if scoped else {'status': 'unverified_scope'}
        eligible = scoped and dated_ask(row) and review['status'] == 'verified_native_mana_steal'
        observations.append(
            {
                **{
                    key: row.get(key)
                    for key in ('id', 'source', 'seller_id', 'observed_at', 'sockets', 'socket_contents')
                },
                'insert': row.get('properties', {}).get('934'),
                'dated_material_ask': eligible,
                **review,
            }
        )
    eligible = sum(row['dated_material_ask'] for row in observations)
    cohorts = defaultdict(list)
    for row in observations:
        if row['dated_material_ask']:
            key = (row['native_mana_steal'], row['sockets'], row['socket_contents'], row['insert'] or None)
            cohorts[key].append(row)
    material_cohorts = [
        {
            'native_mana_steal': key[0],
            'sockets': key[1],
            'socket_contents': key[2],
            'insert': key[3],
            'observation_ids': sorted(row['id'] for row in values),
            'seller_ids': sorted({row['seller_id'] for row in values}),
            'independent_sellers': len({row['seller_id'] for row in values}),
        }
        for key, values in sorted(cohorts.items(), key=lambda pair: str(pair[0]))
    ]
    disposition = 'no_verified_material_comparisons'
    if eligible:
        disposition = (
            'requires_exact_comparison_review'
            if any(row['independent_sellers'] >= 3 for row in material_cohorts)
            else 'insufficient_material_sellers'
        )
    return {
        'cached_observations': len(observations),
        'dated_material_asks': eligible,
        'material_statuses': dict(Counter(row['status'] for row in observations)),
        'pricing_disposition': disposition,
        'material_cohorts': material_cohorts,
        'premium_threshold': None,
        'observations': observations,
        'limitation': 'Native roll extraction does not establish exact comparability, trade qualification or a price.',
    }


def main():
    paths = [
        MARKET,
        'pricing/raw/traderie/wpi-windforce.json',
        str(Path(__file__).relative_to(ROOT)),
        'pricing/knowledge/assessment/maintenance/guardian_market_review.py',
        'pricing/knowledge/market.py',
        'third-parties/d2data/json/uniqueitems.json',
        'third-parties/d2data/json/gems.json',
    ]
    native = json.loads((ROOT / paths[-2]).read_text())['266']
    if (native['index'], native['code'], native['prop4'], native['min4'], native['max4']) != (
        'Windforce',
        '6lw',
        'manasteal',
        6,
        8,
    ):
        raise ValueError('Windforce native definition changed; review bounds')
    gems = json.loads((ROOT / paths[-1]).read_text())
    by_name = {row['name']: row for row in gems.values()}
    for name, expected in MANA_EFFECTS.items():
        gem = by_name[name]
        contribution = 0
        for slot in range(1, 4):
            if gem.get(f'weaponMod{slot}Code') == 'manasteal':
                low, high = gem.get(f'weaponMod{slot}Min'), gem.get(f'weaponMod{slot}Max')
                if type(low) is not int or low != high:
                    raise ValueError('Socket mana steal is not fixed')
                contribution += low
        if contribution != expected:
            raise ValueError('Windforce socket contribution changed')
    rows = [json.loads(line) for line in (ROOT / MARKET).read_text().splitlines()]
    result = {
        'schema_version': 1,
        'reviewed_at': date.today().isoformat(),
        'identity': 'Windforce',
        'scope': 'SC / Non-Ladder / PC / RotW',
        'inputs': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        **audit(rows),
    }
    (ROOT / 'pricing/data/appraisal-windforce-material-review.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('inputs', 'observations')}))


if __name__ == '__main__':
    main()
