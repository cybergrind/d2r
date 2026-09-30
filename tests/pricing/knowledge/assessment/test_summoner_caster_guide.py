from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'values'),
    [
        (
            'Harlequin Crest',
            'Shako',
            {'127:0': 2, '216:0': 1.5, '217:0': 1.5, '80:0': 50, '36:0': 10, '0:0': 2, '1:0': 2, '2:0': 2, '3:0': 2},
        ),
        (
            'Skin of the Vipermagi',
            'Serpentskin Armor',
            {'127:0': 1, '105:0': 30, '39:0': 20, '41:0': 20, '43:0': 20, '45:0': 20, '35:0': 9, '16:0': 120},
        ),
        ('Arachnid Mesh', 'Spiderweb Sash', {'127:0': 1, '105:0': 20, '77:0': 5, '16:0': 90}),
        ('War Traveler', 'Battle Boots', {'80:0': 30, '96:0': 25, '0:0': 10, '3:0': 10, '16:0': 150}),
        ("Aldur's Advance", 'Battle Boots', {'96:0': 40, '7:0': 50, '39:0': 40}),
        ('Sandstorm Trek', 'Scarabshell Boots', {'96:0': 20, '99:0': 20, '0:0': 10, '3:0': 10, '45:0': 40}),
        (
            'Wizardspike',
            'Bone Knife',
            {'105:0': 50, '39:0': 75, '41:0': 75, '43:0': 75, '45:0': 75, '217:0': 2, '77:0': 15, '27:0': 15},
        ),
        ("Skullder's Ire", 'Russet Armor', {'127:0': 1, '240:0': 1.25, '35:0': 10}),
        ('Chance Guards', 'Chain Gloves', {'80:0': 25}),
        ('Goldwrap', 'Heavy Belt', {'80:0': 30}),
        ('String of Ears', 'Demonhide Sash', {'36:0': 10, '35:0': 10}),
        ('Silkweave', 'Mesh Boots', {'96:0': 30, '77:0': 10, '138:0': 5, '32:0': 200}),
        ("Bul-Kathos' Wedding Band", 'Ring', {'127:0': 1, '216:0': 0.5}),
        ('Peasant Crown', 'War Hat', {'127:0': 1, '96:0': 15, '3:0': 20, '1:0': 20, '74:0': 6}),
        ('Magefist', 'Light Gauntlets', {'105:0': 20, '27:0': 25, '126:1': 1}),
        ("Natalya's Soul", 'Mesh Boots', {'96:0': 40, '41:0': 15, '43:0': 15}),
    ],
)
def test_summoner_caster_aliases_and_native_utility(name, base, values):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-summoner-caster-gear')]
    assert len(roles) == 1
    role = roles[0]
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
    ]
    item = replace(
        facts(base, 'set' if name in ("Aldur's Advance", "Natalya's Soul") else 'unique', name),
        stats={
            k: {'status': 'decoded', 'value': v}
            for k, v in {**values, '60:0': 5, '93:0': 10, '19:0': 100, '48:0': 5}.items()
        },
    )

    def evaluate(candidate, klass='Necromancer'):
        ctx = {'player_class': klass}
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, roles, ctx)
        )

    assert set(evaluate(item).annotations) == set(values)
    assert not evaluate(item, 'Sorceress').annotations
    for patch in ({'rarity': 'rare'}, {'sockets': 2}, {'base_code': facts('Jewel').base_code}):
        assert not evaluate(replace(item, **patch)).annotations
    assert not evaluate(replace(item, ethereal=True)).annotations
    if name in ('Sandstorm Trek', "Skullder's Ire"):
        assert set(
            evaluate(
                replace(item, ethereal=True, stats={**item.stats, '252:0': {'status': 'decoded', 'value': 20}})
            ).annotations
        ) == set(values)
