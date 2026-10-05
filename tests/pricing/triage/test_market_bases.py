from inventory_tracking.items.metadata import metadata
from pricing.triage.market_bases import compile_market_bases
from tests.pricing.triage.test_bands import listing


def market_fixture():
    base = next(b for b in metadata()['bases'].values() if b['name'] == 'War Pike')
    rows = [
        listing(str(i), price)
        | {
            'category': 'base',
            'name': base['name'],
            'base_code': base['code'],
            'rarity': 'normal',
            'ethereal': True,
            'sockets': 4,
        }
        for i, price in enumerate((1, 2, 3))
    ]
    utility = [
        {
            'base_code': base['code'],
            'sockets': 4,
            'details': {'runeword': 'Infinity', 'legality': 'verified_type_and_capacity'},
        }
    ]
    return rows, utility


def compile_rows(rows, utility, rules=()):
    return compile_market_bases(rows, rules, [], utility, keep_ist=0.25, excluded_words={'Stealth'})


def test_market_base_admission_requires_independent_matched_sellers_and_legal_recipe():
    rows, utility = market_fixture()
    rules = compile_rows(rows, utility)
    assert len(rules) == 1
    assert rules[0]['evidence']['q1_ist'] == 1.5
    assert rules[0]['conditions']['ethereal'] is True
    assert rules[0]['runewords'] == ['Infinity']
    assert not compile_rows(rows[:1], utility)
    assert not compile_rows([r | {'seller_id': 'one'} for r in rows], utility)
    assert not compile_rows([rows[0] | {'ethereal': False}, rows[1]], utility)
    assert not compile_rows([r | {'ask_ist': 0.2} for r in rows], utility)
    assert not compile_rows(rows, [])
    assert not compile_rows(
        rows, [utility[0] | {'details': {'runeword': 'Stealth', 'legality': 'verified_type_and_capacity'}}]
    )
    assert not compile_rows(rows, utility, [{'category': 'base', 'name': 'War Pike', 'bucket': 'existing'}])
    # Regeneration does not count its previous output as pre-existing coverage.
    assert compile_rows(rows, utility, rules) == rules


def test_market_base_rejects_unknown_filled_affixed_or_conflicting_identity():
    rows, utility = market_fixture()
    for change in (
        {'sockets': None},
        {'rarity': None},
        {'socket_contents': 'filled'},
        {'rarity': 'magic'},
        {'amount': 2},
    ):
        assert not compile_rows([r | change for r in rows], utility)
    for props in ({'520': 35, '511': 2}, {'510': 16}, {'937': 15}):
        assert not compile_rows([r | {'properties': r['properties'] | props} for r in rows], utility)
    inferred = compile_rows([r | {'properties': r['properties'] | {'510': 15}} for r in rows], utility)
    assert len(inferred) == 1
    assert inferred[0]['conditions']['rarity'] == 'superior'
    assert inferred[0]['conditions']['base_ed_grade'] == 'perfect'
    armor = next(b for b in metadata()['bases'].values() if b['name'] == 'Archon Plate')
    conflicting = [r | {'base_code': armor['code']} for r in rows]
    armor_recipe = [
        {
            'base_code': armor['code'],
            'sockets': 4,
            'details': {'runeword': 'Fortitude', 'legality': 'verified_type_and_capacity'},
        }
    ]
    assert not compile_rows(conflicting, armor_recipe)


def test_market_rules_price_only_the_admitted_variant_and_use_scoped_bands():
    from pricing.triage.adapters import from_listing
    from pricing.triage.bands import build_bands
    from pricing.triage.engine import assess
    from pricing.triage.market_bases import FACETS

    rows, utility = market_fixture()
    rules = compile_rows(rows, utility)
    policies = [{'category': 'base', 'require_bucket': True, 'facets': FACETS}]
    bands = build_bands(rows, [], rules=rules, policies=policies)['bands']
    tables = {
        'rules': {'rows': rules, 'policies': policies, 'keep_ist': 0.25},
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in bands},
        'own': {'rows': []},
    }
    item = from_listing(rows[0])
    result = assess(item, tables)
    assert result['verdict'] == 'slow'
    assert result['band']['q1_ist'] == 1.5
    for change in (
        {'ethereal': False},
        {'ethereal': None},
        {'sockets': 0},
        {'rarity': 'superior'},
        {'base_modifiers': {'423': 3}},
    ):
        assert assess(item | change, tables)['band'] is None


