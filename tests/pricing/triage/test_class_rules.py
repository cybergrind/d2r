import pytest

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
    item['properties'] = {'453': 1, '454': 3, '457': 40}
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


def test_warlock_dagger_class_prefix_checks_without_a_staffmod_or_support_gate():
    # Scoped 2026-10-08 cache: nine priced sellers list +2 Warlock daggers, none below keep.
    for category in ('magic', 'rare'):
        assert verdict('knif', {'1862': 2}, category)['verdict'] == 'check'
        assert verdict('knif', {'1862': 2, '1574': 3}, category, base_name='Dirk')['verdict'] == 'check'
        for props in ({'1862': 1, '1565': 3, '457': 20}, {'1565': 3, '457': 20}):
            assert verdict('knif', props, category)['verdict'] == 'vendor'


def test_warlock_dagger_tree_prefix_needs_the_full_roll_for_its_rarity():
    for tree in ('1546', '1547', '1548'):
        assert verdict('knif', {tree: 3})['verdict'] == 'check'
        assert verdict('knif', {tree: 2})['verdict'] == 'vendor'
        assert verdict('knif', {tree: 2}, 'rare', base_name='Poignard')['verdict'] == 'check'
        assert verdict('knif', {tree: 1}, 'rare')['verdict'] == 'vendor'


def test_magic_dagger_with_three_warcries_is_a_buff_switch_candidate():
    assert verdict('knif', {'406': 3}, base_name='Kriss')['verdict'] == 'check'
    assert verdict('knif', {'406': 2}, base_name='Kriss')['verdict'] == 'vendor'
    assert verdict('knif', {'406': 3}, 'rare', base_name='Kriss')['verdict'] == 'vendor'


def test_rare_physical_dagger_is_gated_by_enhanced_damage_not_leech():
    def rare(props, **fields):
        return verdict('knif', props, 'rare', base_name='Mithral Point', **fields)['verdict']

    assert rare({'510': 200}, ethereal=True) == 'check'
    assert rare({'510': 199, '457': 40}, ethereal=True) == 'vendor'
    assert rare({'510': 299, '457': 40}, ethereal=False) == 'vendor'
    assert rare({'510': 300}, ethereal=False) == 'check'
    assert verdict('knif', {'510': 300}, 'magic', base_name='Mithral Point', ethereal=True)['verdict'] == 'vendor'


@pytest.mark.parametrize('category', ['magic', 'rare'])
def test_grimoire_class_prefix_is_the_only_gate(category):
    assert verdict('grim', {'1862': 2}, category, sockets=0)['verdict'] == 'check'
    assert verdict('grim', {'1862': 2, '446': 20}, category, sockets=0)['verdict'] == 'check'
    assert verdict('grim', {'1862': 1, '441': 20, '418': 30}, category, sockets=2)['verdict'] == 'vendor'


def test_rare_grimoire_tree_prefix_needs_a_paid_staffmod():
    for tree in ('1546', '1547', '1548'):
        assert verdict('grim', {tree: 2, '1554': 3}, 'rare')['verdict'] == 'check'
        assert verdict('grim', {tree: 2, '1554': 2}, 'rare')['verdict'] == 'vendor'
        assert verdict('grim', {tree: 1, '1554': 3}, 'rare')['verdict'] == 'vendor'
        assert verdict('grim', {tree: 2, '1554': 3}, 'magic')['verdict'] == 'vendor'


def test_class_rule_does_not_apply_to_generic_weapon_or_different_rarity():
    props = {'1862': 2, '1565': 3, '457': 20}
    assert verdict('knif', props)['verdict'] == 'check'
    assert verdict('axe', props)['verdict'] == 'vendor'
    assert verdict('knif', props, 'unique')['verdict'] == 'vendor'


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
    assert verdict('knif', props, 'rare', base_name='Dirk', ethereal=True)['verdict'] == 'vendor'


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
    # +2 Paladin skills alone gate a rare Paladin shield on any base.
    for changed in [item | {'base_name': 'Targe'}, item | {'sockets': 0}, item | {'properties': {'442': 2, '418': 20}}]:
        assert assess(changed, tables)['verdict'] == 'check'
    assert assess(item | {'properties': {'442': 1, '441': 30, '418': 20}}, tables)['verdict'] == 'vendor'
    block = item | {'properties': {'442': 2, '449': 30, '430': 17}}
    assert assess(block, tables)['verdict'] == 'check'
    assert assess(item | {'category': 'magic'}, tables)['verdict'] == 'vendor'


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


def test_magic_javelin_lower_class_roll_keeps_full_paid_pattern_for_review():
    assert verdict('ajav', {'453': 1, '456': 3, '457': 40})['verdict'] == 'check'
    assert verdict('ajav', {'456': 3, '457': 40})['verdict'] == 'vendor'
    assert verdict('ajav', {'453': 1, '454': 3, '457': 40})['verdict'] == 'vendor'


