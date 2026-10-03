from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.mechanics.named_rolls import roll_gaps
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.cases.natures_peace_alternatives import ring


@pytest.mark.parametrize('value', [0, 1, 2])
def test_natures_peace_must_have_native_prevent_monster_heal(value):
    item = ring()
    item = replace(item, raw_stats=tuple((s, p, value if s == 117 else v) for s, p, v in item.raw_stats))
    contract, gaps = NamedHandler().contract(normalize(item.capture()), 'jewelry')
    assert (contract is not None) is (value == 1), gaps


@pytest.mark.parametrize(
    ('name', 'stat'),
    [
        ('Windforce', 81),
        ("The Reaper's Toll", 115),
        ("Nature's Peace", 117),
        ('Undead Crown', 118),
        ('Raven Frost', 153),
        ('The Spirit Shroud', 153),
    ],
)
@pytest.mark.parametrize(('value', 'valid'), [(1, True), (0, False), (2, False), (True, False), (0.5, False)])
def test_fixed_boolean_definition_must_match_capture(name, stat, value, valid):
    facts = normalize(ring().capture())
    key = f'{stat}:0'
    facts = replace(facts, stats={key: {'status': 'decoded', 'value': value}})
    gaps = [g for g in roll_gaps(facts, catalog().named['unique', name]) if f' {key} ' in g]
    assert (not gaps) is valid, gaps
