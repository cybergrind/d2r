import pytest

from pricing.triage.engine import assess
from pricing.triage.import_affixed_rules import affixed_rules


def verdict(family, properties, category='rare'):
    return assess(
        {'category': category, 'family': family, 'name': 'Example', 'properties': properties},
        {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}},
    )['verdict']


def test_caster_ring_needs_both_mandatory_and_supporting_stats():
    assert verdict('ring', {'520': 10, '418': 30, '427': 20}) == 'check'
    assert verdict('ring', {'520': 10, '427': 20, '428': 20}) == 'vendor'
    assert verdict('ring', {'418': 30, '427': 20}) == 'vendor'


def test_rare_caster_amulet_counts_mana_but_still_requires_another_support():
    props = {'514': 2, '520': 10, '400': 60, '427': 20}
    assert verdict('amul', props) == 'check'
    for missing in ('514', '520', '400', '427'):
        assert verdict('amul', {k: v for k, v in props.items() if k != missing}) == 'vendor'
    assert verdict('amul', props | {'400': 5}) == 'check'
    assert verdict('amul', props | {'514': 1}) == 'vendor'
    assert verdict('amul', props | {'520': 9}) == 'vendor'
    assert verdict('amul', props, 'crafted') == 'vendor'


@pytest.mark.parametrize('skill', ['453', '514', '498', '442', '403', '488', '519', '1862'])
def test_caster_amulet_stacked_fcr_roll_shortfall_is_check(skill):
    result = assess(
        {'category': 'crafted', 'family': 'amul', 'name': 'Amulet', 'properties': {skill: 2, '520': 15}},
        {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}},
    )
    assert result['verdict'] == 'check'
    assert '15 of 20' in result['reason']
    assert 'faster cast rate' in result['reason']
    assert result['band'] is None
    for props in ({skill: 1, '520': 19}, {skill: 2, '520': 14}, {'520': 19}):
        assert verdict('amul', props, 'crafted') == 'vendor'
    assert verdict('amul', {skill: 2, '520': 19}, 'rare') == 'vendor'


def test_circlet_and_craft_do_not_borrow_other_slots_rules():
    assert verdict('circ', {'1862': 2, '520': 20}, 'magic') == 'check'
    assert verdict('circ', {'1862': 2, '520': 10}, 'magic') == 'vendor'
    assert verdict('amul', {'1862': 2, '520': 20}, 'crafted') == 'check'
    assert verdict('ring', {'1862': 2, '520': 20}, 'crafted') == 'vendor'


def test_boots_require_speed_and_two_resistances_with_low_rolls_kept_for_review():
    assert verdict('boot', {'480': 30, '427': 30, '428': 25}) == 'check'
    assert verdict('boot', {'480': 30, '427': 30, '428': 24}) == 'check'
    assert verdict('boot', {'480': 30, '427': 30}) == 'vendor'
    assert verdict('boot', {'427': 30, '428': 30}) == 'vendor'


@pytest.mark.parametrize(
    ('family', 'properties'),
    [
        ('amul', {'1862': 2, '418': 90}),
        ('amul', {'1862': 2, '526': 1}),
        ('amul', {'514': 2, '461': 30}),
        ('ring', {'461': 35}),
    ],
)
def test_guide_magic_jewelry_combinations(family, properties):
    assert verdict(family, properties, 'magic') == 'check'
    assert verdict(family, {'1862': 2}, 'magic') == 'vendor'
    assert verdict(family, {'526': 1}, 'magic') == 'vendor'


def test_socketed_magic_patterns_keep_base_and_socket_requirements():
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    for family, base, sockets, props in [
        ('shie', 'Monarch', 4, {'446': 20, '449': 30}),
        ('tors', 'Archon Plate', 4, {'418': 95}),
        ('circ', 'Tiara', 3, {'480': 30}),
    ]:
        item = {'category': 'magic', 'family': family, 'base_name': base, 'sockets': sockets, 'properties': props}
        assert assess(item, tables)['verdict'] == 'check'
        for changes in ({'sockets': sockets - 1}, {'base_name': 'Unknown'}):
            assert assess(item | changes, tables)['verdict'] == 'vendor'
        assert assess(item | {'properties': {}}, tables)['verdict'] == 'check'


