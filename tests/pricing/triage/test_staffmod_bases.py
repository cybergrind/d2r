from pricing.triage.adapters import from_listing
from pricing.triage.bands import build_bands
from pricing.triage.engine import assess
from pricing.triage.import_bases import staffmod_rules
from tests.pricing.triage.test_bands import listing


def test_void_base_bands_keep_staffmods_ethereal_and_quality_distinct():
    rules, policies = staffmod_rules()
    rows = []
    for index, (props, price) in enumerate([({}, 0.1), ({'1579': 3}, 10)]):
        for seller in range(3):
            row = listing(f'{index}-{seller}', price) | {
                'category': 'base',
                'name': 'Kris',
                'rarity': 'normal',
                'sockets': 3,
            }
            row['properties'].update(props)
            rows.append(row)
    doc = build_bands(rows, [], rules=rules, policies=policies)
    tables = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
        'rules': {'keep_ist': 0.25, 'rows': rules, 'policies': policies},
        'own': {'rows': []},
    }
    plain, abyss = from_listing(rows[0]), from_listing(rows[-1])
    assert assess(plain, tables)['verdict'] == 'vendor'
    assert assess(plain, tables)['band']['q1_ist'] == 0.1
    assert assess(abyss, tables)['band']['q1_ist'] == 10
    assert assess(abyss | {'sockets': 2}, tables)['decision_ist'] == 10
    for change in (
        {'sockets': None},
        {'ethereal': True},
        {'rarity': 'magic'},
        {'socket_contents': 'filled'},
        {'base_modifiers': {'1579': 2}},
    ):
        assert assess(abyss | change, tables)['band'] is None


def test_staffmod_comparisons_include_lower_rolls_but_not_different_skill_sets():
    rules, policies = staffmod_rules()
    rows = []
    for i, (roll, price) in enumerate([(1, 1), (2, 2), (2, 3), (3, 100)]):
        row = listing(str(i), price) | {'category': 'base', 'name': 'Kris', 'rarity': 'normal', 'sockets': 3}
        row['properties']['1579'] = roll
        rows.append(row)
    extra = rows[0] | {
        'listing_id': 'extra',
        'seller_id': 'extra',
        'ask_ist': 0.01,
        'properties': rows[0]['properties'] | {'1565': 3},
    }
    doc = build_bands([*rows, extra], [], rules=rules, policies=policies)
    data = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
        'rules': {'keep_ist': 0.25, 'rows': rules, 'policies': policies},
        'own': {'rows': []},
    }
    item = from_listing(rows[1])
    result = assess(item, data)
    assert result['verdict'] == 'slow'
    assert result['band']['sellers'] == 3
    assert result['band']['q1_ist'] == 1.5
    from inventory_tracking.appraisal.triage import headline

    assert 'comparable-or-worse +2 Abyss' in headline(result)
    assert assess(from_listing(rows[0]), data)['verdict'] == 'check'


def test_white_grimoire_requires_paid_skill_and_two_empty_sockets():
    from pricing.triage.engine import matches

    rules, policies = staffmod_rules()
    row = listing('grimoire', 1) | {'category': 'base', 'name': 'Occult Codex', 'rarity': 'normal', 'sockets': 2}
    row['properties']['1558'] = 3  # Consume, verified appraisal-properties.json label.
    item = from_listing(row)
    relevant = [r for r in rules if matches(item, r)]
    assert relevant
    doc = build_bands(
        [row | {'seller_id': str(i), 'listing_id': str(i)} for i in range(3)], [], rules=rules, policies=policies
    )
    data = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
        'rules': {'keep_ist': 0.25, 'rows': rules, 'policies': policies},
        'own': {'rows': []},
    }
    assert assess(item, data)['verdict'] == 'slow'
    weak = from_listing(row | {'properties': row['properties'] | {'1558': 2}})
    assert assess(weak, data)['verdict'] == 'check'
    assert 'Consume 2 of 3' in assess(weak, data)['reason']
    for props in ({}, {'1555': 3}):  # no skills or unpaid Blood Oath alone
        assert assess(from_listing(row | {'properties': props}), data)['verdict'] == 'vendor'
    assert assess(item | {'sockets': 1}, data)['decision_ist'] == 1
    for change in ({'sockets': None}, {'socket_contents': 'filled', 'empty_sockets': False}):
        assert assess(item | change, data)['verdict'] == 'vendor'


def test_strong_grimoire_price_includes_lower_listed_rolls_of_its_paid_pattern():
    rules, policies = staffmod_rules()
    rows = []
    for i, (roll, price) in enumerate([(1, 1), (2, 2), (2, 3), (3, 100)]):
        row = listing(str(i), price) | {'category': 'base', 'name': 'Occult Codex', 'rarity': 'normal', 'sockets': 2}
        row['properties']['1558'] = roll
        rows.append(row)
    wrong = rows[0] | {
        'listing_id': 'wrong',
        'seller_id': 'wrong',
        'ask_ist': 0.01,
        'properties': rows[0]['properties'] | {'1559': 3},
    }
    doc = build_bands([*rows, wrong], [], rules=rules, policies=policies)
    tables = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
        'rules': {'keep_ist': 0.25, 'rows': rules, 'policies': policies},
        'own': {'rows': []},
    }
    result = assess(from_listing(rows[-1]), tables)
    assert result['verdict'] == 'slow'
    assert result['band']['sellers'] == 4
    assert result['band']['q1_ist'] == 1.75
    # Three no-better sellers price the weaker roll without borrowing the +3 premium.
    lower = assess(from_listing(rows[1]), tables)
    assert lower['verdict'] == 'slow'
    assert lower['band']['sellers'] == 3
    assert lower['decision_ist'] == 1.5


