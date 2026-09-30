from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'count', 'core'),
    [
        ("Defender's Fire", 4, {'329:0': 10, '333:0': 10}),
        ("Defender's Bile", 1, {'332:0': 10, '336:0': 10}),
        ("Guardian's Light", 8, {'357:0': 10, '358:0': 10}),
        ("Guardian's Thunder", 12, {'330:0': 10, '334:0': 10}),
        ("Protector's Frost", 2, {'331:0': 10, '335:0': 10}),
        ("Protector's Stone", 12, {'17:0': 40, '18:0': 40, '366:0': 10}),
        ('Rainbow Facet', 15, None),
    ],
)
def test_named_jewels_need_matching_damage_and_recipient_without_buffing_inventory(name, count, core):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-named-socket-jewel')]
    assert len(roles) == count
    facet_keys = {
        'blizzard-sorceress': ('331:0', '335:0'),
        'enchant-sorceress': ('329:0', '333:0'),
        'fire-warlock-guide': ('329:0', '333:0'),
        'fissure-druid': ('329:0', '333:0'),
        'fist-of-the-heavens-paladin': ('330:0', '334:0'),
        'lightning-sorceress': ('330:0', '334:0'),
        'lightning-strike-amazon': ('330:0', '334:0'),
        'meteor-sorceress': ('329:0', '333:0'),
        'nova-sorceress-guide': ('330:0', '334:0'),
        'poison-nova-necromancer': ('332:0', '336:0'),
    }
    for role in roles:
        values = (
            dict.fromkeys(facet_keys[role['build']], 5)
            if name == 'Rainbow Facet'
            else {**core, '85:0': 5, '80:0': 35, '79:0': 50}
        )
        expected = set(values)
        if role['build'] == 'berserk-barbarian':
            expected.remove('357:0')
        if role['build'] == 'summoner-necromancer-guide':
            expected -= {'17:0', '18:0', '366:0'}
        if role['build'] == 'gold-find-barbarian' and role['variant'] == 'Standard':
            expected.remove('366:0')
        base = 'Jewel' if name == 'Rainbow Facet' else 'Colossal Jewel'
        item = replace(
            facts(base, 'unique', name), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()}
        )
        host = role['depends_on'][0]['when']['value']
        context = {'player_class': role['must']['all'][0]['value'], 'player_items': [host]}
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, ctx=context, configs=configs, role=role):
            return StatsEvaluator().evaluate(
                candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
            )

        assert set(evaluate(item).annotations) == expected
        assert not evaluate(item, {**context, 'player_items': []}).annotations
        assert not evaluate(item, {'player_class': context['player_class']}).annotations
        for patch in (
            {'rarity': 'rare'},
            {'ethereal': True},
            {'sockets': 1},
            {'name': host},
            {'base_code': facts('Grand Charm').base_code},
        ):
            assert not evaluate(replace(item, **patch)).annotations
        if name == 'Rainbow Facet':
            wrong = {'329:0': 5, '333:0': 5} if '329:0' not in values else {'331:0': 5, '335:0': 5}
            assert not evaluate(
                replace(item, stats={k: {'status': 'decoded', 'value': v} for k, v in wrong.items()})
            ).annotations
        else:
            assert any('Only one Colossal Jewel' in c for c in role['conditions'])
        assert not any(k.startswith(('195:', '197:', '198:', '199:', '201:')) for k in role['important_stats'])
