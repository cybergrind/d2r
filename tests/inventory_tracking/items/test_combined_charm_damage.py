"""Only a verified legal magic prefix/suffix pair can supply combined roll bounds."""

from copy import deepcopy

import pytest


def entries():
    return [
        {
            'name': 'Sharp',
            'table_id': 1038,
            'affix_table': 'prefix',
            'game_definition': {'group': 111},
            'source': {'record_key': '253'},
            'roll_ranges': {'22': {'stat_id': 22, 'min': 7, 'max': 10, 'property': 'dmg-max', 'better': 'higher'}},
        },
        {
            'name': 'of Maiming',
            'table_id': 678,
            'affix_table': 'suffix',
            'game_definition': {'group': 14},
            'source': {'record_key': '678'},
            'roll_ranges': {'22': {'stat_id': 22, 'min': 3, 'max': 4, 'property': 'dmg-max', 'better': 'higher'}},
        },
    ]


def pool(entry, stat):
    assert stat == '22'
    if entry['affix_table'] == 'prefix':
        return {
            'range': {'min': 1, 'max': 10},
            'tiers': [{'min': 7, 'max': 10}, {'min': 4, 'max': 6}, {'min': 1, 'max': 3}],
        }
    return {'range': {'min': 1, 'max': 4}, 'tiers': [{'min': 3, 'max': 4}, {'min': 2, 'max': 2}, {'min': 1, 'max': 1}]}


def test_combines_current_and_global_bounds_without_mutating_sources():
    from inventory_tracking.items.combined_charm_damage import combined_damage_ranges

    rows = entries()
    before = deepcopy(rows)
    result = combined_damage_ranges(rows, {'type': 'lcha'}, 4, pool)['22']
    assert (result['min'], result['max']) == (10, 14)
    assert result['quality_range'] == {'min': 2, 'max': 14}
    assert result['tiers'][0] == {'min': 10, 'max': 14}
    assert {'min': 2, 'max': 4} in result['tiers']
    assert result['affix_ids'] == [1038, 678]
    assert result['source'] == [row['source'] for row in rows]
    assert rows == before


@pytest.mark.parametrize(
    'invalid',
    ['weapon', 'rare', 'same-table', 'same-group', 'third-contributor', 'different-property', 'nonphysical', 'no-pool'],
)
def test_unsupported_contributions_are_not_added(invalid):
    from inventory_tracking.items.combined_charm_damage import combined_damage_ranges

    rows = entries()
    base = {'type': 'lcha'}
    quality = 4
    resolver = pool
    if invalid == 'weapon':
        base = {'type': 'swor'}
    elif invalid == 'rare':
        quality = 6
    elif invalid == 'same-table':
        rows[1]['affix_table'] = 'prefix'
    elif invalid == 'same-group':
        rows[1]['game_definition']['group'] = 111
    elif invalid == 'third-contributor':
        rows.append(deepcopy(rows[0]))
    elif invalid == 'different-property':
        rows[1]['roll_ranges']['22']['property'] = 'unverified'
    elif invalid == 'nonphysical':
        for row in rows:
            row['roll_ranges'] = {'7': {'stat_id': 7, 'min': 1, 'max': 2, 'property': 'hp', 'better': 'higher'}}
    else:

        def resolver(entry, stat):
            return {}

    assert combined_damage_ranges(rows, base, quality, resolver) == {}
