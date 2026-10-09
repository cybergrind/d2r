import pytest

from pricing.triage.engine import assess
from pricing.triage.import_affixed_rules import affixed_rules


def verdict(family, properties, category='rare'):
    return assess(
        {'category': category, 'family': family, 'name': 'Example', 'properties': properties},
        {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}},
    )['verdict']


def test_plain_sharp_grand_charm_keeps_guide_damage_threshold_and_native_ar_floor():
    assert verdict('lcha', {'448': 8, '423': 49}, 'magic') == 'check'
    assert verdict('lcha', {'448': 10, '423': 76}, 'magic') == 'check'
    for props in ({'448': 7, '423': 76}, {'448': 8}, {'423': 76}, {'448': 8, '423': 48}):
        assert verdict('lcha', props, 'magic') == 'vendor'
    assert verdict('mcha', {'448': 8, '423': 49}, 'magic') == 'vendor'


@pytest.mark.parametrize(('prop', 'minimum', 'maximum'), [('418', 81, 100), ('461', 26, 35)])
def test_warlock_magic_circlet_whale_and_luck_require_both_guide_affixes(prop, minimum, maximum):
    for roll in (minimum, maximum):
        assert verdict('circ', {'1862': 2, prop: roll}, 'magic') == 'check'
    for props in ({'1862': 1, prop: maximum}, {'1862': 2, prop: minimum - 1}, {prop: maximum}):
        assert verdict('circ', props, 'magic') == 'vendor'
    assert verdict('circ', {'514': 2, prop: maximum}, 'magic') == 'vendor'


def test_caster_ring_needs_both_mandatory_and_supporting_stats():
    assert verdict('ring', {'520': 10, '418': 30, '427': 20}) == 'check'
    assert verdict('ring', {'520': 10, '427': 20, '428': 20}) == 'vendor'
    assert verdict('ring', {'418': 30, '427': 20}) == 'vendor'


def test_rare_caster_amulet_counts_mana_but_still_requires_another_support():
    props = {'514': 2, '520': 10, '400': 60, '427': 20}
    assert verdict('amul', props) == 'check'
    # Since 2026-10-08 +2 class skills needs one companion, so only losing the skill roll fails.
    assert verdict('amul', {k: v for k, v in props.items() if k != '514'}) == 'vendor'
    for missing in ('520', '427'):
        assert verdict('amul', {k: v for k, v in props.items() if k != missing}) == 'check'
    # The primer's separate strong-resistance rule does not also require mana.
    assert verdict('amul', {k: v for k, v in props.items() if k != '400'}) == 'check'
    assert verdict('amul', props | {'400': 5}) == 'check'
    # +1 class skills needs two companions (FCR and 60+ mana here).
    assert verdict('amul', props | {'514': 1}) == 'check'
    assert verdict('amul', props | {'514': 1, '400': 59}) == 'vendor'
    assert verdict('amul', props | {'520': 9}) == 'check'
    assert verdict('amul', {'514': 2, '520': 9, '400': 59, '427': 20}) == 'vendor'
    assert verdict('amul', props, 'crafted') == 'check'


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
    for props in ({skill: 1, '520': 19}, {skill: 2, '520': 9}, {'520': 19}):
        assert verdict('amul', props, 'crafted') == 'vendor'
    # 10+ FCR is a companion for +2 class skills on rare and crafted amulets since 2026-10-08.
    assert verdict('amul', {skill: 2, '520': 14}, 'crafted') == 'check'
    assert verdict('amul', {skill: 2, '520': 19}, 'rare') == 'check'


def test_circlet_and_craft_do_not_borrow_other_slots_rules():
    assert verdict('circ', {'1862': 2, '520': 20}, 'magic') == 'check'
    assert verdict('circ', {'1862': 2, '520': 10}, 'magic') == 'vendor'
    assert verdict('amul', {'1862': 2, '520': 20}, 'crafted') == 'check'
    assert verdict('ring', {'1862': 2, '520': 20}, 'crafted') == 'vendor'