def test_two_socket_circlet_patterns_keep_casting_and_mobility_separate():
    from pricing.triage.engine import assess
    from pricing.triage.import_affixed_rules import affixed_rules

    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = {'category': 'rare', 'family': 'circ', 'name': 'Diadem', 'sockets': 2, 'properties': {'453': 2, '520': 20}}
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert result['band'] is None
    movement = item | {'properties': {'453': 2, '480': 30}}
    assert assess(movement, tables)['verdict'] == 'check'
    assert assess(item | {'sockets': 1}, tables)['verdict'] == 'check'
    for changed in [
        movement | {'sockets': 1},
        movement | {'properties': {'453': 1, '480': 30}},
        movement | {'properties': {'453': 2, '480': 20}},
        item | {'properties': {'453': 2, '520': 10}},
    ]:
        assert assess(changed, tables)['verdict'] == 'vendor'


def test_skill_speed_mana_leech_gloves_and_lower_rolls_keep_rarity_and_support_gates():
    from pricing.triage.engine import assess
    from pricing.triage.import_affixed_rules import affixed_rules

    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = {'category': 'rare', 'family': 'glov', 'properties': {'456': 2, '457': 20, '463': 3}}
    assert assess(item, tables)['verdict'] == 'check'
    weak = item | {'properties': item['properties'] | {'463': 2}}
    assert 'mana leech 2 of 3' in assess(weak, tables)['reason']
    for props in (
        {'456': 1, '457': 20, '463': 3},
        {'456': 2, '457': 10, '463': 3},
    ):
        assert assess(item | {'properties': props}, tables)['verdict'] == 'vendor'
    bow = item | {'properties': {'454': 2, '457': 20, '463': 3, '437': 10}}
    assert assess(bow, tables)['verdict'] == 'check'
    assert assess(item | {'category': 'magic'}, tables)['verdict'] == 'vendor'
    assert assess(bow, tables)['band'] is None


def test_crafted_amulet_lower_fcr_needs_two_useful_extras():
    from pricing.triage.engine import assess
    from pricing.triage.import_affixed_rules import affixed_rules

    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = {'category': 'crafted', 'family': 'amul', 'properties': {'514': 2, '520': 10, '418': 35, '428': 20}}
    assert assess(item, tables)['verdict'] == 'check'
    assert assess(item, tables)['band'] is None
    for props in (
        {'514': 2, '520': 10, '418': 35},
        {'514': 1, '520': 10, '418': 35, '428': 20},
        {'514': 2, '520': 9, '418': 35, '428': 20},
    ):
        assert assess(item | {'properties': props}, tables)['verdict'] == 'vendor'


def test_warlock_teleport_amulet_is_a_complete_non_fcr_pattern():
    from pricing.triage.engine import assess
    from pricing.triage.import_affixed_rules import affixed_rules

    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    props = {'1862': 2, '463': 7, '418': 31, '441': 13, '526': 3}
    item = {'category': 'rare', 'family': 'amul', 'properties': props}
    assert assess(item, tables)['verdict'] == 'check'
    for key in props:
        assert (
            assess(item | {'properties': {k: v for k, v in props.items() if k != key}}, tables)['verdict'] == 'vendor'
        )


def test_rare_physical_weapon_pattern_requires_damage_speed_base_and_durability():
    from pricing.triage.engine import assess
    from pricing.triage.import_affixed_rules import affixed_rules

    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = {
        'category': 'rare',
        'family': 'axe',
        'name': 'Berserker Axe',
        'base_name': 'Berserker Axe',
        'ethereal': True,
        'sockets': 0,
        'properties': {'510': 350, '457': 40, '431': 1},
    }
    assert assess(item, tables)['verdict'] == 'check'
    for change in (
        {'base_name': 'Hand Axe'},
        {'ethereal': False},
        {'properties': {'510': 350, '457': 40}},
        {'properties': {'510': 350, '431': 1}},
        {'properties': {'510': 50, '457': 40, '431': 1}},
    ):
        assert assess(item | change, tables)['verdict'] == 'vendor'
    socketed = item | {'sockets': 1, 'properties': {'510': 350, '457': 40}}
    assert assess(socketed, tables)['verdict'] == 'check'
    bow = item | {'family': 'bow', 'base_name': 'Hydra Bow', 'ethereal': False, 'properties': {'510': 300, '457': 20}}
    assert assess(bow, tables)['verdict'] == 'check'
    assert assess(bow, tables)['band'] is None


