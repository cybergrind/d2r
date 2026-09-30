from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'quality', 'count', 'values'),
    [
        ('Magefist', 'Light Gauntlets', 'unique', 6, {'105:0': 20, '27:0': 25}),
        ("Trang-Oul's Claws", 'Heavy Bracers', 'set', 6, {'105:0': 20, '43:0': 30, '31:0': 30}),
        ('Lidless Wall', 'Grim Shield', 'unique', 2, {'127:0': 1, '105:0': 20, '77:0': 10, '1:0': 10, '138:0': 3}),
        ("Tal Rasha's Adjudication", 'Amulet', 'set', 4, {'83:1': 2, '7:0': 50, '9:0': 42, '41:0': 33}),
    ],
)
def test_caster_table_alternatives_keep_class_and_damage_recipient_semantics(name, base, quality, count, values):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-caster-gear-alternative')]
    assert len(roles) == count
    for role in roles:
        native = {**values, '126:1': 1, '332:0': 25, '188:16': 2, '48:0': 5, '49:0': 30}
        item = replace(
            facts(base, quality, name), stats={k: {'status': 'decoded', 'value': v} for k, v in native.items()}
        )
        expected = set(values)
        if name == 'Magefist' and role['build'] in (
            'fire-wall-sorceress-guide',
            'hydra-sorceress',
            'frozen-orb-meteor-sorceress',
        ):
            expected.add('126:1')
        if name == 'Lidless Wall' and role['build'] == 'summoner-warlock-guide':
            expected.remove('138:0')
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]
        klass = role['must']['all'][0]['value']

        def evaluate(candidate, player=klass, configs=configs, role=role):
            ctx = {'player_class': player}
            return StatsEvaluator().evaluate(
                candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
            )

        assert set(evaluate(item).annotations) == expected
        assert not evaluate(item, 'Barbarian').annotations
        for patch in ({'ethereal': True}, {'rarity': 'rare'}, {'base_code': facts('Jewel').base_code}):
            assert not evaluate(replace(item, **patch)).annotations
        if name in ('Magefist', "Trang-Oul's Claws"):
            assert not evaluate(replace(item, sockets=1)).annotations
        if name == "Tal Rasha's Adjudication":
            assert (
                '105:0'
                not in evaluate(
                    replace(item, stats={**item.stats, '105:0': {'status': 'decoded', 'value': 10}})
                ).annotations
            )
