"""Offline base comparisons and a catalog-wide research coverage audit.

Historical WP-B buckets used missing=false defaults. They are context, never
verified exact prices. Premium suffixes must agree before displaying a bucket.
"""

import json
from collections import Counter
from pathlib import Path

from pricing.knowledge.market import valid_positive


BASE_QUALITIES = {'normal', 'superior', 'low quality', 'low_quality'}
BASE_PROPERTIES = {'402', '738', '425', '399', '937', '423', '510', '1855', '796', '1940', '934', '441', '454'}


def bucket_matches(bucket, item):
    if item.get('runeword') or item.get('rarity') not in BASE_QUALITIES:
        return False
    if type(item.get('ethereal')) is not bool or item.get('sockets') is None:
        return False
    # Occupied bases are not equivalent to clean bases; clearing destroys contents.
    if item.get('socket_contents') != 'empty':
        return False
    prefix = f'{item["sockets"]}os/{"eth" if item["ethereal"] else "noneth"}/{item["rarity"]}'
    parts = bucket.split('/')
    if '/'.join(parts[:3]) != prefix:
        return False
    suffixes = set(parts[3:])
    props = {str(a['property_id']): a['value'] for a in item.get('affixes', [])}
    ed = max(props.get('425', 0), props.get('510', 0))
    if ('15ed' in suffixes) != (ed >= 15):
        return False
    # These coarse buckets cannot establish staffmod or filled-item comparability.
    if suffixes & {'affixed', 'filled', 'res?', 'skill?'} or set(props) - BASE_PROPERTIES:
        return False
    for token in suffixes - {'15ed'}:
        res, skill = props.get('441'), props.get('454')
        if token.startswith('res'):
            if res is None or token != ('res45' if res >= 45 else 'res40-44' if res >= 40 else 'res<40'):
                return False
        elif token.startswith('skill'):
            if skill is None or token != f'skill{min(3, int(skill))}':
                return False
        else:
            return False
    return True


def assess_base(item, identity):
    """Keep mechanics, curated research and historical asks distinct from valuation."""
    if item.get('runeword') or item.get('rarity') not in BASE_QUALITIES:
        return None
    evidence = identity.get('evidence', {})
    historical = [
        r
        for r in evidence.get('historical_market', [])
        if bucket_matches(r.get('bucket', ''), item) and valid_positive(r.get('details', {}).get('median_ist'))
    ]
    market = identity.get('market') or {}
    comparable_variant = (
        type(item.get('ethereal')) is bool
        and type(item.get('sockets')) is int
        and item.get('socket_contents') == 'empty'
    )
    status = (
        'comparable_asks_require_review'
        if comparable_variant and market.get('priced_sellers')
        else 'historical_asks_only'
        if historical
        else 'unresearched_variant'
    )
    recipes = [r['details'] for r in evidence.get('base_rule', []) if r.get('details', {}).get('runeword')]
    return {
        'price_status': status,
        'historical_asks': historical,
        'research': evidence.get('base_research', []),
        'recipes': recipes,
        'caveat': 'Historical asks use legacy missing-field defaults; scope, empty sockets and seller counts '
        'are unverified. No sale price or premium multiplier is inferred.',
        'important_factors': [
            'base',
            'quality',
            'ethereal',
            'enhanced damage/defense',
            'base defense',
            'socket count and contents',
            'runeword identity and rolls',
            'staffmods',
            'inherent resistances/skills',
            'item level and socket potential',
            'player/mercenary demand',
            'requirements and weapon speed',
        ],
    }


def coverage(root):
    """Every weapon/armor base gets an explicit state, including absent research."""
    root = Path(root)
    data = root / 'pricing/data'
    catalog = json.loads((data / 'appraisal-catalog.json').read_text())['rows']
    history = json.loads((data / 'wp-b-prices.json').read_text())
    research = json.loads((data / 'wp-g-bases.json').read_text())
    prices = {v['name']: v for v in history.values() if isinstance(v, dict) and v.get('name')}
    curated = {v['base'] for v in research.values() if isinstance(v, dict) and v.get('base')}
    observed = Counter()
    comparable = Counter()
    market = data / 'appraisal-market.jsonl'
    if market.exists():
        for line in market.open():
            row = json.loads(line)
            if row.get('scope_status') != 'verified' or row.get('rarity') not in BASE_QUALITIES:
                continue
            observed[row['name']] += 1
            if (
                type(row.get('ethereal')) is bool
                and type(row.get('sockets')) is int
                and row.get('socket_contents') == 'empty'
                and row.get('seller_id')
                and row.get('unit_policy') == 'single_item'
                and valid_positive(row.get('ask_ist'))
            ):
                comparable[row['name']] += 1
    rows = []
    for base in catalog:
        if base['category'] not in ('weapons', 'armor'):
            continue
        buckets = prices.get(base['name'], {}).get('buckets', {})
        rows.append(
            {
                'name': base['name'],
                'code': base['base_code'],
                'status': 'historical_buckets'
                if buckets
                else 'cached_observations_only'
                if observed[base['name']]
                else 'research_only'
                if base['name'] in curated
                else 'unresearched',
                'curated_research': base['name'] in curated,
                'buckets': list(buckets),
                'max_sockets': base['details'].get('max_sockets'),
                'scoped_base_observations': observed[base['name']],
                'explicit_clean_priced_observations': comparable[base['name']],
            }
        )
    return {
        'schema_version': 1,
        'scope': 'SC/NL/PC/RotW; Ist=1',
        'historical_date': history['_meta'].get('pulled'),
        'counts': dict(Counter(r['status'] for r in rows)),
        'bases': rows,
        'limitation': 'Catalog coverage is not price coverage. Historical buckets are not verified prices; '
        'unresearched variants must not be valued at zero.',
    }


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / 'pricing/data/appraisal-base-coverage.json'
    report = coverage(root)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['counts']))
    print(output)


if __name__ == '__main__':
    main()
