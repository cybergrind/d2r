from dataclasses import replace
from datetime import date

import pytest

from inventory_tracking.items.metadata import decode_stats, metadata
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables, reject_reasons
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def nightwing(filler='Ko Rune', bonus=10, intrinsic=20):
    definition = catalog().named['unique', "Nightwing's Veil"]
    native = [
        {'id': s['stat_id'], 'layer': s.get('layer', 0), 'raw': intrinsic + bonus if s['stat_id'] == 2 else s['min']}
        for s in definition['roll_ranges'].values()
    ]
    native += [{'id': 194, 'layer': 0, 'raw': 1}, {'id': 31, 'layer': 0, 'raw': 300}]
    rows, affixes, unresolved = decode_stats(native)
    assert not unresolved
    gem = next(b for b in metadata()['bases'].values() if b['name'] == filler)
    captured = replace(
        facts('Spired Helm', 'unique', "Nightwing's Veil"),
        sockets=1,
        socket_contents='filled',
        socket_items=[
            {'name': filler, 'base_code': gem['code'], 'item_type': gem['type'], 'unit_id': 1, 'position': 0}
        ],
    )
    return normalize(
        {
            'item': {**captured.to_dict(), 'affixes': affixes},
            'decoded_stats': rows,
            'source': {'stat_capture_complete': True},
        }
    )


@pytest.mark.parametrize(
    ('filler', 'bonus'),
    [
        ('Ko Rune', 10),
        ('Chipped Emerald', 3),
        ('Flawed Emerald', 4),
        ('Emerald', 6),
        ('Flawless Emerald', 8),
        ('Perfect Emerald', 10),
    ],
)
def test_fixed_dexterity_filler_contract_retains_observed_total_and_payload(filler, bonus):
    item = nightwing(filler, bonus)
    contract, gaps = NamedHandler().contract(item, 'helm')
    assert contract is not None, gaps
    assert contract.properties['429'] == 20 + bonus
    assert contract.socket_payload == (filler,)
    assert item.stats['2:0']['value'] == 20 + bonus
    assert NamedHandler().contract(nightwing(filler, bonus, intrinsic=21), 'helm')[0] is None


def test_equal_dexterity_totals_with_different_fillers_are_not_comparable():
    contract, gaps = NamedHandler().contract(nightwing(), 'helm')
    assert contract is not None, gaps
    row = {
        **contract.to_dict(),
        'properties': {**contract.properties, '934': 'Ko Rune'},
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'seller',
        'listing_id': 'listing',
        'observed_at': '2026-09-25',
        'ask_ist': 2,
    }
    assert not reject_reasons(contract.to_dict(), row)
    for payload in (None, 'Perfect Emerald', 'Jewel'):
        assert reject_reasons(contract.to_dict(), {**row, 'properties': {**row['properties'], '934': payload}})
    cohort = [{**row, 'seller_id': str(i), 'listing_id': str(i)} for i in range(3)]
    result = price_from_comparables(evaluate(contract.to_dict(), cohort), today=date(2026, 9, 25))
    assert result['estimate_ist'] == 2
    assert (
        price_from_comparables(evaluate(contract.to_dict(), cohort[:2]), today=date(2026, 9, 25))['estimate_ist']
        is None
    )


@pytest.mark.parametrize(
    ('base', 'quality', 'name', 'innate', 'handler'),
    [
        ('Cap', 'normal', None, 0, 'base'),
        ('Diadem', 'magic', None, 10, 'affixed'),
        ('Diadem', 'rare', None, 10, 'affixed'),
        ('Winged Helm', 'set', "Guillaume's Face", 0, 'named'),
    ],
)
def test_ko_comparison_supports_bases_affixed_and_set_items(base, quality, name, innate, handler):
    from pricing.knowledge.assessment.handlers import HANDLERS
    from tests.pricing.knowledge.assessment.test_socket_survival_comparisons import socketed_item

    captured = socketed_item(base, quality, name, ['Ko Rune'], {2: innate + 10})
    contract, gaps = HANDLERS[handler].contract(captured, 'helm')
    assert contract is not None, gaps
    assert contract.properties['429'] == innate + 10
    assert contract.socket_payload == ('Ko Rune',)
