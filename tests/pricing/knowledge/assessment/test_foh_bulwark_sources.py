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


@pytest.mark.parametrize('index', [0, 1])
def test_foh_bulwark_retains_both_documented_mercenary_choices(index):
    bundle = build()
    rid = f'fist-of-the-heavens-paladin-{index}-merc-bulwark-native'
    role = next((r for r in bundle['profiles'] if r['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    item = replace(
        facts('Mask', name='Bulwark'),
        runeword='Bulwark',
        sockets=3,
        socket_contents='filled',
        stats={k: {'status': 'decoded', 'value': v} for k, v in [('60:0', 4), ('36:0', 10), ('76:0', 5), ('99:0', 20)]},
    )

    def evaluate(merc, candidate=item):
        ctx = {'player_class': 'Paladin', 'mercenary_type': merc}
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    for merc in ('Act 2 Might', 'Act 2 Holy Freeze'):
        assert len(evaluate(merc).annotations) == 4
    for merc in (None, 'Act 2 Defiance', 'Act 5 Frenzy', True):
        assert not evaluate(merc).annotations
    assert not evaluate('Act 2 Might', replace(item, base_code=facts('Crown').base_code)).annotations
    assert not evaluate('Act 2 Might', replace(item, socket_contents='empty')).annotations
    assert any('Holy Freeze' in c and 'Might' in c for c in role['conditions'])
    demand = bundle['guide_demand']['summaries']['Bulwark']
    assert 'fist-of-the-heavens-paladin' in demand['builds']
    assert demand['builds'].count('fist-of-the-heavens-paladin') == 1
    assert demand['distinct_builds'] == len(set(demand['builds']))


def test_foh_aura_review_pins_both_planner_profiles_and_helmet_link():
    root = Path.cwd()
    rows = json.loads((root / 'pricing/knowledge/assessment/rules/reviewed_source_issues.json').read_text())['reviews']
    row = next((r for r in rows if r['id'] == 'foh-starter-mercenary-aura'), None)
    assert row is not None
    assert reviewed_source_issues([row], root)[0]['status'] == 'reconciled_source'
    evidence = row['resolution']['evidence']
    for index in (0, 1):
        link = next(r for r in evidence if r.get('locator') == f'/profiles/{index}/mercItems/head')
        assert link['expected'] == 77
    link['expected'] = 35
    assert reviewed_source_issues([row], root)[0]['status'] == 'stale_review'
