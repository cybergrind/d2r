from pricing.triage.adapters import from_listing
from pricing.triage.bands import build_bands
from pricing.triage.engine import assess
from tests.pricing.triage.test_bands import listing


def row(seller, *, ed=15, sockets=4, ethereal=True, price=2):
    result = listing(seller, price) | {
        'name': 'Archon Plate',
        'category': 'base',
        'rarity': 'superior',
        'sockets': sockets,
        'ethereal': ethereal,
    }
    result['properties']['425'] = ed
    return result


def tables(rows):
    policy = {'category': 'base', 'require_bucket': True}
    doc = build_bands(rows, [], policies=[policy])
    return {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
        'rules': {'keep_ist': 0.25, 'rows': [], 'policies': [policy]},
        'own': {'rows': []},
    }


def test_native_shield_floor_keeps_identity_and_sockets_and_is_labelled():
    from inventory_tracking.appraisal.triage import headline

    rows = []
    for i, resistance in enumerate((10, 20, 30)):
        r = listing(str(i), 1 + i) | {
            'name': 'Sacred Rondache',
            'category': 'base',
            'rarity': 'normal',
            'sockets': 4,
            'ethereal': False,
        }
        r['properties']['441'] = resistance
        rows.append(r)
    item, data = from_listing(rows[-1]), tables(rows)
    result = assess(item, data)
    assert result['verdict'] == 'slow'
    assert result['decision_ist'] == 1.5
    assert result['band']['price_basis'] == 'base_floor'
    assert 'at least' in headline(result)
    weaker = from_listing(rows[0] | {'properties': rows[0]['properties'] | {'441': 5}})
    assert assess(weaker, data)['decision_ist'] is None
    unknown = from_listing(rows[0] | {'properties': {k: v for k, v in rows[0]['properties'].items() if k != '441'}})
    assert assess(unknown, data)['decision_ist'] is None
    damage = from_listing(rows[0] | {'properties': unknown['properties'] | {'510': 65, '423': 121}})
    assert assess(damage, data)['decision_ist'] is None
    for change in ({'sockets': 3}, {'ethereal': True}, {'rarity': None}, {'socket_contents': 'filled'}):
        assert assess(item | change, data)['decision_ist'] is None
    low = tables([r | {'ask_ist': 0.1} for r in rows])
    assert assess(item, low)['decision_ist'] is None


def test_base_floor_does_not_erase_staffmods_or_other_class_skills():
    from pricing.triage.import_bases import native_staffmod_policies

    policy = next(p for p in native_staffmod_policies([]) if p['name'] == 'War Scepter')
    skill = next(iter(policy['compare_staffmods']))
    rows = []
    for i in range(3):
        r = listing(str(i), 2) | {
            'name': 'War Scepter',
            'category': 'base',
            'rarity': 'normal',
            'sockets': 3,
            'ethereal': False,
        }
        r['properties'][skill] = i + 1
        rows.append(r)
    assert assess(from_listing(rows[-1]), tables(rows))['decision_ist'] is None


def test_superior_base_can_use_plain_floor_but_plain_cannot_borrow_superior_price():
    rows = [row(str(i), ed=0, sockets=4, price=2) | {'rarity': 'normal'} for i in range(3)]
    superior = from_listing(row('target', ed=15, sockets=4))
    result = assess(superior, tables(rows))
    assert result['decision_ist'] == 2
    assert result['band']['price_basis'] == 'base_floor'
    assert result['band']['sellers'] == 3
    for change in ({'sockets': 3}, {'ethereal': False}, {'rarity': None}):
        assert assess(superior | change, tables(rows))['decision_ist'] is None
    premium_rows = [row(str(i), ed=15, price=20) for i in range(3)]
    assert assess(from_listing(rows[0]), tables(premium_rows))['decision_ist'] is None


def test_base_without_authored_bucket_uses_first_supported_fallback_level():
    exact = [row(str(i), price=10) for i in range(3)]
    other_ed = [row(str(i + 3), ed=10, price=1) for i in range(3)]
    other_socket = [row(str(i + 6), ed=10, sockets=3, price=0.1) for i in range(3)]
    target = from_listing(exact[0])
    assert assess(target, tables(exact + other_ed + other_socket))['decision_ist'] == 10
    result = assess(target, tables(exact[:1] + other_ed + other_socket))
    assert result['decision_ist'] == 1
    assert result['band']['relaxed_facets'] == ['base_ed']
    result = assess(target, tables(exact[:1] + other_socket))
    assert result['decision_ist'] == 0.1
    assert result['verdict'] == 'vendor'
    assert result['band']['relaxed_facets'] == ['base_ed', 'sockets']


