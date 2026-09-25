import pytest

from pricing.knowledge.definitions import add_charm_quality_ranges


def affix(low, high, frequency, *, rare=True):
    return {
        'affix_table': 'suffix',
        'spawnable': True,
        'rare': rare,
        'game_definition': {} if frequency is None else {'frequency': frequency},
        'base_codes': ['fixture-base'],
        'roll_ranges': {'7': {'min': low, 'max': high, 'property': 'hp'}},
    }


@pytest.mark.parametrize('rare', [False, True])
def test_obsolete_affixes_do_not_set_top_tier_or_add_unavailable_brackets(rare):
    rows = [affix(10, 20, 1), affix(21, 30, 1, rare=False), affix(31, 40, 0), affix(41, 50, None)]
    add_charm_quality_ranges(rows, rare=rare)
    prefix = 'rare_' if rare else ''
    expected = [{'min': 10, 'max': 20}] if rare else [{'min': 21, 'max': 30}, {'min': 10, 'max': 20}]
    assert rows[0][prefix + 'roll_tiers']['fixture-base']['7'] == expected
    assert rows[0][prefix + 'quality_ranges']['fixture-base']['7'] == {'min': 10, 'max': 20 if rare else 30}
    # Historical identity/range evidence stays intact; it cannot define today's ceiling.
    assert rows[-1]['roll_ranges']['7']['max'] == 50