def test_battle_orders_base_family_covers_tiers_with_socket_and_skill_boundaries():
    rules, policies = staffmod_rules()
    for name in ('Fanged Helm', 'Slayer Guard', 'Guardian Crown'):
        row = listing(name, 1) | {'category': 'base', 'name': name, 'rarity': 'normal', 'sockets': 3}
        row['properties']['765'] = 3  # Barbarian Battle Orders, not the oskill.
        doc = build_bands(
            [row | {'listing_id': str(i), 'seller_id': str(i)} for i in range(3)], [], rules=rules, policies=policies
        )
        tables = {
            'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
            'rules': {'keep_ist': 0.25, 'rows': rules, 'policies': policies},
            'own': {'rows': []},
        }
        item = from_listing(row)
        assert assess(item, tables)['verdict'] == 'slow'
        weak = from_listing(row | {'properties': row['properties'] | {'765': 2}})
        assert assess(weak, tables)['verdict'] == 'check'
        assert 'Battle Orders 2 of 3' in assess(weak, tables)['reason']
        assert assess(item | {'sockets': 2}, tables)['decision_ist'] == 1
        # Unsocketed preparation cannot inherit an already socketed price.
        assert assess(item | {'sockets': 0}, tables)['decision_ist'] is None
        for change in (
            {'sockets': None},
            {'socket_contents': 'filled', 'empty_sockets': False},
        ):
            assert assess(item | change, tables)['verdict'] == 'vendor'
        for props in ({}, {'1203': 3}):
            assert assess(from_listing(row | {'properties': props}), tables)['verdict'] == 'vendor'
        assert assess(item | {'ethereal': True}, tables)['band'] is None


def test_three_socket_claw_paid_skill_pattern_keeps_other_gates():
    from pricing.triage.engine import matches
    from pricing.triage.import_bases import staffmod_rules

    rows, policies = staffmod_rules()
    candidates = [r for r in rows if r['name'] == 'Runic Talons' and r.get('properties', {}).get('1073') == 3]
    assert candidates
    rule = candidates[0]
    item = {
        'category': 'base',
        'name': 'Runic Talons',
        'rarity': 'normal',
        'sockets': 3,
        'empty_sockets': True,
        'base_ed': 0,
        'properties': {'1073': 3},
    }
    assert matches(item, rule)
    for changes in ({'sockets': 2}, {'empty_sockets': False}, {'rarity': 'magic'}, {'properties': {'1073': 1}}):
        assert not matches(item | changes, rule)
    assert matches(item | {'properties': {'1073': 1}}, rule | rule['pattern'])
    policy = next(p for p in policies if p.get('name') == 'Runic Talons')
    assert 'base_modifiers' in policy['facets']
    assert policy['compare_staffmods']['1073'] == 'Lightning Sentry'


def test_caster_base_patterns_require_recipe_sockets_and_paid_skill():
    from pricing.triage.engine import matches
    from pricing.triage.import_bases import staffmod_rules

    rows, _ = staffmod_rules()
    for name, sockets, prop in [('Bone Wand', 2, '756'), ('Gnarled Staff', 4, '679')]:
        candidates = [r for r in rows if r['name'] == name and r.get('properties', {}).get(prop) == 3]
        assert candidates
        rule = candidates[0]
        item = {
            'category': 'base',
            'name': name,
            'rarity': 'normal',
            'sockets': sockets,
            'empty_sockets': True,
            'base_ed': 0,
            'properties': {prop: 3},
        }
        assert matches(item, rule)
        assert not matches(item | {'sockets': sockets - 1}, rule)
        assert not matches(item | {'properties': {}}, rule)
        assert not matches(item | {'rarity': 'magic'}, rule)
    assert not any(r.get('bucket') == 'white-wand:756' and r['name'] == 'Wand' for r in rows)


