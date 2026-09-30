from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'count', 'values'),
    [
        (
            'Harlequin Crest',
            'Shako',
            6,
            {'127:0': 2, '216:0': 1.5, '217:0': 1.5, '80:0': 50, '36:0': 10, '0:0': 2, '1:0': 2, '2:0': 2, '3:0': 2},
        ),
        (
            'Skin of the Vipermagi',
            'Serpentskin Armor',
            6,
            {'127:0': 1, '105:0': 30, '39:0': 20, '41:0': 20, '43:0': 20, '45:0': 20, '35:0': 9, '16:0': 120},
        ),
        ('Arachnid Mesh', 'Spiderweb Sash', 6, {'127:0': 1, '105:0': 20, '77:0': 5, '16:0': 90}),
        ('The Stone of Jordan', 'Ring', 6, {'127:0': 1, '9:0': 20, '77:0': 25}),
        (
            "Mara's Kaleidoscope",
            'Amulet',
            4,
            {'127:0': 2, '39:0': 20, '41:0': 20, '43:0': 20, '45:0': 20, '0:0': 5, '1:0': 5, '2:0': 5, '3:0': 5},
        ),
        ('War Traveler', 'Battle Boots', 6, {'80:0': 30, '96:0': 25, '0:0': 10, '3:0': 10, '16:0': 150}),
    ],
)
def test_remaining_caster_core_native_rolls_and_recipient_exclusions(name, base, count, values):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-caster-core-gear')]
    assert len(roles) == count
    excluded = {'21:0': 15, '22:0': 25, '50:0': 1, '51:0': 12, '150:0': 10}
    item = replace(
        facts(base, 'unique', name),
        stats={k: {'status': 'decoded', 'value': v} for k, v in {**values, **excluded}.items()},
    )
    for role in roles:
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]
        klass = role['must']['all'][0]['value']

        def evaluate(candidate, player=klass, configs=configs, role=role):
            ctx = {'player_class': player}
            return StatsEvaluator().evaluate(
                candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
            )

        assert set(evaluate(item).annotations) == set(values)
        assert not evaluate(item, 'Barbarian').annotations
        for patch in ({'ethereal': True}, {'rarity': 'rare'}, {'base_code': facts('Jewel').base_code}, {'sockets': 2}):
            assert not evaluate(replace(item, **patch)).annotations
        if name == 'Skin of the Vipermagi':
            assert set(evaluate(replace(item, base_code=facts('Wyrmhide').base_code)).annotations) == set(values)
        if name == "Mara's Kaleidoscope":
            assert klass == 'Sorceress'
        assert not any(k.startswith('204:') for k in role['important_stats'])
