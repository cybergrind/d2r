from pricing.triage.engine import assess
from pricing.triage.import_class_rules import class_rules


def test_amazon_javelin_pattern_requires_javelin_tree_not_bow_tree():
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': class_rules()}, 'own': {'rows': []}}
    item = {
        'category': 'magic',
        'family': 'ajav',
        'name': 'Matriarchal Javelin',
        'properties': {'453': 2, '456': 3, '457': 40},
    }
    assert assess(item, tables)['verdict'] == 'check'
    item['properties'] = {'453': 2, '454': 3, '457': 40}
    assert assess(item, tables)['verdict'] == 'vendor'


def verdict(family, properties, category='magic', **fields):
    fields.setdefault('base_name', 'Stilleto')
    return assess(
        {'category': category, 'family': family, 'name': 'Test', 'properties': properties, **fields},
        {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': class_rules()}, 'own': {'rows': []}},
    )


def test_unpaid_stiletto_staffmods_do_not_trigger_check():
    result = verdict('knif', {'1561': 1, '1574': 3}, sockets=0)
    assert result['verdict'] == 'vendor'
    assert 'staffmods alone' in result['reason']


def test_paid_dagger_needs_class_skill_paid_staffmod_and_support():
    assert verdict('knif', {'1862': 2, '1565': 3, '457': 20})['verdict'] == 'check'
    for props in ({'1862': 2, '1565': 3}, {'1565': 3, '457': 20}, {'1862': 2, '1574': 3, '457': 20}):
        assert verdict('knif', props)['verdict'] == 'vendor'


def test_necro_head_and_barbarian_helm_require_paid_combinations():
    assert verdict('head', {'498': 2, '1024': 3, '449': 20}, 'rare')['verdict'] == 'check'
    assert verdict('head', {'498': 2, '1024': 3}, 'rare')['verdict'] == 'vendor'
    assert verdict('phlm', {'403': 2, '765': 3}, 'rare')['verdict'] == 'check'
    assert verdict('phlm', {'403': 2, '765': 2}, 'rare')['verdict'] == 'vendor'


def test_class_rule_does_not_apply_to_generic_weapon_or_different_rarity():
    props = {'1862': 2, '1565': 3, '457': 20}
    assert verdict('axe', props)['verdict'] == 'vendor'
    assert verdict('knif', props, 'unique')['verdict'] == 'vendor'


def test_paid_dagger_still_needs_an_allowed_base_line():
    props = {'1862': 2, '1565': 3, '457': 20}
    assert verdict('knif', props, base_name='Dirk')['verdict'] == 'vendor'
    assert verdict('knif', props, base_name=None)['verdict'] == 'vendor'


def test_orb_cast_rate_does_not_accept_an_unrelated_skill_tree():
    assert verdict('orb', {'514': 2, '520': 20})['verdict'] == 'check'
    assert verdict('orb', {'514': 2, '486': 20})['verdict'] == 'vendor'


def test_magic_lightning_sentry_claw_accepts_two_socket_alternative_to_ias():
    for prefix in ({'519': 2}, {'408': 3}):
        props = prefix | {'1073': 3}
        result = verdict('h2h2', props, sockets=2)
        assert result['verdict'] == 'check'
        assert result['band'] is None
        assert 'two sockets' in result['reason']
        for sockets in (0, 1, None):
            assert verdict('h2h2', props, sockets=sockets)['verdict'] == 'vendor'
        assert verdict('h2h2', prefix | {'1073': 2}, sockets=2)['verdict'] == 'vendor'
    assert verdict('h2h2', {'1073': 3}, sockets=2)['verdict'] == 'vendor'
    assert verdict('h2h2', {'519': 1, '1073': 3}, sockets=2)['verdict'] == 'vendor'
    assert verdict('h2h2', {'519': 2, '1116': 3}, sockets=2)['verdict'] == 'vendor'


def test_listing_replay_reports_paid_checks_without_counting_them_as_sales():
    from pricing.triage.replay import listing_score
    from tests.pricing.triage.test_bands import listing

    row = listing(1)
    row.update(name='Bone Knife', category='base', rarity='magic')
    row['properties'].update({'1862': 2, '1565': 3, '457': 20})
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': class_rules()}, 'own': {'rows': []}}
    score = listing_score([row], tables)['categories']['magic']
    assert score['checks_valuable'] == 1
    assert score['flagged_valuable'] == 1
    assert score['sell_flagged_valuable'] == 0


def test_rare_amazon_spear_requires_all_gates_and_two_supporting_mods():
    props = {'510': 250, '453': 2, '457': 40, '462': 5, '535': 1}
    assert verdict('aspe', props, 'rare', base_name='Matriarchal Spear', sockets=2)['verdict'] == 'check'
    for removed in ('510', '453', '457', '462', '535'):
        changed = {k: v for k, v in props.items() if k != removed}
        assert verdict('aspe', changed, 'rare', base_name='Matriarchal Spear', sockets=2)['verdict'] == 'vendor'
    assert verdict('aspe', props, 'rare', base_name='Matriarchal Spear', sockets=1)['verdict'] == 'vendor'
    assert verdict('spea', props, 'rare', base_name='Spear', sockets=2)['verdict'] == 'vendor'


def test_ethereal_melee_dagger_is_a_separate_complete_pattern():
    props = {'457': 40, '462': 5, '448': 10}
    assert verdict('knif', props, 'rare', base_name='Bone Knife', ethereal=True)['verdict'] == 'check'
    assert verdict('knif', props, 'rare', base_name='Bone Knife', ethereal=False)['verdict'] == 'vendor'
    assert verdict('knif', {'457': 40, '462': 5}, 'rare', base_name='Bone Knife', ethereal=True)['verdict'] == 'vendor'


def test_magic_orb_tree_spell_and_support_must_match_together():
    assert verdict('orb', {'516': 3, '948': 3, '520': 20})['verdict'] == 'check'
    assert verdict('orb', {'515': 3, '944': 3}, sockets=2)['verdict'] == 'check'
    for props in ({'516': 3, '944': 3, '520': 20}, {'516': 3, '948': 3}, {'516': 3, '520': 20}):
        assert verdict('orb', props)['verdict'] == 'vendor'
    assert verdict('orb', {'515': 3, '944': 3}, sockets=1)['verdict'] == 'vendor'


def test_rare_paladin_shield_requires_elite_base_class_prefix_and_supporting_rolls():
    from pricing.triage.engine import assess
    from pricing.triage.import_class_rules import class_rules

    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': class_rules()}, 'own': {'rows': []}}
    item = {
        'category': 'rare',
        'family': 'ashd',
        'name': 'Sacred Targe',
        'base_name': 'Sacred Targe',
        'sockets': 1,
        'properties': {'442': 2, '441': 30, '418': 20},
    }
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert result['decision_ist'] is None
    for changed in [
        item | {'base_name': 'Targe'},
        item | {'sockets': 0},
        item | {'properties': {'442': 1, '441': 30, '418': 20}},
        item | {'properties': {'442': 2, '418': 20}},
    ]:
        assert assess(changed, tables)['verdict'] == 'vendor'
    block = item | {'properties': {'442': 2, '449': 30, '430': 17}}
    assert assess(block, tables)['verdict'] == 'check'
    assert assess(item | {'category': 'magic'}, tables)['verdict'] == 'vendor'


def test_paid_pelt_combinations_require_matching_skills_and_support():
    from pricing.triage.engine import assess
    from pricing.triage.import_class_rules import class_rules

    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': class_rules()}, 'own': {'rows': []}}
    item = {
        'category': 'rare',
        'family': 'pelt',
        'name': 'Antlers',
        'sockets': 2,
        'properties': {'488': 2, '972': 3, '418': 31},
    }
    assert assess(item, tables)['verdict'] == 'check'
    for properties in (
        {'488': 1, '972': 3, '418': 31},
        {'488': 2, '972': 0, '418': 31},
        {'488': 2, '1155': 3, '418': 31},
    ):
        assert assess(item | {'properties': properties}, tables)['verdict'] == 'vendor'
    for tree, spell in [('487', '972'), ('487', '976'), ('486', '966'), ('485', '974')]:
        magic = item | {'category': 'magic', 'properties': {tree: 3, spell: 3}}
        assert assess(magic, tables)['verdict'] == 'check'
        assert assess(magic | {'sockets': 1}, tables)['verdict'] == 'vendor'
    assert assess(item | {'category': 'magic', 'properties': {'485': 3, '972': 3}}, tables)['verdict'] == 'vendor'


def test_pelt_near_miss_keeps_all_gates_and_names_the_low_skill_roll():
    from pricing.triage.engine import assess
    from pricing.triage.import_class_rules import class_rules

    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': class_rules()}, 'own': {'rows': []}}
    item = {
        'category': 'rare',
        'family': 'pelt',
        'name': 'Antlers',
        'sockets': 2,
        'properties': {'488': 2, '972': 2, '418': 31},
    }
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert 'Tornado 2 of 3' in result['reason']
    assert result['band'] is None
    assert assess(item | {'sockets': 0}, tables)['verdict'] == 'check'
    magic = item | {'category': 'magic', 'properties': {'487': 3, '972': 1}}
    assert assess(magic, tables)['verdict'] == 'check'
    assert 'Tornado 1 of 3' in assess(magic, tables)['reason']
    assert assess(magic | {'properties': {'487': 2, '972': 1}}, tables)['verdict'] == 'vendor'


def test_orb_low_spell_roll_is_a_near_miss_only_with_complete_paid_pattern():
    result = verdict('orb', {'516': 3, '948': 2, '520': 20})
    assert result['verdict'] == 'check'
    assert 'Nova 2 of 3' in result['reason']
    assert result['band'] is None
    assert verdict('orb', {'516': 3, '948': 1}, sockets=2)['verdict'] == 'check'
    for props in (
        {'516': 2, '948': 2, '520': 20},
        {'516': 3, '948': 2, '520': 10},
        {'516': 3, '944': 2, '520': 20},
        {'516': 3, '948': 0, '520': 20},
    ):
        assert verdict('orb', props)['verdict'] == 'vendor'
    assert verdict('orb', {'516': 3, '948': 1}, sockets=1)['verdict'] == 'vendor'


def test_stacked_amazon_javelin_skills_do_not_need_a_second_class_prefix():
    for skills, speed in ((6, 40), (5, 40), (6, 30)):
        result = verdict('ajav', {'456': skills, '457': speed})
        assert result['verdict'] == 'check'
        assert result['band'] is None
    for skills, speed in ((5, 30), (4, 40), (6, 20)):
        assert verdict('ajav', {'456': skills, '457': speed})['verdict'] == 'vendor'
    assert verdict('ajav', {'454': 6, '457': 40})['verdict'] == 'vendor'
    assert verdict('jave', {'456': 6, '457': 40})['verdict'] == 'vendor'
    assert verdict('ajav', {'456': 6, '457': 40}, 'rare')['verdict'] == 'vendor'


def test_javelin_prices_preserve_ethereal_and_primary_skill_pattern():
    from inventory_tracking.items.metadata import metadata
    from pricing.triage.adapters import from_listing
    from pricing.triage.bands import build_bands
    from tests.pricing.triage.test_bands import listing

    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Maiden Javelin')
    rows = []
    for n, price in enumerate((1, 2, 3)):
        row = listing(str(n), price) | {
            'category': 'base',
            'name': base['name'],
            'base_code': base['code'],
            'rarity': 'magic',
            'ethereal': False,
        }
        row['properties'].update({'456': 5, '457': 40})
        rows.append(row)
    rules = class_rules()
    bands = build_bands(rows, [], rules=rules)['bands']
    tables = {
        'rules': {'rows': rules, 'keep_ist': 0.25},
        'own': {'rows': []},
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in bands},
    }
    item = from_listing(rows[0])
    result = assess(item, tables)
    assert result['verdict'] == 'slow'
    assert result['band']['q1_ist'] == 1.5
    for change in (
        {'ethereal': True},
        {'ethereal': None},
        {'properties': item['properties'] | {'456': 6}},
    ):
        assert assess(item | change, tables)['band'] is None

    for change in (
        {'base_code': None},
        {'base_code': next(b['code'] for b in metadata()['bases'].values() if b['name'] == 'Matriarchal Javelin')},
        {'base_modifiers': item['base_modifiers'] | {'418': 30}},
    ):
        assert assess(item | change, tables)['decision_ist'] == 1.5