def test_base_fallback_never_borrows_ethereal_modifiers_filled_or_foreign_scope():
    rows = [row(str(i)) for i in range(3)]
    data = tables(rows)
    target = from_listing(rows[0])
    for change in (
        {'ethereal': False},
        {'ethereal': None},
        {'sockets': 5},
        {'base_modifiers': {'441': 45}},
        {'socket_contents': 'filled', 'empty_sockets': False},
        {'rarity': 'magic'},
    ):
        assert assess(target | change, data)['decision_ist'] is None
    foreign = [r | {'properties': r['properties'] | {'800': True}} for r in rows]
    assert assess(target, tables(foreign))['decision_ist'] is None
    repeated_seller = [r | {'seller_id': 'same'} for r in rows]
    assert assess(target, tables(repeated_seller))['decision_ist'] is None


def test_guide_listed_base_with_missing_or_sparse_variant_evidence_is_check():
    target = from_listing(row('target'))
    for rows in ([], [row('one')], [row('one'), row('two')]):
        data = tables(rows)
        data['rules']['rows'] = [
            {
                'category': 'base',
                'name': 'Archon Plate',
                'bucket': 'guide',
                'source': 'guides/pricing-primer.html#s2',
                'conditions': {'sockets': 3},
            }
        ]
        result = assess(target, data)
        assert result['verdict'] == 'check'
        assert result['decision_ist'] is None
        assert 'sockets' in result['reason']
        unknown = assess(target | {'ethereal': None}, data)
        assert unknown['verdict'] == 'check'
        assert 'ethereal status' in unknown['reason']


def test_fallback_pools_sparse_superior_secondary_rolls_but_keeps_supported_premiums():
    rows = [row(str(i)) for i in range(3)]
    for i, r in enumerate(rows):
        r['properties']['937'] = 10 + i
    target = from_listing(rows[0])
    result = assess(target, tables(rows))
    assert result['decision_ist'] == 2
    assert result['band']['sellers'] == 3
    # A paid durability distinction still needs its own three-seller support.
    rows = [row(str(i), price=1 if i < 3 else 10) for i in range(6)]
    for i, r in enumerate(rows):
        r['properties']['937'] = 10 if i < 3 else 15
    data = tables(rows)
    assert assess(from_listing(rows[0]), data)['decision_ist'] == 1
    assert assess(from_listing(rows[-1]), data)['decision_ist'] == 10
    assert assess(target | {'base_modifiers': {'937': 10, '441': 45}}, data)['decision_ist'] is None


def test_native_staffmod_listings_do_not_require_a_curated_price_policy():
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.adapters.market_projection import market_properties

    meta, projection = metadata(), market_properties()

    def prop(name):
        skill = next(k for k, v in meta['skills'].items() if v['name'] == name)
        return projection['107:' + skill]

    hammer, concentration, sorceress = map(prop, ('Blessed Hammer', 'Concentration', 'Fire Ball'))
    rows = [
        listing(str(i), 2)
        | {'name': 'War Scepter', 'category': 'base', 'rarity': 'normal', 'sockets': 5, 'ethereal': False}
        for i in range(3)
    ]
    for r in rows:
        r['properties'].update({hammer: 3, concentration: 2})
    result = assess(from_listing(rows[0]), tables(rows))
    assert result['decision_ist'] == 2
    for extra in ({sorceress: 3}, {'520': 20}, {hammer: 4}, {prop('Vigor'): 1, prop('Zeal'): 1}):
        invalid = [r | {'properties': r['properties'] | extra} for r in rows]
        assert assess(from_listing(invalid[0]), tables(invalid))['decision_ist'] is None
    changed = from_listing(rows[0] | {'properties': rows[0]['properties'] | {concentration: 1}})
    assert assess(changed, tables(rows))['decision_ist'] is None