def test_rare_jewel_needs_two_paid_stats_and_reports_low_rolls():
    from pricing.triage.engine import assess
    from pricing.triage.import_affixed_rules import affixed_rules

    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = {'category': 'rare', 'family': 'jewl', 'properties': {'510': 20, '441': 8}}
    assert assess(item, tables)['verdict'] == 'check'
    low = assess(item | {'properties': {'510': 19, '441': 8}}, tables)
    assert low['verdict'] == 'check'
    assert 'enhanced damage' in low['reason']
    assert '19' in low['reason']
    assert low['band'] is None
    for properties in ({'510': 30}, {'441': 10}, {'448': 15}, {'510': 30, '441': 0}):
        assert assess(item | {'properties': properties}, tables)['verdict'] == 'vendor'


def test_crafted_melee_ring_uses_same_complete_pattern_as_rare_ring():
    from pricing.triage.engine import assess
    from pricing.triage.import_affixed_rules import affixed_rules

    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = {'category': 'crafted', 'family': 'ring', 'properties': {'423': 110, '462': 6, '418': 40, '437': 20}}
    assert assess(item, tables)['verdict'] == 'check'
    for properties in ({'462': 6, '418': 40, '437': 20}, {'423': 110, '462': 6, '418': 40}):
        assert assess(item | {'properties': properties}, tables)['verdict'] == 'vendor'
    assert assess(item, tables)['band'] is None


@pytest.mark.parametrize('family', ['jave', 'tkni', 'taxe'])
def test_echoing_throwing_weapon_is_a_paid_switch_pattern(family):
    assert verdict(family, {'406': 3}, 'magic') == 'check'
    assert verdict(family, {'406': 2}, 'magic') == 'vendor'
    assert verdict(family, {'456': 3}, 'magic') == 'vendor'
    assert verdict(family, {'406': 3}, 'rare') == 'vendor'


def test_echoing_price_cannot_cross_base_or_suffix():
    from inventory_tracking.items.metadata import metadata
    from pricing.triage.adapters import from_listing
    from pricing.triage.bands import build_bands
    from tests.pricing.triage.test_bands import listing

    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Throwing Spear')
    rows = []
    for n, price in enumerate((1, 2, 3)):
        row = listing(str(n), price) | {
            'category': 'base',
            'name': base['name'],
            'base_code': base['code'],
            'rarity': 'magic',
            'ethereal': False,
        }
        row['properties']['406'] = 3
        rows.append(row)
    rules = affixed_rules()
    bands = build_bands(rows, [], rules=rules)['bands']
    tables = {
        'rules': {'rows': rules, 'keep_ist': 0.25},
        'own': {'rows': []},
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in bands},
    }
    item = from_listing(rows[0])
    assert assess(item, tables)['band']['q1_ist'] == 1.5
    assert assess(item, tables)['verdict'] == 'slow'
    for changes in ({'base_code': None}, {'ethereal': True}, {'base_modifiers': {'406': 3, '418': 20}}):
        result = assess(item | changes, tables)
        assert result['verdict'] == 'check'
        assert result['band'] is None
    assert verdict('amul', {'406': 3}, 'magic') == 'vendor'


def test_complete_support_pattern_survives_low_rolls_and_explains_shortfall():
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    amulet = {'category': 'rare', 'family': 'amul', 'properties': {'514': 2, '520': 10, '418': 39, '427': 14}}
    result = assess(amulet, tables)
    assert result['verdict'] == 'check'
    assert 'life 39 of 40' in result['reason']
    assert 'fire resistance 14 of 15' in result['reason']
    for props in (
        {'514': 2, '520': 10, '418': 39},
        {'514': 2, '520': 10, '427': 14, '428': 14},
        {'514': 1, '520': 10, '418': 39, '427': 14},
        {'514': 2, '520': 9, '418': 39, '427': 14},
        {'514': 2, '520': 10, '418': 0, '427': 14},
    ):
        assert assess(amulet | {'properties': props}, tables)['verdict'] == 'vendor'
    boots = {'category': 'rare', 'family': 'boot', 'properties': {'480': 30, '427': 30, '428': 24}}
    result = assess(boots, tables)
    assert result['verdict'] == 'check'
    assert 'lightning resistance 24 of 25' in result['reason']


