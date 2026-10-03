"""Source-bound Stormshield listing arithmetic audit, not an implicit roll conversion."""

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

from pricing.knowledge.assessment.maintenance.trade_waterwalk_evidence import exclusion
from pricing.knowledge.assessment.mechanics.socket_evidence import NATIVE_HASHES, reviewed_native


ROOT = Path(__file__).resolve().parents[4]
MARKET = 'pricing/data/appraisal-market.jsonl'
# uniqueitems253: ac/lvl param30; denominator8. Monarch armor uit133..148.
# These are compatibility classifications; unknown inserts prevent native-roll proof.


def defense_review(properties):
    total, bonus = properties.get('1855'), properties.get('436')
    levels = []
    if '436' in properties:
        if type(bonus) is int:
            levels = [level for level in range(1, 100) if 30 * level // 8 == bonus]
        if not levels:
            return {'status': 'invalid_level_bonus'}
    if total is None:
        return {'status': 'missing_total_defense'}
    if type(total) is not int or total <= 0:
        return {'status': 'invalid_total_defense'}
    if levels:
        base = total - bonus
        if 133 <= base <= 148:
            return {
                'status': 'displayed_total_convention',
                'possible_levels': levels,
                'candidate_base_defense': base,
                'socket_contribution_verified': False,
            }
        return {'status': 'mixed_or_conflicting_defense_fields'}
    if 133 <= total <= 148:
        return {'status': 'base_defense_compatible', 'socket_contribution_verified': False}
    return {'status': 'ambiguous_total_or_socket_contribution'}


def audit(rows):
    unique = {}
    for row in rows:
        if (row.get('rarity'), row.get('name')) != ('unique', 'Stormshield'):
            continue
        if not isinstance(row.get('id'), str) or not row['id']:
            raise ValueError('Stormshield observation requires an ID')
        if unique.setdefault(row['id'], row) != row:
            raise ValueError('Conflicting Stormshield observation')
    records = []
    for row in unique.values():
        reason = exclusion(row)
        review = {'status': reason} if reason else defense_review(row.get('properties', {}))
        records.append(
            {
                'id': row['id'],
                'seller_id': row.get('seller_id'),
                'observed_at': row.get('observed_at'),
                'properties': row.get('properties', {}),
                'sockets': row.get('sockets'),
                'socket_contents': row.get('socket_contents'),
                **review,
            }
        )
    return {
        'observations': records,
        'statuses': dict(Counter(r['status'] for r in records)),
        'native_roll_proved': False,
        'premium_threshold': None,
        'limitation': 'Arithmetic compatibility does not prove intrinsic defense, empty sockets or sellability.',
    }


def main():
    if not reviewed_native(ROOT):
        raise ValueError('Native tables changed; review Stormshield coefficient and base')
    stat_path = ROOT / 'third-parties/d2data/json/itemstatcost.json'
    stat = json.loads(stat_path.read_text())['item_armor_perlevel']
    if (stat.get('*ID'), stat.get('op'), stat.get('op param'), stat.get('op base'), stat.get('op stat1')) != (
        214,
        4,
        3,
        'level',
        'armorclass',
    ):
        raise ValueError('Stormshield level-defense operator changed')
    rows = [json.loads(line) for line in (ROOT / MARKET).read_text().splitlines()]
    paths = [
        MARKET,
        'third-parties/d2data/json/itemstatcost.json',
        str(Path(__file__).relative_to(ROOT)),
        'pricing/knowledge/assessment/maintenance/trade_waterwalk_evidence.py',
        'pricing/knowledge/assessment/maintenance/trade_war_traveler_evidence.py',
        'pricing/knowledge/market.py',
        'pricing/data/wp-f-ladder.json',
        *[f'third-parties/d2data/json/{name}.json' for name in NATIVE_HASHES],
    ]
    paths += sorted({r['source'] for r in rows if r.get('name') == 'Stormshield'})
    result = {
        'schema_version': 1,
        'reviewed_at': date.today().isoformat(),
        'scope': 'SC / Non-Ladder / PC / RotW',
        'inputs': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        **audit(rows),
    }
    (ROOT / 'pricing/data/appraisal-stormshield-material-review.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('inputs', 'observations')}))


if __name__ == '__main__':
    main()
