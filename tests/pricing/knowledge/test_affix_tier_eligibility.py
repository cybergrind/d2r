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


def test_unreachable_grand_charm_vita_tier_does_not_raise_life_ceiling():
    # Native magicsuffix records 338/339/340; the last requires affix level 110.
    rows = []
    for level, low, high in ((77, 36, 40), (91, 41, 45), (110, 46, 50)):
        row = affix(low, high, 1, rare=False)
        row['game_definition']['level'] = level
        rows.append(row)
    add_charm_quality_ranges(rows)
    assert rows[0]['roll_tiers']['fixture-base']['7'] == [{'min': 41, 'max': 45}, {'min': 36, 'max': 40}]
    assert rows[0]['quality_ranges']['fixture-base']['7'] == {'min': 36, 'max': 45}
    assert rows[-1]['roll_ranges']['7']['max'] == 50


@pytest.mark.parametrize(
    ('stat', 'codes'),
    [
        ('96', ('move1', 'move2', 'move3')),
        ('93', ('swing1', 'swing2', 'swing3')),
        ('99', ('balance1', 'balance2', 'balance3')),
    ],
)
def test_native_group_combines_property_codes_without_combining_other_groups(stat, codes):
    rows = []
    for value, code in zip((10, 20, 30), codes, strict=True):
        row = affix(value, value, 1)
        row['game_definition']['group'] = 35
        row['roll_ranges'] = {stat: {'min': value, 'max': value, 'property': code}}
        rows.append(row)
    other = affix(40, 40, 1)
    other['game_definition']['group'] = 36
    other['roll_ranges'] = {stat: {'min': 40, 'max': 40, 'property': codes[0]}}
    rows.append(other)
    add_charm_quality_ranges(rows, rare=True)
    assert rows[0]['rare_roll_tiers']['fixture-base'][stat] == [{'min': value, 'max': value} for value in (30, 20, 10)]
    assert other['rare_quality_ranges']['fixture-base'][stat] == {'min': 40, 'max': 40}


def test_multi_stat_affix_does_not_borrow_single_stat_ceiling_in_same_group():
    single, combined = affix(20, 30, 1), affix(5, 10, 1)
    for row in (single, combined):
        row['game_definition']['group'] = 120
    combined['roll_ranges']['9'] = {'min': 5, 'max': 10, 'property': 'mana'}
    add_charm_quality_ranges([single, combined])
    assert combined['quality_ranges']['fixture-base']['7'] == {'min': 5, 'max': 10}


@pytest.mark.parametrize('rarity', ['magic', 'rare', 'crafted'])
@pytest.mark.parametrize(('level', 'eligible'), [(99, True), (100, False), (110, False)])
def test_affix_generation_respects_native_maximum_level(rarity, level, eligible):
    from pricing.knowledge.assessment.mechanics.affix_pool import can_generate

    row = affix(1, 2, 1)
    row['game_definition']['level'] = level
    assert can_generate(row, 'fixture-base', rarity) is eligible
