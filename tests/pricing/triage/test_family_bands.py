from pricing.triage.adapters import from_listing
from pricing.triage.bands import build_bands
from pricing.triage.engine import assess
from tests.pricing.triage.test_bands import listing


RULE = {
    'category': 'magic',
    'name': 'Small Charm',
    'bucket': 'fine-life',
    'properties': {'448': 3, '423': {'min': 10, 'max': 20}, '418': {'min': 16, 'max': 20}},
    'pattern': {'properties': {'448': {'min': 1}, '423': {'min': 1}, '418': {'min': 1}}},
}


def charm(seller, life, price):
    row = listing(seller, price)
    row.update(name='Small Charm', category='charms', rarity='magic')
    row['properties'].update({'448': 3, '423': 18, '418': life})
    return row


def test_family_band_prices_matching_rolls_without_borrowing_perfect_asks():
    rows = [charm(i, 17, 2) for i in range(3)] + [charm(i + 3, 20, 50) for i in range(3)]
    document = build_bands(rows, [], rules=[RULE])
    tables = {
        'bands': {(r['category'], r['name'].casefold(), r['bucket']): r for r in document['bands']},
        'rules': {'keep_ist': 0.25, 'rows': [RULE]},
        'own': {'rows': []},
    }
    result = assess(from_listing(rows[0]), tables)
    assert result['decision_ist'] == 2
    assert result['band']['sellers'] == 3
    assert result['verdict'] == 'slow'
    unseen = from_listing(charm(10, 16, 1))
    result = assess(unseen, tables)
    assert result['band'] is None
    assert result['verdict'] == 'check'
    assert result['reference_band']['median_ist'] == 26


def test_family_band_does_not_pool_stacks_or_sellers():
    rows = [charm(1, 17, 2), {**charm(1, 17, 100), 'listing_id': 'second'}, {**charm(2, 17, 50), 'amount': 40}]
    document = build_bands(rows, [], rules=[RULE])
    bands = [r for r in document['bands'] if r['category'] == 'family' and r.get('roll_properties')]
    assert len(bands) == 1
    assert bands[0]['sellers'] == 1
    assert bands[0]['median_ist'] == 2


def test_magic_skill_gloves_price_only_matching_skill_base_and_modifier_cohort():
    from inventory_tracking.items.metadata import metadata
    from pricing.triage.import_affixed_rules import affixed_rules

    bases = {b['name']: b['code'] for b in metadata()['bases'].values()}
    rules = affixed_rules()
    rows = []
    for seller in range(3):
        row = listing(seller, 4)
        row.update(
            name='Gauntlets',
            category='magic',
            rarity='magic',
            base_code=bases['Gauntlets'],
            sockets=0,
            socket_contents='empty',
        )
        row['properties'].update({'410': 3, '457': 20})
        rows.append(row)
    document = build_bands(rows, [], rules=rules)
    tables = {
        'bands': {(r['category'], r['name'].casefold(), r['bucket']): r for r in document['bands']},
        'rules': {'keep_ist': 0.25, 'rows': rules},
        'own': {'rows': []},
    }
    item = from_listing(rows[0])
    result = assess(item, tables)
    assert result['decision_ist'] == 4
    assert result['band']['sellers'] == 3
    assert result['verdict'] == 'slow'
    for changes in (
        {'name': 'Heavy Gloves', 'base_code': bases['Heavy Gloves']},
        {'ethereal': True, 'properties': rows[0]['properties'] | {'738': True}},
        {'properties': {**{k: v for k, v in rows[0]['properties'].items() if k != '410'}, '456': 3}},
        {'properties': rows[0]['properties'] | {'427': 10}},
    ):
        other = from_listing(rows[0] | changes)
        result = assess(other, tables)
        assert result['verdict'] == 'check'
        assert result['band'] is None