def test_missing_ed_sources_participate_only_after_ed_is_relaxed():
    rows = [row(str(i), ed=5 + i, price=2) for i in range(3)]
    target = from_listing(rows[0]) | {'base_ed': None, 'base_ed_grade': None}
    result = assess(target, tables(rows))
    assert result['decision_ist'] == 2
    assert result['band']['relaxed_facets'] == ['base_ed']
    assert target['base_ed'] is None
    incomplete = [r | {'properties': {k: v for k, v in r['properties'].items() if k != '425'}} for r in rows]
    sparse = assess(target, tables(incomplete))
    assert sparse['decision_ist'] == 2
    assert sparse['band']['relaxed_facets'] == ['base_ed']
    assert all(from_listing(r)['base_ed'] is None for r in incomplete)
    exact = [row('exact-' + str(i), ed=15, price=100) for i in range(2)]
    mixed = assess(from_listing(exact[0]), tables(exact + incomplete))
    assert mixed['band']['relaxed_facets'] == ['base_ed']
    assert mixed['band']['sellers'] == 5
    assert mixed['decision_ist'] == 2
    assert assess(target | {'ethereal': None}, tables(rows))['decision_ist'] is None
    assert assess(target | {'base_ed': 99}, tables(rows))['decision_ist'] is None


def test_superior_weapon_cannot_have_three_quality_bonuses():
    rows = [
        listing(str(i), 2)
        | {'name': 'Flail', 'category': 'base', 'rarity': 'superior', 'sockets': 4, 'ethereal': False}
        for i in range(3)
    ]
    for r in rows:
        r['properties'].update({'510': 15, '423': 3, '937': 15})
    assert assess(from_listing(rows[0]), tables(rows))['decision_ist'] is None
    # Target validation must agree with source admission, even after ED is relaxed.
    clean = [r | {'properties': {k: v for k, v in r['properties'].items() if k != '937'}} for r in rows]
    assert assess(from_listing(rows[0]), tables(clean))['decision_ist'] is None


def test_relaxed_ed_keeps_same_skill_pattern_and_uses_only_no_better_rolls():
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.adapters.market_projection import market_properties

    meta = metadata()
    base = next(b for b in meta['bases'].values() if b['name'] == 'War Scepter')
    skill = next(k for k, v in meta['skills'].items() if v['name'] == 'Blessed Hammer')
    prop = market_properties()['107:' + skill]
    rows = []
    for i in range(3):
        r = listing(str(i), 2) | {
            'name': base['name'],
            'base_code': base['code'],
            'category': 'base',
            'rarity': 'superior',
            'ethereal': False,
            'sockets': 5,
        }
        r['properties'].update({'510': 5 + i, prop: 1 + i})
        rows.append(r)
    policy = {'category': 'base', 'require_bucket': True, 'compare_staffmods': {prop: 'Blessed Hammer'}}
    doc = build_bands(rows, [], policies=[policy])
    data = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
        'rules': {'keep_ist': 0.25, 'rows': [], 'policies': [policy]},
        'own': {'rows': []},
    }
    target = from_listing(rows[-1])
    result = assess(target, data)
    assert result['decision_ist'] == 2
    assert result['band']['relaxed_facets'] == ['base_ed']
    assert result['band']['sellers'] == 3
    assert assess(from_listing(rows[0]), data)['decision_ist'] is None
    assert assess(target | {'base_modifiers': {}}, data)['decision_ist'] is None
    assert assess(target | {'ethereal': True}, data)['decision_ist'] is None
    socket_target = target | {'sockets': 4}
    assert assess(socket_target, data)['band']['relaxed_facets'] == ['base_ed', 'sockets']


def test_shield_all_resistance_comparison_changes_linked_elements_together():
    from inventory_tracking.items.metadata import metadata
    from pricing.triage.import_bases import native_shield_rules

    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Sacred Targe')
    rows = []
    for i, roll in enumerate((37, 40, 43)):
        r = listing(str(i), 1 + i) | {
            'category': 'base',
            'name': base['name'],
            'base_code': base['code'],
            'rarity': 'normal',
            'sockets': 4,
            'ethereal': False,
        }
        r['properties']['441'] = roll
        rows.append(r)
    _, policies = native_shield_rules()
    doc = build_bands(rows, [], policies=policies)
    data = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
        'rules': {'keep_ist': 0.25, 'rows': [], 'policies': policies},
        'own': {'rows': []},
    }
    high = from_listing(rows[-1])
    assert assess(high, data)['decision_ist'] == 1.5
    low = assess(from_listing(rows[0]), data)
    assert low['decision_ist'] is None  # one lower-roll seller cannot borrow the 40/43 premiums
    changed = from_listing(rows[-1] | {'properties': rows[-1]['properties'] | {'427': 44}})
    assert assess(changed, data)['decision_ist'] is None
    assert assess(high | {'ethereal': True}, data)['decision_ist'] is None