@pytest.mark.parametrize(
    ('family', 'base'),
    [('swor', 'Phase Blade'), ('axe', 'Berserker Axe'), ('mace', 'Scourge'), ('hamm', 'Legendary Mallet')],
)
def test_fools_weapon_requires_both_scaling_stats_and_physical_gates(family, base):
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    props = {'510': 250, '457': 30, '535': 40, '536': 1300}
    item = {
        'category': 'rare',
        'family': family,
        'base_name': base,
        'ethereal': True,
        'sockets': 1,
        'properties': props,
    }
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert "Fool's" in result['reason']
    assert result['band'] is None
    for missing in props:
        assert (
            assess(item | {'properties': {k: v for k, v in props.items() if k != missing}}, tables)['verdict']
            == 'vendor'
        )
    for change in (
        {'base_name': 'Hand Axe'},
        {'category': 'magic'},
        {'properties': props | {'510': 199}},
        {'properties': props | {'457': 20}},
    ):
        assert assess(item | change, tables)['verdict'] == 'vendor'
    if base == 'Phase Blade':
        assert assess(item | {'sockets': 0, 'ethereal': False}, tables)['verdict'] == 'check'
    else:
        assert assess(item | {'ethereal': False}, tables)['verdict'] == 'vendor'
        assert assess(item | {'sockets': 0}, tables)['verdict'] == 'vendor'
        assert assess(item | {'sockets': 0, 'properties': props | {'431': 1}}, tables)['verdict'] == 'check'


@pytest.mark.parametrize('skill', ['515', '516', '517', '443', '500', '1547', '1548'])
def test_paid_magic_tree_circlets_require_three_skills_and_twenty_fcr(skill):
    assert verdict('circ', {skill: 3, '520': 20}, 'magic') == 'check'
    assert verdict('circ', {skill: 2, '520': 20}, 'magic') == 'vendor'
    assert verdict('circ', {skill: 3, '520': 10}, 'magic') == 'vendor'
    assert verdict('circ', {skill: 3}, 'magic') == 'vendor'
    assert verdict('circ', {skill: 3, '520': 20}, 'rare') == 'vendor'
    assert verdict('ring', {skill: 3, '520': 20}, 'magic') == 'vendor'


def test_unreviewed_tree_does_not_borrow_paid_caster_circlet_pattern():
    assert verdict('circ', {'404': 3, '520': 20}, 'magic') == 'vendor'


def test_user_labelled_caster_ring_with_two_resistances_and_magic_find_is_check():
    from inventory_tracking.corpus.build import DATA
    from inventory_tracking.corpus.score import load
    from pricing.triage.adapters import from_drop

    items, _ = load(DATA)
    capture = next(row['observation'] for row in items if row['id'] == '2d289b42b674')
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    assert assess(from_drop(capture), tables)['verdict'] == 'check'
    assert verdict('ring', {'520': 10, '427': 29, '428': 10, '461': 10}) == 'check'
    for props in (
        {'520': 10, '427': 29, '461': 10},
        {'520': 10, '427': 29, '428': 10},
        {'427': 29, '428': 10, '461': 10},
    ):
        assert verdict('ring', props) == 'vendor'