def test_amazon_class_prefix_javelins_do_not_borrow_stacked_skill_prefix_prices():
    from inventory_tracking.items.metadata import metadata
    from pricing.triage.import_class_rules import class_rules

    bases = {b['name']: b['code'] for b in metadata()['bases'].values()}
    rows = []
    for seller in range(3):
        row = listing(seller, 5)
        row.update(
            name='Maiden Javelin',
            category='magic',
            rarity='magic',
            base_code=bases['Maiden Javelin'],
            sockets=0,
            socket_contents='empty',
        )
        row['properties'].update({'453': 2, '456': 3, '457': 40})
        rows.append(row)
    rules = class_rules()
    document = build_bands(rows, [], rules=rules)
    tables = {
        'bands': {(r['category'], r['name'].casefold(), r['bucket']): r for r in document['bands']},
        'rules': {'keep_ist': 0.25, 'rows': rules},
        'own': {'rows': []},
    }
    item = from_listing(rows[0])
    assert assess(item, tables)['decision_ist'] == 5
    for props in ({'456': 5, '457': 40}, {'456': 6, '457': 40}):
        other = from_listing(rows[0] | {'properties': props})
        result = assess(other, tables)
        assert result['verdict'] == 'check'
        assert result['band'] is None
    for changed in ({'ethereal': True}, {'base_code': bases['Matriarchal Javelin']}, {'base_code': None}):
        result = assess(item | changed, tables)
        assert result['verdict'] == 'check'
        assert result['band'] is None


def test_echoing_switch_uses_no_better_ias_without_pooling_bases_or_other_suffixes():
    from inventory_tracking.items.metadata import metadata
    from pricing.triage.import_affixed_rules import affixed_rules

    bases = {b['name']: b['code'] for b in metadata()['bases'].values()}
    rows = []
    for seller in range(3):
        row = listing(seller, 1)
        row.update(
            name='Throwing Spear',
            category='magic',
            rarity='magic',
            base_code=bases['Throwing Spear'],
            sockets=0,
            socket_contents='empty',
        )
        row['properties'].update({'406': 3})
        rows.append(row)
    rows += [
        rows[0]
        | {'listing_id': str(n), 'seller_id': str(n), 'ask_ist': 100, 'properties': rows[0]['properties'] | {'457': 40}}
        for n in range(3, 6)
    ]
    rules = affixed_rules()
    document = build_bands(rows, [], rules=rules)
    tables = {
        'bands': {(r['category'], r['name'].casefold(), r['bucket']): r for r in document['bands']},
        'rules': {'keep_ist': 0.25, 'rows': rules},
        'own': {'rows': []},
    }
    captured = from_listing(rows[0] | {'properties': rows[0]['properties'] | {'457': 10}})
    result = assess(captured, tables)
    assert result['decision_ist'] == 1
    assert result['band']['sellers'] == 3
    assert result['verdict'] == 'slow'
    assert result['band']['comparison']['label'] == 'IAS ≤10'
    assert assess(from_listing(rows[0]), tables)['band']['sellers'] == 3
    for changes in (
        {'ethereal': True},
        {'base_code': bases['Javelin']},
        {'base_modifiers': captured['base_modifiers'] | {'437': 10}},
        {'properties': captured['properties'] | {'457': None}},
    ):
        other = assess(captured | changes, tables)
        assert other['band'] is None


def test_rare_skill_gloves_price_no_better_resistance_with_other_rolls_fixed():
    from inventory_tracking.items.metadata import metadata
    from pricing.triage.import_affixed_rules import affixed_rules

    base = next(b['code'] for b in metadata()['bases'].values() if b['name'] == 'Gauntlets')
    rows = []
    for seller, resistance, price in ((1, 5, 5), (2, 10, 7), (3, 15, 9), (4, 30, 100)):
        row = listing(seller, price)
        row.update(name='Gauntlets', category='rare', rarity='rare', base_code=base, sockets=0, socket_contents='empty')
        row['properties'].update({'456': 2, '457': 20, '463': 3, '428': resistance})
        rows.append(row)
    rules = affixed_rules()
    document = build_bands(rows, [], rules=rules)
    tables = {
        'bands': {(r['category'], r['name'].casefold(), r['bucket']): r for r in document['bands']},
        'rules': {'keep_ist': 0.25, 'rows': rules},
        'own': {'rows': []},
    }
    item = from_listing(rows[2])
    result = assess(item, tables)
    assert result['verdict'] == 'slow'
    assert result['band']['sellers'] == 3
    assert result['decision_ist'] == 6
    assert result['band']['comparison']['label'] == 'lightning resistance ≤15'
    assert assess(from_listing(rows[0]), tables)['verdict'] == 'check'
    changed = from_listing(rows[2] | {'properties': rows[2]['properties'] | {'463': 2}})
    assert assess(changed, tables)['band'] is None
