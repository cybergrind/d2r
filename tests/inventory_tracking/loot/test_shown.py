"""What the pickup step takes because the loot filter shows it: the filter's Show rules by item class."""

import json
from pathlib import Path

from inventory_tracking.items.identity import ETHEREAL_FLAG, IDENTIFIED_FLAG, SOCKETED_FLAG
from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot.shown import (
    FILTER,
    ShownRule,
    filter_rules,
    game_filter,
    hides,
    oversize_rules,
    pickup_rules,
    shown_gems,
    shown_label,
)


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


def test_an_armor_or_a_weapon_no_rule_shows_is_hidden():
    rules = (ShownRule(frozenset({7}), False, classes('uap')),)

    assert not hides(rules, BY_CODE['uap'], 7)
    assert hides(rules, BY_CODE['uap'], 5)  # shown as a unique only
    assert hides(rules, BY_CODE['skp'], 7)
    assert not hides(rules, BY_CODE['rin'], 7)  # the accessories rule shows every ring


def test_the_gems_a_show_rule_lists_are_shown_by_code_or_all_by_the_category(tmp_path):
    # user, 2026-10-12: chipped gems enabled in the game's filter editor
    path = filter_file(
        tmp_path,
        {'itemCode': ['gcv', 'skc', 'hp5'], 'itemCategory': ['runes']},
        {'itemCode': ['gpw'], 'enabled': False},
        {'itemCode': ['gfb'], 'ruleType': 'hide'},
    )

    assert shown_gems(path) == {BY_CODE['gcv']: 'Chipped Amethyst', BY_CODE['skc']: 'Chipped Skull'}
    every = filter_file(tmp_path, {'itemCategory': ['gems']})
    assert len(shown_gems(every)) == 35


def test_the_games_copy_of_the_profile_is_read_where_there_is_one(tmp_path):
    path = tmp_path / 'profile.json'
    path.write_text(json.dumps({'name': 'Lean', 'rules': []}))
    assert game_filter(path, tmp_path) == path
    (tmp_path / 'Lean.fltr').write_text('{}')
    assert game_filter(path, tmp_path) == tmp_path / 'Lean.fltr'


D2DATA = Path('third-parties/d2data/json/base')


def d2data_codes(file, *names):
    """The base codes of `names` in the d2data dump (the lootfilter skill: never a code from memory)."""
    by_name = {row['name']: code for code, row in json.loads((D2DATA / file).read_text()).items()}
    return [by_name[name] for name in names]


def repository_rule(name):
    [found] = [rule for rule in json.loads(FILTER.read_text())['rules'] if rule['name'] == name]
    return found


def test_the_2026_10_20_show_rules_list_the_d2data_codes_of_their_bases():
    # The player, 2026-10-20 ~13:00: "add the filter show rules too" (loot/design.md §9: G15, G17)
    cure = d2data_codes('armor.json', 'Corona', 'Spired Helm', 'Bone Visage', 'Demonhead')
    polearms = d2data_codes(
        'weapons.json', 'Thresher', 'Giant Thresher', 'Cryptic Axe', 'Great Poleaxe', 'Colossus Voulge', 'Mancatcher'
    )
    amazon = d2data_codes(
        'weapons.json',
        'Matriarchal Bow',
        'Grand Matron Bow',
        'Ceremonial Pike',
        'Matriarchal Spear',
        'Matriarchal Pike',
    )
    assert repository_rule('SHOW Cure Helms Gray')['equipmentItemCode'] == cure
    assert repository_rule('SHOW Rare Merc Polearms')['equipmentItemCode'] == polearms
    assert repository_rule('SHOW Magic Amazon Bows Spears')['equipmentItemCode'] == amazon
    # gray only: an elite base is never low quality (itemratio.json "Uber": Normal 1, NormalDivisor 1)
    assert repository_rule('SHOW Cure Helms Gray')['equipmentRarity'] == ['lowQuality']
    assert repository_rule('SHOW Cure Helms Gray')['filterEtherealSocketed'] is True


def test_the_repositorys_filter_shows_the_cure_helms_the_big_field_items_and_keeps_monarchs_and_circlets():
    small, every = pickup_rules(6), filter_rules()
    field = oversize_rules(6, frozenset((4, 6)))

    def label(rules, code, quality, flags=0):
        return shown_label(rules, BY_CODE[code], quality, flags)

    # G17 Cure bases: eth (any sockets, normal or superior) and socketed copies; plain and 0os Superior hidden
    assert label(small, 'urn', 2, WHITE | ETHEREAL_FLAG) == 'Ethereal Corona'
    assert label(small, 'uhm', 3, WHITE | ETHEREAL_FLAG | SOCKETED_FLAG) == 'Ethereal Socketed Superior Spired Helm'
    assert label(small, 'uh9', 2, WHITE | SOCKETED_FLAG) == 'Socketed Bone Visage'  # the filter cannot ask for eth
    assert label(small, 'usk', 2, WHITE) is None
    assert label(small, 'urn', 3, WHITE) is None
    # A rare Corona-line helm can roll no FCR and no +class skills (magicprefix/magicsuffix.json): still hidden
    assert all(label(every, code, 6) is None for code in ('urn', 'uhm', 'uh9', 'usk'))
    # G15: rare merc polearms and magic Amazon bows / spears, 2x4, for the field identify only (over the cell cap)
    for code, quality, name in (('7wc', 6, 'Rare Giant Thresher'), ('7br', 6, 'Rare Mancatcher')):
        assert label(field, code, quality) == name
        assert label(small, code, quality) is None
    assert label(field, 'amc', 4) == 'Magic Grand Matron Bow'
    assert label(field, 'amd', 4) == 'Magic Matriarchal Spear'
    assert label(every, '7wc', 4) is None  # magic polearms: no wants row, no scoped trade
    # Unchanged: rare circlets of every tier, white 4os and Superior Monarchs, eth polearm bases
    assert all(
        label(small, code, 6) == f'Rare {BASES[str(BY_CODE[code])]["name"]}' for code in ('ci0', 'ci1', 'ci2', 'ci3')
    )
    assert label(small, 'uit', 2, WHITE | SOCKETED_FLAG) == 'Socketed Monarch'
    assert label(small, 'uit', 3, WHITE) == 'Superior Monarch'
    assert label(oversize_rules(6, frozenset((2, 3))), '7wc', 2, WHITE | ETHEREAL_FLAG) == 'Ethereal Giant Thresher'


def test_the_repositorys_filter_keeps_the_players_chipped_and_flawed_gems():
    # The player enabled them in the game's editor (2026-10-12); a re-import must not take them away
    gems = set(shown_gems(FILTER).values())
    assert {'Chipped Amethyst', 'Flawed Ruby', 'Chipped Skull', 'Flawless Topaz', 'Perfect Skull'} <= gems
    assert len(gems) == 28
