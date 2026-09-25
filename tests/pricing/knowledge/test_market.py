import pytest

from pricing.knowledge.market import normalize_listing, scope_status, summarize


def listing(**changes):
    row = {
        'id': '1',
        'seller_id': 's',
        'amount': 1,
        'properties': [
            {'property_id': k, 'type': t, t: v}
            for k, t, v in [
                (799, 'string', 'softcore'),
                (800, 'bool', False),
                (798, 'string', 'PC'),
                (1854, 'string', 'reign of the warlock'),
                (402, 'number', 3),
                (738, 'bool', False),
                (797, 'string', 'normal'),
            ]
        ],
        'prices': [{'name': 'Ist Rune', 'quantity': 2, 'group': 0}],
    }
    row.update(changes)
    return row


def norm(row):
    return normalize_listing(row, name='Greater Talons', category='base', source='fixture', currencies={'ist': 1})


def test_scope_requires_explicit_version():
    p = {'799': 'softcore', '800': False, '798': 'PC'}
    assert scope_status(p) == 'unknown'
    assert scope_status(p | {'1854': 'classic'}) == 'rejected'
    assert scope_status(p | {'1854': 'lord of destruction,reign of the warlock'}) == 'verified'


def test_unknown_or_group_does_not_destroy_complete_group():
    row = norm(
        listing(
            prices=[{'name': 'Unknown', 'quantity': 1, 'group': 0}, {'name': 'Ist Rune', 'quantity': 3, 'group': 1}]
        )
    )
    assert row['ask_ist'] == 3
    assert row['conversion']['unknown_currencies'] == ['Unknown']


def test_comparables_exclude_bundle_unknown_and_wrong_facets():
    rows = [norm(listing()), norm(listing(id='2', seller_id='b', amount=2))]
    assert summarize(rows, {'sockets': 3})['priced_sellers'] == 1
    assert summarize(rows, {'sockets': 4})['priced_sellers'] == 0
    assert summarize(rows, {'properties.999': 3})['priced_sellers'] == 0


def test_missing_seller_and_duplicate_seller_do_not_inflate_band():
    rows = [norm(listing()), norm(listing(id='2')), norm(listing(id='3', seller_id=None))]
    result = summarize(rows, {'sockets': 3})
    assert result['priced_sellers'] == 1
    assert result['median_ist'] == 2
    assert result['thin'] is True


def test_unknown_fetch_date_preserved_and_stack_units_explicit():
    row = normalize_listing(
        listing(amount=10), name='Ist Rune', category='runes', source='fixture', currencies={'ist': 1}
    )
    assert row['observed_at'] is None
    assert row['ask_ist'] == pytest.approx(0.2)
    assert row['unit_policy'] == 'stack_total'


def test_nested_properties_and_bounded_evidence():
    rows = [norm(listing(id=str(i), seller_id=str(i))) for i in range(6)]
    result = summarize(rows, {'properties': {'402': 3}})
    assert result['priced_sellers'] == 6
    assert len(result['representatives']) == 3
    assert summarize(rows, {'properties': {'402': 2}})['priced_sellers'] == 0


def test_scope_rejects_numeric_false_and_invalid_prices():
    assert scope_status({'799': 'softcore', '800': 0, '798': 'PC', '1854': 'reign of the warlock'}) != 'verified'
    for quantity in [True, 0, -1, float('nan'), float('inf')]:
        row = norm(listing(prices=[{'name': 'Ist Rune', 'quantity': quantity}]))
        assert row['ask_ist'] is None


def test_non_numeric_and_missing_seller_are_excluded():
    row = norm(listing())
    for value in [True, 0, -1, float('nan'), float('inf'), '2']:
        assert summarize([row | {'ask_ist': value}])['priced_sellers'] == 0


def test_scalar_facets_preserve_unknown_types():
    source = listing()
    for prop in source['properties']:
        if prop['property_id'] == 738:
            prop.update(type='number', number=0)
    row = norm(source)
    assert 'ethereal' not in row
    assert summarize([row], {'ethereal': False})['priced_sellers'] == 0


def test_array_properties_keep_string_values_and_empty_sockets_require_evidence():
    raw = listing()
    raw['properties'].append(
        {'property_id': 934, 'type': 'array', 'string': 'Rainbow Facet: Lightning Death', 'property': 'Sockets'}
    )
    filled = norm(raw)
    assert filled['properties']['934'] == 'Rainbow Facet: Lightning Death'
    assert filled['socket_contents'] == 'filled'
    unknown = norm(listing(id='unknown'))
    assert summarize([filled, unknown], {'properties': {'934': ''}})['priced_sellers'] == 0
    raw['properties'][-1]['string'] = ''
    empty = norm(raw)
    assert empty['socket_contents'] == 'empty'
    assert summarize([filled, unknown, empty], {'properties': {'934': ''}})['priced_sellers'] == 1


def test_named_unique_catalog_supplies_quality_without_guessing_scope():
    raw = listing()
    raw['properties'] = [p for p in raw['properties'] if p['property_id'] not in (797, 800)]
    row = normalize_listing(raw, name='Harlequin Crest', category='uniques', source='fixture')
    assert row['rarity'] == 'unique'
    assert row['rarity_basis'] == 'named_catalog_category'
    assert row['scope_status'] == 'unknown'