def test_boots_require_speed_and_two_resistances_with_low_rolls_kept_for_review():
    assert verdict('boot', {'480': 30, '427': 30, '428': 25}) == 'check'
    assert verdict('boot', {'480': 30, '427': 30, '428': 24}) == 'check'
    assert verdict('boot', {'480': 30, '427': 30}) == 'check'
    assert verdict('boot', {'480': 30, '427': 29}) == 'vendor'
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
        # Four sockets gate magic armor and shields on any base; a three-socket Deflecting shield also checks.
        # A lone 30 FRW circlet checks on any base and socket count (7 priced sellers, 2026-10-08).
        changes = {'shie': (), 'tors': ({'sockets': 3},), 'circ': () if props.get('480') == 30 else None}.get(family)
        if changes is None:
            changes = ({'sockets': sockets - 1}, {'base_name': 'Unknown'})
        for change in changes:
            assert assess(item | change, tables)['verdict'] == 'vendor'
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
    # +2 class skills alone gate a rare circlet; +1 with run speed does not.
    for changed in [
        movement | {'sockets': 1},
        movement | {'properties': {'453': 2, '480': 20}},
        item | {'properties': {'453': 2, '520': 10}},
    ]:
        assert assess(changed, tables)['verdict'] == 'check'
    assert assess(movement | {'properties': {'453': 1, '480': 30}}, tables)['verdict'] == 'vendor'


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
    # Magic +2 Javelin / 20 IAS is a listed low pattern; +2 Bow is not.
    assert assess(item | {'category': 'magic'}, tables)['verdict'] == 'check'
    assert assess(bow | {'category': 'magic'}, tables)['verdict'] == 'vendor'
    assert assess(bow, tables)['band'] is None