def test_magic_fist_of_heavens_scepter_requires_prefix_spell_and_utility():
    for prefix, level in (('442', 2), ('443', 3)):
        for support, value in (('1047', 1), ('520', 10)):
            props = {prefix: level, '581': 3, support: value}
            result = verdict('scep', props)
            assert result['verdict'] == 'check'
            assert result['band'] is None
            for missing in props:
                assert verdict('scep', {k: v for k, v in props.items() if k != missing})['verdict'] == 'vendor'
            assert verdict('scep', props | {'581': 2})['verdict'] == 'vendor'
            assert verdict('wand', props)['verdict'] == 'vendor'
            assert verdict('scep', props, 'rare')['verdict'] == 'vendor'
    assert verdict('scep', {'444': 3, '581': 3, '1047': 3})['verdict'] == 'vendor'
    assert verdict('scep', {'442': 2, '581': 3, '520': 5})['verdict'] == 'vendor'


def test_fools_claw_pattern_separates_ethereal_preparation_from_caster_skills():
    props = {'510': 250, '457': 30, '535': 40, '536': 1300}
    for family, base in [('h2h', 'Claws'), ('h2h2', 'Runic Talons')]:
        for ethereal in (False, True):
            result = verdict(family, props, 'rare', base_name=base, ethereal=ethereal)
            assert result['verdict'] == 'check'
            assert result['band'] is None
            assert ('repair/Zod' in result['reason']) is ethereal
            assert ('upgrade' in result['reason']) is (base == 'Claws')
            repaired = verdict(family, props | {'431': 1}, 'rare', base_name=base, ethereal=ethereal)
            assert 'repair/Zod' not in repaired['reason']
        for missing in props:
            assert (
                verdict(
                    family, {k: v for k, v in props.items() if k != missing}, 'rare', base_name=base, ethereal=False
                )['verdict']
                == 'vendor'
            )
        assert verdict(family, props, 'rare', base_name=base, ethereal=None)['verdict'] == 'vendor'
        assert verdict(family, props, 'magic', base_name=base, ethereal=False)['verdict'] == 'vendor'
    assert verdict('swor', props, 'rare', base_name='Runic Talons', ethereal=False)['verdict'] == 'vendor'
    assert verdict('h2h2', props, 'rare', base_name='Unknown', ethereal=True)['verdict'] == 'vendor'


