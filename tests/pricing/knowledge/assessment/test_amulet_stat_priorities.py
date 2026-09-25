import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('role', 'quality', 'skill', 'ranks', 'fcr'),
    [
        ('enchant-budget-amulet', 'magic', '188:8', 3, 10),
        ('enchant-prebuff-amulet', 'magic', '188:8', 3, 10),
        ('nova-standard-amulet', 'crafted', '83:1', 2, 10),
        ('nova-mf-amulet', 'crafted', '83:1', 2, 10),
        ('nova-hydra-amulet', 'crafted', '83:1', 2, 10),
        ('enchant-standard-amulet', 'crafted', '83:1', 2, 15),
        ('enchant-mf-amulet', 'crafted', '83:1', 2, 15),
    ],
)
def test_amulet_markers_keep_skill_fcr_and_combined_resistance_targets(role, quality, skill, ranks, fcr):
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role]
    assert len(configs) == 1

    def evaluate(values, **changes):
        item = replace(
            facts('Amulet', quality), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()}, **changes
        )
        return StatsEvaluator().evaluate(item, configs, role_outcomes=assess_role_results(item, profiles))

    values = {skill: ranks, '105:0': fcr, '7:0': 10, '9:0': 20, '39:0': 5}
    result = evaluate(values)
    assert result.annotations[skill]['desirability'] == 'desirable'
    assert result.annotations['105:0']['desirability'] == 'desirable'
    assert not evaluate({**values, '105:0': fcr - 1}).annotations
    assert not evaluate({k: v for k, v in values.items() if k != skill}, capture_complete=False).annotations
    assert not evaluate(values, rarity='rare').annotations
    if role.startswith('nova-'):
        assert result.annotations['9:0']['desirability'] == 'supporting'
    if role.startswith('enchant-') and quality == 'crafted':
        assert '39:0' not in result.annotations
        combined = evaluate({**values, '41:0': 5, '43:0': 5, '45:0': 5})
        assert all(combined.annotations[k]['desirability'] == 'supporting' for k in ('39:0', '41:0', '43:0', '45:0'))
