import pytest

from inventory_tracking.shop.rules import match_item, skill_targets
from inventory_tracking.shop.staffmods import GROUPS, PRIMARY_SKILLS
from tests.inventory_tracking.shop.test_rules import observation, skill


@pytest.mark.parametrize('name', sorted(PRIMARY_SKILLS))
def test_reviewed_primary_requires_same_class_or_full_tree_prefix(name):
    target = next(t for t in skill_targets() if t['name'] == name)
    base = {
        1: 'Eldritch Orb',
        2: 'Bone Wand',
        3: 'War Scepter',
        4: 'Slayer Guard',
        5: 'Antlers',
        6: 'Greater Talons',
        7: 'Kriss',
    }[target['class_id']]
    native = (107, target['id'], 3)
    for prefix, total in [((83, target['class_id'], 2), 5), ((188, target['tab_layer'], 3), 6)]:
        item = observation(base, [prefix, native])
        assert not item['unresolved_stats']
        assert any(f'+{total} {name} (' in r for r in match_item(item))
    for prefix in [
        (188, target['tab_layer'], 2),
        (83, (target['class_id'] + 1) % 8, 2),
        (188, target['class_id'] * 8 + (target['tab_layer'] % 8 + 1) % 3, 3),
    ]:
        # No other standalone pattern on these bases can bypass the threshold.
        assert not match_item(observation(base, [prefix, native]))


@pytest.mark.parametrize(
    'name',
    [
        'Teleport',
        'Telekinesis',
        'Warmth',
        'Poison Explosion',
        'Find Potion',
        'Battle Command',
        'Blade Warp',
        'Levitation Mastery',
    ],
)
def test_utility_synergy_or_companion_alone_does_not_trigger(name):
    target = next(t for t in skill_targets() if t['name'] == name)
    base = {1: 'Eldritch Orb', 2: 'Bone Wand', 4: 'Slayer Guard', 7: 'Kriss'}[target['class_id']]
    assert not match_item(observation(base, [(83, target['class_id'], 2), (107, target['id'], 3)]))


def test_companions_are_labeled_only_for_a_qualifying_related_primary():
    item = observation(
        'Eldritch Orb',
        [(188, 8, 3), (107, skill('Enchant'), 3), (107, skill('Fire Mastery'), 3), (107, skill('Cold Mastery'), 3)],
    )
    reasons = match_item(item)
    assert len(reasons) == 1
    assert '+6 Enchant' in reasons[0]
    assert 'also +3 Fire Mastery' in reasons[0]
    assert 'Cold Mastery' not in reasons[0]
    item['unresolved_stats'] = [{'id': 188, 'layer': 8, 'raw': 3}]
    assert not match_item(item)


def test_all_reviewed_names_resolve_to_native_catalog():
    names = {t['name'] for t in skill_targets()}
    assert {name for primary, companions in GROUPS for name in (*primary, *companions)} <= names
