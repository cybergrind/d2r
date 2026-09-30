"""Inventory authored scenarios; passing coverage is not proof that tests passed."""

import hashlib
import json
from collections import defaultdict
from pathlib import Path

from tests.pricing.knowledge.assessment.item_bank.cases import CASES


SCENARIOS = frozenset({'positive', 'negative', 'unknown'})


def ordinary_leveling_targets(reviews, recommendations):
    """Exclude only positively reviewed ordinary uses; missing evidence stays required."""
    indexed = {row['id']: row for row in recommendations}
    ordinary = set()
    for row in reviews:
        tiers = []
        if supplemental := row.get('recommendation'):
            tiers.append(supplemental['tier'])
        for identifier in row.get('recommendation_ids', []):
            source = indexed.get(identifier, {})
            valid = (
                source.get('intent') == 'recommend'
                and source.get('purpose') == 'leveling'
                and source.get('review')
                and source.get('evidence_strength') in ('explicit', 'reviewed_inference')
            )
            tiers.append({1: 'high', 2: 'med', 3: 'med', 5: 'low'}.get(source.get('priority')) if valid else None)
        if tiers and all(tier in ('med', 'low') for tier in tiers):
            ordinary.add(f'named:{row["quality"]}:{row["name"]}')
    return ordinary


def audit_cases(
    cases,
    profiles,
    tiers,
    *,
    watches=(),
    consumables=(),
    socket_materials=(),
    supplies=(),
    value_scope=None,
    source_root=None,
    named_leveling=(),
    recommendations=(),
):
    from pricing.knowledge.assessment.maintenance.value_scope import use_exclusions

    exclusions = use_exclusions(profiles, value_scope, source_root or Path.cwd())
    optional = {'role:' + key.removeprefix('use:') for key in exclusions}
    valuable_named = {
        f'named:{row["quality"]}:{row["name"]}' for row in tiers['rows'] if row['tier'] in {'high', 'med', 'mid'}
    }
    valuable_named.update(
        f'named:{row["rarity"]}:{row["name"]}'
        for row in watches
        if row.get('rarity') in ('unique', 'set') and row.get('details', {}).get('priority') == 'valuable_candidate'
    )
    optional.update(ordinary_leveling_targets(named_leveling, recommendations) - valuable_named)
    required = {f'role:{row["id"]}:{quality}' for row in profiles for quality in row['qualities']}
    required.update(valuable_named)
    required.update(
        f'named:{row["quality"]}:{row["name"]}'
        for row in tiers['rows']
        if row['tier'] in {'high', 'med', 'mid'}
        or row.get('leveling_review') in {'recommendation', 'conditional_combination'}
    )
    required.update(
        f'watch:{row["details"]["watch_id"]}:{row["rarity"]}'
        for row in watches
        if row.get('kind') == 'affixed_value_watch' and row.get('details', {}).get('priority') == 'valuable_candidate'
    )
    required.update('consumable:' + code for code in consumables)
    required.update('socket_material:' + code for code in socket_materials)
    required.update('supply:' + code for code in supplies)
    required -= optional
    present = defaultdict(set)
    ids = set()
    for case in cases:
        if case.id in ids or case.scenario not in SCENARIOS or not case.evidence:
            raise ValueError('Duplicate, unsupported or unsourced item-bank case')
        ids.add(case.id)
        for target in case.covers:
            if (
                target.startswith('role:')
                and target.rsplit(':', 1)[-1] != case.item.rarity
                and case.scenario != 'negative'
            ):
                raise ValueError('Different target quality is valid only for a negative scenario')
            key = (
                target
                if target.startswith(('named:', 'consumable:', 'socket_material:', 'supply:', 'role:'))
                else f'{target}:{case.item.rarity}'
                if target.startswith('watch:')
                else f'role:{target}:{case.item.rarity}'
            )
            present[key].add(case.scenario)
    missing = {key: sorted(SCENARIOS - present[key]) for key in sorted(required) if SCENARIOS - present[key]}
    orphaned = sorted(set(present) - required - optional)
    return {
        'schema_version': 1,
        'case_coverage_complete': not missing and not orphaned,
        'verification': 'Case inventory only; execute appraisal tests to establish behavior.',
        'counts': {'cases': len(cases), 'required_targets': len(required), 'targets_missing_cases': len(missing)},
        'missing': missing,
        'orphaned_case_targets': orphaned,
        'optional_case_targets': sorted(set(present) & optional),
        'scope_excluded_targets': sorted(optional),
        'builds': sorted({row['build'] for row in profiles}),
    }


def main():
    paths = [
        Path('pricing/data/appraisal-build-profiles.json'),
        Path('pricing/data/appraisal-named-gate.json'),
        Path('pricing/data/appraisal-value-watch.json'),
        Path('pricing/knowledge/assessment/rules/value_scope_reviews.json'),
        Path('pricing/data/appraisal-recommendations.json'),
        Path('pricing/knowledge/assessment/rules/named_leveling_reviews.json'),
    ]
    raw = [path.read_bytes() for path in paths]
    from pricing.knowledge.assessment.policies.consumables import REVIEWED_CODES
    from pricing.knowledge.assessment.policies.named_leveling import reviews
    from pricing.knowledge.assessment.policies.supplies import definitions as supply_definitions
    from pricing.knowledge.socket_materials import SOURCE, definitions

    result = audit_cases(
        CASES,
        json.loads(raw[0])['profiles'],
        json.loads(raw[1]),
        watches=json.loads(raw[2])['rows'],
        consumables=REVIEWED_CODES,
        socket_materials=definitions(),
        supplies=supply_definitions(),
        value_scope=json.loads(raw[3]),
        source_root=Path.cwd(),
        named_leveling=reviews().values(),
        recommendations=json.loads(raw[4])['rows'],
    )
    result['inputs'] = {
        str(path): hashlib.sha256(content).hexdigest() for path, content in zip(paths, raw, strict=True)
    }
    for path in sorted(Path(__file__).parent.rglob('*.py')):
        result['inputs'][str(path.relative_to(Path.cwd())) if path.is_absolute() else str(path)] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    for path in (
        Path('pricing/knowledge/assessment/maintenance/value_scope.py'),
        Path('pyproject.toml'),
        Path('uv.lock'),
        SOURCE.relative_to(Path.cwd()),
        Path('pricing/knowledge/assessment/policies/supplies.py'),
    ):
        result['inputs'][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    target = Path('pricing/data/appraisal-item-bank-coverage.json')
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['counts']))


if __name__ == '__main__':
    main()
