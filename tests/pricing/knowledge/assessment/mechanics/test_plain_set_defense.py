from copy import deepcopy

import pytest

from pricing.knowledge.assessment.mechanics.market_named_defense import with_variant_evidence


@pytest.mark.parametrize(
    ('name', 'original', 'upgraded', 'low', 'high', 'up_low', 'up_high'),
    [
        ("Aldur's Advance", 'xtb', 'utb', 39, 47, 59, 68),
        ("Horazon's Hold", 'xlg', 'ulg', 28, 35, 54, 62),
    ],
)
def test_native_total_defense_proves_base_without_rewriting_cache(name, original, upgraded, low, high, up_low, up_high):
    contract = {'policy': 'named', 'name': name, 'rarity': 'set', 'ethereal': False, 'base_code': original}
    row = {'name': name, 'rarity': 'set', 'ethereal': False, 'sockets': 0, 'socket_contents': 'empty'}
    before = deepcopy(row)
    for total, code in ((low, original), (high, original), (up_low, upgraded), (up_high, upgraded)):
        result = with_variant_evidence(contract, {**row, 'properties': {'1855': total}})
        assert result['base_code'] == code
        assert result['base_upgrade'] is (code == upgraded)
        assert result['facet_basis']['base_code']['kind'] == 'reviewed_named_defense'
    assert row == before


@pytest.mark.parametrize(
    ('changes', 'properties'),
    [
        ({'base_code': 'utb'}, {'1855': 40}),
        ({}, {'1855': 40, '930': 'Elite'}),
        ({}, {'1855': 40, '1216': True}),
        ({'ethereal': True}, {'1855': 40}),
        ({'sockets': None}, {'1855': 40}),
        ({'socket_contents': 'filled'}, {'1855': 40}),
        ({}, {'1855': 40, '399': 40}),
        ({}, {'1855': 40, '425': 10}),
        ({}, {'1855': 40, '934': 'Pul Rune'}),
        ({}, {'1855': 48}),
        ({}, {'1855': True}),
        ({}, {}),
    ],
)
def test_conflicting_or_unknown_set_defense_is_not_comparable(changes, properties):
    contract = {'policy': 'named', 'name': "Aldur's Advance", 'rarity': 'set', 'ethereal': False, 'base_code': 'xtb'}
    row = {
        'name': "Aldur's Advance",
        'rarity': 'set',
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': properties,
        **changes,
    }
    assert with_variant_evidence(contract, row).get('mechanics_conflicts')


def test_cached_aldur_elite_selector_cannot_override_original_defense():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.adapters.capture import normalize
    from pricing.knowledge.assessment.comparables import evaluate
    from pricing.knowledge.assessment.handlers.named import NamedHandler
    from tests.pricing.knowledge.assessment.item_bank.models import Item

    item = Item(
        'Mirrored Boots',
        'set',
        "Aldur's Advance",
        (
            (31, 0, 40),
            (152, 0, 1),
            (28, 0, 32),
            (7, 0, 50 * 256),
            (114, 0, 10),
            (96, 0, 40),
            (11, 0, 180 * 256),
            (39, 0, 43),
        ),
        complete=True,
    )
    contract, gaps = NamedHandler().contract(normalize(item.capture()), 'accessory')
    assert contract is None
    assert any('total defense' in gap for gap in gaps)
    from dataclasses import replace

    item = replace(item, raw_stats=((31, 0, 66), *item.raw_stats[1:]))
    contract, gaps = NamedHandler().contract(normalize(item.capture()), 'accessory')
    assert contract is not None, gaps
    rows = [
        r
        for r in map(json.loads, Path('pricing/data/appraisal-market.jsonl').read_text().splitlines())
        if r['id'] == '88e98e15926f0a530aec5b77'
    ]
    assert len(rows) == 1
    result = evaluate(contract.to_dict(), rows)
    assert not result['accepted']
    assert any('defense and variant' in reason for reason in result['rejected'][0]['reasons'])
