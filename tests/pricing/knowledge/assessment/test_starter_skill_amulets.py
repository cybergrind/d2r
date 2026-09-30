from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


MEMBERS = [
    ('fire-warlock-guide', 0, 'Warlock', '83:7'),
    ('fissure-druid', 0, 'Druid', '188:42'),
    ('fist-of-the-heavens-paladin', 0, 'Paladin', '188:24'),
    ('fist-of-the-heavens-paladin', 1, 'Paladin', '188:24'),
]


@pytest.mark.parametrize(('slug', 'index', 'cls', 'skill'), MEMBERS)
def test_starter_magic_amulet_requires_skill_and_cast_rate_on_same_item(slug, index, cls, skill):
    bundle = build()
    rid = f'{slug}-{index}-magic-skill-fcr-amulet'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    item = replace(
        facts('Amulet', 'magic'), stats={k: {'status': 'decoded', 'value': v} for k, v in [(skill, 1), ('105:0', 10)]}
    )
    ctx = {'player_class': cls}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == {skill, '105:0'}
    for key in (skill, '105:0'):
        one = replace(item, stats={k: v for k, v in item.stats.items() if k != key})
        assert not evaluate(one, {**ctx, 'player_total_fcr': 200, 'player_equipment': {'ring_left': item}}).annotations
    for change in (
        {'rarity': 'rare'},
        {'rarity': 'crafted'},
        {'identified': None},
        {'ethereal': True},
        {'base_code': facts('Ring').base_code, 'item_type': facts('Ring').item_type},
    ):
        assert not evaluate(replace(item, **change)).annotations
    assert not evaluate(context={}).annotations
    assert not evaluate(context={'player_class': 'Other'}).annotations
    assert assess_role_results(item, [role], ctx)[0].status == 'partial'
    if slug == 'fissure-druid':
        # The illustrated +2 is a target, not a gate that rejects a useful +1 amulet.
        assert role['preferences']
