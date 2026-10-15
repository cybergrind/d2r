"""The MF guide's charm swap is conditional on explicitly known activity."""

from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from tests.pricing.knowledge.assessment.role_rows import role_rows
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.fixture(scope='module')
def role():
    return next(p for p in build()['profiles'] if p['id'] == 'lightning-sentry-assassin-mf-high-player-skiller')


@pytest.mark.parametrize(
    ('activity', 'truth'),
    [('high_player_count_farming', 'true'), ('solo_farming', 'false'), (None, 'unknown')],
)
def test_mf_swap_preserves_activity_condition(role, activity, truth):
    item = replace(
        facts('Grand Charm', 'magic'),
        stats={'188:48': {'status': 'decoded', 'value': 1}, '7:0': {'status': 'decoded', 'value': 36}},
    )
    result = role_rows(item, [role], {'player_class': 'Assassin', 'activity': activity})[0]
    assert result['rule_trace']['truth'] == truth
    assert result['status'] == {'true': 'matched', 'false': 'failed', 'unknown': 'partial'}[truth]
    assert result['dependencies'][0]['status'] == truth
    assert role['variant'] == 'Magic Find'
    assert 'high player count' in str(role['source']).lower()


@pytest.mark.parametrize('key', ['188:48', '7:0'])
def test_mf_swap_requires_known_skill_and_vita_suffix(role, key):
    item = replace(
        facts('Grand Charm', 'magic'),
        stats={k: {'status': 'decoded', 'value': v} for k, v in {'188:48': 1, '7:0': 36}.items() if k != key},
    )
    ctx = {'player_class': 'Assassin', 'activity': 'high_player_count_farming'}
    assert role_rows(item, [role], ctx)[0]['rule_trace']['truth'] == 'false'
    assert role_rows(replace(item, capture_complete=False), [role], ctx)[0]['rule_trace']['truth'] == 'unknown'
