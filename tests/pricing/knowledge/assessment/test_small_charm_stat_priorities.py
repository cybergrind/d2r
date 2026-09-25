import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


ALL_RES = {'39:0': 3, '41:0': 3, '43:0': 3, '45:0': 3}
GROUPS = [
    (
        ['blizzard-standard-sc-life-res', 'hammer-ubers-sc-life-res', 'lightning-ubers-sc-life-res'],
        {'7:0': 15, **ALL_RES},
    ),
    (['blizzard-standard-sc-life-cold'], {'7:0': 15, '43:0': 8}),
    (
        [
            'blizzard-mf-sc-mf-res',
            'blizzard-set-sc-mf-res',
            'hammer-standard-sc-mf-res',
            'hammer-mf-sc-mf-res',
            'nova-standard-sc-mf-res',
            'nova-mf-sc-mf-res',
            'nova-hydra-sc-mf-res',
            'poison-standard-sc-mf-res',
            'poison-mf-sc-mf-res',
            'lightning-standard-sc-mf-res',
            'lightning-mf-sc-mf-res',
        ],
        {'80:0': 5, **ALL_RES},
    ),
    (
        [
            'blizzard-mf-sc-fhr-res',
            'blizzard-set-sc-fhr-res',
            'poison-standard-sc-fhr-res',
            'lightning-standard-sc-fhr-res',
            'lightning-mf-sc-fhr-res',
        ],
        {'99:0': 5, **ALL_RES},
    ),
    (['nova-standard-sc-light-mf', 'nova-mf-sc-light-mf', 'nova-hydra-sc-light-mf'], {'41:0': 8, '80:0': 5}),
    (['nova-hydra-sc-fire-mf'], {'39:0': 8, '80:0': 5}),
    (['nova-mf-sc-mana-mf'], {'9:0': 12, '80:0': 5}),
]


@pytest.mark.parametrize(('roles', 'values'), GROUPS)
def test_small_charm_annotations_keep_whole_family_combinations(roles, values):
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id in roles]
    assert {c.role_id for c in configs} == set(roles)

    def evaluate(values, **changes):
        item = replace(
            facts('Small Charm', 'magic'),
            stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
            **changes,
        )
        return StatsEvaluator().evaluate(item, configs, role_outcomes=assess_role_results(item, profiles))

    result = evaluate(values)
    assert set(result.annotations) == set(values)
    assert len(result.configurations) == len(roles)
    assert all(r['role']['status'] == 'partial' for r in result.configurations)
    assert all(
        a['desirability'] == 'desirable' and a['roll_quality'] == 'unassessed' for a in result.annotations.values()
    )
    for required in values:
        assert not evaluate({**values, required: 0}).annotations
        assert not evaluate({k: v for k, v in values.items() if k != required}, capture_complete=False).annotations
    for changes in (
        {'item_type': 'mcha'},
        {'item_type': 'lcha'},
        {'rarity': 'rare'},
        {'rarity': 'unique'},
        {'ethereal': True},
        {'ethereal': None},
        {'identified': False},
    ):
        assert not evaluate(values, **changes).annotations
    for actual, wrong in (('7:0', '6:0'), ('9:0', '8:0'), ('80:0', '79:0')):
        if actual in values:
            assert not evaluate({(wrong if k == actual else k): v for k, v in values.items()}).annotations
    if set(ALL_RES).issubset(values):
        assert not evaluate({k: v for k, v in values.items() if k not in ('43:0', '45:0')}).annotations
