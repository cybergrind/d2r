"""Totals cannot identify the Sharp/Maiming configuration when they overlap."""

from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from tests.pricing.knowledge.assessment.role_rows import role_rows
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.fixture(scope='module')
def role():
    return next(r for r in build()['profiles'] if r['id'] == 'double-throw-barbarian-guide-main-sharp-maiming')


@pytest.mark.parametrize(
    ('affixes', 'truth'),
    [
        ({'prefix': [1038], 'suffix': [678], 'auto': []}, 'true'),
        ({'prefix': [1038], 'suffix': [], 'auto': []}, 'false'),
        (None, 'unknown'),
    ],
)
def test_equal_totals_preserve_native_identity(role, affixes, truth):
    item = replace(
        facts('Grand Charm', 'magic'),
        native_affixes=affixes,
        stats={'19:0': {'status': 'decoded', 'value': 49}, '22:0': {'status': 'decoded', 'value': 10}},
    )
    result = role_rows(item, [role], {'player_class': 'Barbarian'})[0]
    assert result['rule_trace']['truth'] == truth
    if truth == 'true':
        assert result['status'] == 'matched'
