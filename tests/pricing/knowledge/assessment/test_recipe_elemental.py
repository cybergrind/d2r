from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers.runeword import definitions, intrinsic_properties
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def elemental_item(base, stats):
    mapping = {48: '458', 49: '459', 50: '478', 51: '479'}
    return replace(
        facts(base),
        stats={
            f'{s}:0': {'status': 'decoded', 'raw': v, 'value': v, 'market_property': mapping[s]}
            for s, v in stats.items()
        },
        properties={mapping[s]: v for s, v in stats.items()},
    )


@pytest.mark.parametrize(
    ('name', 'base', 'stats', 'expected'),
    [
        ('Faith', 'Grand Matron Bow', {48: 120, 49: 120}, {'458': 120, '459': 120}),
        ('Holy Thunder', 'War Scepter', {48: 5, 49: 30, 50: 21, 51: 110}, {'458': 5, '459': 30, '478': 21, '479': 110}),
        ('Lawbringer', 'Phase Blade', {48: 150, 49: 210}, {'458': 150, '459': 210}),
    ],
)
def test_fixed_recipe_damage_is_combined_with_destination_rune_effects(name, base, stats, expected):
    item = elemental_item(base, stats)
    assert intrinsic_properties(item, definitions()[name], 'weapon') == expected
    for key in item.stats:
        changed = replace(item, stats={**item.stats, key: {**item.stats[key], 'raw': 999}})
        pair = {'458', '459'} if key.split(':')[0] in ('48', '49') else {'478', '479'}
        assert not pair & intrinsic_properties(changed, definitions()[name], 'weapon').keys()


def test_holy_thunder_cannot_accept_only_ort_damage_as_the_completed_lightning_total():
    item = elemental_item('War Scepter', {50: 1, 51: 50})
    assert not {'478', '479'} & intrinsic_properties(item, definitions()['Holy Thunder'], 'weapon').keys()


def test_unspecified_recipe_cold_duration_cannot_be_verified_from_a_rune():
    from pricing.knowledge.assessment.handlers.runeword import elemental_effects
    from pricing.knowledge.assessment.mechanics.elemental import fixed_elemental_properties

    definition = definitions()['Lawbringer']
    cold = next(e for e in definition['fixed_elemental_effects'] if e['kind'] == 'cold')
    assert cold['duration_frames'] is None
    item = replace(
        facts('Phase Blade'),
        stats={
            '54:0': {'status': 'decoded', 'raw': 3, 'value': 3},
            '55:0': {'status': 'decoded', 'raw': 14, 'value': 14},
            '56:0': {'status': 'decoded', 'raw': 75, 'value': 3, 'unit': 'seconds'},
        },
        properties={'482': 3, '483': 14},
    )
    # A rune-like additional source does not erase the unverified recipe source.
    rune = {'kind': 'cold', 'minimum_damage': 3, 'maximum_damage': 14, 'duration_frames': 75}
    combined = [*elemental_effects(definition, 'weapon'), rune]
    assert not fixed_elemental_properties(item, combined)
