import pytest

from inventory_tracking.items.metadata import metadata
from pricing.triage.adapters import from_drop


def observation(code, **fields):
    return {
        'item': {'name': 'Example', 'base_code': code, 'rarity': 'unique', 'affixes': [], **fields},
        'source': {},
        'decoded_stats': [],
    }


def test_old_jewelry_capture_uses_verified_nonsocketable_nonethereal_mechanics():
    item = from_drop(observation('rin'))
    assert item['ethereal'] is False
    assert item['sockets'] == 0
    assert item['socket_contents'] == 'empty'


def test_missing_armor_flags_are_not_inferred_from_no_listed_ethereal_sellers():
    item = from_drop(observation('uap'))
    assert item['ethereal'] is None
    assert item['sockets'] is None
    assert item['socket_contents'] is None


def test_explicit_capture_flags_are_not_silently_overwritten():
    item = from_drop(observation('rin', ethereal=True, sockets=1, socket_contents='filled'))
    assert item['ethereal'] is True
    assert item['sockets'] == 1
    assert item['socket_contents'] == 'filled'


@pytest.mark.parametrize('family', ['boot', 'glov', 'belt'])
def test_nonsocketable_equipment_recovers_socket_facts_without_inventing_ethereal(family):
    base = next(b for b in metadata()['bases'].values() if b['type'] == family)
    item = from_drop(observation(base['code']))
    assert base['max_sockets'] == 0
    assert item['sockets'] == 0
    assert item['socket_contents'] == 'empty'
    assert item['ethereal'] is None


def test_nonsocketable_equipment_does_not_hide_conflicting_capture():
    base = next(b for b in metadata()['bases'].values() if b['type'] == 'boot')
    item = from_drop(observation(base['code'], sockets=1, socket_contents='filled'))
    assert item['sockets'] == 1
    assert item['socket_contents'] == 'filled'


@pytest.mark.parametrize(('quantity', 'verdict'), [(1, 'check'), (15, 'slow'), (32, 'slow')])
def test_captured_gem_quantity_reaches_supported_sale_lot(quantity, verdict):
    from pricing.triage.engine import assess

    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Perfect Ruby')
    captured = observation(base['code'], name=base['name'], rarity='normal', quantity=quantity)
    item = from_drop(captured)
    band = {'q1_ist': 0.05, 'quantity': 15, 'sellers': 3, 'liquidity': 'thin', 'observed_at': '2026-10-03'}
    tables = {
        'rules': {'rows': [], 'keep_ist': 0.25},
        'own': {'rows': []},
        'bands': {('gems', 'perfect ruby', 'quantity:15'): band},
    }
    result = assess(item, tables)
    assert item['quantity'] == quantity
    assert result['verdict'] == verdict
    if quantity > 1:
        assert result['decision_ist'] == 0.75


def test_weapon_quantity_is_not_a_sale_lot():
    base = next(b for b in metadata()['bases'].values() if b['type'] == 'jave')
    item = from_drop(observation(base['code'], rarity='magic', quantity=120))
    assert item['quantity'] == 1


@pytest.mark.parametrize('name', ['Rejuvenation Potion', 'Full Rejuvenation Potion'])
def test_captured_material_potions_use_misc_market_and_keep_quantity(name):
    base = next(b for b in metadata()['bases'].values() if b['name'] == name)
    item = from_drop(observation(base['code'], name=name, rarity='normal', quantity=96))
    assert item['category'] == 'misc'
    assert item['name'] == name
    assert item['quantity'] == 96


def test_jewel_required_level_comes_from_verified_affixes_not_item_level():
    from pricing.triage.engine import assess
    from pricing.triage.import_affixed_rules import affixed_rules

    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Jewel')
    suffix = next(
        int(k)
        for k, r in metadata()['affixes']['suffix'].items()
        if r['name'] == 'of Carnage' and base['code'] in r['base_codes']
    )
    captured = observation(
        base['code'], rarity='magic', identified=True, item_level=99, affixes=[{'property_id': '448', 'value': 11}]
    )
    captured['source'] = {
        'stat_capture_complete': True,
        'native_affixes': {'prefix': [], 'suffix': [suffix], 'auto': []},
    }
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = from_drop(captured)
    assert item['properties']['796'] == 18
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert 'low-level' in result['reason'].lower()
    assert result['decision_ist'] is None
    for level in [41, 50, None]:
        properties = item['properties'] | {'796': level}
        assert assess(item | {'properties': properties}, tables)['verdict'] == 'vendor'
    for source in [
        {},
        captured['source'] | {'stat_capture_complete': False},
        captured['source'] | {'native_affixes': {'prefix': [], 'suffix': [999999], 'auto': []}},
    ]:
        unknown = from_drop(captured | {'source': source})
        assert '796' not in unknown['properties']
        assert assess(unknown, tables)['verdict'] == 'vendor'
    high_prefix = next(
        int(k)
        for k, r in metadata()['affixes']['prefix'].items()
        if r['name'] == 'Vermillion' and base['code'] in r['base_codes']
    )
    high = from_drop(
        captured
        | {
            'item': captured['item'] | {'affixes': [{'property_id': '448', 'value': 26}]},
            'source': captured['source']
            | {'native_affixes': {'prefix': [high_prefix], 'suffix': [suffix], 'auto': []}},
        }
    )
    assert high['properties']['796'] == 50
    assert assess(high, tables)['verdict'] == 'vendor'
    # Carnage is not rare-eligible; malformed IDs never establish LLD eligibility.
    rare = from_drop(captured | {'item': captured['item'] | {'rarity': 'rare'}})
    assert '796' not in rare['properties']
    for stat in (92, 94):
        adjusted = from_drop(
            captured
            | {
                'decoded_stats': [
                    {
                        'memory_stat': {'id': stat, 'layer': 0, 'raw': 10},
                        'status': 'unresolved',
                    }
                ]
            }
        )
        assert '796' not in adjusted['properties']