def test_guide_class_combinations_keep_single_support_pelts_and_blocking_shields():
    from pricing.triage.engine import assess
    from pricing.triage.import_class_rules import class_rules

    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': class_rules()}, 'own': {'rows': []}}
    pelt = {
        'category': 'rare',
        'family': 'pelt',
        'base_name': 'Antlers',
        'sockets': 0,
        'properties': {'488': 2, '972': 3, '418': 30},
    }
    shield = {
        'category': 'rare',
        'family': 'ashd',
        'base_name': 'Sacred Targe',
        'sockets': 0,
        'properties': {'442': 2, '441': 45, '449': 30, '446': 20},
    }
    for item in (pelt, shield):
        result = assess(item, tables)
        assert result['verdict'] == 'check'
        assert result['decision_ist'] is None
    assert assess(pelt | {'properties': {'488': 2, '972': 3}}, tables)['verdict'] == 'vendor'
    assert assess(pelt | {'properties': {'488': 2, '972': 3}, 'sockets': 1}, tables)['verdict'] == 'check'
    assert assess(shield | {'properties': {'442': 2, '441': 45, '449': 30, '446': 19}}, tables)['verdict'] == 'vendor'


def test_magic_javelin_lower_class_roll_keeps_full_paid_pattern_for_review():
    assert verdict('ajav', {'453': 1, '456': 3, '457': 40})['verdict'] == 'check'
    assert verdict('ajav', {'456': 3, '457': 40})['verdict'] == 'vendor'
    assert verdict('ajav', {'453': 1, '454': 3, '457': 40})['verdict'] == 'vendor'
