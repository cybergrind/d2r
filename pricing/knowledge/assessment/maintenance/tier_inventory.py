"""Inventory all named tier reviews without treating missing evidence as a tier."""

import json
from collections import Counter, defaultdict

from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.refresh import atomic_json


def compile_tier_inventory(census, watch, recommendations, facts, *, dispositions=()):
    identities = {}
    for row in census:
        key = row['quality'], row['name']
        if key in identities:
            raise ValueError(f'Duplicate named identity: {key}')
        identities[key] = row
    resolved = {}
    for disposition in dispositions:
        key = disposition['quality'], disposition['name']
        if key not in identities:
            raise ValueError(f'Unknown disposition identity: {key}')
        if key in resolved or identities[key]['status'] == 'reviewed_policy':
            raise ValueError(f'Duplicate tier/disposition review: {key}')
        resolved[key] = disposition
    historical = {(r['rarity'], r['name']): r for r in watch}
    native = {(r['quality'], r['name']): r for r in facts}
    leveling = defaultdict(list)
    for row in recommendations:
        leveling[row['item_id']].append(row['id'])
    rows = []
    for key, source in sorted(identities.items()):
        fact = native.get(key, {})
        details = historical.get(key, {}).get('details', {})
        row = {
            **source,
            'historical_guide_tier': details.get('guide_tier'),
            'historical_guide_conditions': details.get('guide_conditions'),
            'set_name': fact.get('set_name'),
            'leveling_recommendations': sorted(set(leveling.get(fact.get('item_id'), []))),
            **({'disposition': resolved[key]} if key in resolved else {}),
        }
        rows.append(row)
    reviewed = sum(r['status'] == 'reviewed_policy' for r in rows)
    return {
        'schema_version': 1,
        'complete': bool(rows) and reviewed + len(resolved) == len(rows),
        'completion_scope': 'Identity tier or explicit native disposition; not complete variant or price coverage.',
        'counts': {
            'identities': len(rows),
            'reviewed': reviewed,
            'pending': len(rows) - reviewed - len(resolved),
            'dispositions': len(resolved),
            'tiers': dict(Counter(r['tier'] for r in rows if r['status'] == 'reviewed_policy')),
        },
        'rows': rows,
    }


def main():
    from pricing.knowledge.assessment.maintenance.named_gate import audit

    data = ROOT / 'pricing/data'

    def rows(filename):
        return json.loads((data / filename).read_text())['rows']

    rules = ROOT / 'pricing/knowledge/assessment/rules'
    reviews = json.loads((rules / 'named_tier_reviews.json').read_text())
    result = compile_tier_inventory(
        rows('appraisal-tier-coverage.json'),
        rows('appraisal-value-watch.json'),
        rows('appraisal-recommendations.json'),
        rows('appraisal-item-facts.json'),
        dispositions=reviews['non_trade_definitions'],
    )
    policies = {(r['quality'], r['name']): r for r in json.loads((rules / 'named_tiers.json').read_text())['policies']}
    gate = audit()
    baselines = {(r['quality'], r['name']): r for r in gate['rows']}
    result['complete'] = gate['complete']
    result['completion_scope'] = 'Named baselines, complete-set tiers, rendered variants and leveling reviews.'
    result['gates'] = gate['gates']
    result['complete_sets'] = gate['sets']
    for row in result['rows']:
        baseline = baselines.get((row['quality'], row['name']))
        if baseline:
            row['tier'] = baseline['tier']
            row['leveling_review'] = baseline['leveling_review']
    lines = [
        '# Named item tier inventory',
        '',
        'Reviewed 2026-09-26. SC / Non-Ladder / PC / RotW.',
        'Baseline priorities are qualitative; exact cached comparisons can refine them.',
        'Listed conditions are implemented branches, not complete coverage of every collector or affix premium.',
        'Leveling is independent of trade tier. “Indexed” means a separate reviewed leveling recommendation exists.',
        '',
        '| Quality | Item | Baseline tier | Higher-tier conditions | Leveling |',
        '| --- | --- | --- | --- | --- |',
    ]
    for row in result['rows']:
        policy = policies.get((row['quality'], row['name']), {})
        branches = list(policy.get('overrides', []))
        for variant in policy.get('variant_rules', []):
            branches.extend(variant['overrides'])
        conditions = '; '.join(dict.fromkeys(f'{b["tier"]}: {b["reason"]}' for b in branches))
        row['tier_conditions'] = conditions
        tier = row['tier'] or row.get('disposition', {}).get('kind', 'pending')
        leveling = 'Indexed' if row['leveling_recommendations'] else ''
        lines.append(f'| {row["quality"]} | {row["name"]} | {tier} | {conditions} | {leveling} |')
    atomic_json(data / 'appraisal-tier-inventory.json', result)
    (rules.parent / 'planning/NAMED_TIERS.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps(result['counts']))


if __name__ == '__main__':
    main()
