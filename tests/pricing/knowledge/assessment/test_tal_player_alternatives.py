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
            "Tal Rasha's Guardianship",
            'Lacquered Plate',
            6,
            {'80:0': 88, '35:0': 15, '39:0': 40, '41:0': 40, '43:0': 40},
        ),
        ("Tal Rasha's Adjudication", 'Amulet', 3, {'83:1': 2, '7:0': 50, '9:0': 42, '41:0': 33}),
        ("Tal Rasha's Fine-Spun Cloth", 'Mesh Belt', 3, {'80:0': 10, '9:0': 30, '2:0': 20, '114:0': 37}),
        ("Tal Rasha's Lidless Eye", 'Swirling Crystal', 3, {'105:0': 20, '7:0': 57, '9:0': 77, '1:0': 10}),
    ],
)
def test_tal_pieces_only_prioritize_native_benefits_and_relevant_mastery(name, base, count, values):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-tal-player-alternative')]
    assert len(roles) == count
    for role in roles:
        expected = set(values)
        if name == "Tal Rasha's Lidless Eye":
            expected.add(
                {'blizzard-sorceress': '107:65', 'lightning-sorceress': '107:63', 'meteor-sorceress': '107:61'}[
                    role['build']
                ]
            )
        item = replace(
            facts(base, 'set', name),
            stats={
                k: {'status': 'decoded', 'value': v}
                for k, v in {
                    '105:0': 10,
                    '127:0': 3,
                    '83:1': 1,
                    '107:61': 1,
                    '107:63': 1,
                    '107:65': 1,
                    **values,
                }.items()
            },
        )
        context = {'player_class': role['must']['all'][0]['value']}
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, role=role, context=context, configs=configs):
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        assert set(evaluate(item).annotations) == expected
        assert not evaluate(replace(item, ethereal=True)).annotations
        assert not evaluate(replace(item, rarity='unique')).annotations
        if base in ('Amulet', 'Mesh Belt'):
            assert not evaluate(replace(item, sockets=1)).annotations
        if base == 'Mesh Belt':
            assert set(evaluate(replace(item, base_code=facts('Mithril Coil').base_code)).annotations) == expected
            assert not evaluate(replace(item, base_code=facts('Belt').base_code)).annotations
        assert any('companion' in condition for condition in role['conditions'])
