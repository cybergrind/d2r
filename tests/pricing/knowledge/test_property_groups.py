"""Random item properties retain alternatives instead of becoming mandatory totals."""

import json
from pathlib import Path

import pytest

from pricing.knowledge.definitions import build_definitions


ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def compiled():
    return build_definitions(ROOT)


def test_opalvein_preserves_all_six_alternatives_with_native_bounds(compiled):
    item = next(r for r in compiled['rows'] if r['rarity'] == 'unique' and r['table_id'] == 416)
    group = item['property_groups'][0]
    assert group['code'] == 'magdam-rand'
    assert group['selection'] == 'single_scalar_choice'
    assert group['source']['locator'] == '/magdam-rand'
    native = json.loads((ROOT / group['source']['path']).read_text())['magdam-rand']
    assert group['game_definition'] == native
    assert group['source']['sha256'] == compiled['inputs'][group['source']['path']]
    assert [(c['property'], set(c['roll_ranges'])) for c in group['choices']] == [
        ('extra-mag', {'357'}),
        ('dmg%', {'17', '18'}),
        ('extra-fire', {'329'}),
        ('extra-cold', {'331'}),
        ('extra-ltng', {'330'}),
        ('extra-pois', {'332'}),
    ]
    for choice in group['choices']:
        bounds = (20, 40) if choice['property'] == 'dmg%' else (3, 5)
        assert all((r['min'], r['max']) == bounds for r in choice['roll_ranges'].values())
        assert not set(choice['roll_ranges']) & item['roll_ranges'].keys()


def test_random_parameter_and_pickmode_two_are_not_misrepresented_as_scalar_choices(compiled):
    for table_id in (62, 413):
        item = next(r for r in compiled['rows'] if r['rarity'] == 'unique' and r['table_id'] == table_id)
        assert item['property_groups']
        assert all(g['selection'] == 'unresolved' for g in item['property_groups'])


@pytest.mark.parametrize(
    ('ids', 'low', 'high'),
    [((357,), 3, 5), ((17, 18), 20, 40), ((329,), 3, 5), ((331,), 3, 5), ((330,), 3, 5), ((332,), 3, 5)],
)
def test_only_observed_choice_gets_displayed_range(compiled, ids, low, high):
    from inventory_tracking.items.ranges import annotate_roll_ranges

    item = next(r for r in compiled['rows'] if r['rarity'] == 'unique' and r['table_id'] == 416)
    for value, quality in ((low, 'low'), (high, 'perfect')):
        rows = [
            {
                'memory_stat': {'id': sid, 'layer': 0},
                'status': 'decoded',
                'value': value,
                'label': '+{{value}}% Damage',
                'text': f'+{value}% Damage',
            }
            for sid in ids
        ]
        annotate_roll_ranges(rows, item)
        assert all(row['roll_range']['min'] == low and row['roll_range']['max'] == high for row in rows)
        assert all(row['roll_quality'] == quality for row in rows)
        assert all(f'({low}-{high}%)' in row['text'] for row in rows)


@pytest.mark.parametrize(
    'values',
    [
        {},
        {329: 2},
        {329: 6},
        {329: True},
        {329: 4.5},
        {329: float('nan')},
        {329: 3, 330: 4},
        {17: 20},
        {17: 20, 18: 21},
    ],
)
def test_invalid_random_choice_has_no_display_range(compiled, values):
    from inventory_tracking.items.ranges import annotate_roll_ranges

    item = next(r for r in compiled['rows'] if r['rarity'] == 'unique' and r['table_id'] == 416)
    rows = [
        {
            'memory_stat': {'id': sid, 'layer': 0},
            'status': 'decoded',
            'value': value,
            'label': '+{{value}}% Damage',
            'text': 'Damage',
        }
        for sid, value in values.items()
    ]
    annotate_roll_ranges(rows, item)
    assert all('roll_range' not in row for row in rows)


def opalvein_facts(values):
    from dataclasses import replace

    from tests.pricing.knowledge.assessment.test_family_contracts import facts, scalar_properties

    stats = {
        f'{sid}:0': {'status': 'decoded', 'value': value}
        for sid, value in {105: 10, 86: 1, 138: 1, 39: 6, 41: 6, 43: 6, 45: 6, **values}.items()
    }
    stats['195:25487'] = {'status': 'decoded', 'raw': 2, 'value': 2, 'unit': 'percent_chance'}
    return replace(facts('Ring', 'unique', 'Opalvein'), stats=stats, properties=scalar_properties(stats))


