from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.mechanics.named_rolls import roll_gaps
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.models import Item


EYE = Item(
    'Amulet',
    'unique',
    'The Eye of Etlich',
    ((32, 0, 40), (89, 0, 5), (127, 0, 1), (60, 0, 7), (54, 0, 2), (55, 0, 5), (56, 0, 50)),
    complete=True,
)


@pytest.mark.parametrize(
    ('name', 'stat', 'low', 'high'),
    [
        ("Griswold's Edge", 48, 10, 12),
        ("Griswold's Edge", 49, 15, 25),
        ('Hellclap', 49, 30, 50),
        ("Kinemil's Awl", 49, 20, 40),
        ('Skull Splitter', 51, 12, 15),
        ('The Eye of Etlich', 54, 1, 2),
        ('The Eye of Etlich', 55, 3, 5),
    ],
)
def test_native_elemental_endpoints_have_integer_bounds(name, stat, low, high):
    definition = catalog().named['unique', name]
    facts = normalize(EYE.capture())
    key = f'{stat}:0'
    for value, valid in (
        (low, True),
        (high, True),
        (low - 1, False),
        (high + 1, False),
        (True, False),
        (low + 0.5, False),
    ):
        changed = replace(facts, stats={key: {'status': 'decoded', 'value': value}})
        errors = [g for g in roll_gaps(changed, definition) if f' {key} ' in g]
        assert (not errors) is valid, (name, value, errors)


@pytest.mark.parametrize(
    ('frames', 'valid'), [(49, False), (50, True), (51, True), (249, True), (250, True), (251, False)]
)
def test_cold_duration_bounds_use_native_frames(frames, valid):
    item = replace(EYE, raw_stats=tuple((s, p, frames if s == 56 else v) for s, p, v in EYE.raw_stats))
    facts = normalize(item.capture())
    errors = [g for g in roll_gaps(facts, catalog().named['unique', EYE.name]) if ' 56:0 ' in g]
    assert (not errors) is valid, errors


@pytest.mark.parametrize('change', [{'value': 50}, {'value': 2.01}, {'raw': 50.0}, {'unit': None}])
def test_cold_duration_requires_consistent_raw_and_decoded_units(change):
    facts = normalize(EYE.capture())
    changed = replace(facts, stats={**facts.stats, '56:0': {**facts.stats['56:0'], **change}})
    assert any(' 56:0 ' in g for g in roll_gaps(changed, catalog().named['unique', 'The Eye of Etlich']))
