from dataclasses import replace
from datetime import date

from inventory_tracking.items.metadata import decode_stats
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables, reject_reasons
from pricing.knowledge.assessment.handlers.runeword import RunewordHandler
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def treachery():
    rows = [
        {'id': 198, 'layer': 278 * 64 + 15, 'raw': 25},
        {'id': 201, 'layer': 267 * 64 + 15, 'raw': 5},
        {'id': 31, 'layer': 0, 'raw': 250},
    ]
    decoded, _, _ = decode_stats(rows)
    item = replace(facts('Mage Plate'), name='Treachery', runeword='Treachery', sockets=3, socket_contents='filled')
    return normalize({'item': item.to_dict(), 'decoded_stats': decoded, 'source': {'stat_capture_complete': True}})


def test_runeword_procs_are_verified_fixed_properties():
    contract, gaps = RunewordHandler().contract(treachery(), 'armor')
    assert contract is not None, gaps
    assert contract.intrinsic_properties['846'] == 25
    assert contract.intrinsic_properties['763'] == 5
    serialized = contract.to_dict()
    rows = [
        {
            **{
                k: serialized[k]
                for k in ('name', 'rarity', 'base_code', 'ethereal', 'sockets', 'socket_contents', 'base_rarity')
            },
            'properties': {'1855': 250},
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': str(i),
            'listing_id': str(i),
            'observed_at': '2026-09-24',
            'ask_ist': i,
        }
        for i in (1, 2, 3)
    ]
    assert price_from_comparables(evaluate(serialized, rows), today=date(2026, 9, 24))['estimate_ist'] == 2
    assert reject_reasons(serialized, {**rows[0], 'properties': {'1855': 250, '763': 15}})


def test_missing_or_changed_runeword_trigger_blocks_comparison_even_without_projection_gaps():
    item = treachery()
    for key in ['198:17807', '201:17103']:
        for stats in (
            {k: v for k, v in item.stats.items() if k != key},
            {**item.stats, key: {**item.stats[key], 'value': 99}},
            {**item.stats, key: {**item.stats[key], 'raw': 99}},
            {**item.stats, key: {**item.stats[key], 'unit': 'unknown'}},
        ):
            contract, gaps = RunewordHandler().contract(replace(item, stats=stats, projection_gaps=[]), 'armor')
            assert contract is None
            assert any('trigger' in gap.lower() for gap in gaps)


def test_obedience_cannot_omit_its_lowercase_named_enchant_proc():
    from pricing.knowledge.assessment.handlers.runeword import definitions

    definition = definitions()['Obedience']
    assert definition['fixed_triggers'] == ({'stat_id': 196, 'skill_id': 52, 'level': 21, 'chance': 30},)
    item = replace(
        facts('Cryptic Axe'),
        name='Obedience',
        runeword='Obedience',
        sockets=5,
        socket_contents='filled',
        stats={
            f'{s}:0': {'status': 'decoded', 'value': value}
            for s, value in [(31, 250), (39, 25), (41, 25), (43, 25), (45, 25)]
        },
    )
    contract, gaps = RunewordHandler().contract(item, 'weapon')
    assert contract is None
    assert any('trigger 196:3349' in gap for gap in gaps)
    stats = {**item.stats, '196:3349': {'status': 'decoded', 'value': 30, 'raw': 30, 'unit': 'percent_chance'}}
    contract, gaps = RunewordHandler().contract(replace(item, stats=stats), 'weapon')
    assert not gaps
    assert contract.intrinsic_properties['874'] == 30