def test_crafted_amulet_lower_fcr_needs_two_useful_extras():
    from pricing.triage.engine import assess
    from pricing.triage.import_affixed_rules import affixed_rules

    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = {'category': 'crafted', 'family': 'amul', 'properties': {'514': 2, '520': 10, '418': 35, '428': 20}}
    assert assess(item, tables)['verdict'] == 'check'
    assert assess(item, tables)['band'] is None
    # Crafted +2 class skills with 10 FCR alone is listed by 22 priced sellers (2026-10-08).
    assert assess(item | {'properties': {'514': 2, '520': 10, '418': 35}}, tables)['verdict'] == 'check'
    for props in (
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
    # +2 class skills with 5%+ mana leech is itself a paid combination; only losing one of those two fails.
    for key in props:
        rest = {k: v for k, v in props.items() if k != key}
        assert assess(item | {'properties': rest}, tables)['verdict'] == (
            'vendor' if key in ('1862', '463') else 'check'
        )


PHYSICAL = [
    ('swor', 'Colossus Blade', 'Long Sword'),
    ('axe', 'Berserker Axe', 'Hand Axe'),
    ('mace', 'Scourge', 'Flail'),
    ('hamm', 'Legendary Mallet', 'Maul'),
    ('club', 'Truncheon', 'Club'),
    ('scep', 'Caduceus', 'War Scepter'),
    ('h2h', None, 'Katar'),  # this claw type has no elite base
    ('h2h2', 'Runic Talons', 'Greater Talons'),
    ('spea', 'War Pike', 'Pike'),
    ('pole', 'Thresher', 'Scythe'),
    ('jave', 'Ghost Glaive', 'Pilum'),
    ('ajav', 'Matriarchal Javelin', 'Ceremonial Javelin'),
    ('taxe', 'Winged Axe', 'Balanced Axe'),
    ('tkni', 'Flying Knife', 'War Dart'),
]


@pytest.mark.parametrize(('family', 'elite', 'lower'), PHYSICAL)
def test_rare_ethereal_weapon_is_gated_by_enhanced_damage_alone(family, elite, lower):
    # Scoped 2026-10-08 cache: speed, durability remedies, scaling stats and elite bases are not gates.
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = {'category': 'rare', 'family': family, 'base_name': elite or lower, 'ethereal': True, 'sockets': 0}
    if elite:
        result = assess(item | {'properties': {'510': 200}}, tables)
        assert result['verdict'] == 'check'
        assert result['band'] is None
        assert 'upgrade' not in result['reason']
    upgraded = assess(item | {'base_name': lower, 'properties': {'510': 200}}, tables)
    assert upgraded['verdict'] == 'check'
    assert 'review upgrade costs' in upgraded['reason']
    # Javelins have their own lower gates, and an ethereal magic sword is paid from 200%.
    below = {'510': 119, '457': 40} if family == 'jave' else {'510': 199, '457': 40, '431': 1}
    for change in (
        {'properties': below},
        {'ethereal': None, 'properties': {'510': 199 if family == 'jave' else 350}},
        {'base_name': 'Unknown', 'properties': {'510': 199 if family == 'jave' else 350}},
        {'category': 'magic', 'properties': {'510': 350}},
        {'category': 'crafted', 'properties': {'510': 350}},
    ):
        expected = 'check' if (family, change.get('category')) == ('swor', 'magic') else 'vendor'
        assert assess(item | change, tables)['verdict'] == expected
    plain = assess(item | {'ethereal': False, 'properties': {'510': 350, '457': 40}}, tables)['verdict']
    assert plain == ('check' if family in ('ajav', 'h2h2', 'jave') else 'vendor')


@pytest.mark.parametrize(
    ('family', 'base', 'gate'),
    [
        ('bow', 'Hydra Bow', 200),
        ('bow', 'Razor Bow', 200),
        ('abow', 'Matriarchal Bow', 200),
        ('xbow', 'Demon Crossbow', 300),
    ],
)
def test_rare_bow_is_gated_by_enhanced_damage_without_speed(family, base, gate):
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = {'category': 'rare', 'family': family, 'base_name': base, 'ethereal': False, 'sockets': 0}
    assert assess(item | {'properties': {'510': gate}}, tables)['verdict'] == 'check'
    assert assess(item | {'properties': {'510': gate - 1, '457': 20}}, tables)['verdict'] == 'vendor'


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
    # Three useful rolls carry a crafted ring without attack rating (30 priced sellers, 2026-10-08); two do not.
    assert assess(item | {'properties': {'462': 6, '418': 40, '437': 20}}, tables)['verdict'] == 'check'
    assert assess(item | {'properties': {'423': 110, '462': 6, '418': 40}}, tables)['verdict'] == 'vendor'
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
    # +2 class skills with 10 FCR needs no further support (7 priced sellers from 34 Ist, 2026-10-08).
    for props in ({'514': 2, '520': 10, '418': 39}, {'514': 2, '520': 10, '418': 0, '427': 14}):
        assert assess(amulet | {'properties': props}, tables)['verdict'] == 'check'
    for props in ({'514': 1, '520': 10, '418': 39, '427': 14}, {'514': 2, '520': 9, '418': 39, '427': 14}):
        assert assess(amulet | {'properties': props}, tables)['verdict'] == 'vendor'
    boots = {'category': 'rare', 'family': 'boot', 'properties': {'480': 30, '427': 30, '428': 24}}
    result = assess(boots, tables)
    assert result['verdict'] == 'check'
    assert 'lightning resistance 24 of 25' in result['reason']


def test_plain_phase_blade_fools_pattern_requires_both_scaling_stats_and_speed():
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    props = {'510': 250, '457': 30, '535': 40, '536': 1300}
    item = {
        'category': 'rare',
        'family': 'swor',
        'base_name': 'Phase Blade',
        'ethereal': False,
        'sockets': 0,
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
        {'base_name': 'Colossus Blade'},
        {'category': 'magic'},
        {'properties': props | {'510': 199}},
        {'properties': props | {'457': 20}},
    ):
        assert assess(item | change, tables)['verdict'] == 'vendor'


@pytest.mark.parametrize('skill', ['515', '516', '517', '443', '500', '1547', '1548'])
def test_paid_magic_tree_circlets_require_three_skills_and_twenty_fcr(skill):
    assert verdict('circ', {skill: 3, '520': 20}, 'magic') == 'check'
    assert verdict('circ', {skill: 2, '520': 20}, 'magic') == 'vendor'
    assert verdict('circ', {skill: 3, '520': 10}, 'magic') == 'vendor'
    assert verdict('circ', {skill: 3}, 'magic') == 'vendor'
    assert verdict('circ', {skill: 3, '520': 20}, 'rare') == 'check'
    assert verdict('circ', {skill: 3, '520': 10}, 'rare') == 'vendor'
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
        # Scoped rare-belt evidence: 24 FHR needs one companion, so only losing the recovery roll fails.
        # Rare boots keep CHECK on 30 FRW with one 30+ resistance.
        # Crafted belts check on 24 FHR or 20+ strength alone; crafted boots share the rare 30-FRW gate.
        kept = {
            ('rare', 'belt'): ('418', '437', '401'),
            ('rare', 'boot'): ('428',),
            ('crafted', 'belt'): ('430', '418', '437', '401'),
            ('crafted', 'boot'): ('428',),
        }.get((category, family), ())
        expected = 'check' if prop in kept else 'vendor'
        assert verdict(family, {k: v for k, v in properties.items() if k != prop}, category) == expected
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
        # +2 class skills alone gate a rare circlet, so losing cast rate keeps CHECK there.
        expected = 'check' if (family, prop) == ('circ', '520') else 'vendor'
        assert verdict(family, {k: v for k, v in properties.items() if k != prop}) == expected
    for prop in support:
        assert verdict(family, {k: v for k, v in properties.items() if k != prop}) == 'check'
    # A rare circlet with +1 class skills and 20 FCR is itself a reviewed pattern.
    assert verdict(family, {**properties, primary[0]: 1}) == ('check' if family == 'circ' else 'vendor')
    assert verdict(family, {**properties, primary[1]: 10}) == ('check' if family == 'circ' else 'vendor')


def test_plain_phase_blade_intrinsic_durability_preserves_physical_stat_gates():
    ethereal = False
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
    for change in ({'sockets': 3}, {'sockets': None}):
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
    # Four sockets plus a paid suffix gate every magic Paladin shield (11 priced sellers, 2026-10-08).
    for change in ({'properties': {'446': 20}}, {'properties': {'418': 60}}, {'base_name': 'Sacred Rondache'}):
        assert assess(item | change, tables)['verdict'] == 'check'
    for change in ({'sockets': 3}, {'category': 'rare', 'sockets': 1}, {'properties': {}}):
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
    # Rare circlets also check on +1 class with 20 FCR and on +2 class alone; gloves keep both gates.
    relaxed = 'check' if family == 'circ' else 'vendor'
    assert verdict(family, {skill: 1, speed: 20}) == relaxed
    assert verdict(family, {skill: 2, speed: 10}) == relaxed
    assert verdict(family, {skill: 1, speed: 10}) == 'vendor'
    assert verdict(family, {skill: 2}) == relaxed
    assert verdict('ring', {skill: 2, speed: 20}) == 'vendor'


def test_four_socket_magic_monarch_is_reviewable_without_deflecting_price():
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = {'category': 'magic', 'family': 'shie', 'base_name': 'Monarch', 'sockets': 4, 'properties': {}}
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert result['decision_ist'] is None
    for change in ({'sockets': 3}, {'category': 'rare', 'sockets': 1}):
        assert assess(item | change, tables)['verdict'] == 'vendor'
    assert assess(item | {'category': 'rare', 'sockets': 2}, tables)['verdict'] == 'check'


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
    assert assess(item | {'category': 'rare', 'sockets': 1}, tables)['verdict'] == 'vendor'


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
    # A lone 30 FRW circlet is listed by 7 priced sellers from 11.4 Ist (2026-10-08).
    assert assess(item | {'properties': {'480': 30}}, tables)['verdict'] == 'check'
    for properties in ({'480': 20}, {'441': 30}):
        assert assess(item | {'properties': properties}, tables)['verdict'] == 'vendor'


@pytest.mark.parametrize(
    ('support', 'minimum'), [('427', 15), ('428', 15), ('426', 15), ('401', 15), ('418', 40), ('526', 1)]
)
def test_primer_caster_amulet_accepts_one_strong_support_without_inventing_price(support, minimum):
    from pricing.triage.engine import assess
    from pricing.triage.import_affixed_rules import affixed_rules

    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = {'category': 'rare', 'family': 'amul', 'properties': {'514': 2, '520': 10, support: minimum}}
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert result['decision_ist'] is None
    # +2 class skills with 10 FCR stands alone since 2026-10-08; without the FCR the weak support fails.
    assert assess(item | {'properties': {'514': 2, '520': 10, support: minimum - 1}}, tables)['verdict'] == 'check'
    for properties in ({'514': 1, '520': 10, support: minimum - 1}, {'514': 2, '520': 9, support: minimum - 1}):
        assert assess(item | {'properties': properties}, tables)['verdict'] == 'vendor'


def test_blood_ring_support_pattern_does_not_require_rare_ring_attack_rating():
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}
    item = {'category': 'crafted', 'family': 'ring', 'properties': {'462': 1, '437': 10, '418': 30, '401': 10}}
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert result['decision_ist'] is None
    assert 'Blood ring' in result['reason']
    for prop in item['properties']:
        assert (
            assess(item | {'properties': {k: v for k, v in item['properties'].items() if k != prop}}, tables)['verdict']
            == 'vendor'
        )
    for changes in ({'437': 5, '418': 20}, {'437': 9}, {'418': 29}, {'401': 9}):
        assert assess(item | {'properties': item['properties'] | changes}, tables)['verdict'] == 'vendor'
    assert assess(item | {'category': 'rare'}, tables)['verdict'] == 'vendor'


