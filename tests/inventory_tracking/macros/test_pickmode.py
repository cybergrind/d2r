"""The KP_6 loop's pickup mode (macros/pickmode.py; routes/lower-kurast-loop-plan.md phase 7). Item classes by their
items.txt row as the bundled metadata names them (items/metadata.py `item_base`), looked up, not written from memory."""

from dataclasses import replace

import pytest

from inventory_tracking.game.records import GOLD, HEALING, VALUABLE, Drop, Loot, Rolls
from inventory_tracking.items.metadata import metadata
from inventory_tracking.macros.pickmode import (
    MODES,
    MOST,
    SURE,
    is_candidate,
    kept,
    next_mode,
    sure,
)


def class_of(name: str) -> int:
    [found] = [int(cid) for cid, base in metadata()['bases'].items() if base['name'] == name]
    return found


def drop(name: str, *, source: str = 'material', quality: int = 2, kind: str = VALUABLE, prized: bool = False) -> Drop:
    return Drop(class_of(name), 0.0, 0.0, name, kind, prized=prized, source=source, txt=class_of(name), quality=quality)


def test_every_rune_gem_and_charm_is_a_sure_valuable():
    for name in ('El Rune', 'Ber Rune', 'Chipped Amethyst', 'Perfect Skull', 'Flawed Topaz', 'Small Charm',
                 'Large Charm', 'Grand Charm'):  # fmt: skip
        assert sure(drop(name, source='rune' if 'Rune' in name else 'material'))


def test_a_ring_or_amulet_is_one_when_rare_and_a_unique_when_the_marks_price_it():
    # The player, 2026-10-17: "rare amulets - also pickup"
    for name in ('Ring', 'Amulet'):
        assert sure(drop(name, quality=6))
        assert sure(drop(name, source='unique', quality=7))
    assert not sure(drop('Ring', quality=4))  # magic
    assert not is_candidate(drop('Amulet', quality=4))  # magic: 2.2k a sale (13:36 on 2026-10-17): left


def test_a_set_or_unique_ring_or_amulet_is_one_though_the_read_calls_it_a_material():
    # A set Amulet was left beside the Amn Rune and Flawless Topaz taken (game 84, 08:10:10 on 2026-10-17): the read
    # finds jewelry as a material, so it never was the unique or set item the loot filter shows (`NAMED`)
    for name in ('Ring', 'Amulet'):
        assert sure(drop(name, source='material', quality=5))
        assert sure(drop(name, source='material', quality=7))


def test_every_jewel_and_whatever_the_loot_marks_point_at_is_one():
    # The player, later on 2026-10-16: "make sure that we still pickup all jewels, + pickup worldstone shards/other
    # valuable drops"
    assert sure(drop('Jewel', quality=4))
    assert sure(drop('Colossal Jewel', quality=6))
    assert sure(drop('Southern Worldstone Shard', prized=True))
    assert sure(drop('Twisted Essence of Suffering', prized=True))
    assert sure(drop('Archon Plate', source='named', quality=7, prized=True))  # a unique the loot filter shows


def test_the_rest_the_regular_pickup_takes_is_left_and_the_supplies_stay():
    assert not sure(drop('Phase Blade', source='shown', quality=4))
    assert not sure(drop('Archon Plate', source='shown', quality=6))  # rare equipment
    assert sure(Drop(9, 0.0, 0.0, '6000 gold', GOLD))  # the staff's repairs (the player, 2026-10-16)
    assert sure(Drop(10, 0.0, 0.0, 'a super healing potion', HEALING))


def test_the_mode_keeps_or_filters_and_a_double_press_goes_round():
    blade, rune = drop('Phase Blade', source='shown', quality=4), drop('Ist Rune', source='rune')
    loot = Loot(drops=(blade, rune))
    assert kept(loot, MOST) == loot
    assert kept(loot, SURE).drops == (rune,)
    assert MODES == (SURE, MOST)  # GOOD (the default) and MOST; the trade goods' level dropped (2026-10-19)
    assert next_mode(SURE) == MOST
    assert next_mode(MOST) == SURE