@pytest.mark.parametrize(('rate', 'frames', 'total'), [(299, 150, 175), (385, 300, 451)])
def test_poison_charm_native_rates_reach_trade_pattern(rate, frames, total):
    from inventory_tracking.items.metadata import decode_stats
    from pricing.triage.engine import assess
    from pricing.triage.import_affixed_rules import affixed_rules

    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Small Charm')
    captured = observation(base['code'], rarity='magic', identified=True)
    raw = [{'id': stat, 'layer': 0, 'raw': value} for stat, value in [(57, rate), (58, rate), (59, frames), (326, 1)]]
    decoded, affixes, _ = decode_stats(raw, base=base)
    captured['decoded_stats'] = decoded
    captured['item']['affixes'] = affixes
    item = from_drop(captured)
    assert item['properties']['518'] == total
    result = assess(item, {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}})
    assert result['verdict'] == 'check'
    assert result['decision_ist'] is None
    # Missing duration/source evidence must not be inferred from rate alone.
    for missing in (59, 326):
        decoded, affixes, _ = decode_stats([r for r in raw if r['id'] != missing], base=base)
        captured['decoded_stats'], captured['item']['affixes'] = decoded, affixes
        assert '518' not in from_drop(captured)['properties']


@pytest.mark.parametrize(
    ('stat', 'prop'), [(152, '432'), (153, '591'), (118, '447'), (115, '553'), (81, '532'), (117, '531')]
)
@pytest.mark.parametrize('raw', [0, 1, 2])
def test_native_flags_use_market_booleans_without_truthy_coercion(raw, stat, prop):
    from inventory_tracking.items.metadata import decode_stats
    from pricing.triage.guide_cases import item_from_spec

    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Berserker Axe')
    native = [{'id': stat, 'layer': 0, 'raw': raw}]
    decoded, affixes, _ = decode_stats(native, base=base)
    captured = observation(base['code'], rarity='rare', ethereal=True, sockets=0, socket_contents='empty')
    captured['item']['affixes'] = affixes
    captured['decoded_stats'] = decoded
    item = from_drop(captured)
    guide = item_from_spec(
        {'base': base['name'], 'rarity': 'rare', 'ethereal': True, 'sockets': 0, 'stats': {f'{stat}:0': raw}}
    )
    if raw == 1:
        assert item['properties'][prop] is True
        assert guide['properties'][prop] is True
    else:
        assert item['properties'].get(prop) is not True
        assert guide['properties'].get(prop) is not True


def test_self_repair_and_replenish_reach_the_market_properties_rules_match_on():
    from pricing.knowledge.assessment.adapters.market_projection import market_properties

    # Sellers enter the seconds-per-point number (20 or 33), which is the decoded value.
    assert market_properties()['252:0'] == '431'
    assert market_properties()['253:0'] == '563'


@pytest.mark.parametrize(('raw', 'bonus', 'verdict'), [(24, None, 'vendor'), (44, 20, 'check')])
def test_captured_shield_block_total_loses_its_base_before_matching_deflecting(raw, bonus, verdict):
    # Charsi's Artisan's Tower Shield of Charged Bolt (2026-10-09): 24 is the base, not Deflecting.
    from inventory_tracking.items.metadata import decode_stats
    from pricing.triage.engine import Tables, assess

    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Tower Shield')
    decoded, affixes, _ = decode_stats([{'id': 20, 'layer': 0, 'raw': raw}], base=base)
    captured = observation(base['code'], rarity='magic', ethereal=False, sockets=3, socket_contents='empty')
    captured['item']['affixes'] = affixes
    captured['decoded_stats'] = decoded
    item = from_drop(captured)
    assert item['properties'].get('446') == bonus
    assert assess(item, Tables().load())['verdict'] == verdict
