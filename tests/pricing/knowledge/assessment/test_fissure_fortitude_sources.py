import json
from dataclasses import replace
from pathlib import Path

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.maintenance.reviewed_source_issues import reviewed_source_issues
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('index', [1, 2])
def test_fissure_fortitude_supports_reviewed_aura_choices_without_perfect_roll_gates(index):
    b = build()
    rid = f'fissure-druid-{index}-merc-fortitude'
    role = next((r for r in b['profiles'] if r['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in b['stat_evaluation']['configurations'] if c['role_id'] == rid]
    item = replace(
        facts('Sacred Armor', name='Fortitude'),
        runeword='Fortitude',
        sockets=4,
        socket_contents='filled',
        ethereal=True,
        stats={
            k: {'status': 'decoded', 'value': v}
            for k, v in [
                ('17:0', 300),
                ('18:0', 300),
                ('16:0', 200),
                ('39:0', 25),
                ('41:0', 25),
                ('43:0', 25),
                ('45:0', 25),
            ]
        },
    )

    def evaluate(merc, candidate=item):
        ctx = {'player_class': 'Druid', 'mercenary_type': merc}
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    for merc in ['Act 2 Might', 'Act 2 Holy Freeze']:
        assert len(evaluate(merc).annotations) == 7
    for merc in [None, 'Act 2 Defiance', 'Act 5 Frenzy', True]:
        assert not evaluate(merc).annotations
    assert not evaluate('Act 2 Might', replace(item, ethereal=False)).annotations
    assert not evaluate('Act 2 Might', replace(item, base_code=facts('Archon Plate').base_code)).annotations
    assert any('Holy Freeze' in c and 'Might' in c for c in role['conditions'])
    assert any('Infinity' in c for c in role['conditions'])
    assert {'build': 'fissure-druid', 'variant': role['variant'], 'side': 'merc', 'strength': 'preferred'} in b[
        'guide_demand'
    ]['summaries']['Fortitude']['contexts']


def test_fissure_review_pins_current_variant_planner_instead_of_old_ubers_profile():
    root = Path.cwd()
    rows = json.loads((root / 'pricing/knowledge/assessment/rules/reviewed_source_issues.json').read_text())['reviews']
    row = next((r for r in rows if r['id'] == 'fissure-standard-mf-mercenary-aura'), None)
    assert row is not None
    assert reviewed_source_issues([row], root)[0]['status'] == 'reconciled_source'
    evidence = row['resolution']['evidence']
    assert any(r['path'].endswith('tt9vl0l2.json') for r in evidence)
    assert not any(r['path'].endswith('vf0106vk.json') for r in evidence)
    link = next(r for r in evidence if r.get('locator') == '/profiles/1/merc')
    assert link['expected'] == '10'
    link['expected'] = '11'
    assert reviewed_source_issues([row], root)[0]['status'] == 'stale_review'
