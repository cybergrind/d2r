"""Main guide skillers must use the correct class tree and suffix, not perfect rolls."""

from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_main_skill_charm_rules_distinguish_class_tree_and_suffix():
    profiles = {r['id']: r for r in build()['profiles']}
    for build_id, klass, layer, wrong_layer, suffixes in (
        ('lightning-sentry-assassin', 'Assassin', 48, 49, ('vita',)),
        ('lightning-sorceress', 'Sorceress', 9, 8, ('vita', 'balance', 'plain')),
        ('lightning-strike-amazon', 'Amazon', 2, 0, ('vita', 'balance', 'inertia', 'plain')),
        ('poison-nova-necromancer', 'Necromancer', 17, 18, ('vita', 'balance', 'plain')),
    ):
        for suffix in suffixes:
            ident = f'{build_id}-main-skiller-{suffix}'
            assert ident in profiles
            role = profiles[ident]
            secondary = {'vita': {'7:0': 36}, 'balance': {'99:0': 12}, 'inertia': {'96:0': 7}, 'plain': {}}[suffix]
            key = f'188:{layer}'
            item = replace(
                facts('Grand Charm', 'magic'),
                stats={k: {'status': 'decoded', 'value': v} for k, v in {key: 1, **secondary}.items()},
            )
            assert assess_roles(item, [role], {'player_class': klass})[0]['rule_trace']['truth'] == 'true'
            assert assess_roles(item, [role], {'player_class': klass})[0]['status'] == 'matched'
            assert assess_roles(item, [role], {'player_class': 'Druid'})[0]['rule_trace']['truth'] == 'false'
            assert assess_roles(item, [role], {})[0]['rule_trace']['truth'] == 'unknown'
            wrong = replace(
                item,
                stats={
                    **{k: v for k, v in item.stats.items() if k != key},
                    f'188:{wrong_layer}': {'status': 'decoded', 'value': 1},
                },
            )
            assert assess_roles(wrong, [role], {'player_class': klass})[0]['rule_trace']['truth'] == 'false'
            for stat in item.stats:
                missing = replace(item, stats={k: v for k, v in item.stats.items() if k != stat})
                assert assess_roles(missing, [role], {'player_class': klass})[0]['rule_trace']['truth'] == 'false'
                assert (
                    assess_roles(replace(missing, capture_complete=False), [role], {'player_class': klass})[0][
                        'rule_trace'
                    ]['truth']
                    == 'unknown'
                )