def test_elemental_small_charms_keep_reviewed_damage_patterns_without_a_price():
    for poison in (175, 313, 451):
        assert verdict('scha', {'518': poison}, 'magic') == 'check'
    for damage in (44, 71):
        for life in (16, 20):
            assert verdict('scha', {'478': 1, '479': damage, '418': life}, 'magic') == 'check'
    for props in ({'518': 100}, {'479': 71}, {'479': 43, '418': 20}, {'479': 71, '418': 15}):
        assert verdict('scha', props, 'magic') == 'vendor'
    assert verdict('mcha', {'518': 175}, 'magic') == 'vendor'


@pytest.mark.parametrize('sellers', [1, 2])
def test_premium_rule_cannot_turn_sparse_asks_into_a_price(sellers):
    rule = {
        'category': 'magic',
        'name': 'Small Charm',
        'bucket': 'poison',
        'properties': {'518': {'min': 313}},
        'premium': True,
    }
    from pricing.triage.family_bands import roll_bucket

    item = {'category': 'magic', 'name': 'Small Charm', 'family': 'scha', 'properties': {'518': 451}}
    bucket = roll_bucket(rule, item)
    band = {
        'bucket': bucket,
        'q1_ist': 11,
        'median_ist': 11,
        'sellers': sellers,
        'liquidity': 'none',
        'observed_at': '2026-10-04',
    }
    tables = {
        'bands': {('family', 'small charm', bucket): band},
        'rules': {'keep_ist': 0.25, 'rows': [rule]},
        'own': {'rows': []},
    }
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert result['decision_ist'] is None
    assert result['band'] is None
    assert result['reference_band']['q1_ist'] == 11


