import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.maintenance.stat_dispositions import validate_stat_dispositions
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_angelic_roles import BUILDS
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(('build_id', 'klass', 'rings'), BUILDS)
def test_angelic_ring_marker_requires_captured_bonus_and_player_combination(build_id, klass, rings):
    document = build()
    profiles = document['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    role_id = build_id + '-angelic-ring'
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role_id]
    assert len(configs) == 1
    role = next(p for p in profiles if p['id'] == role_id)
    items = ['Angelic Wings'] + ['Angelic Halo'] * rings
    context = {'player_class': klass, 'player_items': items}
    item = replace(facts('Ring', 'set', 'Angelic Halo'), stats={'224:0': {'status': 'decoded', 'value': 12}})

    def evaluate(candidate=item, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    result = evaluate()
    assert set(result.annotations) == {'224:0'}
    assert result.annotations['224:0']['desirability'] == 'desirable'
    assert result.annotations['224:0']['roll_quality'] == 'unassessed'
    assert result.configurations[0]['role']['status'] == 'partial'
    for changes in (
        {'name': 'Angelic Wings'},
        {'name': None},
        {'rarity': 'unique'},
        {'item_type': 'amul'},
        {'identified': False},
        {'stats': {}},
        {'stats': {'224:0': {'status': 'decoded', 'value': 0}}},
        {'stats': {'19:0': {'status': 'decoded', 'value': 1000}}},
        {'gaps': ['Duplicate native stat 224:0.']},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    for ctx in (
        {'player_class': klass},
        {**context, 'player_items': [], 'mercenary_items': items},
        {**context, 'player_items': ['Angelic Halo'] * rings},
        {**context, 'player_class': 'Sorceress'},
    ):
        assert not evaluate(ctx=ctx).annotations
    if rings == 2:
        assert not evaluate(ctx={**context, 'player_items': ['Angelic Wings', 'Angelic Halo']}).annotations
    # The enabling amulet does not own the ring's AR bonus or gain a fabricated marker.
    dispositions = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_dispositions.json').read_text())
    excluded = validate_stat_dispositions(dispositions, document, root=ROOT)
    assert excluded[build_id + '-angelic-amulet']['state'] == 'excluded'
    assert not any(c.role_id == build_id + '-angelic-amulet' for c in compile_stat_configurations(reviews, profiles))
