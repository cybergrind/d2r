"""Runtime tier denominator and evidence ledger for the mandatory named-item gate."""

import json
from collections import Counter
from dataclasses import replace

from inventory_tracking.appraisal.presentation import ItemAssessment
from pricing.knowledge.assessment.domain.facts import ItemFacts
from pricing.knowledge.assessment.policies import complete_sets, named_baselines, named_leveling
from pricing.knowledge.assessment.policies.sources import source_error
from pricing.knowledge.definition_store import catalog
from pricing.knowledge.refresh import atomic_json


ROOT = named_baselines.ROOT
OUTPUT = ROOT / 'pricing/data/appraisal-named-gate.json'


def native_cases(identity, definition):
    """Ordinary and unknown specimen facts; explicit table identity survives upgrades."""
    quality, name = identity
    base = definition['base_definition']
    modifiers = {definition['game_definition'].get(f'prop{i}') for i in range(1, 13)}
    socket_range = definition.get('native_socket_range') or {}
    item = ItemFacts(
        name,
        base['name'],
        definition['base_codes'][0],
        base['type'],
        quality,
        None,
        True,
        'ethereal' in modifiers,
        socket_range.get('min', 0),
        'empty',
        [],
        True,
        provenance={'capture': {'item_identity': {'table': quality, 'table_id': definition['table_id']}}},
    )
    # A complete synthetic capture must retain the definition's native bonuses.
    # In particular, seasonal variants can both have nonzero IAS/FRW: an empty
    # stat array would contradict both versions rather than represent either.
    item = replace(
        item,
        stats={
            (key if ':' in key else key + ':0'): {'status': 'decoded', 'value': row['min']}
            for key, row in definition['roll_ranges'].items()
        },
    )
    yield 'unknown_premium', replace(item, capture_complete=False, ethereal=None, sockets=None, socket_contents=None)
    for bound in ('min', 'max'):
        stats = {
            (key if ':' in key else key + ':0'): {'status': 'decoded', 'value': row[bound]}
            for key, row in definition['roll_ranges'].items()
        }
        yield bound, replace(item, stats=stats)
    if base.get('durability', 0) > 0 and not base.get('nodurability'):
        yield (
            'filled_socket_unknown_contribution',
            replace(item, sockets=max(1, item.sockets), socket_contents='filled', filled_sockets=max(1, item.sockets)),
        )
        if quality == 'unique' and 'indestruct' not in modifiers and 'ethereal' not in modifiers:
            yield 'ethereal', replace(item, ethereal=True)
    for code in dict.fromkeys(base.get(key) for key in ('ubercode', 'ultracode')):
        if code and code != item.base_code:
            # resolve_named_definition validates whether this is actually an upgrade.
            from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition

            upgraded = replace(item, base_code=code)
            if resolve_named_definition(upgraded)[0] is not None:
                yield 'upgrade:' + code, upgraded


def audit():
    rows = named_baselines.baselines(named_baselines.RULES.read_bytes())
    reviews = json.loads((named_baselines.RULES.parent / 'named_tier_reviews.json').read_bytes())
    excluded = {(row['quality'], row['name']): row for row in reviews['non_trade_definitions']}
    recommendations = json.loads((ROOT / 'pricing/data/appraisal-recommendations.json').read_bytes())['rows']
    leveling = {}
    leveling_reviews = named_leveling.reviews()
    for row in recommendations:
        if row.get('purpose') == 'leveling' and row.get('intent') == 'recommend':
            leveling.setdefault(row['name'], []).append(row['id'])
    census = []
    failures = []
    cases = 0
    for identity, definitions in sorted(catalog().named_variants.items()):
        if identity in excluded:
            continue
        baseline = rows.get(identity)
        error = source_error(baseline['source'], identity, ROOT) if baseline else 'Missing baseline'
        for definition in definitions:
            for label, item in native_cases(identity, definition):
                tier = named_baselines.assess_tier(item)
                record = {
                    'state': 'complete',
                    'request_id': 'tier-census',
                    'result': {
                        'extraction': {'item': item.to_dict()},
                        'assessment': {'trade_tier': tier},
                        'decision': {'price_status': 'unknown'},
                    },
                }
                document = ItemAssessment.from_record(record)
                lines = [line for line in document.to_osd() if line.text.startswith('Trade tier:')]
                cases += 1
                if tier.get('tier') is None or not lines:
                    failures.append(
                        {
                            'quality': identity[0],
                            'name': identity[1],
                            'table_id': definition['table_id'],
                            'case': label,
                            'result': tier,
                        }
                    )
        census.append(
            {
                'quality': identity[0],
                'name': identity[1],
                'tier': baseline['tier'] if baseline and not error else None,
                'baseline_error': error,
                'leveling_recommendations': leveling.get(identity[1], []),
                'leveling_review': leveling_reviews.get(identity, {}).get('status', 'pending'),
            }
        )
    sets = [complete_sets.assess_complete_set(name) for name in json.loads(complete_sets.NATIVE.read_bytes())]
    guides = json.loads((ROOT / 'pricing/data/appraisal-guide-inventory.json').read_bytes())
    # Retain all discovered planner alternatives as evidence, not as endorsements.
    named_evidence = Counter()
    for row in guides['occurrences']:
        if row.get('category') in ('unique', 'set'):
            named_evidence[row['category'], row['name']] += 1
    for row in census:
        row['gathered_occurrences'] = named_evidence[row['quality'], row['name']]
    gates = {
        'uniques_missing_baseline': sum(r['quality'] == 'unique' and r['tier'] is None for r in census),
        'set_pieces_missing_baseline': sum(r['quality'] == 'set' and r['tier'] is None for r in census),
        'complete_sets_missing_baseline': sum(r['tier'] is None for r in sets),
        'rendered_tier_failures': len(failures),
        'unreviewed_leveling': sum(r['leveling_review'] == 'pending' for r in census),
        'unaccounted_guide_occurrences': guides['counts']['unaccounted_guide_occurrences'],
        'unaccounted_planner_occurrences': guides['counts']['unaccounted_planner_occurrences'],
    }
    return {
        'schema_version': 1,
        'complete': not any(gates.values()),
        'gates': gates,
        'counts': {
            'eligible_named': len(census),
            'excluded': len(excluded),
            'complete_sets': len(sets),
            'rendered_cases': cases,
        },
        'rows': census,
        'sets': sets,
        'excluded': list(excluded.values()),
        'rendering_failures': failures,
        'guide_counts': guides['counts'],
        'limitations': [
            'Occurrence accounting does not endorse every shared planner alternative. '
            'Source ambiguities remain in the guide inventory.'
        ],
    }


def main():
    result = audit()
    atomic_json(OUTPUT, result)
    print(json.dumps({'counts': result['counts'], 'gates': result['gates'], 'complete': result['complete']}))


if __name__ == '__main__':
    main()