@pytest.mark.parametrize('resist', ['427', '428', '426', '401'])
def test_large_charm_single_resistance_life_uses_its_own_guide_thresholds(resist):
    assert verdict('mcha', {resist: 13, '418': 30}, 'magic') == 'check'
    assert verdict('mcha', {resist: 15, '418': 35}, 'magic') == 'check'
    for props in ({resist: 12, '418': 35}, {resist: 15, '418': 29}, {resist: 15}, {'418': 35}):
        assert verdict('mcha', props, 'magic') == 'vendor'


def test_large_charm_sharp_shimmering_and_mana_patterns_are_not_life_only():
    for props in ({'448': 4, '423': 21}, {'448': 8, '423': 48}, {'441': 7}, {'400': 20, '418': 30}):
        # Captured/listed all-resistance is expanded by the shared adapter.
        if '441' in props:
            props |= dict.fromkeys(['427', '428', '426', '401'], props['441'])
        assert verdict('mcha', props, 'magic') == 'check'
    for props in ({'448': 3, '423': 48}, {'448': 6}, {'400': 19, '418': 35}, {'400': 34, '418': 29}):
        assert verdict('mcha', props, 'magic') == 'vendor'


@pytest.mark.parametrize(
    ('family', 'rarity', 'props', 'weaker'),
    [
        ('boot', 'rare', {'480': 20, '427': 20, '428': 20, '426': 20}, {'480': 10}),
        ('belt', 'rare', {'430': 24, '418': 40, '437': 15}, {'430': 16}),
        ('belt', 'crafted', {'430': 24, '418': 40, '566': 10, '462': 1}, {'430': 23}),
        ('glov', 'magic', {'455': 3, '457': 20}, {'455': 2}),
        ('glov', 'rare', {'455': 2, '457': 20, '428': 20}, {'457': 9}),
    ],
)
def test_scoped_equipment_patterns_require_the_complete_combination(family, rarity, props, weaker):
    assert verdict(family, props, rarity) == 'check'
    assert verdict(family, props | weaker, rarity) == 'vendor'
    # A rare belt keeps CHECK while 24 FHR has any one companion roll; +2 Passive gloves need only speed.
    required = {('belt', 'rare'): ['430'], ('belt', 'crafted'): ['430'], ('glov', 'rare'): ['455', '457']}.get(
        (family, rarity), props
    )
    for key in required:
        assert verdict(family, {k: v for k, v in props.items() if k != key}, rarity) == 'vendor'


@pytest.mark.parametrize('tree', ['1546', '1547', '1548'])
def test_grimoire_guide_tree_prefix_requires_three_levels_and_magic_book(tree):
    assert verdict('grim', {tree: 3}, 'magic') == 'check'
    assert verdict('grim', {tree: 2}, 'magic') == 'vendor'
    assert verdict('grim', {}, 'magic') == 'vendor'
    assert verdict('grim', {tree: 3}, 'rare') == 'vendor'
    assert verdict('shie', {tree: 3}, 'magic') == 'vendor'


def test_fhr_life_dual_resistance_belt_can_qualify_without_strength():
    properties = {'430': 24, '418': 60, '427': 30, '428': 30}
    assert verdict('belt', properties) == 'check'
    assert verdict('belt', {k: v for k, v in properties.items() if k != '430'}) == 'vendor'
    assert verdict('belt', properties | {'428': 24}) == 'check'


