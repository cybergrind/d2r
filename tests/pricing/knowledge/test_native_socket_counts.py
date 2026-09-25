from pricing.knowledge.native_socket_counts import native_socket_range


def test_native_socket_parameter_and_rolls_are_clamped_by_every_item_level_bracket():
    base = {'gemsockets': 2, 'invwidth': 1, 'invheight': 3, 'type': 'swor'}
    types = {'swor': {'MaxSockets1': 2, 'MaxSockets2': 2, 'MaxSockets3': 2}}
    assert native_socket_range({'prop1': 'sock', 'par1': 3}, base, types)['fixed'] == 2
    result = native_socket_range({'prop1': 'sock', 'min1': 1, 'max1': 3}, base, types)
    assert result['min'] == 1
    assert result['max'] == 2
    assert result['fixed'] is None
    types['swor']['MaxSockets1'] = 1
    assert native_socket_range({'prop1': 'sock', 'par1': 2}, base, types)['fixed'] is None
    assert native_socket_range({}, base, types) is None
    assert native_socket_range({'prop1': 'sock', 'par1': 2}, base, {}) is None


def test_fixed_socket_normalization_preserves_unknown_contents_and_rejects_conflicts(monkeypatch):
    from types import SimpleNamespace

    from pricing.knowledge import market_mechanics

    variant = {
        'base_definition': {'type': 'helm', 'gemsockets': 3, 'hasinv': 1},
        'game_definition': {'prop1': 'sock', 'min1': 2, 'max1': 2},
        'native_socket_range': {'min': 2, 'max': 2, 'fixed': 2},
    }
    monkeypatch.setattr(
        market_mechanics,
        'catalog',
        lambda: SimpleNamespace(named_variants={('set', 'Test Helm'): [variant]}, generation='fixture'),
    )
    row = {'name': 'Test Helm', 'category': 'sets', 'properties': {}}
    market_mechanics.apply_named_equipment_facts(row)
    assert row['sockets'] == 2
    assert 'socket_contents' not in row
    assert row['facet_basis']['sockets']['kind'] == 'fixed_native_sockets'
    row = {'name': 'Test Helm', 'category': 'sets', 'properties': {'402': 1}, 'sockets': 1}
    market_mechanics.apply_named_equipment_facts(row)
    assert row['sockets'] == 1
    assert row['mechanics_conflicts']


def test_prepared_definitions_supply_fixed_counts_without_assuming_empty_sockets():
    from pricing.knowledge.market import normalize_facets

    for name, category, count in (
        ("Moser's Blessed Circle", 'uniques', 2),
        ('Blade of Ali Baba', 'uniques', 2),
        ("Griswold's Heart", 'sets', 3),
        ("Immortal King's Will", 'sets', 2),
    ):
        row = {'name': name, 'category': category, 'properties': {}}
        normalize_facets(row)
        assert row['sockets'] == count
        assert row['socket_contents'] == 'unknown'
        assert row['facet_basis']['sockets']['generation']
    for name in ('Crown of Ages', 'Tomb Reaver', 'Vampire Gaze'):
        row = {'name': name, 'category': 'uniques', 'properties': {}}
        normalize_facets(row)
        assert 'sockets' not in row
