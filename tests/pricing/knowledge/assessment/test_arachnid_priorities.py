from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('build_name', 'fcr', 'fhr'), [('blizzard', 105, None), ('meteor', 63, 60), ('lightning', 117, None)]
)
def test_arachnid_support_requires_source_specific_loadout_breakpoints(build_name, fcr, fhr):
    bundle = build()
    rid = build_name + '-standard-arachnid'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    assert len(configs) == 1
    item = replace(
        facts('Spiderweb Sash', 'unique', 'Arachnid Mesh'),
        stats={
            k: {'status': 'decoded', 'value': v}
            for k, v in [('105:0', 20), ('127:0', 1), ('77:0', 5), ('16:0', 120), ('150:0', 10)]
        },
    )
    ctx = {'player_class': 'Sorceress', 'player_total_fcr': fcr, 'player_total_fhr': fhr}
    wanted = {'105:0', '127:0', '77:0'}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == wanted
    for value in (None, True, str(fcr), fcr - 1):
        assert not evaluate(context={**ctx, 'player_total_fcr': value}).annotations
    # A stat on this belt is not a measured whole-character breakpoint.
    assert not evaluate(context={'player_class': 'Sorceress'}).annotations
    if fhr:
        assert not evaluate(context={**ctx, 'player_total_fhr': fhr - 1}).annotations
    for patch in ({'identified': False}, {'name': 'Other'}, {'rarity': 'rare'}):
        assert not evaluate(replace(item, **patch)).annotations
    for key in wanted:
        assert set(
            evaluate(replace(item, stats={k: v for k, v in item.stats.items() if k != key})).annotations
        ) == wanted - {key}
    assert bundle['guide_demand']['summaries']['Arachnid Mesh']['distinct_builds'] >= 3
    assert bundle['guide_demand']['summaries']['Arachnid Mesh']['distinct_builds'] == len(
        set(bundle['guide_demand']['summaries']['Arachnid Mesh']['builds'])
    )