def test_rare_belt_needs_recovery_with_one_companion():
    # Scoped 2026-10-08 cache: 24 FHR with strength, life or one resistance; life is not a separate gate.
    for companion in ({'437': 15}, {'418': 30}, {'427': 20}, {'401': 20}):
        assert verdict('belt', {'430': 24} | companion, 'rare') == 'check'
    for weak in ({}, {'437': 14}, {'418': 29}, {'427': 19}, {'400': 40}):
        assert verdict('belt', {'430': 24} | weak, 'rare') == 'vendor'
    assert verdict('belt', {'430': 17, '418': 40}, 'rare') == 'check'
    assert verdict('belt', {'430': 17, '437': 20}, 'rare') == 'check'
    assert verdict('belt', {'430': 17, '418': 39, '437': 19, '427': 30}, 'rare') == 'vendor'
    assert verdict('belt', {'430': 10, '418': 60, '437': 30}, 'rare') == 'vendor'
    assert verdict('belt', {'437': 25, '428': 20}, 'rare') == 'check'
    assert verdict('belt', {'437': 24, '428': 20}, 'rare') == 'vendor'
    assert verdict('belt', {'437': 25, '428': 19}, 'rare') == 'vendor'
    assert verdict('belt', {'430': 24, '437': 15}, 'magic') == 'vendor'


def test_rare_speed_gloves_need_two_companions_but_no_skill_prefix():
    # Scoped 2026-10-08 cache: 38 priced sellers at two companions; one companion has a 1-Ist lower quartile.
    for pair in ({'427': 20, '428': 20}, {'426': 20, '462': 3}, {'437': 15, '429': 15}, {'461': 15, '463': 3}):
        assert verdict('glov', {'457': 20} | pair, 'rare') == 'check'
        assert verdict('glov', {'457': 10} | pair, 'rare') == 'vendor'
    for weak in ({}, {'427': 20}, {'427': 19, '428': 19, '437': 14}, {'418': 40, '400': 40}):
        assert verdict('glov', {'457': 20} | weak, 'rare') == 'vendor'
    assert verdict('glov', {'455': 2, '457': 10}, 'rare') == 'check'
    assert verdict('glov', {'455': 1, '457': 10}, 'rare') == 'vendor'
    assert verdict('glov', {'456': 2, '457': 10}, 'rare') == 'vendor'


def test_magic_armor_and_shields_are_gated_by_sockets_on_any_base():
    # Scoped 2026-10-08 cache: 63 priced sellers of suffixed four-socket magic armor, most on non-elite bases.
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}

    def result(family, base, sockets, properties=None, ethereal=False):
        item = {'category': 'magic', 'family': family, 'base_name': base, 'sockets': sockets, 'ethereal': ethereal}
        return assess(item | {'properties': properties or {}}, tables)['verdict']

    assert result('tors', 'Gothic Plate', 4, {'430': 24}) == 'check'
    assert result('tors', 'Gothic Plate', 4, {'418': 60}) == 'check'
    # No seller lists a bare four-socket body armor or shield (0 of 249 and 0 of 74 listings).
    assert result('tors', 'Gothic Plate', 4) == 'vendor'
    assert result('tors', 'Gothic Plate', 4, {'427': 30}) == 'vendor'
    assert result('tors', 'Gothic Plate', 3, {'418': 100}) == 'vendor'
    assert result('tors', 'Sacred Armor', 2, ethereal=True) == 'check'
    assert result('tors', 'Sacred Armor', 2) == 'vendor'
    assert result('shie', 'Ward', 4, {'419': 60}) == 'check'
    assert result('shie', 'Ward', 4) == 'vendor'
    assert result('ashd', 'Targe', 4, {'446': 20}) == 'check'
    assert result('ashd', 'Targe', 4, {'441': 30}) == 'vendor'
    assert result('shie', 'Tower Shield', 3, {'446': 20, '449': 30}) == 'check'
    assert result('shie', 'Kite Shield', 2, {'446': 20}) == 'check'
    assert result('shie', 'Tower Shield', 3) == 'vendor'
    assert result('shie', 'Tower Shield', 1, {'446': 20}) == 'vendor'
    assert result('helm', 'Crown', 3, {'418': 30}) == 'check'
    assert result('helm', 'Crown', 3, {'418': 29}) == 'vendor'
    assert result('helm', 'Armet', 0, {'431': 33}, ethereal=True) == 'check'
    assert result('helm', 'Spired Helm', 2, ethereal=True) == 'check'
    assert result('helm', 'Spired Helm', 2) == 'vendor'


