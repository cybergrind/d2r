"""Decrepify support prose identifies the mercenary, not the player, as wearer."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_player_utility_context import run, setup as utility_setup


QUOTES = (
    "Reposition your Mercenary to apply Decrepify from his The Reaper's Toll or Lawbringers to nearby targets.",
    "Use a Mercenary with The Reaper's Toll or Lawbringers for Decrepify to deal with Physical Immunes.",
)


def setup(root, quote=QUOTES[0], lawbringer=False):
    label = 'Lawbringers' if lawbringer else "The Reaper's Toll"
    name = 'Lawbringer' if lawbringer else label
    merc = 'Act 5 Frenzy' if lawbringer else 'Act 2 Might'
    role, occurrence, doc = utility_setup(root, (label, 'runeword' if lawbringer else 'unique', 'Weapon', '', quote))
    role.update(names=[name], side='merc')
    if lawbringer:
        role['must']['all'][1]['value'] = name
    role['must'] = {'all': [role['must'], {'op': 'context_eq', 'field': 'mercenary_type', 'value': merc}]}
    occurrence['name'] = name
    row = doc['rows'][0]
    row['kind'] = 'mercenary_support_reference'
    row['expected_occurrence']['name'] = name
    row['branches'][0].update(mercenary_type=merc, profile_fingerprint=fingerprint(role))
    row['branches'][0].pop('utility_kind')
    return role, occurrence, doc


@pytest.mark.parametrize('quote', QUOTES)
@pytest.mark.parametrize('lawbringer', [False, True])
def test_explicit_support_sentence_preserves_raw_player_label(tmp_path, quote, lawbringer):
    role, occurrence, doc = setup(tmp_path, quote, lawbringer)
    saved = deepcopy(occurrence)
    assert run(tmp_path, role, occurrence, doc)[0]['state'] == 'reviewed'
    assert occurrence == saved


@pytest.mark.parametrize('change', ['player', 'slot', 'class', 'merc', 'optional-merc', 'name-only', 'section'])
def test_support_sentence_cannot_hide_wrong_wearer_or_effect(tmp_path, change):
    role, occurrence, doc = setup(tmp_path)
    row = doc['rows'][0]
    branch = row['branches'][0]
    if change == 'player':
        role['side'] = 'player'
    elif change == 'slot':
        role['slot'] = branch['slot'] = 'Helmet'
    elif change == 'class':
        role['must']['all'][0]['value'] = 'Sorceress'
    elif change == 'merc':
        role['must']['all'][1]['value'] = 'Act 5 Frenzy'
    elif change == 'optional-merc':
        role['must']['all'][1] = {
            'any': [role['must']['all'][1], {'op': 'fact_eq', 'field': 'identified', 'value': True}]
        }
    elif change == 'name-only':
        row['evidence']['quote'] = occurrence['name']
    else:
        row['evidence']['locator'] = row['evidence']['locator'].replace('/sections/2/', '/sections/1/')
        row['evidence']['quote'] = occurrence['name']
    branch['profile_fingerprint'] = fingerprint(role)
    with pytest.raises(ValueError, match='source-context'):
        run(tmp_path, role, occurrence, doc)