def test_two_seller_base_variant_is_check_with_reference_price_not_vendor_or_sell():
    from pricing.triage.adapters import from_listing
    from pricing.triage.bands import build_bands
    from pricing.triage.engine import assess
    from pricing.triage.market_bases import FACETS

    rows, utility = market_fixture()
    rows = rows[:2]
    rules = compile_rows(rows, utility)
    assert len(rules) == 1
    policies = [{'category': 'base', 'require_bucket': True, 'facets': FACETS}]
    bands = build_bands(rows, [], rules=rules, policies=policies)['bands']
    tables = {
        'rules': {'rows': rules, 'policies': policies, 'keep_ist': 0.25},
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in bands},
        'own': {'rows': []},
    }
    item = from_listing(rows[0])
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert result['band'] is None
    assert result['decision_ist'] is None
    assert result['reference_band']['sellers'] == 2
    assert result['liquidity'] == 'none'
    assert 'reference' in result['reason']
    for change in ({'sockets': 3}, {'ethereal': False}, {'base_modifiers': {'423': 3}}):
        other = assess(item | change, tables)
        assert other['verdict'] == 'vendor'
        assert other['band'] is None
    assert not compile_rows(rows[:1], utility)
    assert not compile_rows([r | {'seller_id': 'one'} for r in rows], utility)


def test_market_base_better_superior_bonus_can_use_no_better_comparisons():
    from pricing.triage.adapters import from_listing
    from pricing.triage.bands import build_bands
    from pricing.triage.engine import assess
    from pricing.triage.market_bases import FACETS

    rows, utility = market_fixture()
    rows = [r | {'rarity': 'superior', 'properties': r['properties'] | {'510': 15, '423': 1}} for r in rows]
    policies = [
        {
            'category': 'base',
            'require_bucket': True,
            'facets': FACETS,
            'compare_modifiers': {'423': {'min': 1, 'max': 3, 'label': 'attack rating'}},
        }
    ]
    rules = compile_market_bases(rows, [], policies, utility, keep_ist=0.25, excluded_words=set())
    bands = build_bands(rows, [], rules=rules, policies=policies)['bands']
    tables = {
        'rules': {'rows': rules, 'policies': policies, 'keep_ist': 0.25},
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in bands},
        'own': {'rows': []},
    }
    item = from_listing(rows[0]) | {'base_modifiers': {'423': 3}}
    result = assess(item, tables)
    assert result['verdict'] == 'slow'
    assert result['decision_ist'] == 1.5
    assert result['band']['sellers'] == 3
    assert result['band']['cohort_depth'] == 0
    for change in ({'base_modifiers': {}}, {'base_modifiers': {'423': 3, '937': 15}}, {'ethereal': False}):
        assert assess(item | change, tables)['band'] is None


def test_market_base_combines_different_no_better_rolls_before_counting_sellers():
    from pricing.triage.adapters import from_listing
    from pricing.triage.bands import build_bands
    from pricing.triage.engine import assess
    from pricing.triage.market_bases import FACETS

    rows, utility = market_fixture()
    rows = [
        r | {'rarity': 'superior', 'properties': r['properties'] | {'510': 15, '423': bonus}}
        for bonus, r in enumerate(rows, 1)
    ]
    policies = [
        {
            'category': 'base',
            'require_bucket': True,
            'facets': FACETS,
            'compare_modifiers': {'423': {'min': 1, 'max': 3, 'label': 'attack rating'}},
        }
    ]
    rules = compile_market_bases(rows, [], policies, utility, keep_ist=0.25, excluded_words=set())
    assert len(rules) == 2
    bands = build_bands(rows, [], rules=rules, policies=policies)['bands']
    tables = {
        'rules': {'rows': rules, 'policies': policies, 'keep_ist': 0.25},
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in bands},
        'own': {'rows': []},
    }
    results = [assess(from_listing(r), tables) for r in rows]
    assert [r['verdict'] for r in results] == ['vendor', 'check', 'slow']
    assert results[-1]['band']['sellers'] == 3
    assert results[-1]['decision_ist'] == 1.5
    assert not compile_market_bases(
        [r | {'seller_id': 'one'} for r in rows], [], policies, utility, keep_ist=0.25, excluded_words=set()
    )


def test_native_all_resistance_projection_does_not_block_shield_base_admission():
    from pricing.triage.adapters import from_listing
    from pricing.triage.market_bases import clean_modifiers

    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Gilded Shield')
    rows = [
        listing(str(i), 1)
        | {
            'category': 'base',
            'name': base['name'],
            'base_code': base['code'],
            'rarity': 'normal',
            'ethereal': False,
            'sockets': 4,
        }
        for i in range(3)
    ]
    for r in rows:
        r['properties']['441'] = 40
    item = from_listing(rows[0])
    assert item['base_modifiers']['427'] == 40
    assert clean_modifiers(item, base, {})
    utility = [
        {
            'base_code': base['code'],
            'sockets': 4,
            'details': {'runeword': 'Spirit', 'legality': 'verified_type_and_capacity'},
        }
    ]
    rules = compile_rows(rows, utility)
    assert len(rules) == 1
    assert rules[0]['evidence']['sellers'] == 3
    assert not clean_modifiers(item | {'base_modifiers': item['base_modifiers'] | {'427': 50}}, base, {})
    assert not clean_modifiers(item | {'base_modifiers': item['base_modifiers'] | {'510': 60, '423': 110}}, base, {})
