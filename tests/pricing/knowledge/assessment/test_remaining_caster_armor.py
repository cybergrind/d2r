from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.fixture(scope='module')
def armor_bundle():
    return build()


@pytest.mark.parametrize(
    ('name', 'base', 'count', 'values'),
    [
        (
            "Que-Hegan's Wisdom",
            'Mage Plate',
            2,
            {'127:0': 1, '105:0': 20, '99:0': 20, '138:0': 3, '35:0': 6, '1:0': 15, '16:0': 140},
        ),
        (
            "Ormus' Robes",
            'Dusk Shroud',
            4,
            {'105:0': 20, '27:0': 10, '31:0': 10, '329:0': 10, '330:0': 10, '331:0': 10},
        ),
        ('Bone', 'Archon Plate', 1, {'83:2': 2, '9:0': 100, '39:0': 30, '41:0': 30, '43:0': 30, '45:0': 30, '34:0': 7}),
        ('The Spirit Shroud', 'Ghost Armor', 1, {'127:0': 1, '153:0': 1, '35:0': 7, '74:0': 10, '16:0': 150}),
    ],
)
def test_remaining_caster_armor_keeps_native_recipients_and_optional_skills(armor_bundle, name, base, count, values):
    roles = [
        r for r in armor_bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-caster-armor-remainder')
    ]
    assert len(roles) == count
    word = name == 'Bone'
    item = replace(
        facts(base, 'normal' if word else 'unique', name),
        runeword=name if word else None,
        sockets=3 if word else 0,
        socket_contents='filled' if word else 'empty',
    )
    for role in roles:
        observed = dict(values)
        wanted = set(values)
        if name == "Que-Hegan's Wisdom" and role['build'] == 'summoner-warlock-guide':
            wanted.remove('138:0')
        if name == "Ormus' Robes":
            wanted.remove('330:0')
            if role['build'] in ('fire-wall-sorceress-guide', 'hydra-sorceress'):
                wanted.remove('331:0')
            if role['build'] == 'frozen-orb-sorceress':
                wanted.remove('329:0')
            skill = {'fire-wall-sorceress-guide': 51, 'frozen-orb-meteor-sorceress': 56}.get(role['build'], 54)
            observed[f'107:{skill}'] = 3
            if skill != 54:
                wanted.add(f'107:{skill}')
        candidate = replace(item, stats={k: {'status': 'decoded', 'value': v} for k, v in observed.items()})
        configs = [
            configuration_from_row(c)
            for c in armor_bundle['stat_evaluation']['configurations']
            if c['role_id'] == role['id']
        ]
        klass = role['must']['all'][0]['value']

        def evaluate(obj, player=klass, configs=configs, role=role):
            ctx = {'player_class': player}
            return StatsEvaluator().evaluate(obj, configs, ctx, role_outcomes=assess_role_results(obj, [role], ctx))

        assert set(evaluate(candidate).annotations) == wanted
        for patch in (
            {'ethereal': True},
            {'ethereal': None},
            {'rarity': 'rare'},
            {'identified': False},
            {'base_code': facts('Monarch').base_code},
            {'sockets': 2},
        ):
            assert not evaluate(replace(candidate, **patch)).annotations
        assert not evaluate(candidate, 'Barbarian').annotations
        if word:
            assert not evaluate(replace(candidate, runeword=None)).annotations
            assert not evaluate(replace(candidate, socket_contents='empty')).annotations
        else:
            assert set(evaluate(replace(candidate, sockets=1, socket_contents='filled')).annotations) == wanted
        if name == "Ormus' Robes":
            without_skill = replace(
                candidate, stats={k: v for k, v in candidate.stats.items() if not k.startswith('107:')}
            )
            assert set(evaluate(without_skill).annotations) == {k for k in wanted if not k.startswith('107:')}
            assert not any('15%' in p['label'] for p in role.get('preferences', []))
        if name in ("Que-Hegan's Wisdom", 'The Spirit Shroud'):
            upgraded = facts('Archon Plate' if name == "Que-Hegan's Wisdom" else 'Dusk Shroud')
            assert set(evaluate(replace(candidate, base_code=upgraded.base_code)).annotations) == wanted
