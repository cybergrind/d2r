from dataclasses import replace

import pytest

from inventory_tracking.appraisal.presentation import ItemAssessment
from inventory_tracking.appraisal.text import roll_styles
from inventory_tracking.presentation import PALETTE, Tone
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.domain.facts import ItemFacts
from pricing.knowledge.assessment.ethereal import ethereal_preference
from tests.pricing.knowledge.assessment.test_base_use import capture


TYPES = {"Andariel's Visage": 'helm', 'War Traveler': 'boot', 'Sandstorm Trek': 'boot', "Death's Fathom": 'orb'}


def unique(name, ethereal, rarity='unique'):
    return ItemFacts(name, None, None, TYPES.get(name), rarity, None, True, ethereal, 0, 'empty', [], True)


@pytest.mark.parametrize(
    ('name', 'ethereal', 'expected'),
    [
        ("Andariel's Visage", False, Tone.ETHEREAL_TARGET),
        ("Andariel's Visage", True, Tone.ETHEREAL_DESIRED),
        ('War Traveler', True, Tone.ETHEREAL_UNDESIRED),
        ('War Traveler', False, Tone.DEFAULT),
        ('Sandstorm Trek', True, Tone.ETHEREAL_DESIRED),
        ("Death's Fathom", True, Tone.DEFAULT),
        ('Unknown item', True, Tone.DEFAULT),
    ],
)
def test_ethereal_rule_reaches_terminal_osd_and_compatibility_styles(name, ethereal, expected):
    facts = unique(name, ethereal)
    result = {
        'extraction': {'item': {'name': name, 'ethereal': ethereal}},
        'assessment': {'ethereal_preference': ethereal_preference(facts)},
        'decision': {'price_status': 'unknown'},
    }
    record = {'state': 'complete', 'request_id': 1, 'result': result}
    document = ItemAssessment.from_record(record)
    line = next(line for line in document.to_osd() if line.text.startswith('Ethereal:'))
    assert line.tone == expected
    assert line.text == ('Ethereal: yes' if ethereal else 'Ethereal: no')
    assert roll_styles(record).get(line.text, PALETTE[Tone.DEFAULT]) == PALETTE[expected]
    assert document.to_rich().plain == document.to_text()


@pytest.mark.parametrize('item_type', ['glov', 'boot', 'belt'])
@pytest.mark.parametrize('rarity', ['unique', 'rare', 'magic', 'normal'])
def test_any_ethereal_gloves_boots_or_belt_is_avoided_without_naming_the_item(item_type, rarity):
    facts = replace(unique('Unlisted item', True, rarity), item_type=item_type)
    preference = ethereal_preference(facts)
    assert preference['preference'] == 'avoid'
    assert preference['source'].endswith('itemtypes.json')
    assert ethereal_preference(replace(facts, item_type='helm')) is None
    assert ethereal_preference(replace(facts, stats={'152:0': {'raw': 1}})) is None  # indestructible


def test_base_rules_exclude_bad_sockets_magic_items_and_unknown_flags():
    for name in ('Giant Thresher', 'Cryptic Axe', 'Mancatcher'):
        assert ethereal_preference(normalize(capture(name)))['preference'] == 'preferred'
    assert ethereal_preference(normalize(capture(sockets=1))) is None
    assert ethereal_preference(normalize(capture(quality='magic'))) is None
    assert ethereal_preference(normalize(capture(ethereal=None))) is None


def test_repair_indestructibility_and_incomplete_capture_override_negative_rule():
    facts = unique('War Traveler', True)
    for stat in (152, 252):
        facts = replace(facts, stats={f'{stat}:0': {'raw': 1}})
        assert ethereal_preference(facts) is None
    facts = replace(facts, stats={}, capture_complete=False)
    assert ethereal_preference(facts) is None
