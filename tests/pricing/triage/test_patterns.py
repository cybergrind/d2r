from pricing.triage.engine import assess


def test_vendor_boots_explain_unmet_combination_without_claiming_no_listings():
    from pricing.triage.engine import prepare_tables
    from pricing.triage.import_affixed_rules import affixed_rules

    tables = prepare_tables({'bands': []}, {'keep_ist': 0.25, 'rows': affixed_rules()}, {'rows': []})
    item = {
        'category': 'rare',
        'family': 'boot',
        'name': 'War Boots',
        'base_name': 'War Boots',
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': {'480': 20, '429': 5, '425': 51, '427': 8},
    }
    result = assess(item, tables)
    assert result['verdict'] == 'vendor'
    assert '20 FRW + two resistances of 30+' in result['reason']
    assert 'fire resistance 8 of 30' in result['reason']
    assert '0 of 2' in result['reason']
    assert 'no listings' not in result['reason']
    supported = item | {'properties': {'480': 20, '427': 25, '428': 25, '426': 25}}
    assert assess(supported, tables)['verdict'] == 'check'


def test_unknown_affixed_combination_does_not_claim_cache_absence():
    tables = {'rules': {'keep_ist': 0.25, 'rows': []}, 'own': {'rows': []}, 'bands': {}}
    result = assess({'category': 'rare', 'family': 'ring', 'name': 'Ring', 'properties': {}}, tables)
    assert result['verdict'] == 'vendor'
    assert result['reason'] == 'no supported trade combination for these stats'


def test_complete_paid_pattern_below_bucket_is_check_not_vendor():
    rule = {
        'category': 'magic',
        'name': 'Small Charm',
        'bucket': 'physical-life',
        'pattern': {'properties': {'damage': {'min': 1}, 'ar': {'min': 1}, 'life': {'min': 1}}},
        'properties': {'damage': {'min': 3}, 'ar': {'min': 10}, 'life': {'min': 16}},
        'labels': {'damage': 'max damage', 'ar': 'attack rating', 'life': 'life'},
        'pattern_label': 'Physical pattern complete',
        'premium': True,
    }
    tables = {'rules': {'keep_ist': 0.25, 'rows': [rule]}, 'own': {'rows': []}, 'bands': {}}
    item = {'category': 'magic', 'name': 'Small Charm', 'properties': {'damage': 2, 'ar': 18, 'life': 17}}
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert 'max damage 2 of 3' in result['reason']
    assert assess({**item, 'properties': {'damage': 3, 'ar': 18, 'life': 17}}, tables)['verdict'] == 'sell'
    assert assess({**item, 'properties': {'damage': 3, 'life': 17}}, tables)['verdict'] == 'vendor'


def test_keep_price_uses_q1_instead_of_high_median():
    tables = {
        'rules': {'keep_ist': 0.25, 'rows': []},
        'own': {'rows': []},
        'bands': {('sets', 'example', 'name'): {'q1_ist': 0.2, 'median_ist': 7, 'liquidity': 'liquid', 'sellers': 10}},
    }
    assert assess({'category': 'sets', 'name': 'Example'}, tables)['verdict'] == 'vendor'


def test_check_is_white_on_identify_and_scored_separately_from_sell():
    from inventory_tracking.corpus.score import score
    from inventory_tracking.identify.service import item_summary, result_lines
    from inventory_tracking.presentation import Tone
    from tests.inventory_tracking.identify.test_service import observation

    triage = {'verdict': 'check', 'reason': 'max damage 2 of 3', 'band': None}
    item = item_summary(observation(), {'triage': triage})
    lines = result_lines({'state': 'complete', 'items': [item], 'issues': []})
    assert any('CHECK' in line.text for line in lines)
    assert lines[-1].tone == Tone.DEFAULT
    scored = score([{'id': 'a', **triage}], {'a': 'check'})
    assert scored['check_recall'] == 1
    assert scored['checks'] == 1
    assert scored['keeps'] == 0


def test_imported_fine_life_acceptance_and_unrelated_stats():
    import json
    from pathlib import Path

    from pricing.triage.import_watches import compile_watches

    rows = compile_watches(json.loads(Path('pricing/data/appraisal-value-watch.json').read_text())['rows'])
    tables = {'rules': {'keep_ist': 0.25, 'rows': rows}, 'own': {'rows': []}, 'bands': {}}
    item = {'category': 'magic', 'name': 'Small Charm', 'properties': {'448': 2, '423': 18, '418': 17}}
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert 'max damage 2 of 3' in result['reason']
    assert assess({**item, 'properties': {'448': 3, '423': 18, '418': 17}}, tables)['verdict'] == 'sell'
    assert assess({**item, 'properties': {'448': 2, '418': 17}}, tables)['verdict'] == 'vendor'
    assert assess({**item, 'properties': {'418': 17}}, tables)['verdict'] == 'vendor'
    poison = {**item, 'properties': {'518': 175, '418': 17}}
    assert assess(poison, tables)['verdict'] == 'sell'
    assert assess({**item, 'properties': {'418': 17, 'duration': 6}}, tables)['verdict'] == 'vendor'


def test_guide_priority_does_not_promote_unpriced_low_or_medium_charms_to_sell():
    import json
    from pathlib import Path

    from pricing.triage.import_watches import compile_watches

    rows = compile_watches(json.loads(Path('pricing/data/appraisal-value-watch.json').read_text())['rows'])
    tables = {'rules': {'keep_ist': 0.25, 'rows': rows}, 'own': {'rows': []}, 'bands': {}}
    for resistance in (3, 4):
        for life in (0, 5):
            properties = dict.fromkeys(('427', '428', '426', '401'), resistance)
            if life:
                properties['418'] = life
            item = {'category': 'magic', 'name': 'Small Charm', 'properties': properties}
            assert assess(item, tables)['verdict'] == 'check'
    # An exact low-priority pattern may still sell when scoped asks support it.
    from pricing.triage.adapters import from_listing
    from pricing.triage.bands import build_bands
    from tests.pricing.triage.test_bands import listing

    listings = []
    for seller in range(4):
        row = listing(seller, 0.5)
        row.update(name='Small Charm', category='charms', rarity='magic')
        row['properties'].update(dict.fromkeys(('427', '428', '426', '401'), 3))
        listings.append(row)
    document = build_bands(listings, [], rules=rows)
    tables['bands'] = {(r['category'], r['name'].casefold(), r['bucket']): r for r in document['bands']}
    item = from_listing(listings[0])
    assert assess(item, tables)['verdict'] == 'slow'
    assert assess({**item, 'properties': {'427': 3}}, tables)['verdict'] == 'vendor'
