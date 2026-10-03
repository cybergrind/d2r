"""Physical charm recommendations accept native minima, not only planner maxima."""

from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.fixture(scope='module')
def profiles():
    return {r['id']: r for r in build()['profiles']}


@pytest.mark.parametrize(
    ('build_id', 'klass', 'suffix'),
    [
        (b, k, s)
        for b, k, suffixes in [
            ('double-throw-barbarian-guide', 'Barbarian', ('vita', 'balance', 'inertia', 'plain')),
            ('berserk-barbarian', 'Barbarian', ('vita', 'balance', 'plain')),
            ('dream-paladin', 'Paladin', ('vita', 'balance')),
        ]
        for s in suffixes
    ],
)
def test_sharp_charm_native_minima_and_unknowns(profiles, build_id, klass, suffix):
    role = profiles[f'{build_id}-main-sharp-{suffix}']
    values = {
        '19:0': 49,
        '22:0': 7,
        **{'vita': {'7:0': 36}, 'balance': {'99:0': 12}, 'inertia': {'96:0': 7}, 'plain': {}}[suffix],
    }
    item = replace(
        facts('Grand Charm', 'magic'), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()}
    )
    context = {'player_class': klass}
    assert assess_roles(item, [role], context)[0]['status'] == 'matched'
    assert assess_roles(item, [role], {'player_class': 'Sorceress'})[0]['rule_trace']['truth'] == 'false'
    assert assess_roles(item, [role], {})[0]['rule_trace']['truth'] == 'unknown'
    for key, value in values.items():
        low = replace(item, stats={**item.stats, key: {'status': 'decoded', 'value': value - 1}})
        assert assess_roles(low, [role], context)[0]['rule_trace']['truth'] == 'false'
        missing = replace(item, stats={k: v for k, v in item.stats.items() if k != key})
        assert assess_roles(missing, [role], context)[0]['rule_trace']['truth'] == 'false'
        assert (
            assess_roles(replace(missing, capture_complete=False), [role], context)[0]['rule_trace']['truth']
            == 'unknown'
        )