def test_rare_circlet_class_prefix_gates_alone_while_trees_need_cast_rate():
    for prop in ('453', '442', '403', '1862'):
        assert verdict('circ', {prop: 2}, 'rare') == 'check'
        assert verdict('circ', {prop: 1}, 'rare') == 'vendor'
        assert verdict('circ', {prop: 1, '520': 20}, 'rare') == 'check'
    for tree in ('515', '443', '1547'):
        assert verdict('circ', {tree: 2, '520': 20}, 'rare') == 'check'
        assert verdict('circ', {tree: 2, '520': 10}, 'rare') == 'vendor'
    assert verdict('circ', {'480': 30, '520': 20}, 'rare') == 'check'
    assert verdict('circ', {'480': 20, '520': 20}, 'rare') == 'vendor'


def test_rare_boots_accept_high_resistances_with_reduced_or_no_run_speed():
    assert verdict('boot', {'427': 30, '428': 30, '401': 30}, 'rare') == 'check'
    assert verdict('boot', {'427': 30, '428': 30, '401': 29}, 'rare') == 'vendor'
    assert verdict('boot', {'480': 30, '428': 30}, 'rare') == 'check'
    assert verdict('boot', {'480': 30, '428': 29}, 'rare') == 'vendor'
    assert verdict('boot', {'480': 20, '428': 30, '426': 30}, 'rare') == 'check'
    assert verdict('boot', {'480': 20, '428': 30}, 'rare') == 'vendor'


def tables():
    return {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}}


def shaped(category, family, properties=None, sockets=0, ethereal=False):
    item = {'category': category, 'family': family, 'name': 'Example', 'sockets': sockets, 'ethereal': ethereal}
    return assess(item | {'properties': properties or {}}, tables())['verdict']


def test_magic_sword_is_gated_by_three_warcries_or_ethereal_damage():
    # Scoped 2026-10-08 cache: 40 priced sellers of +3 Warcries swords, lower quartile 4.1 Ist.
    assert shaped('magic', 'swor', {'406': 3}, sockets=2) == 'check'
    assert shaped('magic', 'swor', {'406': 3}) == 'check'
    assert shaped('magic', 'swor', {'406': 2}, sockets=2) == 'vendor'
    assert shaped('magic', 'swor', {'510': 200}, ethereal=True) == 'check'
    assert shaped('magic', 'swor', {'510': 299}) == 'vendor'
    assert shaped('magic', 'swor', {'431': 33}, ethereal=True) == 'check'
    assert shaped('magic', 'swor', {'431': 33}) == 'vendor'


@pytest.mark.parametrize('family', ['helm', 'tors', 'shie', 'ashd'])
def test_rare_generic_armor_needs_two_sockets_or_ethereal_self_repair(family):
    assert shaped('rare', family, {'418': 10}, sockets=2) == 'check'
    assert shaped('rare', family, {'418': 60, '427': 30}, sockets=1) == 'vendor'
    assert shaped('rare', family, {'431': 20}, ethereal=True) == 'check'
    assert shaped('rare', family, {'431': 20}) == 'vendor'
    assert shaped('rare', family, {'418': 60}, ethereal=True) == 'vendor'


def test_paladin_shields_accept_four_magic_sockets_or_forty_rare_resistances():
    assert shaped('magic', 'ashd', {'441': 26, '446': 20}, sockets=4) == 'check'
    assert shaped('magic', 'ashd', {'441': 26}, sockets=4) == 'vendor'
    assert shaped('magic', 'ashd', {'441': 26, '446': 20}, sockets=3) == 'vendor'
    assert shaped('rare', 'ashd', {'441': 40}) == 'check'
    assert shaped('rare', 'ashd', {'441': 39}) == 'vendor'


def test_rare_javelin_gates_sit_below_the_melee_damage_gate():
    # 37 priced sellers of ethereal 120 ED / 20 IAS javelins, lowest ask 4.1 Ist.
    assert shaped('rare', 'jave', {'510': 120, '457': 20}, ethereal=True) == 'check'
    assert shaped('rare', 'jave', {'510': 119, '457': 40}, ethereal=True) == 'vendor'
    assert shaped('rare', 'jave', {'510': 120}, ethereal=True) == 'vendor'
    assert shaped('rare', 'jave', {'563': 1}, ethereal=True) == 'check'
    assert shaped('rare', 'jave', {'563': 20}) == 'vendor'
    assert shaped('rare', 'jave', {'510': 200}) == 'check'
    assert shaped('rare', 'jave', {'510': 200}, ethereal=None) == 'vendor'
    assert shaped('rare', 'jave', {'510': 199, '457': 30}) == 'vendor'