def test_tornado_and_find_item_bases_keep_skill_socket_and_price_boundaries():
    from inventory_tracking.items.metadata import metadata

    rules, policies = staffmod_rules()
    bases = {b['name']: b for b in metadata()['bases'].values()}
    for name, skill, unpaid in [('Antlers', '972', '975'), ('Destroyer Helm', '993', '997')]:
        row = listing(name, 1) | {
            'category': 'base',
            'name': name,
            'base_code': bases[name]['code'],
            'rarity': 'normal',
            'sockets': 3,
        }
        row['properties'][skill] = 3
        doc = build_bands(
            [row | {'listing_id': str(i), 'seller_id': str(i)} for i in range(3)],
            [],
            rules=rules,
            policies=policies,
        )
        tables = {
            'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
            'rules': {'keep_ist': 0.25, 'rows': rules, 'policies': policies},
            'own': {'rows': []},
        }
        result = assess(from_listing(row), tables)
        assert result['verdict'] == 'slow'
        assert result['band']['q1_ist'] == 1
        weak = from_listing(row | {'properties': row['properties'] | {skill: 2}})
        assert assess(weak, tables)['verdict'] == 'check'
        for props in ({}, {unpaid: 3}):
            assert assess(from_listing(row | {'properties': props}), tables)['verdict'] == 'vendor'
        assert assess(from_listing(row | {'sockets': 2}), tables)['decision_ist'] == 1
        for change in ({'sockets': None}, {'socket_contents': 'filled'}):
            assert assess(from_listing(row | change), tables)['verdict'] == 'vendor'
        assert assess(from_listing(row | {'ethereal': True}), tables)['band'] is None


def test_caster_base_patterns_use_full_socket_and_skill_requirements():
    from inventory_tracking.items.metadata import metadata

    rules, policies = staffmod_rules()
    bases = {b['name']: b for b in metadata()['bases'].values()}
    for name, sockets, prop in [
        ('War Staff', 5, '679'),
        ('Antlers', 3, '971'),
        ('Sky Spirit', 3, '976'),
        ('Tome', 2, '1554'),
        ('Tome', 2, '1578'),
        ('Tome', 2, '1579'),
    ]:
        row = listing(name, 1) | {
            'category': 'base',
            'name': name,
            'base_code': bases[name]['code'],
            'rarity': 'normal',
            'sockets': sockets,
        }
        row['properties'][prop] = 3
        doc = build_bands(
            [row | {'listing_id': str(i), 'seller_id': str(i)} for i in range(3)],
            [],
            rules=rules,
            policies=policies,
        )
        tables = {
            'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
            'rules': {'keep_ist': 0.25, 'rows': rules, 'policies': policies},
            'own': {'rows': []},
        }
        assert assess(from_listing(row), tables)['verdict'] == 'slow'
        weak = from_listing(row | {'properties': row['properties'] | {prop: 2}})
        assert assess(weak, tables)['verdict'] == 'check'
        assert assess(from_listing(row | {'sockets': 1}), tables)['decision_ist'] == 1
        for change in ({'properties': {}}, {'socket_contents': 'filled'}):
            assert assess(from_listing(row | change), tables)['verdict'] == 'vendor'
        assert assess(from_listing(row | {'ethereal': True}), tables)['band'] is None
    # A five-socket CTA rule must never be emitted for a four-socket staff base.
    for rule in rules:
        assert rule['conditions']['sockets'] <= bases[rule['name']]['max_sockets']


def test_void_eligibility_covers_the_full_three_socket_dagger_line():
    from pricing.triage.engine import matches

    rules, policies = staffmod_rules()
    void = [r for r in rules if r.get('bucket') == 'void-three-socket']
    for name in ('Blade', 'Cinquedeas', 'Stilleto', 'Kriss', 'Fanged Knife', 'Legend Spike'):
        item = from_listing(listing(name, 1) | {'category': 'base', 'name': name, 'rarity': 'normal', 'sockets': 3})
        assert any(matches(item, r) for r in void)
        policy = next(p for p in policies if p.get('name') == name)
        assert policy['compare_staffmods']['1579'] == 'Abyss'
        assert not any(matches(item | {'sockets': 2}, r) for r in void)
        assert not any(matches(item | {'rarity': 'magic'}, r) for r in void)
    assert not any(r['name'] in ('Dagger', 'Dirk', 'Bone Knife', 'Mithral Point') for r in void)


def test_unlisted_scepter_policy_compares_native_rolls_without_creating_demand():
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.adapters.market_projection import market_properties

    meta = metadata()
    skill = next(k for k, value in meta['skills'].items() if value['name'] == 'Concentration')
    prop = market_properties()['107:' + skill]
    rules, policies = staffmod_rules()
    policies.append(
        {
            'category': 'base',
            'require_bucket': True,
            'facets': ['rarity', 'ethereal', 'sockets', 'socket_contents', 'base_modifiers'],
        }
    )
    rows = []
    for n, roll in enumerate((1, 2, 3)):
        row = listing(str(n), n + 1) | {
            'category': 'base',
            'name': 'Grand Scepter',
            'rarity': 'normal',
            'ethereal': False,
            'sockets': 3,
        }
        row['properties'][prop] = roll
        rows.append(row)
    document = build_bands(rows, [], rules=rules, policies=policies)
    tables = {
        'rules': {'keep_ist': 0.25, 'rows': rules, 'policies': policies},
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in document['bands']},
        'own': {'rows': []},
    }
    target = from_listing(rows[-1])
    result = assess(target, tables)
    assert result['verdict'] == 'slow'
    assert result['decision_ist'] == 1.5
    assert result['band']['sellers'] == 3
    assert assess(from_listing(rows[0]), tables)['decision_ist'] is None
    assert assess(target | {'ethereal': True}, tables)['decision_ist'] is None
    assert not any(r['name'] == 'Grand Scepter' for r in rules)