@pytest.mark.parametrize(
    ('family', 'base', 'upgrade'),
    [
        ('taxe', 'Winged Axe', False),
        ('tkni', 'Flying Knife', False),
        ('jave', 'Ghost Glaive', False),
        ('taxe', 'Balanced Axe', True),
        ('tkni', 'War Dart', True),
        ('jave', 'Pilum', True),
    ],
)
def test_double_throw_candidates_need_ethereal_damage_speed_but_not_replenish(family, base, upgrade):
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = {
        'category': 'rare',
        'family': family,
        'base_name': base,
        'ethereal': True,
        'properties': {'510': 300, '457': 30},
    }
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert result['band'] is None
    assert ('upgrade' in str(result).lower()) == upgrade
    for change in (
        {'ethereal': False},
        {'ethereal': None},
        {'base_name': 'Unknown'},
        {'properties': {'510': 299, '457': 30}},
        {'properties': {'510': 300, '457': 20}},
        {'properties': {'510': 300, '563': 10}},
        {'family': 'ajav'},
        {'category': 'magic'},
        {'category': 'crafted'},
    ):
        assert assess(item | change, tables)['verdict'] == 'vendor'


@pytest.mark.parametrize('category', ['rare', 'crafted'])
@pytest.mark.parametrize(
    ('family', 'properties', 'missing'),
    [
        ('boot', {'480': 30, '427': 31, '428': 10}, ['480', '427', '428']),
        ('belt', {'430': 24, '418': 42, '437': 29, '401': 6}, ['430', '418', '437', '401']),
    ],
)
def test_resistance_boots_and_life_strength_belts_share_rare_and_crafted_patterns(
    category, family, properties, missing
):
    assert verdict(family, properties, category) == 'check'
    for prop in missing:
        assert verdict(family, {k: v for k, v in properties.items() if k != prop}, category) == 'vendor'
    assert verdict(family, properties, 'magic') == 'vendor'


@pytest.mark.parametrize(
    ('family', 'properties', 'primary', 'support'),
    [
        ('circ', {'488': 2, '520': 20, '400': 47, '427': 20}, ['488', '520'], ['400', '427']),
        ('glov', {'456': 2, '457': 20, '462': 3, '428': 16}, ['456', '457'], ['462', '428']),
    ],
)
def test_useful_mana_and_life_leech_count_as_support_but_do_not_replace_primary_gates(
    family, properties, primary, support
):
    assert verdict(family, properties) == 'check'
    for prop in primary:
        assert verdict(family, {k: v for k, v in properties.items() if k != prop}) == 'vendor'
    for prop in support:
        assert verdict(family, {k: v for k, v in properties.items() if k != prop}) == 'check'
    assert verdict(family, {**properties, primary[0]: 1}) == 'vendor'
    assert verdict(family, {**properties, primary[1]: 10}) == 'vendor'


@pytest.mark.parametrize('ethereal', [False, True])
def test_phase_blade_intrinsic_durability_preserves_physical_stat_gates(ethereal):
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = {
        'category': 'rare',
        'family': 'swor',
        'base_name': 'Phase Blade',
        'ethereal': ethereal,
        'sockets': 0,
        'properties': {'510': 300, '457': 30},
    }
    assert assess(item, tables)['verdict'] == 'check'
    for change in (
        {'base_name': 'Crystal Sword'},
        {'base_name': 'Cryptic Sword'},
        {'ethereal': None},
        {'properties': {'510': 299, '457': 30}},
        {'properties': {'510': 300, '457': 20}},
    ):
        assert assess(item | change, tables)['verdict'] == 'vendor'


@pytest.mark.parametrize('base', ['Balrog Skin', 'Great Hauberk', 'Lacquered Plate'])
@pytest.mark.parametrize('properties', [{'418': 90}, {'430': 24}, {'429': 10}])
def test_jeweler_armor_uses_elite_family_and_complete_suffix(base, properties):
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = {'category': 'magic', 'family': 'tors', 'base_name': base, 'sockets': 4, 'properties': properties}
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert result['band'] is None
    for change in ({'sockets': 3}, {'sockets': None}, {'base_name': 'Embossed Plate'}, {'properties': {}}):
        assert assess(item | change, tables)['verdict'] == 'vendor'


def test_jeweler_sacred_targe_requires_both_deflecting_mods_and_four_sockets():
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = {
        'category': 'magic',
        'family': 'ashd',
        'base_name': 'Sacred Targe',
        'sockets': 4,
        'properties': {'446': 20, '449': 30},
    }
    assert assess(item, tables)['verdict'] == 'check'
    assert assess(item, tables)['band'] is None
    for change in (
        {'sockets': 3},
        {'properties': {'446': 20}},
        {'properties': {'449': 30}},
        {'base_name': 'Sacred Rondache'},
        {'category': 'rare'},
    ):
        assert assess(item | change, tables)['verdict'] == 'vendor'


