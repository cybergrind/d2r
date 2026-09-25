from datetime import date

import pytest

from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables, reject_reasons
from pricing.knowledge.assessment.engine import assess
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('table', 'values', 'trigger', 'required'),
    [
        (393, {54: 24, 55: 38, 56: 3, 331: 5, 335: 4}, (197, 59, 37), {'747': 5, '609': 4, '781': 100}),
        (397, {54: 24, 55: 38, 56: 3, 331: 5, 335: 4}, (199, 44, 43), {'747': 5, '609': 4, '786': 100}),
        (392, {50: 1, 51: 74, 330: 5, 334: 4}, (197, 53, 47), {'743': 5, '736': 4, '780': 100}),
        (394, {48: 17, 49: 45, 329: 5, 333: 4}, (197, 56, 31), {'750': 5, '735': 4, '782': 100}),
        (396, {50: 1, 51: 74, 330: 5, 334: 4}, (199, 48, 41), {'743': 5, '736': 4, '785': 100}),
        (398, {48: 17, 49: 45, 329: 5, 333: 4}, (199, 46, 29), {'750': 5, '735': 4, '787': 100}),
    ],
)
def test_facet_price_requires_rolls_and_event_but_listing_can_omit_verified_fixed_damage(
    table, values, trigger, required
):
    stat, skill, level = trigger
    decoded = [
        {'status': 'decoded', 'value': value, 'memory_stat': {'id': key, 'layer': 0, 'raw': value}}
        for key, value in values.items()
    ]
    for row in decoded:
        if row['memory_stat']['id'] == 56:
            row.update(value=row['memory_stat']['raw'] / 25, unit='seconds')
    decoded.append(
        {'status': 'decoded', 'value': 100, 'memory_stat': {'id': stat, 'layer': skill * 64 + level, 'raw': 100}}
    )
    extraction = {
        'item': facts('Jewel', 'unique', 'Rainbow Facet').to_dict(),
        'decoded_stats': decoded,
        'source': {'stat_capture_complete': True, 'item_identity': {'table': 'unique', 'table_id': table}},
    }
    contract = assess(extraction, profiles=[])['contract']
    assert contract is not None
    assert len(contract['intrinsic_properties']) == 2
    rows = [
        {
            **{k: contract[k] for k in ('name', 'rarity', 'base_code', 'ethereal', 'sockets', 'socket_contents')},
            'properties': required,
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
    assert price_from_comparables(evaluate(contract, rows), today=date(2026, 9, 24))['estimate_ist'] == 2
    event = next(k for k, v in required.items() if v == 100)
    assert reject_reasons(contract, {**rows[0], 'properties': {k: v for k, v in required.items() if k != event}})
    assert reject_reasons(contract, {**rows[0], 'properties': {**required, event: level}})
    fixed = next(iter(contract['intrinsic_properties']))
    assert reject_reasons(contract, {**rows[0], 'properties': {**required, fixed: 999}})

    missing_damage = {**extraction, 'decoded_stats': decoded[1:]}
    assert assess(missing_damage, profiles=[])['contract'] is None
    changed_damage = {**extraction, 'decoded_stats': [{**decoded[0], 'value': 999}, *decoded[1:]]}
    assert assess(changed_damage, profiles=[])['contract'] is None

    if 56 in values:
        for duration in (
            None,
            {'status': 'decoded', 'value': 3, 'unit': 'seconds', 'memory_stat': {'id': 56, 'layer': 0, 'raw': 75}},
        ):
            changed = [r for r in decoded if r['memory_stat']['id'] != 56]
            if duration:
                changed.append(duration)
            assert assess({**extraction, 'decoded_stats': changed}, profiles=[])['contract'] is None


def test_poison_facet_price_checks_rates_duration_and_single_source():
    from inventory_tracking.items.poison import combine_poison

    raw = {57: 187, 58: 187, 59: 50, 326: 1}
    poison = combine_poison([{'memory_stat': {'id': key, 'layer': 0, 'raw': value}} for key, value in raw.items()])[0]
    decoded = [
        poison,
        *[
            {'status': 'decoded', 'value': value, 'memory_stat': {'id': key, 'layer': layer, 'raw': value}}
            for key, layer, value in ((332, 0, 5), (336, 0, 4), (197, 92 * 64 + 51, 100))
        ],
    ]
    extraction = {
        'item': facts('Jewel', 'unique', 'Rainbow Facet').to_dict(),
        'decoded_stats': decoded,
        'source': {'stat_capture_complete': True, 'item_identity': {'table': 'unique', 'table_id': 395}},
    }
    contract = assess(extraction, profiles=[])['contract']
    assert contract is not None
    assert contract['intrinsic_properties']['589'] == 37
    rows = [
        {
            **{k: contract[k] for k in ('name', 'rarity', 'base_code', 'ethereal', 'sockets', 'socket_contents')},
            'properties': {'783': 5, '723': 4, '784': 100},
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
    assert price_from_comparables(evaluate(contract, rows), today=date(2026, 9, 24))['estimate_ist'] == 2
    assert reject_reasons(contract, {**rows[0], 'properties': {**rows[0]['properties'], '589': 38}})
    for key in raw:
        missing = {**poison, 'memory_stats': [r for r in poison['memory_stats'] if r['id'] != key]}
        assert assess({**extraction, 'decoded_stats': [missing, *decoded[1:]]}, profiles=[])['contract'] is None
        changed = {**poison, 'native_values': {**poison['native_values'], f'{key}:0': {'value': 999, 'unit': 'count'}}}
        assert assess({**extraction, 'decoded_stats': [changed, *decoded[1:]]}, profiles=[])['contract'] is None

        changed_raw = {
            **poison,
            'memory_stats': [{**r, 'raw': r['raw'] + 1} if r['id'] == key else r for r in poison['memory_stats']],
        }
        assert assess({**extraction, 'decoded_stats': [changed_raw, *decoded[1:]]}, profiles=[])['contract'] is None
    # Fixed poison support must not invent an unverified Venom level-up market field.
    venom = {
        **extraction,
        'source': {**extraction['source'], 'item_identity': {'table': 'unique', 'table_id': 399}},
        'decoded_stats': [
            *decoded[:-1],
            {
                'status': 'decoded',
                'value': 100,
                'memory_stat': {'id': 199, 'layer': 278 * 64 + 23, 'raw': 100},
            },
        ],
    }
    assert assess(venom, profiles=[])['contract'] is None
