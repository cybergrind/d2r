"""Physical charm recommendations accept native minima, not only planner maxima."""

from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from tests.pricing.knowledge.assessment.role_rows import role_rows
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
    assert role_rows(item, [role], context)[0]['status'] == 'matched'
    assert role_rows(item, [role], {'player_class': 'Sorceress'})[0]['rule_trace']['truth'] == 'false'
    assert role_rows(item, [role], {})[0]['rule_trace']['truth'] == 'unknown'
    for key, value in values.items():
        low = replace(item, stats={**item.stats, key: {'status': 'decoded', 'value': value - 1}})
        assert role_rows(low, [role], context)[0]['rule_trace']['truth'] == 'false'
        missing = replace(item, stats={k: v for k, v in item.stats.items() if k != key})
        assert role_rows(missing, [role], context)[0]['rule_trace']['truth'] == 'false'
        assert (
            role_rows(replace(missing, capture_complete=False), [role], context)[0]['rule_trace']['truth'] == 'unknown'
        )