def test_magic_resistance_damage_jewel_requires_both_modifiers():
    assert verdict('jewl', {'441': 8, '448': 10}, 'magic') == 'check'
    assert verdict('jewl', {'441': 8}, 'magic') == 'vendor'
    assert verdict('jewl', {'448': 10}, 'magic') == 'vendor'


@pytest.mark.parametrize(('prop', 'minimum'), [('510', 30), ('457', 15), ('441', 10)])
def test_documented_single_affix_magic_jewel_pattern_has_a_review_floor(prop, minimum):
    assert verdict('jewl', {prop: minimum}, 'magic') == 'check'
    assert verdict('jewl', {prop: minimum - 1}, 'magic') == 'vendor'
    assert verdict('ring', {prop: minimum}, 'magic') == 'vendor'
    assert verdict('jewl', {prop: minimum}, 'rare') == 'vendor'


@pytest.mark.parametrize(('family', 'skill', 'speed'), [('circ', '514', '520'), ('glov', '456', '457')])
def test_guide_two_skill_twenty_speed_patterns_do_not_require_extra_affixes(family, skill, speed):
    assert verdict(family, {skill: 2, speed: 20}) == 'check'
    assert verdict(family, {skill: 1, speed: 20}) == 'vendor'
    assert verdict(family, {skill: 2, speed: 10}) == 'vendor'
    assert verdict(family, {skill: 2}) == 'vendor'
    assert verdict('ring', {skill: 2, speed: 20}) == 'vendor'


def test_four_socket_magic_monarch_is_reviewable_without_deflecting_price():
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = {'category': 'magic', 'family': 'shie', 'base_name': 'Monarch', 'sockets': 4, 'properties': {}}
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert result['decision_ist'] is None
    for change in ({'sockets': 3}, {'base_name': 'Kite Shield'}, {'category': 'rare'}):
        assert assess(item | change, tables)['verdict'] == 'vendor'


def test_plain_small_charm_guide_patterns_without_borrowing_combination_prices():
    assert verdict('scha', {'461': 6}, 'magic') == 'check'
    assert verdict('scha', {'461': 7}, 'magic') == 'check'
    assert verdict('scha', {'461': 5}, 'magic') == 'vendor'
    assert verdict('scha', {'448': 3, '423': 20}, 'magic') == 'check'
    assert verdict('scha', {'448': 2, '423': 18}, 'magic') == 'check'
    assert verdict('scha', {'448': 3}, 'magic') == 'vendor'
    assert verdict('scha', {'423': 20}, 'magic') == 'vendor'
    assert verdict('mcha', {'448': 3, '423': 20}, 'magic') == 'vendor'


@pytest.mark.parametrize(
    ('base', 'family', 'sockets'), [('Archon Plate', 'tors', 4), ('Tiara', 'circ', 3), ('Diadem', 'circ', 3)]
)
def test_documented_magic_socket_bases_do_not_need_premium_suffix(base, family, sockets):
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = {'category': 'magic', 'family': family, 'base_name': base, 'sockets': sockets, 'properties': {}}
    assert assess(item, tables)['verdict'] == 'check'
    assert assess(item, tables)['decision_ist'] is None
    assert assess(item | {'sockets': sockets - 1}, tables)['verdict'] == 'vendor'
    assert assess(item | {'category': 'rare'}, tables)['verdict'] == 'vendor'


def test_speed_resistance_tiara_needs_both_stats_without_three_sockets():
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = {
        'category': 'magic',
        'family': 'circ',
        'base_name': 'Tiara',
        'sockets': 0,
        'properties': {'480': 30, '441': 30},
    }
    assert assess(item, tables)['verdict'] == 'check'
    assert assess(item | {'properties': {'480': 20, '441': 20}}, tables)['verdict'] == 'check'
    for properties in ({'480': 30}, {'441': 30}):
        assert assess(item | {'properties': properties}, tables)['verdict'] == 'vendor'