def test_the_trade_goods_are_taken_at_most_only():
    # The player, 2026-10-18: "move things that we're added for gold trades (to repair our staff charges) into separate
    # category ... and use sure for valuable things or small things"; their own level dropped on 2026-10-19
    grimoire = drop('Possessed Compendium', source='shown', quality=4)
    claws = drop('Greater Claws', source='shown', quality=6)
    rune = drop('Ist Rune', source='rune')
    kriss = replace(drop('Kriss', source='shown', quality=2), rolls=Rolls(3, ((402, 3),)))  # +3 Abyss, 3os
    for good in (grimoire, claws):
        assert is_candidate(good)
        assert not sure(good)
    assert sure(kriss)  # a base kept by its rolls is a valuable: no identify, no sale for gold
    assert sure(drop('Small Charm', quality=4))  # small things stay
    loot = Loot(drops=(grimoire, rune, kriss, claws))
    assert kept(loot, SURE).drops == (rune, kriss)
    assert kept(loot, MOST).drops == loot.drops


def test_the_ground_census_says_what_an_item_is_and_whether_a_rule_takes_it():
    # The player, 2026-10-17: "maybe we need to log drops in case if we're missing something right now"
    from inventory_tracking.game.decode import census
    from inventory_tracking.items.identity import ETHEREAL_FLAG, SOCKETED_FLAG

    assert census('Amulet', 6, 0, (5100.4, 5200.0), None, None) == 'rare Amulet at (5100, 5200): left'
    assert (
        census('Phase Blade', 4, ETHEREAL_FLAG | SOCKETED_FLAG, (1, 2), 'shown', 'Phase Blade')
        == 'magic Phase Blade eth socketed at (1, 2): taken (shown)'
    )
    assert (
        census('Ring', 7, 0, (0, 0), 'unique', 'Stone of Jordan')
        == 'unique Ring "Stone of Jordan" at (0, 0): taken (unique)'
    )


ABYSS, HEX_PURGE, APOCALYPSE, CONSUME, PSYCHIC_WARD = 402, 389, 401, 381, 387  # skills metadata ids


def test_a_white_void_base_is_taken_only_with_three_sockets_and_a_paid_staff_mod_at_three():
    # The player, 18:56 on 2026-10-17: "it looks like we're storing daggers with 1os ... we need good staff mod and we
    # need 3os; we shouldn't waste shared stash tab"
    kriss = drop('Kriss', source='shown', quality=2)
    assert is_candidate(replace(kriss, rolls=Rolls(3, ((ABYSS, 3),))))
    assert not is_candidate(replace(kriss, rolls=Rolls(1, ((ABYSS, 3),))))  # Void needs exactly three
    assert not is_candidate(replace(kriss, rolls=Rolls(2, ((ABYSS, 3),))))
    # No socket and +3 Abyss: Larzuk's sockets make it one (the player, 19:40: "0 socket +3 abyss - let's pickup them")
    assert is_candidate(replace(kriss, rolls=Rolls(0, ((ABYSS, 3),))))
    # 2026-10-20 ~18:45 ("it worth to assess every item"): 0os +3 Hex: Purge too, by the wants row
    # void-dagger-0os-plus3-hex-purge (fills 8 trades median 18.1, rca/2026-10-20/white-bases-findings.md)
    assert is_candidate(replace(kriss, rolls=Rolls(0, ((HEX_PURGE, 3),))))
    assert not is_candidate(replace(kriss, rolls=Rolls(0, ((ABYSS, 2),))))
    assert not is_candidate(replace(kriss, rolls=Rolls(3, ((ABYSS, 2),))))  # a staff mod buyers do not pay for
    assert is_candidate(replace(kriss, rolls=Rolls(3, ((HEX_PURGE, 3),))))
    assert not is_candidate(replace(kriss, rolls=Rolls(3, ((PSYCHIC_WARD, 3),))))
    assert not is_candidate(replace(kriss, rolls=Rolls(3, ((CONSUME, 3),))))  # asked, never paid
    assert not is_candidate(replace(kriss, rolls=Rolls(3)))  # no staff mod
    assert not is_candidate(kriss)  # unread: not taken
    assert not sure(replace(kriss, rolls=Rolls(1, ((ABYSS, 3),))))


