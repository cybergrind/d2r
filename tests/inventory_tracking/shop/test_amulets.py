import pytest

from inventory_tracking.shop.rules import match_item
from tests.inventory_tracking.shop.test_rules import observation


@pytest.mark.parametrize('layer', [8, 9, 10, 17, 18, 24, 34, 40, 42, 48, 49, 57, 58])
def test_a_plain_or_cast_rate_three_skill_amulet_stays_in_the_shop(layer):
    # 2026-10-22: a plain +3 tree asks a median of 0.57 (20 sellers), with 10 FCR 7.6 (14): not a vendor buy
    assert not match_item(observation('Amulet', [(188, layer, 3)]))
    assert not match_item(observation('Amulet', [(188, layer, 3), (105, 0, 10)]))


@pytest.mark.parametrize(
    ('layer', 'stat', 'raw', 'label'),
    [(40, 7, 81 * 256, '81 life'), (8, 80, 30, '30 MF'), (58, 0, 25, '25 strength'), (57, 2, 30, '30 dexterity')],
)
def test_a_three_skill_amulet_with_a_big_suffix_alerts(layer, stat, raw, label):
    reasons = match_item(observation('Amulet', [(188, layer, 3), (stat, 0, raw)]))
    assert len(reasons) == 1
    assert label in reasons[0]


def test_summoning_classes_are_distinguished_and_unknown_bonus_does_not_alert():
    necro = match_item(observation('Amulet', [(188, 18, 3), (80, 0, 30)]))[0]
    druid = match_item(observation('Amulet', [(188, 40, 3), (80, 0, 30)]))[0]
    assert 'Necromancer' in necro
    assert 'Druid' in druid
    item = observation('Amulet', [(188, 18, 3), (80, 0, 30)])
    item['unresolved_stats'] = [{'id': 188, 'layer': 18, 'raw': 3}]
    assert not match_item(item)


@pytest.mark.parametrize('kwargs', [{'rarity': 'rare'}, {'identified': False}])
def test_magic_tree_review_does_not_accept_other_quality_or_unidentified(kwargs):
    assert not match_item(observation('Amulet', [(188, 18, 3), (80, 0, 30)], **kwargs))


def test_unreviewed_trees_and_wrong_item_type_stay_out():
    assert not match_item(observation('Amulet', [(188, 16, 3), (80, 0, 30)]))
    assert not match_item(observation('Ring', [(188, 18, 3), (80, 0, 30)]))
    assert not match_item(observation('Amulet', [(83, 2, 2)]))
