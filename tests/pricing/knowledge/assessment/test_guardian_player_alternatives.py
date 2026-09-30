from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('slug', 'class_name', 'extra'),
    [('enchant-sorceress', 'Sorceress', set()), ('smite-paladin', 'Paladin', {'83:3', '20:0', '102:0'})],
)
def test_guardian_player_uses_do_not_transfer_paladin_or_shield_stats_to_bow_enchant(slug, class_name, extra):
    bundle = build()
    role = next((r for r in bundle['profiles'] if r['id'] == slug + '-guardian-armor-alternative'), None)
    assert role is not None
    caps = {f'{k}:0': 15 for k in (40, 42, 44, 46)}
    item = replace(
        facts('Templar Coat', 'unique', 'Guardian Angel'),
        stats={
            k: {'status': 'decoded', 'value': v}
            for k, v in {**caps, '83:3': 1, '20:0': 20, '102:0': 30, '16:0': 180}.items()
        },
    )
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
    ]
    context = {'player_class': class_name}

    def evaluate(candidate):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate(item).annotations) == set(caps) | extra
    assert not evaluate(replace(item, ethereal=True)).annotations
    upgraded = replace(item, base_code=facts('Hellforge Plate').base_code)
    assert set(evaluate(upgraded).annotations) == set(caps) | extra
