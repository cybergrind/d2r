from dataclasses import replace

import pytest

from inventory_tracking.appraisal.presentation import ItemAssessment
from inventory_tracking.appraisal.text import roll_styles
from inventory_tracking.presentation import PALETTE, Tone
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.domain.facts import ItemFacts
from pricing.knowledge.assessment.ethereal import ethereal_preference
from tests.pricing.knowledge.assessment.test_base_use import capture


def unique(name, ethereal):
    return ItemFacts(name, None, None, None, 'unique', None, True, ethereal, 0, 'empty', [], True)


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
