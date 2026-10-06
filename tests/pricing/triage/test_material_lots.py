import pytest

from pricing.knowledge.market import normalize_listing
from pricing.triage.bands import build_bands
from pricing.triage.engine import assess, prepare_tables


def test_sparse_key_quote_is_reference_and_supported_bulk_lot_takes_priority():
    from tests.pricing.triage.test_bands import listing

    rows = [listing(i, 1) | {'name': 'Key of Destruction', 'category': 'misc'} for i in range(2)]
    rules = {'rows': [], 'keep_ist': 0.25}
    item = {'name': 'Key of Destruction', 'category': 'misc', 'quantity': 1}
    tables = prepare_tables(build_bands(rows, []), rules, {'rows': []})
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert result['decision_ist'] is None
    assert result['band'] is None
    assert result['reference_band']['sellers'] == 2
    stack = assess(item | {'quantity': 4}, tables)
    assert stack['verdict'] == 'check'
    assert stack['decision_ist'] is None
    assert stack['reference_band']['quantity'] == 1
    lots = [
        listing(i + 2, 0.5) | {'name': item['name'], 'category': 'misc', 'amount': 3, 'unit_policy': 'stack_total'}
        for i in range(3)
    ]
    tables = prepare_tables(build_bands(rows + lots, []), rules, {'rows': []})
    assert assess(item, tables)['sale_mode'] == 'accumulate'
    ready = assess(item | {'quantity': 3}, tables)
    assert ready['verdict'] == 'slow'
    assert ready['decision_ist'] == 1.5
    # A lone extravagant ask does not override the lower-gem pickup policy.
    flawed = [listing(0, 30) | {'name': 'Flawed Ruby', 'category': 'gems'}]
    tables = prepare_tables(build_bands(flawed, []), rules, {'rows': []})
    assert assess({'name': 'Flawed Ruby', 'category': 'gems'}, tables)['verdict'] == 'vendor'


@pytest.mark.parametrize('gem', ['Amethyst', 'Diamond', 'Emerald', 'Ruby', 'Sapphire', 'Skull', 'Topaz'])
def test_flawless_gems_keep_cube_use_without_inventing_a_price(gem):
    tables = prepare_tables(build_bands([], []), {'rows': [], 'keep_ist': 0.25}, {'rows': []})
    item = {'name': f'Flawless {gem}', 'category': 'gems', 'quantity': 1}
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert result['reason'] == f'Save 3 Flawless {gem} to cube 1 Perfect {gem}'
    assert result['decision_ist'] is None
    assert result['band'] is None
    assert assess(item | {'category': 'magic'}, tables)['verdict'] == 'vendor'
    assert assess(item | {'name': f'Flawed {gem}'}, tables)['verdict'] == 'vendor'


@pytest.mark.parametrize(
    ('name', 'catalog_id'),
    [
        ('Key of Terror', '3117972750'),
        ('Western Worldstone Shard', '1189945720'),
        ('Token of Absolution', '3193724423'),
        ('Full Rejuvenation Potion', '2483707607'),
    ],
)
def test_material_finite_lots_reach_accumulation_and_stack_sale(name, catalog_id):
    rows = []
    for seller in range(3):
        raw = {
            'id': str(seller),
            'seller_id': str(seller),
            'item_id': catalog_id,
            'stock': False,
            'amount': 10,
            'active': True,
            'selling': True,
            'completed': False,
            'properties': [
                {'property_id': k, 'type': t, t: v}
                for k, t, v in [
                    (799, 'string', 'softcore'),
                    (800, 'bool', False),
                    (798, 'string', 'PC'),
                    (1854, 'string', 'reign of the warlock'),
                ]
            ],
            'prices': [{'name': 'Ist Rune', 'quantity': 1}],
            'updated_at': '2026-10-06T00:00:00Z',
        }
        row = normalize_listing(
            raw, name=name, category='misc', source='fixture', observed_at='2026-10-06', currencies={'ist': 1}
        )
        assert row['unit_policy'] == 'stack_total'
        assert row['ask_ist'] == 0.1
        rows.append(row)
    document = build_bands(rows, [])
    tables = prepare_tables(document, {'rows': [], 'keep_ist': 0.25}, {'rows': []})
    item = {'name': name, 'category': 'misc', 'quantity': 1}
    assert assess(item, tables)['verdict'] == 'check'
    sold = assess(item | {'quantity': 23}, tables)
    assert sold['verdict'] == 'slow'
    assert sold['decision_ist'] == 1
    assert sold['sale_mode'] == 'split_bulk'


@pytest.mark.parametrize('stock', [True, None])
def test_material_available_stock_is_not_divided_into_unit_quotes(stock):
    row = normalize_listing(
        {'item_id': '3117972750', 'stock': stock, 'amount': 10, 'prices': [{'name': 'Ist Rune', 'quantity': 1}]},
        name='Key of Terror',
        category='misc',
        source='fixture',
        currencies={'ist': 1},
    )
    assert row['unit_policy'] == 'ambiguous'


@pytest.mark.parametrize(('name', 'catalog_id'), [('3x3 Key Set', '3357156195'), ('Key of Terror', 'wrong')])
def test_bundle_or_conflicting_identity_is_not_a_material_lot(name, catalog_id):
    row = normalize_listing(
        {'item_id': catalog_id, 'stock': False, 'amount': 10, 'prices': [{'name': 'Ist Rune', 'quantity': 1}]},
        name=name,
        category='misc',
        source='fixture',
        currencies={'ist': 1},
    )
    assert row['unit_policy'] == 'ambiguous'
