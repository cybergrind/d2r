"""Reports retain useful watch guidance and omit research placeholders."""

import json
from pathlib import Path

import pytest

from inventory_tracking.appraisal.sections import value_watch_lines


@pytest.mark.parametrize('placeholder', ['no roll bucket', 'no roll', '-', '  No roll bucket.  '])
def test_watch_placeholders_do_not_dilute_actionable_item_advice(placeholder):
    details = {
        'priority': 'valuable_candidate',
        'roll_bucket': placeholder,
        'guide_conditions': 'Used on an Act 2 mercenary.',
        'stat_priority': 'Ethereal; life stolen per hit.',
    }
    assert value_watch_lines({'value_watch': [{'details': details}]}) == [
        'VALUABLE CANDIDATE',
        '  Used on an Act 2 mercenary.',
        '  Ethereal; life stolen per hit.',
    ]
    assert details['roll_bucket'] == placeholder  # Research evidence stays intact.


def test_actual_entropy_watch_does_not_print_an_empty_roll_bucket():
    rows = json.loads(Path('pricing/data/appraisal-value-watch.json').read_text())['rows']
    row = next(row for row in rows if row['name'] == 'Entropy Locket')
    assert row['details']['roll_bucket'] == 'no roll bucket'
    lines = value_watch_lines({'value_watch': [row]})
    assert lines[0] == 'VALUABLE CANDIDATE'
    assert any('Echoing Strike Warlock' in line for line in lines)
    assert all('no roll bucket' not in line for line in lines)


def test_concrete_roll_target_is_retained():
    row = {'details': {'priority': 'valuable_candidate', 'roll_bucket': 'Perfect native magic pierce: 5%'}}
    assert value_watch_lines({'value_watch': [row]}) == [
        'VALUABLE CANDIDATE',
        '  Perfect native magic pierce: 5%',
    ]


@pytest.mark.parametrize(
    'note',
    [
        'Versatile Leveling Set Drops in Value after Early Ladder',
        'Versatile Leveling Set Drops in Value quickly',
        'Extremely strong survivability Helmet for Leveling More useful on Hardcore',
        'Strong +1 to All Skills Helmet for Leveling Used on several budget builds Drops in Value after Early Ladder',
        'High Resistance Shield Used during Leveling and in Hardcore',
        'Solid Magic Find option until Harlequin Crest Drops in Value after Early Ladder',
    ],
)
def test_generic_progression_and_ladder_value_notes_are_not_visible(note):
    details = {
        'priority': 'valuable_candidate',
        'guide_conditions': note,
        'stat_priority': 'Keep the independently reviewed roll target.',
    }
    lines = value_watch_lines({'value_watch': [{'details': details}]})
    assert lines == ['VALUABLE CANDIDATE', '  Keep the independently reviewed roll target.']
    assert details['guide_conditions'] == note


def test_mixed_tal_note_keeps_full_set_use_without_ladder_price_comment():
    note = "Used on early-game Mercenaries and full Tal Rasha's Wrappings setups Drops in Value after Early Ladder"
    row = {'details': {'priority': 'build_demand', 'guide_conditions': note}}
    assert value_watch_lines({'value_watch': [row]}) == ['BUILD DEMAND', "  Used in full Tal Rasha's Wrappings setups."]


@pytest.mark.parametrize(
    'note',
    [
        'Provides great survivability stats Best in Slot Leveling Unique',
        'Best in Slot Weapon for Leveling with the help of an Enchant Sorceress',
        'Perfect damage roll required for this Non-Ladder comparison.',
    ],
)
def test_exceptional_leveling_conditions_and_non_ladder_notes_remain(note):
    row = {'details': {'priority': 'valuable_candidate', 'guide_conditions': note}}
    assert '  ' + note in value_watch_lines({'value_watch': [row]})
