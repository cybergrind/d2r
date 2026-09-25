from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers.definitions import named_definitions
from tests.pricing.knowledge.assessment.roles.test_fissure_player_helmets import assess
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('variant', ['standard', 'magic-find'])
@pytest.mark.parametrize(
    ('name', 'base', 'slug'),
    [('Magefist', 'Light Gauntlets', 'magefist'), ('War Traveler', 'Battle Boots', 'war-traveler')],
)
def test_named_farming_components_accept_nonperfect_rolls_and_keep_context(variant, name, base, slug):
    item = facts(base, 'unique', name)
    result = assess(item, f'{variant}-{slug}')[0]
    assert result['status'] == 'partial'
    assert result['rule_trace']['truth'] == 'true'
    assert result['preferences'] == []
    assert assess(replace(item, ethereal=True), f'{variant}-{slug}')[0]['status'] == 'failed'
    assert assess(replace(item, identified=False), f'{variant}-{slug}')[0]['status'] == 'unknown'
    assert assess(replace(item, ethereal=None), f'{variant}-{slug}')[0]['status'] == 'partial'
    assert assess(item, f'{variant}-{slug}', 'Sorceress')[0]['status'] == 'failed'
    assert not assess(replace(item, rarity='rare'), f'{variant}-{slug}')
    assert not assess(replace(item, name='Other'), f'{variant}-{slug}')
    wrong = facts('Heavy Gloves' if slug == 'magefist' else 'Boots', 'unique', name)
    assert assess(wrong, f'{variant}-{slug}')[0]['status'] == 'failed'


@pytest.mark.parametrize('base', ['Light Gauntlets', 'Battle Gauntlets', 'Crusader Gauntlets'])
def test_ubers_magefist_distinguishes_upgrade_candidate_from_equipped_destination(base):
    item = replace(
        facts(base, 'unique', 'Magefist'),
        provenance={
            'capture': {
                'item_identity': {
                    'table': 'unique',
                    'table_id': named_definitions()['unique', 'Magefist']['table_id'],
                }
            }
        },
    )
    result = assess(item, 'ubers-magefist')[0]
    assert result['status'] == 'partial'
    assert result['dependencies'][0]['status'] == ('true' if base == 'Crusader Gauntlets' else 'false')
    if base != 'Crusader Gauntlets':
        assert 'Crusader Gauntlets' in str(result)
        assert 'Upgrade to' in str(result)
    # The Standard build does not inherit the Ubers upgrade dependency.
    standard = assess(facts(base, 'unique', 'Magefist'), 'standard-magefist')[0]
    assert standard['rule_trace']['truth'] == 'true'
    assert standard['dependencies'] == []


def test_upgraded_war_traveler_remains_a_farming_candidate_without_claiming_better_magic_find():
    result = assess(facts('Mirrored Boots', 'unique', 'War Traveler'), 'magic-find-war-traveler')[0]
    assert result['status'] == 'partial'
    assert result['rule_trace']['truth'] == 'true'
    assert result['preferences'] == []
