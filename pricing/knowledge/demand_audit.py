"""Audit offline demand publication; gaps are evidence, not implied recommendations."""

import json
from collections import Counter
from pathlib import Path

from pricing.knowledge.index import normalize_name


def audit(root):
    root = Path(root)

    def read(name):
        return json.loads((root / 'pricing/data' / name).read_text())

    demand = read('appraisal-demand.json')
    watch = read('appraisal-value-watch.json')
    definitions = read('appraisal-definitions.json')['rows']
    ledger = read('wp-a-builds.json')
    named = {normalize_name(r['name']): r['name'] for r in definitions if r.get('rarity') in ('unique', 'set')}
    watched = {normalize_name(r['name']) for r in watch['rows']}
    recommended = [r for r in demand['rows'] if r.get('details', {}).get('recommended')]
    named_demand = {normalize_name(r['name']) for r in recommended} & named.keys()
    unresolved = [r for r in recommended if r['details'].get('resolution_status') != 'resolved']
    # Named mentions inside composite prose are audit candidates only, never automatic endorsements.
    candidates = []
    for row in unresolved:
        label = normalize_name(row['name'])
        mentions = [name for key, name in named.items() if key in label]
        candidates.append(
            {k: row.get(k) for k in ('name', 'build', 'variant', 'side', 'slot', 'source_id', 'source_locator')}
            | {'possible_named_items': mentions}
        )
    coverage = demand['coverage']
    imported = set(coverage['guides'])
    variants = {p.stem for p in (root / 'pricing/data/wp-a-variants').glob('*.json') if p.stem != 'index'}
    planners = [r for r in demand['rows'] if r.get('details', {}).get('profile_uid')]
    by_build = []
    for slug in sorted(imported):
        rows = [r for r in recommended if r['build'] == slug]
        by_build.append(
            {
                'build': slug,
                'recommended_occurrences': len(rows),
                'merc_occurrences': sum(r['side'] == 'merc' for r in rows),
                'variants': sorted({r['variant'] for r in rows}),
                'unresolved_occurrences': sum(r['details'].get('resolution_status') != 'resolved' for r in rows),
            }
        )
    return {
        'date': '2026-09-24',
        'scope': 'Cached research coverage; not proof every current guide or valuable item is covered.',
        'summary': {
            'cached_builds_imported': len(imported),
            'planners_imported': coverage['planner_count'],
            'planner_profiles': coverage['sets'],
            'demand_occurrences': len(demand['rows']),
            'recommended_occurrences': len(recommended),
            'unresolved_recommended_occurrences': len(unresolved),
            'unique_unresolved_recommended_labels': len({r['name'] for r in unresolved}),
            'named_unique_set_demand_items': len(named_demand),
            'named_demand_missing_watch': len(named_demand - watched),
            'watch_records': len(watch['rows']),
            'watch_distinct_names': len(watched),
            'planner_only_unendorsed_occurrences': sum(not r['details'].get('recommended') for r in planners),
            'historical_planner_occurrences': sum(bool(r['details'].get('historical')) for r in planners),
        },
        'missing_named_watch': sorted(named[k] for k in named_demand - watched),
        'ledger_builds_not_imported': sorted(set(ledger) - imported),
        'variant_files_without_imported_build': sorted(variants - imported),
        'unavailable_planners': coverage.get('unavailable_planners', {}),
        'named_prose_candidates_missing_watch': sorted(
            {name for row in candidates for name in row['possible_named_items'] if normalize_name(name) not in watched}
        ),
        'unresolved_by_side': dict(Counter(r['side'] for r in unresolved)),
        'by_build': by_build,
        'unresolved_recommended': candidates,
        'remaining_gaps': [
            'Decorated named identities are resolved; composite prose and generic affix patterns still require review.',
            'Planner association is not endorsement: shared, testing, historical and unreferenced profiles '
            'remain candidates.',
            'Variant JSON files currently supply planner links; arbitrary prose in those files is not fully imported.',
            'Build-wide stat prose is not a reviewed slot-specific executable stat/roll rule.',
            'Set companions and socket upgrades are preserved as setup text, not evaluated against the captured item.',
            'Guide mention context can be incomplete; retained mentions are discovery evidence, not required gear.',
            'Missing source downloads and current guide changes cannot be resolved by an offline audit.',
            'Full price coverage is separate: only verified NL observations matching the actual variant '
            'may price an item.',
        ],
    }


def main():
    root = Path(__file__).resolve().parents[2]
    result = audit(root)
    (root / 'pricing/data/appraisal-demand-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    lines = [
        '# Build-demand coverage audit — 2026-09-24',
        '',
        result['scope'],
        '',
        'The Sazabi failure was an identity-join loss: decorated variant labels did not match canonical item names.',
        'The importer now preserves setup text while resolving named identities. Reports retain variant/side/slot.',
        '',
        '| Measure | Count |',
        '| --- | ---: |',
    ]
    lines += [f'| {k.replace("_", " ")} | {v} |' for k, v in result['summary'].items()]
    lines += ['', '## Remaining gaps', ''] + [f'- {x}' for x in result['remaining_gaps']]
    for key in (
        'missing_named_watch',
        'ledger_builds_not_imported',
        'variant_files_without_imported_build',
        'unavailable_planners',
        'named_prose_candidates_missing_watch',
    ):
        lines += ['', f'{key}: `{json.dumps(result[key])}`']
    lines += [
        '',
        '## Per-build coverage',
        '',
        '| Build | Occurrences | Mercenary | Unresolved |',
        '| --- | ---: | ---: | ---: |',
    ]
    lines += [
        f'| {r["build"]} | {r["recommended_occurrences"]} | {r["merc_occurrences"]} | {r["unresolved_occurrences"]} |'
        for r in result['by_build']
    ]
    lines += [
        '',
        'Full unresolved labels, source locators, variants and possible named matches: '
        '`pricing/data/appraisal-demand-audit.json`.',
        'Reproduce after builds → valuable → index rebuild: '
        '`uv run --offline python -m pricing.knowledge.demand_audit`.',
        'Classifier contract: [ASSESSMENT_DESIGN.md](ASSESSMENT_DESIGN.md).',
    ]
    (root / 'pricing/knowledge/DEMAND_AUDIT.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps(result['summary']))


if __name__ == '__main__':
    main()