def test_catalog_spelling_uses_verified_base_code_for_fallback_mechanics():
    from inventory_tracking.items.metadata import metadata

    for native, catalog in (('Kriss', 'Kris'), ('Stilleto', 'Stiletto')):
        code = next(b['code'] for b in metadata()['bases'].values() if b['name'] == native)
        rows = [
            listing(str(i), 2)
            | {
                'category': 'base',
                'name': catalog,
                'base_code': code,
                'rarity': 'normal',
                'ethereal': False,
                'sockets': 3,
            }
            for i in range(3)
        ]
        target = from_listing(rows[0])
        result = assess(target, tables(rows))
        assert result['decision_ist'] == 2
        assert result['band']['sellers'] == 3
        assert assess(target | {'sockets': 4}, tables(rows))['decision_ist'] is None
        unknown = [r | {'base_code': 'not-a-native-code'} for r in rows]
        assert assess(from_listing(unknown[0]), tables(unknown))['decision_ist'] is None
        other_code = next(b['code'] for b in metadata()['bases'].values() if b['name'] == 'Bone Knife')
        conflicting = [*rows[:2], rows[2] | {'base_code': other_code}]
        assert assess(target, tables(conflicting))['decision_ist'] is None


def test_base_name_cannot_price_rows_carrying_another_native_identity():
    from inventory_tracking.items.metadata import metadata

    code = next(b['code'] for b in metadata()['bases'].values() if b['name'] == 'Crystal Sword')
    rows = [
        listing(str(i), 2)
        | {
            'category': 'base',
            'name': 'Phase Blade',
            'base_code': code,
            'rarity': 'normal',
            'ethereal': False,
            'sockets': 3,
        }
        for i in range(3)
    ]
    assert assess(from_listing(rows[0]), tables(rows))['decision_ist'] is None


def test_unsocketed_staffmod_candidate_does_not_borrow_socketed_price():
    from pricing.triage.guide_cases import item_from_spec

    rows = [
        listing(str(i), 2)
        | {
            'name': 'Fanged Helm',
            'category': 'base',
            'rarity': 'superior',
            'sockets': 3,
            'ethereal': False,
        }
        for i in range(3)
    ]
    for r in rows:
        r['properties']['765'] = 3
    target = item_from_spec(
        {
            'base': 'Fanged Helm',
            'rarity': 'superior',
            'sockets': 0,
            'ethereal': False,
            'stats': {'107:149': 3},
            'item_level': 25,
        }
    )
    assert assess(target, tables(rows))['decision_ist'] is None
    unsocketed = [r | {'sockets': 0} for r in rows]
    result = assess(target, tables(unsocketed))
    assert result['decision_ist'] == 2
    assert result['band']['relaxed_facets'] == ['base_ed']


def test_superior_floor_combines_sellers_without_lending_premiums_to_ordinary():
    rows = [
        row('ordinary', ed=0, price=1) | {'rarity': 'normal'},
        row('superior-a', ed=10, price=2),
        row('superior-b', ed=15, price=3),
    ]
    data = tables(rows)
    result = assess(from_listing(row('target', ed=15)), data)
    assert result['verdict'] == 'slow'
    assert result['band']['sellers'] == 3
    assert result['band']['price_basis'] == 'base_floor'
    assert assess(from_listing(rows[0]), data)['decision_ist'] is None
    # At 12 ED only two source sellers are comparable-or-worse.
    assert assess(from_listing(row('target', ed=12)), data)['decision_ist'] is None


def test_same_socket_plain_floor_precedes_different_socket_fallback():
    ordinary = [row(str(i), ed=0, sockets=4, price=2) | {'rarity': 'normal'} for i in range(3)]
    other_sockets = [row('other-' + str(i), ed=15, sockets=3, price=0.1) for i in range(3)]
    target = from_listing(row('target', ed=15, sockets=4))
    result = assess(target, tables(ordinary + other_sockets))
    assert result['verdict'] == 'slow'
    assert result['decision_ist'] == 2
    assert result['band']['price_basis'] == 'base_floor'
    # A supported exact superior cohort still wins over the plain-base floor.
    exact = [row('exact-' + str(i), ed=15, sockets=4, price=4) for i in range(3)]
    assert assess(target, tables(ordinary + other_sockets + exact))['decision_ist'] == 4