def test_a_three_socket_dagger_with_plus_three_apocalypse_is_a_sure_valuable():
    # The player, 08:42 on 2026-10-20: "+3os daggers with +3 apocalypse"; Q9 as recommended (loot/design.md §8): "only
    # +3 Abyss / Hex: Purge / Apocalypse". Apocalypse 401 in third-parties/d2data/json/skills.json (charclass war)
    for name, quality in (('Legend Spike', 2), ('Fanged Knife', 3), ('Cinquedeas', 2)):
        dagger = replace(drop(name, source='shown', quality=quality), rolls=Rolls(3, ((APOCALYPSE, 3),)))
        assert sure(dagger), name  # taken at the default GOOD level, kept without an identify
        assert kept(Loot(drops=(dagger,)), SURE).drops == (dagger,)
    legend = drop('Legend Spike', source='shown', quality=2)
    assert not sure(replace(legend, rolls=Rolls(3, ((APOCALYPSE, 2),))))  # +2: not paid
    assert not sure(replace(legend, rolls=Rolls(2, ((APOCALYPSE, 3),))))  # Void needs exactly three
    assert not sure(replace(legend, rolls=Rolls(0, ((APOCALYPSE, 3),))))  # 0os: only +3 Abyss waits for Larzuk
    assert not sure(replace(drop('Dagger', source='shown', quality=2), rolls=Rolls(3, ((APOCALYPSE, 3),))))


def test_the_candidates_for_an_identify_are_skilled_magic_or_rare_items_the_filter_shows_and_white_void_bases():
    # The player, 2026-10-17: "picking items with +skill, identifying them, appraising, selling [bad ones] ... some
    # smaller things that may be good to keep for warlock (good void base with +3 for example)"
    for name in ('Kriss', 'Stilleto', 'Circlet', 'Tiara', 'Old Book', 'Eldritch Orb'):
        assert is_candidate(drop(name, source='shown', quality=4)), name
        assert is_candidate(drop(name, source='shown', quality=6)), name
    good = ((ABYSS, 3),)
    assert is_candidate(replace(drop('Kriss', source='shown', quality=2), rolls=Rolls(3, good)))  # no identify
    assert is_candidate(replace(drop('Cinquedeas', source='shown', quality=3), rolls=Rolls(3, good)))
    assert not is_candidate(replace(drop('Dagger', source='shown', quality=2), rolls=Rolls(3, good)))  # no Void
    # the player, 11:38: "the most gold cost is weapons and items that can give +skills": no skills to roll, left
    assert not is_candidate(drop('Heavy Boots', source='shown', quality=6))
    assert not is_candidate(drop('Gauntlets', source='shown', quality=4))
    assert not is_candidate(drop('Phase Blade', source='shown', quality=4))  # no skills to roll
    assert not is_candidate(drop('Gauntlets', source='named', quality=5, prized=True))  # a set: a valuable, kept
    loot = Loot(drops=(drop('Kriss', source='shown', quality=4),))
    assert kept(loot, MOST) == loot
    assert kept(loot, SURE).drops == ()  # a trade good: MOST's