def test_rare_staff_with_teleport_charges_is_reviewable():
    assert shaped('rare', 'staf', {'526': 1}) == 'check'
    assert shaped('rare', 'staf', {'520': 20}) == 'vendor'


def test_rare_amulet_skill_rolls_need_companions():
    # Bare +2 class skills asks 1 Ist and matches two stored drops; one companion lifts the lowest ask to 11 Ist.
    assert verdict('amul', {'514': 2, '418': 40}) == 'check'
    assert verdict('amul', {'514': 2, '427': 30}) == 'check'
    assert verdict('amul', {'514': 2, '418': 39}) == 'vendor'
    assert verdict('amul', {'403': 1, '520': 10, '400': 60}) == 'check'
    assert verdict('amul', {'403': 1, '418': 40}) == 'vendor'
    assert verdict('amul', {'408': 2, '418': 40, '441': 15}) == 'check'
    assert verdict('amul', {'408': 2, '418': 40}) == 'vendor'
    assert verdict('amul', {'418': 40, '441': 15, '437': 20}) == 'vendor'


def test_magic_tree_amulets_and_circlets_need_a_paid_suffix():
    assert verdict('amul', {'516': 3, '520': 10}, 'magic') == 'check'
    assert verdict('amul', {'487': 3, '418': 80}, 'magic') == 'check'
    assert verdict('amul', {'516': 3, '400': 20}, 'magic') == 'vendor'
    assert verdict('amul', {'516': 2, '520': 10}, 'magic') == 'vendor'
    assert verdict('circ', {'408': 3, '437': 25}, 'magic') == 'check'
    assert verdict('circ', {'515': 3, '413': 20}, 'magic') == 'check'
    assert verdict('circ', {'515': 3, '400': 20}, 'magic') == 'vendor'
    assert verdict('circ', {'480': 30}, 'magic') == 'check'
    assert verdict('circ', {'480': 20}, 'magic') == 'vendor'
    assert verdict('circ', {'520': 20}, 'magic') == 'vendor'
    assert verdict('circ', {'404': 3, '520': 20}, 'magic') == 'vendor'


def test_magic_two_skill_gloves_of_alacrity_are_limited_to_listed_trees():
    # guides/pricing.html §8: no seller lists a magic +2 Passive and Magic / 20 IAS pair.
    assert verdict('glov', {'456': 2, '457': 20}, 'magic') == 'check'
    assert verdict('glov', {'410': 2, '457': 20}, 'magic') == 'check'
    assert verdict('glov', {'455': 2, '457': 20}, 'magic') == 'vendor'
    assert verdict('glov', {'454': 2, '457': 20}, 'magic') == 'vendor'
    assert verdict('glov', {'456': 2, '457': 10}, 'magic') == 'vendor'


def test_rare_jewel_with_two_useful_rolls_is_reviewable():
    assert verdict('jewl', {'510': 20, '437': 6}) == 'check'
    assert verdict('jewl', {'441': 8, '429': 7}) == 'check'
    assert verdict('jewl', {'510': 20, '437': 5}) == 'vendor'


@pytest.mark.parametrize(
    ('family', 'paid', 'weaker'),
    [
        ('amul', {'514': 2, '520': 10}, {'514': 2}),
        ('amul', {'408': 2, '418': 40, '400': 60}, {'408': 2, '418': 40}),
        ('belt', {'430': 24}, {'430': 17}),
        ('belt', {'437': 20}, {'437': 19}),
        ('ring', {'437': 18, '429': 10, '418': 40}, {'429': 10, '418': 40}),
        ('ring', {'437': 18, '462': 5}, {'437': 18}),
        ('glov', {'456': 2, '457': 20}, {'456': 2, '457': 10}),
        ('glov', {'457': 20, '437': 15}, {'457': 20}),
        ('glov', {'437': 15, '462': 3}, {'437': 15}),
        ('boot', {'480': 30, '461': 20}, {'480': 30}),
        ('boot', {'480': 20, '427': 30, '428': 30}, {'480': 20, '427': 30}),
    ],
)
def test_crafted_gates_are_looser_than_rare_ones_but_still_need_the_combination(family, paid, weaker):
    assert verdict(family, paid, 'crafted') == 'check'
    assert verdict(family, weaker, 'crafted') == 'vendor'
