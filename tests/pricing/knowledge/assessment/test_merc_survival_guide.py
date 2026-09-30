from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'sockets', 'count', 'values'),
    [
        ('Wealth', 'Mage Plate', 3, 2, {'80:0': 100, '79:0': 300, '2:0': 10}),
        ('Smoke', 'Mage Plate', 2, 7, {'39:0': 50, '41:0': 50, '43:0': 50, '45:0': 50, '99:0': 20, '32:0': 280}),
        (
            'Duress',
            'Mage Plate',
            3,
            7,
            {
                '136:0': 15,
                '135:0': 33,
                '17:0': 10,
                '18:0': 10,
                '99:0': 40,
                '39:0': 15,
                '41:0': 15,
                '43:0': 45,
                '45:0': 15,
            },
        ),
        ('Rockstopper', 'Sallet', 0, 7, {'36:0': 10, '99:0': 30, '39:0': 20, '41:0': 20, '43:0': 20}),
        ('Rockfleece', 'Field Plate', 0, 7, {'36:0': 10, '34:0': 5, '0:0': 5}),
        (
            'Lionheart',
            'Mage Plate',
            3,
            3,
            {'17:0': 20, '18:0': 20, '7:0': 50, '0:0': 25, '2:0': 15, '39:0': 30, '41:0': 30, '43:0': 30, '45:0': 30},
        ),
        ('Temper', 'Mask', 3, 7, {'39:0': 40, '142:0': 10, '76:0': 5, '99:0': 20}),
        ('Cure', 'Mask', 3, 7, {'151:109': 1, '45:0': 40, '110:0': 50, '76:0': 5, '99:0': 20}),
        ('Ground', 'Mask', 3, 6, {'41:0': 40, '144:0': 10, '76:0': 5, '99:0': 20}),
        ('Guardian Angel', 'Templar Coat', 0, 3, {'40:0': 15, '42:0': 15, '44:0': 15, '46:0': 15}),
        ('Skin of the Flayed One', 'Demonhide Armor', 0, 3, {'60:0': 5, '74:0': 15}),
        ('The Face of Horror', 'Mask', 0, 3, {'0:0': 20, '39:0': 10, '41:0': 10, '43:0': 10, '45:0': 10}),
        ('Venom Ward', 'Breast Plate', 0, 2, {'45:0': 90, '46:0': 15, '110:0': 50, '16:0': 60}),
        (
            'Goldskin',
            'Full Plate Mail',
            0,
            5,
            {'39:0': 35, '41:0': 35, '43:0': 35, '45:0': 35, '16:0': 120, '79:0': 100},
        ),
        ("The Gladiator's Bane", 'Wire Fleece', 0, 1, {'34:0': 15, '35:0': 15, '153:0': 1, '99:0': 30, '110:0': 50}),
    ],
)
def test_merc_survival_uses_preserve_bearer_and_native_low_rolls(name, base, sockets, count, values):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-merc-survival-gear')]
    assert len(roles) == count
    item = replace(
        facts(base, 'normal' if sockets else 'unique', name),
        runeword=name if sockets else None,
        sockets=sockets,
        socket_contents='filled' if sockets else 'empty',
        stats={
            k: {'status': 'decoded', 'value': v}
            for k, v in {**values, '3:0': 20, '1:0': 20, '83:3': 1, '252:0': 10}.items()
        },
    )
    for role in roles:
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]
        klass = role['must']['all'][0]['value']

        def evaluate(candidate, merc='Act 2 Might', player=klass, configs=configs, role=role):
            ctx = {'player_class': player, 'mercenary_type': merc}
            return StatsEvaluator().evaluate(
                candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
            )

        assert set(evaluate(item).annotations) == set(values)
        if sockets:
            for quality in ('superior', 'low_quality'):
                assert set(evaluate(replace(item, rarity=quality)).annotations) == set(values)
        assert set(evaluate(replace(item, ethereal=True)).annotations) == set(values)
        assert not evaluate(item, 'Act 3 Fire').annotations
        assert not evaluate(item, player='Barbarian').annotations
        assert not evaluate(replace(item, base_code=facts('Jewel').base_code)).annotations
        assert not evaluate(replace(item, rarity='magic')).annotations
        if sockets:
            assert not evaluate(replace(item, runeword=None)).annotations
            assert not evaluate(replace(item, socket_contents='empty')).annotations
        else:
            assert not evaluate(replace(item, sockets=2)).annotations
        # The reviewed Zeal Early-Game column explicitly offers both mercenaries.
        frenzy_names = {
            'Goldskin',
            'Venom Ward',
            'Rockfleece',
            'Lionheart',
            'Temper',
            'Cure',
            'Skin of the Flayed One',
            'The Face of Horror',
        }
        if role['build'] == 'zeal-paladin' and name in frenzy_names:
            assert set(evaluate(item, 'Act 5 Frenzy').annotations) == set(values)
        else:
            assert not evaluate(item, 'Act 5 Frenzy').annotations
