import json
from dataclasses import replace
from pathlib import Path

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.maintenance.reviewed_source_issues import reviewed_source_issues
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


ROLE_ID = 'blessed-hammer-paladin-2-merc-chains-honor'


def test_hammer_mf_accepts_both_cited_bases_without_inheriting_ethereal_or_perfect_rolls():
    bundle = build()
    role = next((r for r in bundle['profiles'] if r['id'] == ROLE_ID), None)
    assert role is not None
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == ROLE_ID
    ]
    values = {'80:0': 25, '60:0': 8, '127:0': 2, '36:0': 8, '39:0': 65, '41:0': 65, '43:0': 65, '45:0': 65}
    item = replace(
        facts('Archon Plate', name='Chains of Honor'),
        ethereal=True,
        runeword='Chains of Honor',
        sockets=4,
        socket_contents='filled',
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    ctx = {'player_class': 'Paladin', 'mercenary_type': 'Act 2 Holy Freeze'}

    def evaluate(candidate, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert evaluate(item).annotations['80:0']['desirability'] == 'desirable'
    for ethereal in (True, False):
        sacred = replace(item, base_code=facts('Sacred Armor').base_code, ethereal=ethereal)
        assert evaluate(sacred).annotations
    for changes in (
        {'ethereal': False},
        {'ethereal': None},
        {'base_code': facts('Dusk Shroud').base_code},
        {'runeword': None},
        {'socket_contents': 'empty'},
        {'sockets': 3},
        {'identified': None},
        {'rarity': 'magic'},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    assert not evaluate(item, {'player_class': 'Paladin', 'mercenary_type': 'Act 5 Frenzy'}).annotations
    assert not evaluate(item, {'player_class': 'Paladin'}).annotations
    assert any('mercenary gets the kill' in c for c in role['conditions'])
    assert any('requirements' in c for c in role['conditions'])
    assert assess_role_results(item, [role], ctx)[0].status == 'partial'
    assert bundle['guide_demand']['summaries']['Chains of Honor']['distinct_builds'] >= 13
    assert bundle['guide_demand']['summaries']['Chains of Honor']['distinct_builds'] == len(
        set(bundle['guide_demand']['summaries']['Chains of Honor']['builds'])
    )


def test_hammer_mf_resolution_pins_original_planner_link_and_preserves_prose():
    root = Path.cwd()
    reviews = json.loads((root / 'pricing/knowledge/assessment/rules/reviewed_source_issues.json').read_text())[
        'reviews'
    ]
    row = next((r for r in reviews if r['id'] == 'hammer-mf-chains-honor-base-examples'), None)
    assert row is not None
    assert reviewed_source_issues([row], root)[0]['status'] == 'reconciled_source'
    assert 'Sacred Armor' in str(row['source']['expected'])
    assert row['resolution']['reviewed_profile_ids'] == [ROLE_ID]
    link = next(r for r in row['resolution']['evidence'] if r.get('locator') == '/profiles/2/mercItems/tors')
    assert link['expected'] == 24
    link['expected'] = 1
    assert reviewed_source_issues([row], root)[0]['status'] == 'stale_review'
