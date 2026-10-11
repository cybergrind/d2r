"""What the pickup step takes because the loot filter shows it: the filter's Show rules by item class."""

import json

from inventory_tracking.items.identity import ETHEREAL_FLAG, IDENTIFIED_FLAG, SOCKETED_FLAG
from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot.shown import ShownRule, filter_rules, pickup_rules, shown_label


BASES = metadata()['bases']
BY_CODE = {base['code']: int(class_id) for class_id, base in BASES.items()}
WHITE = IDENTIFIED_FLAG  # a white item is always identified


def classes(*codes):
    return frozenset(BY_CODE[code] for code in codes)


def filter_file(tmp_path, *rules):
    path = tmp_path / 'filter.json'
    path.write_text(json.dumps({'rules': [{'enabled': True, 'ruleType': 'show'} | rule for rule in rules]}))
    return path


def test_show_rules_are_read_by_rarity_category_and_item_code(tmp_path):
    path = filter_file(
        tmp_path,
        {'equipmentRarity': ['unique'], 'equipmentItemCode': ['7pa']},
        {'equipmentRarity': ['rare'], 'equipmentCategory': ['circl'], 'equipmentItemCode': ['7kr']},
        {'equipmentRarity': ['hiQuality'], 'filterEtherealSocketed': True, 'equipmentItemCode': ['uit']},
        {'equipmentRarity': ['unique'], 'equipmentItemCode': ['hax'], 'enabled': False},
        {'equipmentRarity': ['unique'], 'equipmentItemCode': ['cap'], 'ruleType': 'hide'},
        {'equipmentRarity': ['magic', 'rare'], 'equipmentCategory': ['acce'], 'itemCode': ['gpw']},  # materials.py
        {'itemCode': ['hp5']},
    )

    assert filter_rules(path) == (
        ShownRule(frozenset({7}), False, classes('7pa')),
        ShownRule(frozenset({6}), False, classes('ci0', 'ci1', 'ci2', 'ci3', '7kr')),
        ShownRule(frozenset({3}), True, classes('uit')),
    )


def test_below_set_quality_only_the_smaller_bases_are_taken(tmp_path):
    # user, 2026-10-11: "prefer smaller types". Cryptic Axe 2x4, Monarch 2x3, Fanged Knife 1x3, Circlet 2x2.
    path = filter_file(
        tmp_path,
        {'equipmentRarity': ['unique'], 'equipmentItemCode': ['7pa', 'uit']},
        {'equipmentRarity': ['rare'], 'equipmentItemCode': ['7pa', 'uit', '7kr', 'ci0']},
        {'equipmentRarity': ['magic'], 'equipmentItemCode': ['uit']},
    )

    assert pickup_rules(4, path) == (
        ShownRule(frozenset({7}), False, classes('7pa', 'uit')),
        ShownRule(frozenset({6}), False, classes('7kr', 'ci0')),
    )
    assert len(pickup_rules(8, path)) == 3


def test_an_item_is_matched_as_the_game_matches_it():
    rules = (
        ShownRule(frozenset({6}), False, classes('7kr')),
        ShownRule(frozenset({3}), True, classes('ci0')),  # superior, and the gray ones
        ShownRule(frozenset({2, 3}), True, classes('wa1')),
    )
    kriss, circlet, book = BY_CODE['7kr'], BY_CODE['ci0'], BY_CODE['wa1']

    assert shown_label(rules, kriss, 6, 0) == 'Rare Fanged Knife'
    assert shown_label(rules, kriss, 6, IDENTIFIED_FLAG) is None  # read and dropped by the player
    assert shown_label(rules, kriss, 4, 0) is None
    assert shown_label(rules, kriss, 2, WHITE | SOCKETED_FLAG) is None  # the rare rule has no gray items
    assert shown_label(rules, circlet, 3, WHITE) == 'Superior Circlet'
    assert shown_label(rules, circlet, 2, WHITE) is None  # a plain white one
    assert shown_label(rules, circlet, 2, WHITE | SOCKETED_FLAG) == 'Socketed Circlet'
    assert shown_label(rules, circlet, 1, WHITE | ETHEREAL_FLAG) == 'Ethereal Low Quality Circlet'
    assert shown_label(rules, circlet, 4, ETHEREAL_FLAG) is None  # gray is a white item only
    assert shown_label(rules, book, 2, WHITE) == BASES[str(book)]['name']
    assert shown_label(rules, BY_CODE['hax'], 6, 0) is None


def test_the_repositorys_filter_gives_the_pickup_the_sold_uniques_and_what_a_warlock_uses():
    # 2026-10-09 trades: Tomb Reaver (Cryptic Axe) 4.55 Ist; the old ask table of the marks lacked its base
    rules = pickup_rules(6)

    def label(code, quality, flags=0):
        return shown_label(rules, BY_CODE[code], quality, flags)

    assert label('7pa', 7) == 'Unique Cryptic Axe'
    assert label('7pa', 6) is None
    assert label('uar', 5) == 'Set Sacred Armor'
    # A Warlock's own: grimoires of every quality, the dagger line (user, 2026-10-11)
    assert all(label('wa1', quality, WHITE if quality < 4 else 0) for quality in (2, 3, 4, 6))
    assert all(label('7kr', quality, WHITE if quality < 4 else 0) for quality in (2, 4, 6))
    # Small rares and magics of the other classes and slots
    assert label('ne5', 6) == 'Rare Demon Head'
    assert label('hgl', 4) == 'Magic Gauntlets'
    assert label('hgl', 2, WHITE) is None
    assert label('uit', 4) == 'Magic Monarch'  # 2x3: taken since the limit is 6 cells
    # Shown by the filter, left to the player's own click: 2x4
    assert label('7gd', 6) is None  # Colossus Blade
