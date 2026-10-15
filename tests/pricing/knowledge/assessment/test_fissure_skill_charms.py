"""Fissure's source-listed charm suffixes stay distinct from the bare skiller."""

from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from tests.pricing.knowledge.assessment.role_rows import role_rows
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_fissure_charm_rules_require_the_correct_tree_and_source_suffix():
    profiles = {r['id']: r for r in build()['profiles']}
    for suffix, secondary in [
        ('plain', {}),
        ('vita', {'7:0': 36}),
        ('balance', {'99:0': 12}),
        ('inertia', {'96:0': 7}),
    ]:
        ident = f'fissure-elemental-grand-charm-{suffix}'
        assert ident in profiles
        role = profiles[ident]
        item = replace(
            facts('Grand Charm', 'magic'),
            stats={k: {'status': 'decoded', 'value': v} for k, v in {'188:42': 1, **secondary}.items()},
        )
        assert role_rows(item, [role], {'player_class': 'Druid'})[0]['rule_trace']['truth'] == 'true'
        assert role_rows(item, [role], {'player_class': 'Druid'})[0]['status'] == 'matched'
        assert role_rows(item, [role], {'player_class': 'Sorceress'})[0]['rule_trace']['truth'] == 'false'
        assert role_rows(item, [role], {})[0]['rule_trace']['truth'] == 'unknown'
        wrong = replace(
            item,
            stats={
                **{k: v for k, v in item.stats.items() if k != '188:42'},
                '188:40': {'status': 'decoded', 'value': 1},
            },
        )
        assert role_rows(wrong, [role], {'player_class': 'Druid'})[0]['rule_trace']['truth'] == 'false'
        for key in item.stats:
            missing = replace(item, stats={k: v for k, v in item.stats.items() if k != key})
            assert role_rows(missing, [role], {'player_class': 'Druid'})[0]['rule_trace']['truth'] == 'false'
            unread = replace(missing, capture_complete=False)
            assert role_rows(unread, [role], {'player_class': 'Druid'})[0]['rule_trace']['truth'] == 'unknown'
