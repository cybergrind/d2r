import json
from pathlib import Path

from inventory_tracking.items.metadata import decode_stats
from pricing.knowledge.assessment.engine import assess
from tests.pricing.knowledge.assessment.test_family_contracts import facts


ROOT = Path(__file__).resolve().parents[4]


def atma():
    saved = json.loads((ROOT / 'tests/inventory_tracking/fixtures/atma_scarab.json').read_text())
    decoded, _, _ = decode_stats(saved['arrays']['arrays'][-1]['stats'])
    catalog = json.loads((ROOT / 'pricing/data/appraisal-properties.json').read_text())['properties']
    item = facts('Amulet', 'unique', "Atma's Scarab").to_dict()
    item['affixes'] = []
    for row in decoded:
        if row.get('label'):
            prop = next(k for k, v in catalog.items() if row['label'] in v['labels'])
            item['affixes'].append({'property_id': prop, 'value': row['value'], 'memory_stat': row['memory_stat']})
    return {'item': item, 'decoded_stats': decoded, 'source': {'stat_capture_complete': True}}


def test_saved_atma_proc_becomes_verified_fixed_comparison_property():
    extraction = atma()
    trigger = next(r for r in extraction['decoded_stats'] if r.get('memory_stat', {}).get('id') == 198)
    assert trigger.get('value') == 5
    assert trigger.get('unit') == 'percent_chance'
    result = assess(extraction, profiles=[])
    assert result['contract'] is not None, result['price_gaps']
    assert result['contract']['intrinsic_properties']['543'] == 5
    assert result['contract']['intrinsic_properties']['589'] == 40


def test_named_trigger_requires_event_skill_level_chance_and_typed_capture():
    extraction = atma()
    trigger = next(r for r in extraction['decoded_stats'] if r.get('memory_stat', {}).get('id') == 198)
    changed = [
        {**trigger, 'value': 2},
        {**trigger, 'unit': 'unverified'},
        {**trigger, 'memory_stat': {**trigger['memory_stat'], 'layer': 66 * 64 + 3}},
        {**trigger, 'memory_stat': {**trigger['memory_stat'], 'layer': 67 * 64 + 2}},
        {**trigger, 'memory_stat': {**trigger['memory_stat'], 'id': 201}},
        {**trigger, 'memory_stat': {**trigger['memory_stat'], 'raw': 2}},
    ]
    for replacement in [*changed, None]:
        modified = {
            **extraction,
            'decoded_stats': [
                replacement if r is trigger else r
                for r in extraction['decoded_stats']
                if r is not trigger or replacement is not None
            ],
        }
        assert assess(modified, profiles=[])['contract'] is None


def test_atma_comparisons_allow_fixed_proc_omission_but_reject_wrong_chance():
    from datetime import date

    from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables, reject_reasons

    contract = assess(atma(), profiles=[])['contract']
    assert contract is not None
    required = {k: v for k, v in contract['properties'].items() if k not in contract['intrinsic_properties']}
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
    assert reject_reasons(contract, {**rows[0], 'properties': {**required, '543': 2}})
    assert reject_reasons(contract, {**rows[0], 'properties': {**required, '812': 5}})
