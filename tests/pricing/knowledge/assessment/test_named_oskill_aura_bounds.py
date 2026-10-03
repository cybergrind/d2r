from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.mechanics.named_rolls import roll_gaps
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.models import Item


WIDOW = Item(
    'Ward Bow',
    'unique',
    'Widowmaker',
    ((17, 0, 200), (18, 0, 200), (141, 0, 33), (115, 0, 1), (157, 0, 11), (97, 22, 5)),
    complete=True,
)


@pytest.mark.parametrize(('level', 'valid'), [(3, True), (5, True), (2, False), (6, False)])
def test_widowmaker_requires_legal_guided_arrow_bonus(level, valid):
    item = replace(WIDOW, raw_stats=tuple((s, p, level if s == 97 else v) for s, p, v in WIDOW.raw_stats))
    contract, gaps = NamedHandler().contract(normalize(item.capture()), 'weapon')
    assert contract is None  # Verified market mappings are still required.
    assert any('No verified market mapping' in gap for gap in gaps)
    assert (not any('Named roll 97:22 ' in gap for gap in gaps)) is valid, gaps


@pytest.mark.parametrize(
    ('name', 'stat', 'skill', 'low', 'high'),
    [
        ('Widowmaker', 97, 22, 3, 5),
        ('Flamebellow', 97, 41, 12, 18),
        ('Wolfhowl', 97, 223, 3, 6),
        ('Wolfhowl', 97, 224, 3, 6),
        ('Wolfhowl', 97, 232, 3, 6),
        ('Azurewrath', 151, 119, 10, 13),
    ],
)
def test_native_skill_layer_and_level(name, stat, skill, low, high):
    facts = normalize(WIDOW.capture())
    definition = catalog().named['unique', name]
    key = f'{stat}:{skill}'
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
    wrong = replace(facts, stats={f'{stat}:{skill + 1}': {'status': 'decoded', 'value': low}})
    assert any(f' {key} ' in g for g in roll_gaps(wrong, definition))