def test_a_monarch_or_a_sacred_targe_is_taken_by_the_rolls_that_sell(monkeypatch):
    # The player, 19:10 on 2026-10-17: "start picking up monarchs (for 4os deflecting) and sacred targes (check what
    # are expensive ones)"; the market study's rule (pickmode.py SHIELD_*). With SPIRIT_MONARCH_CAP Spirit bases owned
    # (2026-10-20 ~12:50 "I want to keep more monarch bases"), as before; under it a plain 4os copy is taken too
    from inventory_tracking.loot import value

    owned = {'count': 6}
    monkeypatch.setattr(value, 'owned_bases', lambda facts: owned['count'])
    monarch = drop('Monarch', source='shown', quality=3)
    assert is_candidate(replace(monarch, rolls=Rolls(4, defense=15)))
    assert is_candidate(replace(monarch, rolls=Rolls(0, defense=15)))  # Larzuk's sockets
    assert not is_candidate(replace(monarch, rolls=Rolls(4, defense=12)))  # asked 2 Ist
    assert not is_candidate(replace(monarch, rolls=Rolls(4, defense=None)))  # ED unread: not taken
    assert not is_candidate(replace(monarch, quality=2, rolls=Rolls(4)))  # a white 4os asked 0.79
    assert is_candidate(replace(monarch, quality=4, rolls=Rolls(4)))  # magic 4os: identified, then appraised
    assert not is_candidate(replace(monarch, quality=4, rolls=Rolls(2)))
    owned['count'] = 2  # under the cap: the Spirit base, white or superior, non-eth 4os
    assert is_candidate(replace(monarch, quality=2, rolls=Rolls(4)))
    assert is_candidate(replace(monarch, rolls=Rolls(4, defense=12)))
    assert not is_candidate(replace(monarch, quality=2, rolls=Rolls(4, ethereal=True)))
    assert not is_candidate(replace(monarch, quality=2, rolls=Rolls(3)))
    owned['count'] = 6
    targe = drop('Sacred Targe', source='shown', quality=2)
    assert is_candidate(replace(targe, rolls=Rolls(0, resists=45)))
    assert is_candidate(replace(targe, rolls=Rolls(3, resists=42)))
    assert not is_candidate(replace(targe, rolls=Rolls(2, resists=42)))
    assert not is_candidate(replace(targe, rolls=Rolls(4, resists=38)))
    rondache = drop('Sacred Rondache', source='shown', quality=2)
    assert is_candidate(replace(rondache, rolls=Rolls(4, resists=45)))
    assert is_candidate(replace(rondache, rolls=Rolls(0, resists=45, ethereal=True)))
    assert not is_candidate(replace(rondache, rolls=Rolls(3, resists=45)))
    assert not is_candidate(replace(rondache, rolls=Rolls(4, resists=39)))
    # The Exile base since 2026-10-20 ~12:15 (the player: "4os, at least +40 all res"; loot/ground_judge.py, M5)
    assert is_candidate(replace(rondache, rolls=Rolls(4, resists=44)))
    assert not is_candidate(replace(rondache, rolls=Rolls(2, resists=44)))
    assert not is_candidate(targe)  # unread: not taken


@pytest.mark.parametrize('broken', [False, True])
def test_the_loot_shadow_logs_beside_the_look_and_never_changes_what_it_takes(monkeypatch, caplog, broken):
    # loot/design.md §7 M1: the new ground verdicts logged once per item beside the mode's; a broken shadow changes
    # nothing either
    import inventory_tracking.loot.shadow as shadow_module

    shadow = shadow_module.Shadow(shadow_module.Book())
    if broken:
        monkeypatch.setattr(shadow, '_ground', lambda *args: 1 / 0)
    monkeypatch.setattr(shadow_module, 'SHADOW', shadow)
    monarch = Drop(5, 0.0, 0.0, 'Monarch', VALUABLE, (2, 3), prized=False, source='shown', txt=447, quality=4,
                   rolls=Rolls(0))  # fmt: skip
    gold = Drop(6, 0.0, 0.0, 'Gold', GOLD, source='', txt=538)
    loot = Loot(drops=(monarch, gold), game=('game-1', 7))

    with caplog.at_level('INFO'):
        first, again = kept(loot, SURE), kept(loot, SURE)

    assert first.drops == again.drops == (gold,)  # the magic Monarch left, as before
    if broken:
        assert caplog.text.count('Macro: loot: shadow: ground failed (ZeroDivisionError') == 1
    else:
        lines = [r.message for r in caplog.records if r.message.startswith('Macro: loot: shadow: ground:')]
        assert lines == ['Macro: loot: shadow: ground: magic Monarch: new pick G6 identify / old leave (differ)']


