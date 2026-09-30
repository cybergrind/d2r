"""Shield comparisons use added blocking, never the native shield total."""

from dataclasses import replace

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.exact import AffixedHandler, BaseHandler
from tests.pricing.knowledge.assessment.item_bank.models import Item


def monarch(total=42):
    return normalize(
        Item(
            'Monarch',
            'magic',
            None,
            ((20, 0, total), (102, 0, 30), (31, 0, 133), (194, 0, 4)),
            sockets=4,
            complete=True,
        ).capture()
    )


def test_jmod_comparison_subtracts_only_native_base_blocking():
    facts = monarch()
    contract, gaps = AffixedHandler().contract(facts, 'shield')
    assert not gaps
    assert contract.properties['446'] == 20
    assert facts.properties['446'] == facts.stats['20:0']['value'] == 42


def test_unmodified_paladin_base_does_not_request_a_fake_blocking_bonus():
    facts = normalize(Item('Sacred Rondache', 'normal', None, ((20, 0, 28), (31, 0, 160)), complete=True).capture())
    contract, gaps = BaseHandler().contract(facts, 'shield')
    assert not gaps
    assert '446' not in contract.properties


def test_inconsistent_block_total_cannot_be_priced_as_a_bonus():
    for facts in (
        monarch(20),
        replace(monarch(), properties={'446': 20}),
        replace(monarch(), stats={k: v for k, v in monarch().stats.items() if k != '20:0'}),
    ):
        contract, gaps = AffixedHandler().contract(facts, 'shield')
        assert contract is None
        assert any('blocking' in gap.lower() for gap in gaps)


def test_base_block_catalog_requires_consistent_native_evidence():
    from pricing.knowledge.definition_store import DefinitionCatalog

    code = monarch().base_code

    def definition(value):
        return {
            'base_codes': [code],
            'base_stat_ranges': {code: {'20': {'stat_id': 20, 'min': value, 'max': value, 'property': 'base_block'}}},
        }

    agreed = DefinitionCatalog('a', {}, {'one': definition(22), 'two': definition(22)}, {})
    assert agreed.shield_base_blocks[code] == 22
    assert agreed.shield_base_blocks is agreed.shield_base_blocks
    conflict = DefinitionCatalog('b', {}, {'one': definition(22), 'two': definition(24)}, {})
    assert code not in conflict.shield_base_blocks
    malformed = definition(22)
    malformed['base_stat_ranges'][code]['20']['max'] = 23
    assert code not in DefinitionCatalog('c', {}, {'one': definition(22), 'two': malformed}, {}).shield_base_blocks
    assert code not in DefinitionCatalog('d', {}, {}, {}).shield_base_blocks
    malformed = definition(0)
    malformed['base_stat_ranges'][code]['20']['max'] = False
    assert code not in DefinitionCatalog('e', {}, {'one': malformed}, {}).shield_base_blocks


def test_unknown_native_base_cannot_borrow_monarch_blocking():
    contract, gaps = AffixedHandler().contract(replace(monarch(), base_code='unknown-base'), 'shield')
    assert contract is None
    assert any('base blocking' in gap for gap in gaps)


def test_eld_bonus_is_retained_without_bypassing_socket_eligibility():
    from tests.pricing.knowledge.assessment.item_bank.models import SocketItem

    facts = normalize(
        Item(
            'Monarch',
            'magic',
            None,
            ((20, 0, 49), (102, 0, 30), (31, 0, 133), (194, 0, 1)),
            sockets=1,
            socket_contents='filled',
            socket_items=(SocketItem('Eld Rune'),),
            complete=True,
        ).capture()
    )
    contract, gaps = AffixedHandler().contract(facts, 'shield')
    assert contract is None
    assert 'Filled sockets require a contribution-aware comparison policy.' in gaps
    from pricing.knowledge.assessment.mechanics.shield_blocking import modifier_blocking

    projected, block_gaps = dict(facts.properties), []
    modifier_blocking(facts, projected, block_gaps)
    assert not block_gaps
    assert projected['446'] == 27  # 20 from Deflecting, 7 from Eld; exclude only the native 22.


def test_zero_block_base_allows_absent_zero_stat_in_complete_capture():
    facts = normalize(Item('Buckler', 'normal', None, ((31, 0, 4),), complete=True).capture())
    contract, gaps = BaseHandler().contract(facts, 'shield')
    assert not gaps
    assert '446' not in contract.properties


