from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.mechanics.named_rolls import roll_gaps
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.models import Item


TAL = Item(
    'Swirling Crystal',
    'set',
    "Tal Rasha's Lidless Eye",
    ((7, 0, 57 * 256), (9, 0, 77 * 256), (1, 0, 10), (105, 0, 20), (107, 61, 2), (107, 63, 2), (107, 65, 2)),
    complete=True,
)


@pytest.mark.parametrize('skill', [61, 63, 65])
def test_tal_masteries_cannot_receive_random_base_staffmods(skill):
    for bonus, valid in ((1, True), (2, True), (3, False)):
        item = replace(
            TAL, raw_stats=tuple((s, p, bonus if s == 107 and p == skill else v) for s, p, v in TAL.raw_stats)
        )
        contract, gaps = NamedHandler().contract(normalize(item.capture()), 'weapon')
        assert (contract is not None) is valid, gaps


@pytest.mark.parametrize(
    ('name', 'skill', 'low', 'high'),
    [
        ('Boneshade', 67, 4, 5),
        ('Boneshade', 68, 4, 5),
        ('Boneshade', 84, 2, 3),
        ('Boneshade', 93, 1, 2),
        ('Boneshade', 78, 2, 3),
        ('Stormeye', 110, 3, 5),
        ('Bloodletter', 127, 2, 4),
        ('Bloodletter', 151, 1, 3),
        ("Ars Al'Diabolos", 401, 3, 5),
        ('Bloodpact Shard', 378, 2, 3),
    ],
)
def test_unique_skill_bounds_are_definition_specific_not_staffmod_cap(name, skill, low, high):
    facts = normalize(TAL.capture())
    definition = catalog().named['unique', name]
    key = f'107:{skill}'
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