# -- 2026-10-20: the big items and the ground bases (the player, ~11:55: "bases or blue/rare items might take much
# place (like spears, matron bow) -- we want to check them and drop in the middle of the run"; ~12:00 "start all
# three"; ~12:15 the own-use bases)

GAME = ('game-1', 7)
EMPTY = ('..........',) * 4


def base(name: str, size: tuple[int, int], rolls: Rolls | None, *, quality: int = 2, unit: int = 1) -> Drop:
    found = drop(name, source='shown', quality=quality)
    return replace(found, unit_id=unit, size=size, rolls=rolls)


@pytest.fixture
def looping(monkeypatch):
    from inventory_tracking.loot.api import FIELD

    monkeypatch.setattr(FIELD, 'looping', lambda: True)
    FIELD.picked.clear()
    yield FIELD
    FIELD.picked.clear()


@pytest.mark.parametrize('mode', MODES)
def test_an_eth_4os_giant_thresher_is_taken_over_the_cell_cap_as_a_must_have_and_a_plain_one_is_left(mode):
    gt_eth = base('Giant Thresher', (2, 4), Rolls(4, ethereal=True), unit=1)
    gt_plain = base('Giant Thresher', (2, 4), Rolls(4), unit=2)  # non-eth: "Floor: any non-eth" (PK-merc-polearms)
    partizan = base('Partizan', (2, 4), Rolls(2), unit=3)  # no row names it: never picked
    found = kept(Loot(drops=(gt_eth, gt_plain, partizan), game=GAME, room=EMPTY), mode).drops
    assert [d.unit_id for d in found] == [1]
    assert found[0].prized  # the merc BiS: no game is left with it on the ground, a press stops for it
    assert not is_candidate(found[0])


def test_the_ground_bases_follow_the_wants_rows_in_the_good_level(monkeypatch):
    from inventory_tracking.loot import value

    owned = {'count': 2}  # the Spirit base Monarchs owned (collection.sqlite, 2026-10-20: MSockB, MSockC)
    monkeypatch.setattr(value, 'owned_bases', lambda facts: owned['count'])
    archon_eth = base('Archon Plate', (2, 3), Rolls(4, ethereal=True), unit=1)  # CoH (merc)
    archon_plain = base('Archon Plate', (2, 3), Rolls(4), unit=2)  # plain 4os: "Sell", not picked ("no bad bases")
    spirit_plain = base('Monarch', (2, 3), Rolls(4), unit=3)  # under SPIRIT_MONARCH_CAP owned: picked (~12:50)
    spirit_superior = base('Monarch', (2, 3), Rolls(4, defense=15), quality=3, unit=4)  # the better copy
    exile = base('Sacred Targe', (2, 2), Rolls(4, resists=41, ethereal=True), unit=5)
    cure = base('Corona', (2, 2), Rolls(3, ethereal=True), unit=6)
    cure_plain = base('Corona', (2, 2), Rolls(3), unit=7)  # non-eth: the merc's is eth
    bow = base('Grand Matron Bow', (2, 4), Rolls(4, damage=15, tabs=((0, 3),)), quality=3, unit=8)  # Q7 G16
    bow_plain = base('Grand Matron Bow', (2, 4), Rolls(4, tabs=((0, 3),)), unit=9)  # "never plain ones"
    drops = (archon_eth, archon_plain, spirit_plain, spirit_superior, exile, cure, cure_plain, bow, bow_plain)
    loot = Loot(drops=drops, game=GAME, room=EMPTY)
    assert [d.unit_id for d in kept(loot, SURE).drops] == [1, 3, 4, 5, 6, 8]
    assert is_candidate(kept(loot, SURE).drops[1])  # the Spirit base: no game kept for it, no trip
    assert is_candidate(kept(loot, SURE).drops[3])  # the Exile base: no game kept for it, no trip
    owned['count'] = 6  # the cap reached: the plain copy is left, the Superior 15 ED one (the better copy) still taken
    assert [d.unit_id for d in kept(loot, SURE).drops] == [1, 4, 5, 6, 8]


