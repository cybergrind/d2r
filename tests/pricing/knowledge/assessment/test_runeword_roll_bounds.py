from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers.runeword import RunewordHandler
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('stat', 'valid', 'invalid'), [(105, 35, 36), (105, 25, 24), (9, 112, 113), (147, 8, 9), (105, 30, 30.5)]
)
def test_spirit_rejects_impossible_variable_rolls(stat, valid, invalid):
    item = replace(
        facts('Monarch'),
        name='Spirit',
        runeword='Spirit',
        sockets=4,
        socket_contents='filled',
        stats={f'{s}:0': {'status': 'decoded', 'value': v} for s, v in [(105, 35), (9, 112), (147, 8), (31, 148)]},
    )
    key = f'{stat}:0'
    assert RunewordHandler().contract(
        replace(item, stats={**item.stats, key: {'status': 'decoded', 'value': valid}}), 'shield'
    )[0]
    contract, gaps = RunewordHandler().contract(
        replace(item, stats={**item.stats, key: {'status': 'decoded', 'value': invalid}}), 'shield'
    )
    assert contract is None
    assert any('outside' in g and key in g for g in gaps)


def test_call_to_arms_oskill_is_not_allowed_above_its_own_range():
    item = replace(
        facts('Crystal Sword'),
        name='Call to Arms',
        runeword='Call to Arms',
        sockets=5,
        socket_contents='filled',
        stats={
            key: {'status': 'decoded', 'value': value}
            for key, value in [('17:0', 220), ('18:0', 220), ('97:155', 6), ('97:149', 6), ('97:146', 5)]
        },
    )
    contract, gaps = RunewordHandler().contract(item, 'weapon')
    assert contract is None
    assert any('97:146' in g and 'outside' in g for g in gaps)


def test_last_wish_crushing_blow_bounds_include_ber_contribution():
    from pricing.knowledge.assessment.handlers.runeword import definitions
    from pricing.knowledge.assessment.mechanics.runeword_rolls import variable_roll_gaps

    item = replace(facts('Phase Blade'), stats={f'{s}:0': {'status': 'decoded', 'value': 365} for s in (17, 18)})
    for value in (60, 70):
        captured = replace(item, stats={**item.stats, '136:0': {'status': 'decoded', 'value': value}})
        assert not variable_roll_gaps(captured, definitions()['Last Wish'], 'weapon')
    for value in (40, 50, 59, 71):
        captured = replace(item, stats={**item.stats, '136:0': {'status': 'decoded', 'value': value}})
        assert any('136:0' in gap for gap in variable_roll_gaps(captured, definitions()['Last Wish'], 'weapon'))
