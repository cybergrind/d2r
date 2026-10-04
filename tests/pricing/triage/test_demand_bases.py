from pricing.triage.import_bases import demand_rules


def test_demand_bases_use_documented_socket_counts_and_skip_existing_or_leveling_only():
    demand = {
        'War Pike': {'sockets_by_runeword': {'Breath of the Dying': 6}},
        'Archon Staff': {'sockets_by_runeword': {'Obsession': 6}},
        'Leather Armor': {'sockets_by_runeword': {'Stealth': 2}},
        'Archon Plate': {'sockets_by_runeword': {'Enigma': 3}},
        'Unknown base': {'sockets_by_runeword': {'Obsession': 6}},
    }
    rows, policies = demand_rules(demand, {'Archon Plate': {3}})
    assert {r['name'] for r in rows} == {'War Pike', 'Archon Staff'}
    assert all(r['conditions']['sockets'] == 6 for r in rows)
    assert all(r['conditions']['empty_sockets'] is True for r in rows)
    assert all('base_modifiers' in p['facets'] for p in policies)
    assert all('base_ed_grade' in p['facets'] for p in policies)


def test_ordinary_ed_rolls_share_band_but_perfect_and_unknown_do_not():
    from pricing.triage.adapters import from_listing
    from pricing.triage.bands import build_bands
    from pricing.triage.engine import assess
    from tests.pricing.triage.test_bands import listing

    rules, policies = demand_rules({'War Pike': {'sockets_by_runeword': {'Breath of the Dying': 6}}}, {})
    rows = []
    for i, (ed, price) in enumerate([(5, 0.5), (11, 1), (14, 1.5), (15, 100), (15, 100), (15, 100)]):
        row = listing(str(i), price) | {
            'category': 'base',
            'name': 'War Pike',
            'rarity': 'superior',
            'sockets': 6,
            'ethereal': True,
        }
        row['properties']['510'] = ed
        rows.append(row)
    doc = build_bands(rows, [], rules=rules, policies=policies)
    tables = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
        'rules': {'keep_ist': 0.25, 'rows': rules, 'policies': policies},
        'own': {'rows': []},
    }
    ordinary = assess(from_listing(rows[0]), tables)
    assert ordinary['verdict'] == 'slow'
    assert ordinary['band']['sellers'] == 3
    assert ordinary['band']['q1_ist'] == 0.75
    assert assess(from_listing(rows[-1]), tables)['band']['q1_ist'] == 100
    missing = rows[0] | {'properties': {k: v for k, v in rows[0]['properties'].items() if k != '510'}}
    assert assess(from_listing(missing), tables)['band'] is None


def test_demand_prose_cannot_authorize_an_incompatible_or_unknown_recipe():
    rows, _ = demand_rules(
        {
            'Ward': {'sockets_by_runeword': {'Venom': 3}},
            'War Pike': {'sockets_by_runeword': {'Breath of the Dying': 5}},
            "Hunter's Bow": {'sockets_by_runeword': {'Hustle': 3, 'Unverified word': 3}},
        },
        {},
    )
    assert [(r['name'], r['runewords']) for r in rows] == [("Hunter's Bow", ['Hustle'])]


def test_existing_socket_pattern_does_not_hide_another_documented_recipe():
    rows, _ = demand_rules({'Archon Staff': {'sockets_by_runeword': {'Obsession': 6}}}, {'Archon Staff': {4}})
    assert len(rows) == 1
    assert rows[0]['conditions']['sockets'] == 6


def test_all_build_variants_supply_missing_legal_base_recipes():
    from pricing.triage.import_bases import build_demand

    document = {
        'variants': [
            {'player': {'Helmet': ['Dream Bone Visage']}, 'mercenary': {'Weapon': ['Infinity Mancatcher (ethereal)']}},
            {'player': {'Helmet': ['Dream Bone Visage'], 'Weapon': ['Dream Phase Blade']}},
        ]
    }
    demand = build_demand(document, 'cached-builds.json')
    assert demand['Bone Visage']['sockets_by_runeword'] == {'Dream': 3}
    assert demand['Mancatcher']['sockets_by_runeword'] == {'Infinity': 4}
    assert 'Phase Blade' not in demand
    rows, _ = demand_rules(demand, {})
    assert {r['name'] for r in rows} == {'Bone Visage', 'Mancatcher'}
    assert all(r['source'].startswith('cached-builds.json#') for r in rows)


def test_build_base_import_skips_generic_starter_variants_but_keeps_uber_mercenary_gear():
    from pricing.triage.import_bases import build_demand

    document = {
        'variants': [
            {'name': 'Starter', 'merc': {'Weapon': ['Insight Poleaxe']}},
            {'name': 'Ubers', 'merc': {'Off-Hand': ['Malice Mythical Sword (ethereal)']}},
        ]
    }
    demand = build_demand(document, 'cached-builds.json')
    assert 'Poleaxe' not in demand
    assert demand['Mythical Sword']['sockets_by_runeword'] == {'Malice': 3}


def test_superior_secondary_rolls_merge_without_a_supported_price_split():
    from pricing.triage.adapters import from_listing
    from pricing.triage.bands import build_bands
    from pricing.triage.engine import assess
    from tests.pricing.triage.test_bands import listing

    rules, policies = demand_rules({'War Pike': {'sockets_by_runeword': {'Breath of the Dying': 6}}}, {})
    policies[0]['compare_modifiers'] = {'937': {'min': 10, 'max': 15, 'label': 'maximum durability'}}
    rows = []
    for i, (durability, price) in enumerate([(10, 1), (11, 2), (12, 3), (15, 100)]):
        row = listing(str(i), price) | {
            'category': 'base',
            'name': 'War Pike',
            'rarity': 'superior',
            'sockets': 6,
            'ethereal': True,
        }
        row['properties'].update({'510': 15, '937': durability})
        rows.append(row)
    doc = build_bands(rows, [], rules=rules, policies=policies)
    tables = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
        'rules': {'keep_ist': 0.25, 'rows': rules, 'policies': policies},
        'own': {'rows': []},
    }
    result = assess(from_listing(rows[2]), tables)
    assert result['verdict'] == 'slow'
    assert result['band']['q1_ist'] == 1.75
    assert result['band']['sellers'] == 4
    assert assess(from_listing(rows[0]), tables)['verdict'] == 'slow'
    absent = from_listing(rows[2] | {'properties': {'510': 15}})
    assert assess(absent, tables)['decision_ist'] == 1.75
    target = from_listing(rows[2] | {'properties': {'510': 15, '937': 12, '423': 3}})
    assert assess(target, tables)['band'] is None