@pytest.mark.parametrize('values', [{}, {329: 2}, {329: 6}, {329: 3, 330: 4}, {17: 20}, {17: 20, 18: 21}])
def test_complete_named_contract_rejects_invalid_random_choices(compiled, monkeypatch, values):
    from pricing.knowledge.assessment.handlers.named import NamedHandler

    item = next(r for r in compiled['rows'] if r['rarity'] == 'unique' and r['table_id'] == 416)
    monkeypatch.setattr('pricing.knowledge.assessment.handlers.named.resolve_named_definition', lambda _: (item, []))
    contract, gaps = NamedHandler().contract(opalvein_facts(values), 'jewelry')
    assert contract is None
    assert any('magdam-rand' in gap for gap in gaps), gaps


@pytest.mark.parametrize(
    'values', [{329: 3}, {329: 5}, {17: 20, 18: 20}, {17: 40, 18: 40}, {357: 3}, {330: 5}, {331: 3}, {332: 5}]
)
def test_valid_choice_requires_market_projection(compiled, monkeypatch, values):
    from dataclasses import replace

    from pricing.knowledge.assessment.handlers.named import NamedHandler
    from tests.pricing.knowledge.assessment.test_family_contracts import scalar_properties

    item = next(r for r in compiled['rows'] if r['rarity'] == 'unique' and r['table_id'] == 416)
    monkeypatch.setattr('pricing.knowledge.assessment.handlers.named.resolve_named_definition', lambda _: (item, []))
    capture = opalvein_facts(values)
    contract, gaps = NamedHandler().contract(capture, 'jewelry')
    projected = scalar_properties({f'{sid}:0': {'value': value} for sid, value in values.items()})
    if projected:
        assert contract is not None, gaps
        assert all(contract.properties[prop] == value for prop, value in projected.items())
        missing = replace(capture, properties={p: v for p, v in capture.properties.items() if p not in projected})
        assert NamedHandler().contract(missing, 'jewelry')[0] is None
    else:
        assert contract is None
        assert any('magdam-rand' in gap for gap in gaps)


@pytest.mark.parametrize(
    ('ids', 'value', 'bounds'),
    [
        ((357,), 5, '3-5%'),
        ((17, 18), 40, '20-40%'),
        ((329,), 5, '3-5%'),
        ((331,), 5, '3-5%'),
        ((330,), 5, '3-5%'),
        ((332,), 5, '3-5%'),
    ],
)
def test_native_capture_reaches_range_display_and_contract(compiled, monkeypatch, ids, value, bounds):
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.adapters.capture import normalize
    from pricing.knowledge.assessment.handlers.named import NamedHandler
    from tests.pricing.knowledge.assessment.item_bank.cases.opalvein import RAW
    from tests.pricing.knowledge.assessment.item_bank.models import Item

    definition = next(r for r in compiled['rows'] if r['rarity'] == 'unique' and r['table_id'] == 416)
    monkeypatch.setitem(metadata()['identities']['unique'], '416', definition)
    monkeypatch.setattr(
        'pricing.knowledge.assessment.handlers.named.resolve_named_definition', lambda _: (definition, [])
    )
    capture = Item(
        'Ring', 'unique', 'Opalvein', (*RAW, *((sid, 0, value) for sid in ids)), named_table_id=416, complete=True
    ).capture()
    rows = capture['decoded_stats']
    assert any(f'({bounds})' in r.get('text', '') for r in rows), rows
    facts = normalize(capture)
    contract, gaps = NamedHandler().contract(facts, 'jewelry')
    assert contract is not None, gaps

    from pricing.knowledge.assessment.comparables import reject_reasons

    matching = {
        **contract.to_dict(),
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'fixture',
        'ask_ist': 1,
    }
    assert not reject_reasons(contract.to_dict(), matching)
    choice_fields = {'1879', '510', '750', '747', '743', '783'}
    captured = choice_fields & contract.properties.keys()
    assert len(captured) == 1
    for other in choice_fields - captured:
        changed = {p: v for p, v in contract.properties.items() if p not in choice_fields}
        changed[other] = value
        assert reject_reasons(contract.to_dict(), {**matching, 'properties': changed})