def test_with_the_switch_off_only_todays_dagger_and_shield_rules_take_a_base(monkeypatch):
    from inventory_tracking.loot import ground_judge

    monkeypatch.setattr(ground_judge, 'BASES', False)
    archon_eth = base('Archon Plate', (2, 3), Rolls(4, ethereal=True), unit=1)
    monarch = base('Monarch', (2, 3), Rolls(4, defense=15), quality=3, unit=2)
    gt_eth = base('Giant Thresher', (2, 4), Rolls(4, ethereal=True), unit=3)
    assert [d.unit_id for d in kept(Loot(drops=(archon_eth, monarch, gt_eth), game=GAME), SURE).drops] == [2]


def test_a_big_magic_or_rare_item_is_picked_for_the_field_check_in_the_loop_only(looping):
    archon = base('Archon Plate', (2, 3), None, quality=4, unit=1)
    bow = base('Grand Matron Bow', (2, 4), None, quality=6, unit=2)
    belt = base('Heavy Belt', (2, 1), None, quality=4, unit=3)  # a magic belt, 2 cells: as before (left in GOOD)
    loot = Loot(drops=(archon, bow, belt), game=GAME, room=EMPTY)
    assert [d.unit_id for d in kept(loot, SURE).drops] == [1, 2]
    assert looping.class_of(1, GAME[0]) == 'G14'
    assert looping.class_of(2, GAME[0]) == 'G15'
    assert is_candidate(bow)  # a field item: no game kept, no trip for it
    looping.looping = lambda: False
    looping.picked.clear()
    assert kept(loot, SURE).drops == ()  # KP_1 by hand: as before
    assert [d.unit_id for d in kept(loot, MOST).drops] == [1, 3]  # MOST: the cap holds for an unjudged one


@pytest.mark.parametrize('mode', MODES)
def test_rare_boots_and_belts_are_picked_for_the_field_identify_and_magic_ones_are_not(looping, mode):
    """The player, 2026-10-20 ~19:05: "is there are good rolls for belts/boots? right now we're not picking/identifying
    them", ~19:25: "we can keep really good ones": every rare boot (G21) and belt (G22) the filter shows is picked with
    the loop on, in both levels, and remembered for the field identify; a magic belt is no class's."""
    boots = base('War Boots', (2, 2), None, quality=6, unit=1)
    belt = base('Mithril Coil', (2, 1), None, quality=6, unit=2)
    magic_belt = base('Mithril Coil', (2, 1), None, quality=4, unit=3)
    loot = Loot(drops=(boots, belt, magic_belt), game=GAME, room=EMPTY)
    assert [d.unit_id for d in kept(loot, mode).drops] == ([1, 2] if mode == SURE else [1, 2, 3])
    assert (looping.class_of(1, GAME[0]), looping.class_of(2, GAME[0])) == ('G21', 'G22')
    assert looping.class_of(3, GAME[0]) is None
    assert is_candidate(belt)  # a field item: no game kept, no trip for it
    looping.looping = lambda: False
    assert not is_candidate(belt)
    assert kept(loot, SURE).drops == ()  # KP_1 by hand: as before