def test_total_weapon_damage_header_does_not_fragment_clean_base_sellers():
    rows = [
        listing(str(i), 2)
        | {
            'category': 'base',
            'name': 'Cryptic Axe',
            'rarity': 'normal',
            'sockets': 4,
            'ethereal': True,
        }
        for i in range(3)
    ]
    for r in rows[1:]:
        r['properties']['551'] = 225  # Traderie label: Two-Hand Damage, not a damage affix.
    target = from_listing(rows[0])
    result = assess(target, tables(rows))
    assert result['decision_ist'] == 2
    assert result['band']['sellers'] == 3
    observed = from_listing(rows[1])
    assert observed['properties']['551'] == 225
    assert observed['base_modifiers'] == {}
    assert assess(observed, tables(rows))['decision_ist'] == 2
    # A true flat damage affix still excludes the listing from clean-base prices.
    invalid = [r | {'properties': r['properties'] | {'448': 3}} for r in rows]
    assert assess(target, tables(invalid))['decision_ist'] is None


def test_amazon_inherent_skills_use_lower_rolls_without_lending_high_roll_premiums():
    for name, prop in (('Matriarchal Bow', '454'), ('Matriarchal Spear', '456')):
        rows = []
        for i in range(3):
            r = listing(str(i), 2 + i) | {
                'category': 'base',
                'name': name,
                'rarity': 'normal',
                'sockets': 4,
                'ethereal': False,
            }
            r['properties'][prop] = i + 1
            rows.append(r)
        data = tables(rows)
        result = assess(from_listing(rows[-1]), data)
        assert result['decision_ist'] == 2.5
        assert result['band']['sellers'] == 3
        assert result['band']['comparison']['rolls'] == {prop: 3}
        for r in rows[:2]:
            assert assess(from_listing(r), data)['decision_ist'] is None
        for change in ({'base_modifiers': {}}, {'ethereal': True}, {'socket_contents': 'filled'}):
            assert assess(from_listing(rows[-1]) | change, data)['decision_ist'] is None


def test_superior_ed_floor_uses_lower_rolls_and_labels_the_floor():
    from inventory_tracking.appraisal.triage import headline

    rows = [row(str(i), ed=10, price=2) for i in range(3)]
    rows += [row(str(i + 3), ed=15, price=20) for i in range(3)]
    result = assess(from_listing(row('target', ed=12)), tables(rows))
    assert result['decision_ist'] == 2
    assert result['band']['price_basis'] == 'base_floor'
    assert 'at least' in headline(result)


def test_superior_staffmod_base_inherits_only_identical_normal_staffmods():
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.adapters.market_projection import market_properties

    skill = next(k for k, v in metadata()['skills'].items() if v['name'] == 'Blessed Hammer')
    prop = market_properties()['107:' + skill]
    rows = [
        listing(str(i), 2)
        | {'name': 'War Scepter', 'category': 'base', 'rarity': 'normal', 'sockets': 5, 'ethereal': False}
        for i in range(3)
    ]
    for r in rows:
        r['properties'][prop] = 3
    superior = rows[0] | {'rarity': 'superior', 'properties': rows[0]['properties'] | {'510': 15}}
    result = assess(from_listing(superior), tables(rows))
    assert result['decision_ist'] == 2
    assert result['band']['price_basis'] == 'base_floor'
    weaker = superior | {'properties': superior['properties'] | {prop: 2}}
    assert assess(from_listing(weaker), tables(rows))['decision_ist'] is None


def test_ed_floor_prefers_nearest_supported_lower_band_over_pooled_cheap_rolls():
    rows = [row(str(i), ed=5, price=1) for i in range(3)]
    rows += [row(str(i + 3), ed=10, price=10) for i in range(3)]
    assert assess(from_listing(row('target', ed=12)), tables(rows))['decision_ist'] == 10


def test_unknown_superior_ed_can_use_zero_bonus_floor_without_inventing_ed():
    from inventory_tracking.appraisal.triage import headline

    ordinary = [row(str(i), ed=0, price=2) | {'rarity': 'normal'} for i in range(3)]
    source = row('target')
    source['properties'].pop('425')
    target = from_listing(source)
    assert target['base_ed'] is None
    result = assess(target, tables(ordinary))
    assert result['decision_ist'] == 2
    assert result['band']['price_basis'] == 'base_floor'
    assert 'at least' in headline(result)
    assert target['base_ed'] is None
    for change in ({'sockets': 3}, {'ethereal': False}, {'rarity': None}):
        assert assess(target | change, tables(ordinary))['decision_ist'] is None