def test_jmod_bonus_comparisons_reject_raw_total_and_reach_three_seller_gate():
    from datetime import date

    from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
    from tests.pricing.knowledge.assessment.test_comparables import listing

    contract, gaps = AffixedHandler().contract(monarch(), 'shield')
    assert not gaps
    rows = [
        listing(
            str(i),
            name='Monarch',
            rarity='magic',
            sockets=4,
            base_code=contract.base_code,
            base_tier='Elite',
            properties={**contract.properties, '446': 20},
            ask_ist=i,
        )
        for i in (1, 2, 3)
    ]
    rows.append(
        listing(
            'raw-total',
            name='Monarch',
            rarity='magic',
            sockets=4,
            base_code=contract.base_code,
            base_tier='Elite',
            properties={**contract.properties, '446': 42},
            ask_ist=50,
        )
    )
    comparisons = evaluate(contract.to_dict(), rows)
    assert comparisons['summary']['priced_sellers'] == 3
    assert len(comparisons['rejected']) == 1
    assert price_from_comparables(comparisons, today=date(2026, 9, 24))['estimate_ist'] == 2


def test_named_shield_bonus_is_intrinsic_without_borrowing_native_base():
    from pricing.knowledge.assessment.comparables import evaluate
    from pricing.knowledge.assessment.handlers.named import NamedHandler
    from tests.pricing.knowledge.assessment.test_comparables import listing

    facts = normalize(Item('Large Shield', 'set', "Civerb's Ward", ((20, 0, 27), (31, 0, 29)), complete=True).capture())
    contract, gaps = NamedHandler().contract(facts, 'shield')
    assert not gaps
    assert contract.properties['446'] == 15
    assert contract.intrinsic_properties['446'] == 15
    assert facts.stats['20:0']['value'] == 27
    common = {
        'name': facts.name,
        'rarity': 'set',
        'sockets': 0,
        'base_code': facts.base_code,
        'base_tier': 'Normal',
        'properties': {'1855': 29},
    }
    rows = [
        listing('implicit', **common),
        listing('explicit', **{**common, 'properties': {'1855': 29, '446': 15}}),
        listing('total', **{**common, 'properties': {'1855': 29, '446': 27}}),
    ]
    comparison = evaluate(contract.to_dict(), rows)
    assert len(comparison['accepted']) == 2
    assert len(comparison['rejected']) == 1


def test_named_shield_uses_actual_upgraded_base_blocking():
    from pricing.knowledge.assessment.handlers.named import NamedHandler

    facts = normalize(Item('Scutum', 'set', "Civerb's Ward", ((20, 0, 29), (31, 0, 80)), complete=True).capture())
    contract, gaps = NamedHandler().contract(facts, 'shield')
    assert not gaps
    assert contract.properties['446'] == contract.intrinsic_properties['446'] == 15


def test_named_shield_missing_native_total_cannot_infer_fixed_bonus():
    from pricing.knowledge.assessment.handlers.named import NamedHandler

    facts = normalize(Item('Large Shield', 'set', "Civerb's Ward", ((31, 0, 29),), complete=True).capture())
    contract, gaps = NamedHandler().contract(facts, 'shield')
    assert contract is None
    assert any('blocking' in gap.lower() for gap in gaps)


def test_unique_shield_keeps_fixed_block_bonus_separate_from_base():
    from pricing.knowledge.assessment.handlers.named import NamedHandler

    facts = normalize(
        Item(
            'Defender',
            'unique',
            'Visceratuant',
            ((20, 0, 40), (31, 0, 100), (83, 1, 1), (102, 0, 30), (16, 0, 125), (128, 0, 10)),
            complete=True,
        ).capture()
    )
    contract, gaps = NamedHandler().contract(facts, 'shield')
    assert not gaps
    assert contract.properties['446'] == contract.intrinsic_properties['446'] == 30
    assert facts.stats['20:0']['value'] == 40


def test_variable_named_block_roll_is_projected_without_becoming_intrinsic():
    from pricing.knowledge.assessment.handlers.named import NamedHandler

    # Spirit Ward: Ward native block 24; variable bonus 20-30. The local
    # definition fixes its when-struck Fade trigger at skill267 / level8 / 5%.
    for bonus in (19, 20, 25, 30, 31):
        facts = normalize(
            Item(
                'Ward',
                'unique',
                'Spirit Ward',
                (
                    (20, 0, 24 + bonus),
                    (31, 0, 450),
                    (16, 0, 150),
                    (149, 0, 8),
                    (39, 0, 35),
                    (41, 0, 35),
                    (43, 0, 35),
                    (45, 0, 35),
                    (102, 0, 25),
                    (201, 267 * 64 + 8, 5),
                ),
                complete=True,
            ).capture()
        )
        contract, gaps = NamedHandler().contract(facts, 'shield')
        if bonus in (19, 31):
            assert contract is None
            assert any('20:0' in gap and '20-30' in gap for gap in gaps)
            continue
        assert not gaps
        assert contract.properties['446'] == bonus
        assert '446' not in contract.intrinsic_properties
        assert facts.stats['20:0']['value'] == 24 + bonus