def test_the_filter_shows_every_rare_boot_and_belt_and_hides_the_magic_ones_but_the_craft_bases():
    """`SHOW Rare ARMOR` (lootfilter/warlock_lean_v2.json) lists the boots and belts categories at every tier: no filter
    change for G21 / G22. Magic boots and belts are shown only as the six caster-craft bases (`SHOW Craft Bases ARMOR`,
    warlock.html §6: "no magic boot or belt roll is worth identifying")."""
    from inventory_tracking.loot.shown import filter_rules, hides

    rules = filter_rules()
    bases = metadata()['bases']
    kinds = {kind: [int(cid) for cid, row in bases.items() if row.get('type') == kind] for kind in ('boot', 'belt')}
    assert len(kinds['boot']) == len(kinds['belt']) == 15
    assert not any(hides(rules, cid, 6) for cid in kinds['boot'] + kinds['belt'])
    crafted = {class_of(name) for name in ('Boots', 'Demonhide Boots', 'Wyrmhide Boots', 'Light Belt',
                                           'Sharkskin Belt', 'Vampirefang Belt')}  # fmt: skip
    assert {cid for cid in kinds['boot'] + kinds['belt'] if not hides(rules, cid, 4)} == crafted


def test_the_most_level_remembers_its_big_items_for_the_field_identify(looping):
    archon = base('Archon Plate', (2, 3), None, quality=4, unit=1)
    rune = replace(drop('Ber Rune', source='rune'), unit_id=2)
    assert [d.unit_id for d in kept(Loot(drops=(archon, rune), game=GAME, room=EMPTY), MOST).drops] == [1, 2]
    assert looping.class_of(1, GAME[0]) == 'G14'  # identified in the field, a bad one dropped there
    assert looping.class_of(2, GAME[0]) is None


def test_a_big_field_item_with_no_grand_charms_room_after_it_is_left(looping):
    bow = base('Grand Matron Bow', (2, 4), None, quality=6, unit=1)
    tight = ('########..',) * 4  # one 2x4 hole: the bow would take the room a valuable needs
    assert kept(Loot(drops=(bow,), game=GAME, room=tight), SURE).drops == ()
    assert looping.class_of(1, GAME[0]) is None


@pytest.mark.parametrize('mode', MODES)
def test_white_class_items_are_taken_by_their_paid_staff_mods_and_the_rest_left(mode):
    # The player, 2026-10-20 ~18:45: "implement [grimoire pickup rules] ... it worth to assess every item": G20 by the
    # ground read (rca/2026-10-20/white-bases-findings.md); a staff (2x4) over the cell cap is taken by the same verdict
    tainted = base('Possessed Grimoire', (2, 2), Rolls(2, ((376, 3),)), unit=1)  # +3 Summon Tainted, 2os
    engorge = base('Possessed Grimoire', (2, 2), Rolls(2, ((379, 3),)), unit=2)  # +3 Engorge: floor
    plus2 = base('Possessed Grimoire', (2, 2), Rolls(2, ((376, 2),)), unit=3)  # +2 alone: left
    wand = base('Lich Wand', (1, 2), Rolls(2, ((84, 3), (93, 3))), unit=4)  # +3 Bone Spear and +3 Bone Spirit
    spear_only = base('Lich Wand', (1, 2), Rolls(2, ((84, 3),)), unit=5)
    staff = base('Archon Staff', (2, 4), Rolls(5, ((58, 3),)), unit=6)  # +3 Energy Shield 5os: Call to Arms
    staff_3os = base('Archon Staff', (2, 4), Rolls(3, ((58, 3),)), unit=7)
    unread = base('Possessed Grimoire', (2, 2), None, unit=8)  # rolls not read: never taken
    drops = (tainted, engorge, plus2, wand, spear_only, staff, staff_3os, unread)
    found = kept(Loot(drops=drops, game=GAME, room=EMPTY), mode).drops
    if mode == MOST:
        assert [d.unit_id for d in found] == [1, 2, 3, 4, 5, 6, 8]  # MOST takes what it took; only the big ones judged
    else:
        assert [d.unit_id for d in found] == [1, 4, 6]
    assert all(is_candidate(d) for d in found if d.unit_id in (1, 4, 6))  # no game is kept for one
