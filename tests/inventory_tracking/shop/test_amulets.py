import pytest

from inventory_tracking.shop.rules import match_item
from tests.inventory_tracking.shop.test_rules import observation


@pytest.mark.parametrize('layer', [8, 9, 10, 17, 18, 24, 34, 40, 42, 48, 49, 57, 58])
def test_reviewed_plain_three_skill_amulets_alert_without_enabling_starter_catalog(layer):
    reasons = match_item(observation('Amulet', [(188, layer, 3)]))
    assert any(r.startswith('Build use:') for r in reasons)
    assert not match_item(observation('Amulet', [(188, layer, 2)]))


@pytest.mark.parametrize(
    ('layer', 'stat', 'raw', 'label'),
    [(18, 105, 10, '10 FCR'), (40, 7, 81 * 256, '81 life'), (8, 80, 26, '26 MF'), (34, 79, 80, '80 gold find')],
)
def test_good_suffix_is_visible_in_single_build_review_reason(layer, stat, raw, label):
    reasons = match_item(observation('Amulet', [(188, layer, 3), (stat, 0, raw)]))
    assert len(reasons) == 1
    assert reasons[0].startswith('Build review:')
    assert label in reasons[0]


def test_summoning_classes_are_distinguished_and_unknown_bonus_does_not_alert():
    necro = match_item(observation('Amulet', [(188, 18, 3)]))[0]
    druid = match_item(observation('Amulet', [(188, 40, 3)]))[0]
    assert 'Necromancer' in necro
    assert 'Druid' in druid
    item = observation('Amulet', [(188, 18, 3)])
    item['unresolved_stats'] = [{'id': 188, 'layer': 18, 'raw': 3}]
    assert not match_item(item)


@pytest.mark.parametrize('kwargs', [{'rarity': 'rare'}, {'identified': False}])
def test_magic_tree_review_does_not_accept_other_quality_or_unidentified(kwargs):
    assert not match_item(observation('Amulet', [(188, 18, 3)], **kwargs))


def test_unreviewed_trees_and_wrong_item_type_stay_out():
    assert not match_item(observation('Amulet', [(188, 16, 3)]))
    assert not match_item(observation('Ring', [(188, 18, 3)]))
    assert not match_item(observation('Amulet', [(83, 2, 2)]))
