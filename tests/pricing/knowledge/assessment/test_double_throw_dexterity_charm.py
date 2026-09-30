"""Sharp/Dexterity inventory charm source is not a perfect-roll-only requirement."""

from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_double_throw_sharp_dexterity_charm_accepts_native_rolls_and_guards_missing_mods():
    profiles = build()['profiles']
    matches = [p for p in profiles if p['id'] == 'double-throw-sharp-dexterity-grand-charm']
    assert len(matches) == 1
    profile = matches[0]
    context = {'player_class': 'Barbarian'}
    for attack, damage, dexterity in ((49, 7, 3), (49, 7, 5), (76, 10, 6)):
        stats = {
            key: {'status': 'decoded', 'value': value}
            for key, value in (
                ('19:0', attack),
                ('22:0', damage),
                ('2:0', dexterity),
            )
        }
        item = replace(facts('Grand Charm', 'magic'), stats=stats)
        assert assess_roles(item, [profile], context)[0]['rule_trace']['truth'] == 'true'
        for key in stats:
            missing = replace(item, stats={k: v for k, v in stats.items() if k != key})
            assert assess_roles(missing, [profile], context)[0]['status'] == 'failed'
            assert (
                assess_roles(replace(missing, capture_complete=False), [profile], context)[0]['rule_trace']['truth']
                == 'unknown'
            )
    assert assess_roles(item, [profile], {})[0]['rule_trace']['truth'] == 'unknown'
    assert assess_roles(item, [profile], {'player_class': 'Paladin'})[0]['status'] == 'failed'
