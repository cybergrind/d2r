import hashlib
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations


def test_compiler_binds_explicit_priorities_to_exact_role_and_source(tmp_path):
    source = tmp_path / 'guide.json'
    source.write_text('{"ring": "cast rate plus mana"}')
    role = {
        'id': 'ring-role',
        'qualities': ['rare'],
        'types': ['ring'],
        'must': {
            'all': [
                {'op': 'stat_at_least', 'key': '105:0', 'value': 10},
                {'op': 'stat_at_least', 'key': '9:0', 'value': 20},
            ]
        },
        'source': {'path': 'guide.json', 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'locator': '/ring'},
    }
    review = {
        'id': 'ring-stats',
        'version': 1,
        'role_id': role['id'],
        'profile_fingerprint': fingerprint(role),
        'review_state': 'reviewed',
        'rationale': 'Reviewed the complete combination',
        'review_date': '2026-09-25',
        'priorities': [
            {
                'key': '105:0',
                'desirability': 'desirable',
                'activation': {'op': 'stat_at_least', 'key': '105:0', 'value': 10},
                'explanation': 'Required cast rate',
            }
        ],
    }
    configs = compile_stat_configurations([review], [role], root=tmp_path)
    assert len(configs) == 1
    assert configs[0].required['all'][1]['key'] == '9:0'
    assert len(configs[0].priorities) == 1  # No conversion of every role stat into a priority.
    with pytest.raises(ValueError, match='exact role conditions'):
        compile_stat_configurations([{**review, 'advisory_conditions': ['Invented exemption']}], [role], root=tmp_path)
    changed = deepcopy(role)
    changed['must']['all'][1]['value'] = 21
    with pytest.raises(ValueError, match='Stale stat review'):
        compile_stat_configurations([review], [changed], root=tmp_path)
    source.write_text('{"ring": "changed"}')
    with pytest.raises(ValueError, match='source'):
        compile_stat_configurations([review], [role], root=tmp_path)


def test_reviewed_amulet_combinations_can_pass_while_build_fit_remains_conditional():
    import json
    from dataclasses import replace
    from pathlib import Path

    from pricing.knowledge.assessment.build_profiles import build
    from pricing.knowledge.assessment.profiles import assess_role_results
    from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
    from tests.pricing.knowledge.assessment.test_family_contracts import facts

    root = Path(__file__).resolve().parents[5]
    reviews = json.loads((root / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    profiles = build()['profiles']
    configs = compile_stat_configurations(reviews, profiles, root=root)
    configs = [c for c in configs if 'amul' in c.types and set(c.qualities) & {'magic', 'rare', 'crafted'}]
    assert len(configs) == 18
    candidate = replace(
        facts('Amulet', 'magic'),
        stats={'188:9': {'status': 'decoded', 'value': 3}, '105:0': {'status': 'decoded', 'value': 10}},
    )
    roles = assess_role_results(candidate, profiles)
    result = StatsEvaluator().evaluate(candidate, configs, role_outcomes=roles)
    assert set(result.annotations) == {'188:9', '105:0'}
    assert {r['status'] for r in result.configurations} == {'matched', 'failed'}
    assert all(r['role']['status'] == 'partial' for r in result.configurations if r['status'] == 'matched')