def test_fire_blast_planner_claw_is_a_review_candidate_without_borrowed_price():
    from pricing.triage.guide_cases import item_from_spec

    spec = {
        'base': 'Greater Claws',
        'rarity': 'magic',
        'ethereal': False,
        'sockets': 2,
        'stats': {'188:48': 3, '93:0': 40, '107:251': 3, '107:263': 3},
    }
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': class_rules()}, 'own': {'rows': []}}
    result = assess(item_from_spec(spec), tables)
    assert result['verdict'] == 'check'
    assert result['decision_ist'] is None
    # Fire Blast is not a skill sellers price, so every part of the planner claw is required.
    stats = {k: v for k, v in spec['stats'].items() if k != '188:48'}
    assert assess(item_from_spec(spec | {'stats': stats}), tables)['verdict'] == 'vendor'
    assert assess(item_from_spec(spec | {'sockets': 1}), tables)['verdict'] == 'vendor'


# family, class prefix, tree prefix, paid skill of that tree, skill of another tree, unpaid skill of that tree
SUMMED = [
    ('phlm', '403', '406', '765', '997', '989'),
    ('pelt', '488', '487', '972', '974', '967'),
    ('head', '498', '500', '1024', None, '1020'),
    ('wand', '498', '500', '756', None, '1020'),
    ('orb', '514', '516', '598', '602', '677'),
    ('scep', '442', '443', '581', None, '1047'),
    ('h2h2', '519', '408', '1073', '1079', '1068'),
]


@pytest.mark.parametrize(('family', 'class_prefix', 'tree', 'paid', 'other_tree', 'unpaid'), SUMMED)
@pytest.mark.parametrize('category', ['magic', 'rare'])
def test_class_items_need_five_to_one_paid_skill(category, family, class_prefix, tree, paid, other_tree, unpaid):
    # Scoped 2026-10-08 cache: under +5 to one skill the pooled magic listings ask a 10-Ist median against 69.
    def check(properties, expected):
        assert verdict(family, properties, category, sockets=0)['verdict'] == expected

    check({class_prefix: 2, paid: 3}, 'check')
    check({tree: 2, paid: 3}, 'check')
    # A magic tree prefix rolls to +3, so +2 on the skill already sums to five.
    check({tree: 3, paid: 2}, 'check' if category == 'magic' else 'vendor')
    for short in ({class_prefix: 2}, {tree: 3}, {paid: 3}, {class_prefix: 2, paid: 2}, {class_prefix: 1, paid: 3}):
        check(short, 'vendor')
    check({tree: 2, paid: 2}, 'vendor')
    # A skill that only rides along on listings sold for another one does not count.
    check({class_prefix: 2, unpaid: 3}, 'vendor')
    check({tree: 3, unpaid: 3}, 'vendor')
    if other_tree:
        # The tree prefix adds nothing to a skill of another tree; the class prefix adds to all.
        check({tree: 3, other_tree: 3}, 'vendor')
        check({class_prefix: 2, other_tree: 3}, 'check')
    assert verdict('axe', {class_prefix: 2, paid: 3}, category, sockets=0)['verdict'] == 'vendor'


@pytest.mark.parametrize(
    ('family', 'category', 'prefix'), [('ashd', 'rare', '442'), ('h2h', 'rare', '519'), ('ajav', 'magic', '453')]
)
def test_class_prefix_alone_gates_items_that_carry_no_staffmods(family, category, prefix):
    assert verdict(family, {prefix: 2}, category, sockets=0)['verdict'] == 'check'
    assert verdict(family, {prefix: 1, '418': 40}, category, sockets=0)['verdict'] == 'vendor'


def test_rare_class_items_under_five_are_gated_by_two_sockets_not_by_one_or_by_magic():
    for family in ('phlm', 'pelt', 'h2h2'):
        assert verdict(family, {}, 'rare', sockets=2)['verdict'] == 'check'
        assert verdict(family, {}, 'rare', sockets=1)['verdict'] == 'vendor'
        assert verdict(family, {}, 'magic', sockets=2)['verdict'] == 'vendor'
    for family in ('head', 'orb', 'wand', 'scep'):
        assert verdict(family, {}, 'rare', sockets=2)['verdict'] == 'vendor'
    assert verdict('phlm', {'431': 20}, 'rare', sockets=0, ethereal=True)['verdict'] == 'check'
    assert verdict('phlm', {'431': 20}, 'rare', sockets=0, ethereal=False)['verdict'] == 'vendor'
    assert verdict('phlm', {'765': 3}, 'rare', sockets=0, ethereal=True)['verdict'] == 'vendor'


def test_rare_grimoire_with_two_warlock_skills_checks_without_a_staffmod():
    result = verdict('grim', {'1862': 2}, 'rare', base_name='Codex', sockets=0)
    assert result['verdict'] == 'check'
    assert result['decision_ist'] is None
    short = {'1862': 1, '1579': 3, '1578': 2}
    assert verdict('grim', short, 'rare', base_name='Codex', sockets=0)['verdict'] == 'vendor'


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


def test_sorceress_orb_with_class_skills_and_cast_rate_checks_without_a_staffmod():
    for category in ('magic', 'rare'):
        assert verdict('orb', {'514': 2, '520': 20}, category, sockets=0)['verdict'] == 'check'
        assert verdict('orb', {'514': 2, '520': 10}, category, sockets=0)['verdict'] == 'vendor'
        assert verdict('orb', {'516': 3, '520': 20}, category, sockets=0)['verdict'] == 'vendor'
