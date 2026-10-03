from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.mechanics.named_rolls import roll_gaps
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.cases.natures_peace_alternatives import ring


CASES = [
    ('Waterwalk', 28, 50),
    ('Swordguard', 33, 200),
    ('Guardian Angel', 40, 15),
    ('Guardian Angel', 42, 15),
    ('Guardian Angel', 44, 15),
    ('Guardian Angel', 46, 15),
    ("Ondal's Wisdom", 85, 5),
    ("The Reaper's Toll", 91, -25),
    ('Guardian Angel', 102, 30),
    ("Culwen's Point", 110, 50),
    ('Woestave', 113, 3),
    ('Infernal Cranium', 114, 20),
    ('Fleshripper', 116, 50),
    ('Soul Drainer', 120, -50),
    ("Dracul's Grasp", 135, 25),
    ("Guillaume's Face", 141, 15),
    ('Arachnid Mesh', 150, 10),
    ('Vampire Gaze', 154, 15),
    ('Razortail', 156, 33),
    ('Witchwild String', 157, 20),
    ('Demon Machine', 158, 6),
    ("Titan's Revenge", 254, 60),
]


@pytest.mark.parametrize(('name', 'stat', 'expected'), CASES)
@pytest.mark.parametrize('offset', [-1, 0, 1])
def test_named_fixed_scalar_bonus_matches_native_definition(name, stat, expected, offset):
    quality = 'set' if name in ('Infernal Cranium', "Guillaume's Face") else 'unique'
    definition = catalog().named[quality, name]
    spec = definition['roll_ranges'][str(stat)]
    assert (spec['min'], spec['max']) == (expected, expected)
    key = f'{stat}:0'
    facts = replace(normalize(ring().capture()), stats={key: {'status': 'decoded', 'value': expected + offset}})
    errors = [e for e in roll_gaps(facts, definition) if f' {key} ' in e]
    assert (not errors) is (offset == 0), errors
