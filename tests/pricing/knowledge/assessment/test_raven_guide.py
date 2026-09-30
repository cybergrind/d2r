from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


MEMBERS = [
    ('berserk-barbarian', 1, 'Barbarian'),
    ('blessed-hammer-paladin', 3, 'Paladin'),
    ('dragon-talon-assassin', 0, 'Assassin'),
    ('dragon-talon-assassin', 1, 'Assassin'),
    ('dream-paladin', 0, 'Paladin'),
    ('dream-paladin', 1, 'Paladin'),
    ('dream-paladin', 2, 'Paladin'),
    ('fist-of-the-heavens-paladin', 3, 'Paladin'),
    ('lightning-fury-amazon-guide', 1, 'Amazon'),
    ('lightning-fury-amazon-guide', 2, 'Amazon'),
    ('lightning-fury-amazon-guide', 3, 'Amazon'),
    ('lightning-strike-amazon', 1, 'Amazon'),
    ('lightning-strike-amazon', 2, 'Amazon'),
    ('mirrored-blades-warlock-guide', 1, 'Warlock'),
    ('mirrored-blades-warlock-guide', 2, 'Warlock'),
    ('smite-paladin', 1, 'Paladin'),
    ('smite-paladin', 2, 'Paladin'),
    ('strafe-amazon', 1, 'Amazon'),
    ('strafe-amazon', 2, 'Amazon'),
]


@pytest.mark.parametrize(('slug', 'index', 'cls'), MEMBERS)
def test_raven_frost_minimum_roll_still_supplies_cbf_without_inventing_smite_ar(slug, index, cls):
    bundle = build()
    rid = f'{slug}-{index}-raven-frost'
    role = next((r for r in bundle['profiles'] if r['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    values = {'153:0': 1, '148:0': 20, '9:0': 40, '2:0': 15, '19:0': 150}
    item = replace(
        facts('Ring', 'unique', 'Raven Frost'), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()}
    )
    ctx = {'player_class': cls}

    def evaluate(candidate=item):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    assert evaluate().annotations['153:0']['desirability'] == 'desirable'
    if slug in ['smite-paladin', 'blessed-hammer-paladin', 'fist-of-the-heavens-paladin']:
        assert '19:0' not in evaluate().annotations
        assert any('Smite' in c and 'attack rating' in c for c in role['conditions'])
    else:
        assert '19:0' in evaluate().annotations
    assert evaluate().annotations['2:0']['desirability'] == 'desirable'
    for change in [{'name': 'Nagelring'}, {'rarity': 'rare'}, {'identified': None}, {'ethereal': True}]:
        assert not evaluate(replace(item, **change)).annotations
    if slug == 'berserk-barbarian':
        assert any('corpse' in c for c in role['conditions'])


def test_raven_frost_review_demand_preserves_distinct_build_count():
    summary = build()['guide_demand']['summaries']['Raven Frost']
    assert set(summary['builds']) == {slug for slug, _, _ in MEMBERS} | {'zeal-paladin'}
    assert summary['distinct_builds'] == 11
