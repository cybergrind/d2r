"""The KP_6 loop's pickup mode (macros/pickmode.py; routes/lower-kurast-loop-plan.md phase 7). Item classes by their
items.txt row as the bundled metadata names them (items/metadata.py `item_base`), looked up, not written from memory."""

from dataclasses import replace

import pytest

from inventory_tracking.game.records import GOLD, HEALING, VALUABLE, Drop, Loot, Rolls
from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot import value as loot_value
from inventory_tracking.macros import pickmode
from inventory_tracking.macros.pickmode import (
    MODES,
    MOST,
    SURE,
    good as sure,
    identify_only as is_candidate,
    next_mode,
    taken as kept,
)


@pytest.fixture(autouse=True, params=[True, False], ids=['assessed', 'legacy'])
def assessed(request, monkeypatch):
    """Every case through the entry point (pickmode.py ASSESS_GROUND, 2026-10-23) and through today's rules (the switch
    off, legacy until ASSESS_GROUND is proven): the same answers both ways."""
    monkeypatch.setattr(pickmode, 'ASSESS_GROUND', request.param)
    return request.param


def class_of(name: str) -> int:
    [found] = [int(cid) for cid, base in metadata()['bases'].items() if base['name'] == name]
    return found


def drop(name: str, *, source: str = 'material', quality: int = 2, kind: str = VALUABLE, prized: bool = False) -> Drop:
    return Drop(class_of(name), 0.0, 0.0, name, kind, prized=prized, source=source, txt=class_of(name), quality=quality)


def held_by_none(assessed: bool, found: Drop) -> bool:
    """`is_candidate`, or through the entry point a drop no pickup level takes (left in both: never at a site)."""
    if is_candidate(found):
        return True
    taken = [kept(Loot(drops=(found,), game=('game-1', 7), room=('..........',) * 4), mode).drops for mode in MODES]
    return assessed and not any(taken)


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


def test_a_three_socket_dagger_with_plus_three_apocalypse_is_a_sure_valuable(assessed):
    # The player, 08:42 on 2026-10-20: "+3os daggers with +3 apocalypse"; Q9 as recommended (loot/design.md §8): "only
    # +3 Abyss / Hex: Purge / Apocalypse". Apocalypse 401 in third-parties/d2data/json/skills.json (charclass war)
    for name, quality in (('Legend Spike', 2), ('Fanged Knife', 3), ('Cinquedeas', 2)):
        dagger = replace(drop(name, source='shown', quality=quality), rolls=Rolls(3, ((APOCALYPSE, 3),)))
        assert sure(dagger) != assessed, name  # today's `sure` still names it a Void base; the entry point leaves it
        # but the allowlist leaves it (2026-10-23, rca/2026-10-23/base-candidates.md §3: +3 Apocalypse alone fills
        # 1.0 and 0.79 Ist): "every base must worth 4+ist at least"
        assert kept(Loot(drops=(dagger,)), SURE).drops == ()
    legend = drop('Legend Spike', source='shown', quality=2)
    assert not sure(replace(legend, rolls=Rolls(3, ((APOCALYPSE, 2),))))  # +2: not paid
    assert not sure(replace(legend, rolls=Rolls(2, ((APOCALYPSE, 3),))))  # Void needs exactly three
    # 0os waits for Larzuk or the cube (the player, 2026-10-22: "add 0os +3 apocalypse too")
    zero = replace(legend, rolls=Rolls(0, ((APOCALYPSE, 3),), ethereal=True))
    assert sure(zero) != assessed  # the allowlist leaves it (void-dagger-0os-plus3-apocalypse unproven)
    assert kept(Loot(drops=(zero,)), SURE).drops == ()
    assert not sure(replace(legend, rolls=Rolls(0, ((APOCALYPSE, 2),))))
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


def test_a_monarch_or_a_sacred_targe_is_taken_by_the_rolls_that_sell(monkeypatch, assessed):
    # The player, 19:10 on 2026-10-17: "start picking up monarchs (for 4os deflecting) and sacred targes (check what
    # are expensive ones)"; the market study's rule (pickmode.py SHIELD_*). With SPIRIT_MONARCH_CAP Spirit bases owned
    # (2026-10-20 ~12:50 "I want to keep more monarch bases"), as before; under it a plain 4os copy is taken too
    from inventory_tracking.loot import value

    owned = {'count': 6}
    monkeypatch.setattr(value, 'owned_bases', lambda facts: owned['count'])
    monarch = drop('Monarch', source='shown', quality=3)
    # Through the entry point a base the allowlist leaves is no candidate: no level takes it, so no site asks
    # (`held_by_none`); today's `is_candidate` answered by the wants row the allowlist overrules
    assert held_by_none(assessed, replace(monarch, rolls=Rolls(4, defense=15)))
    assert held_by_none(assessed, replace(monarch, rolls=Rolls(0, defense=15)))  # Larzuk's sockets
    assert not is_candidate(replace(monarch, rolls=Rolls(4, defense=12)))  # asked 2 Ist
    assert not is_candidate(replace(monarch, rolls=Rolls(4, defense=None)))  # ED unread: not taken
    assert not is_candidate(replace(monarch, quality=2, rolls=Rolls(4)))  # a white 4os asked 0.79
    assert held_by_none(assessed, replace(monarch, quality=4, rolls=Rolls(4)))  # magic 4os: identified, then appraised
    assert not is_candidate(replace(monarch, quality=4, rolls=Rolls(2)))
    owned['count'] = 2  # under the cap: the Spirit base, white or superior, non-eth 4os
    assert held_by_none(assessed, replace(monarch, quality=2, rolls=Rolls(4)))
    assert held_by_none(assessed, replace(monarch, rolls=Rolls(4, defense=12)))
    assert not is_candidate(replace(monarch, quality=2, rolls=Rolls(4, ethereal=True)))
    assert not is_candidate(replace(monarch, quality=2, rolls=Rolls(3)))
    owned['count'] = 6
    targe = drop('Sacred Targe', source='shown', quality=2)
    assert held_by_none(assessed, replace(targe, rolls=Rolls(0, resists=45)))
    assert held_by_none(assessed, replace(targe, rolls=Rolls(3, resists=42)))
    assert not is_candidate(replace(targe, rolls=Rolls(2, resists=42)))
    assert not is_candidate(replace(targe, rolls=Rolls(4, resists=38)))
    rondache = drop('Sacred Rondache', source='shown', quality=2)
    assert held_by_none(assessed, replace(rondache, rolls=Rolls(4, resists=45)))
    assert held_by_none(assessed, replace(rondache, rolls=Rolls(0, resists=45, ethereal=True)))
    assert not is_candidate(replace(rondache, rolls=Rolls(3, resists=45)))
    assert not is_candidate(replace(rondache, rolls=Rolls(4, resists=39)))
    # The Exile base since 2026-10-20 ~12:15 (the player: "4os, at least +40 all res"; loot/ground_judge.py, M5)
    assert held_by_none(assessed, replace(rondache, rolls=Rolls(4, resists=44)))
    assert not is_candidate(replace(rondache, rolls=Rolls(2, resists=44)))
    assert not is_candidate(targe)  # unread: not taken


@pytest.mark.parametrize('broken', [False, True])
def test_the_loot_shadow_logs_beside_the_look_and_never_changes_what_it_takes(monkeypatch, caplog, broken, assessed):
    if assessed:
        pytest.skip("the M1 shadow is the legacy path's: the entry point logs its own (test_pickmode_assess.py)")
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
    # non-eth: "Floor: any non-eth" (PK-merc-polearms), but on the allowlist by the KB's 4os band, asks a median 4.79
    # Ist over 8 sellers (2026-10-04, loot/data/base-pickups.json)
    gt_plain = base('Giant Thresher', (2, 4), Rolls(4), unit=2)
    partizan = base('Partizan', (2, 4), Rolls(2), unit=3)  # on no allowlist entry: never picked
    found = kept(Loot(drops=(gt_eth, gt_plain, partizan), game=GAME, room=EMPTY), mode).drops
    assert [d.unit_id for d in found] == [1, 2]
    assert found[0].prized  # the merc BiS: no game is left with it on the ground, a press stops for it
    assert not is_candidate(found[0])


def test_the_ground_bases_follow_the_wants_rows_in_the_good_level(monkeypatch):
    from inventory_tracking.loot import value

    owned = {'count': 2}  # the Spirit base Monarchs owned (collection.sqlite, 2026-10-20: MSockB, MSockC)
    monkeypatch.setattr(value, 'owned_bases', lambda facts: owned['count'])
    archon_eth = base('Archon Plate', (2, 3), Rolls(4, ethereal=True), unit=1)  # CoH (merc); normal: 2.58 Ist fills
    archon_plain = base('Archon Plate', (2, 3), Rolls(4), unit=2)  # plain 4os: the KB's band 0.68-1.0 Ist: under 4
    spirit_plain = base('Monarch', (2, 3), Rolls(4), unit=3)  # asks 0.42-0.79 Ist (n19): off the allowlist (4+ Ist)
    spirit_superior = base('Monarch', (2, 3), Rolls(4, defense=15), quality=3, unit=4)  # the better copy
    exile = base('Sacred Targe', (2, 2), Rolls(4, resists=41, ethereal=True), unit=5)
    cure = base('Corona', (2, 2), Rolls(3, ethereal=True), unit=6)  # no price evidence of 4 Ist: off the allowlist
    cure_plain = base('Corona', (2, 2), Rolls(3), unit=7)  # non-eth: the merc's is eth
    bow = base('Grand Matron Bow', (2, 4), Rolls(4, damage=15, tabs=((0, 3),)), quality=3, unit=8)  # Q7 G16
    bow_plain = base('Grand Matron Bow', (2, 4), Rolls(4, tabs=((0, 3),)), unit=9)  # "never plain ones"
    drops = (archon_eth, archon_plain, spirit_plain, spirit_superior, exile, cure, cure_plain, bow, bow_plain)
    loot = Loot(drops=drops, game=GAME, room=EMPTY)
    # The allowlist (the player, 2026-10-23 ~00:50: "every base must worth 4+ist at least"), in every level
    # (2026-10-23 ~17:20, "Sales-backed now": the eth 4os normal Archon Plate fills n83 median 2.58: left)
    for mode in MODES:
        assert [d.unit_id for d in kept(loot, mode).drops] == [4, 5, 8]
    assert is_candidate(kept(loot, SURE).drops[1])  # the Exile base: no game kept for it, no trip
    owned['count'] = 6  # the Spirit base's cap: the Superior 15 ED one (the better copy) still taken
    assert [d.unit_id for d in kept(loot, SURE).drops] == [4, 5, 8]


def test_with_the_switch_off_only_todays_dagger_and_shield_rules_take_a_base(monkeypatch, assessed):
    if assessed:
        pytest.skip("today's dagger and shield rules: the legacy path (the entry point's rows judge with PLAIN off)")
    from inventory_tracking.loot import base_floor, ground_judge

    monkeypatch.setattr(ground_judge, 'BASES', False)
    monkeypatch.setattr(base_floor, 'PLAIN_BY_RULES', False)
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
def test_a_shown_item_never_takes_the_room_of_a_named_one_beside_it(looping, mode, monkeypatch):
    """Game 3 at 02:14:54 on 2026-10-26 (alt-d run 20261025T220620Z, Tal Rasha's tomb): back from a trip for room with
    the loop's 2x4 block free, the MOST level took the magic Caduceus (2x3, shown, nearest) beside a Unique Mesh Armor
    (2x3) and a Unique Scourge (1x3); it was appraised vendor in town after a trip made for it. The shown one is left
    while a named one would lose its room to it, in every level, and the 2x3 unique is the press's first."""
    from inventory_tracking.game.records import NAMED
    from inventory_tracking.loot import api
    from inventory_tracking.macros.pickup import choose

    for name, empty in (('waiting', {}), ('left_said', set()), ('judged', {}), ('roomless', {}), ('parking', {})):
        monkeypatch.setattr(api.FIELD, name, empty)
    monkeypatch.setattr(api.FIELD, 'tome_seen', None)
    caduceus = replace(base('Caduceus', (2, 3), None, quality=4, unit=1), x=1.0)
    mesh = replace(drop('Mesh Armor', source=NAMED, quality=7, prized=True), unit_id=2, size=(2, 3), x=3.0)
    scourge = replace(drop('Scourge', source=NAMED, quality=7, prized=True), unit_id=3, size=(1, 3), x=5.0)
    block = ('########..',) * 4  # the loop's 2x4 block, the rest the player's
    look = Loot(drops=(caduceus, mesh, scourge), game=GAME, room=block)
    found = kept(look, mode, lambda: 20)
    assert [d.unit_id for d in found.drops] == [2, 3]
    plan = choose(found, (0.0, 0.0))
    assert plan is not None
    assert plan.drop.unit_id == 2
    alone = Loot(drops=(caduceus,), game=GAME, room=block)  # no named one beside it: taken as before
    assert [d.unit_id for d in kept(alone, mode, lambda: 20).drops] == [1]


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
    # The allowlist in every level (2026-10-23: "a lot of random book"): +3 Summon Tainted asks 0.67-5.89 Ist (n11);
    # the wand +3 Bone Spear and Bone Spirit fills 22.8 Ist (n16), the 5os +3 Energy Shield staff asks 34.3 (n4);
    # unread rolls are left (rca/2026-10-23/base-candidates.md §1a)
    assert [d.unit_id for d in found] == [1, 4, 6]
    assert is_candidate(found[0])  # no game is kept for one


# The allowlist (loot/data/base-pickups.json; macros/pickmode.py PLAIN_BY_RULES; the player, 2026-10-23 ~00:50:
# "every base must worth 4+ist at least / we need to pickup something like +45 all res, 4os sacret target and so on.
# or 3os grey kris with +3 abyss"; "0os crystal sword is a trash!", "+1 skill knife - is a trash"): in every level a
# shown white or grey weapon or armor is taken only by an entry matching its facts read; the rest left, said once
JUNK_FLAIL = Rolls(sockets=0, damage=7)


@pytest.mark.parametrize('mode', MODES)
def test_a_junk_superior_flail_is_left_on_the_ground_and_said_once(mode, caplog):
    from inventory_tracking.macros import pickmode

    pickmode.JUNK_SAID.clear()
    flail = base('Flail', (2, 3), JUNK_FLAIL, quality=3, unit=31)
    with caplog.at_level('INFO'):
        assert kept(Loot(drops=(flail,), game=GAME, room=EMPTY), mode).drops == ()
        assert kept(Loot(drops=(flail,), game=GAME, room=EMPTY), mode).drops == ()
    said = [r.getMessage() for r in caplog.records if 'left on the ground' in r.getMessage()]
    assert len(said) == 1
    assert said[0].startswith('Macro: pickup: Flail 0os 7% ED left on the ground: a plain base')


LEFT = [
    ('Circlet', Rolls(0), 2),
    ('Coronet', Rolls(0), 2),
    ('Tiara', Rolls(0), 2),
    ('Diadem', Rolls(0), 2),
    ('Targe', Rolls(0, resists=9), 3),
    ('Targe', Rolls(0, resists=45), 3),  # 45 res fills n5 median 1.0 Ist (base-candidates.md §4): off the allowlist
    ('Mask', Rolls(0, defense=15), 3),  # superior 15 ED 0os 3.32 Ist (n6)
    ('Crystal Sword', Rolls(5, damage=15), 3),  # 5os: 2 priced listings
    ('Bone Shield', Rolls(0, defense=15), 3),  # 2 priced listings
    ('Cryptic Axe', Rolls(4, ethereal=True), 2),  # eth 4os plain 1.0 Ist (n23)
    ('Colossus Voulge', Rolls(4, ethereal=True), 2),  # 0.79 (n34)
    ('Mancatcher', Rolls(4, ethereal=True), 2),  # 2.0 (n31)
    ('Great Poleaxe', Rolls(4, ethereal=True), 2),  # 3.90 (n16)
    ('Kriss', Rolls(3, ((401, 3),)), 2),  # +3 Apocalypse alone: fills 1.0
    ('Kriss', Rolls(0, ((401, 3),)), 3),
    ('Kriss', Rolls(2), 2),
    ('Kriss', Rolls(1), 2),
    ('Kriss', Rolls(3), 2),  # 3os without a paid +3 staff mod
    ('Kriss', Rolls(0, ((402, 2),)), 2),  # 0os +2 Abyss: not +3
    ('Kriss', Rolls(0, ((401, 3),)), 2),  # 0os +3 Apocalypse: its 3os asks ~5 Ist, a 0os one unproven at 4
    ('Fanged Knife', Rolls(0, ((384, 1), (392, 1))), 2),  # +1 Eldritch Blast +1 Mirrored Blades
    ('Possessed Grimoire', Rolls(2, ((376, 2),)), 2),
    ('Grimoire', Rolls(0), 3),  # a random grimoire
    ('Flail', Rolls(0), 2),
    ('Flail', Rolls(0, damage=7), 3),
    ('Flail', Rolls(0, damage=15, ethereal=True), 3),  # asks 1.68-2.59 Ist (2026-10-04): under 4
    ('Crystal Sword', Rolls(0), 2),
    ('Crystal Sword', Rolls(0, damage=7), 3),
    ('Crystal Sword', Rolls(0, damage=15), 3),
    ('Crystal Sword', Rolls(4), 2),  # the row wants Superior 15 ED
    ('Archon Plate', Rolls(4), 2),  # asks 0.68-1.0 Ist
    ('Archon Plate', Rolls(2), 2),  # a random armor
    ('Mage Plate', Rolls(0, ethereal=True), 2),
    ('Wire Fleece', Rolls(0, defense=13), 3),
    ('Phase Blade', Rolls(5), 2),
    ('Thresher', Rolls(2), 2),
    ('Partizan', Rolls(2), 2),
    ('Monarch', Rolls(4), 2),  # the Spirit base own use: asks 0.42-0.79 Ist
    ('Dusk Shroud', Rolls(4, ethereal=True), 2),  # a must-have row (merc Fortitude), asks 0.25-0.79 Ist: under 4
    ('Flail', None, 3),  # unread: "unread bases filled the stash" (2026-10-17)
    ('Monarch', Rolls(4, defense=None), 3),  # ED unread
    # The verifier's OVERBROAD entries (rca/2026-10-23/base-pickups-verify.md), narrowed
    ('Sacred Rondache', Rolls(4, resists=42), 2),  # non-eth 4os 40-44: asks 0.5-3.59 (n9)
    ('Sacred Rondache', Rolls(0, resists=42), 2),
    ('Possessed Grimoire', Rolls(0, ((400, 3),)), 2),  # 0os single +3: median 1.0
    ('Sacred Targe', Rolls(4, resists=42), 2),  # 4os 40-44: n1 2.59
    ('War Scepter', Rolls(5, ((121, 3),)), 2),  # FoH alone: fills n4 median 3.3
    ('Divine Scepter', Rolls(5, ((121, 3), (123, 1))), 2),  # a +1 companion
    ('Greater Talons', Rolls(0, ((280, 3),)), 2),  # 0os: no fills
    ('Colossus Voulge', Rolls(4, ethereal=True, damage=5), 3),  # eth 4os superior: n1
    ('Wire Fleece', Rolls(4, defense=5), 3),  # superior 4os under 15 ED: wp-b 0.895 (n6)
    ('Wire Fleece', Rolls(0, ethereal=True, defense=5), 3),  # eth 0os superior under 15 ED: 1.0 (n3)
    ('Great Poleaxe', Rolls(6, damage=5), 3),  # the thin ordinary 6os key dropped
    # The base-price ruling (the player, 2026-10-23 ~17:20: "Sales-backed now", "Drop both"; loot/build_base_pickups.py,
    # rca/2026-10-23/base-prices-findings.md): sales decide per facet
    ('Crystal Sword', Rolls(4, damage=15), 3),  # superior 15 ED 4os: contested, asks n42 4.03 against a fill of 1.0
    ('Cinquedeas', Rolls(3, ((384, 3),)), 2),  # +3 Eldritch Blast alone: fills n9 median 1.43
    ('Stilleto', Rolls(3, ((377, 3),)), 3),  # +3 Summon Defiler alone: thin (narrowed: a second mod +2)
    ('Fanged Knife', Rolls(3, ((386, 3),)), 2),  # +3 Hex: Siphon alone: fills 0.84 / 0.89, asks n6 1.72
    ('Thresher', Rolls(4, ethereal=True), 2),  # eth 4os normal: fills n60 median 2.58
    ('Sacred Rondache', Rolls(0, resists=45), 2),  # 0os 45 normal: "Drop both" (asks 4.05 n11, one fill 2.0)
    ('Sacred Armor', Rolls(4, ethereal=True), 2),  # eth 4os normal: fills n34 median 2.58
    ('Giant Thresher', Rolls(5, damage=5), 3),  # superior 5os under 15 ED: asks n15 median 1.43
    ('Cryptic Axe', Rolls(4, damage=5), 3),  # superior 4os under 15 ED: asks n20 median 2.79, a fill of 2.58
    ('Mancatcher', Rolls(4, damage=15), 3),  # superior 15 ED 4os: fills n5 median 1.58
    ('Colossus Blade', Rolls(6, ethereal=True), 2),  # eth 6os normal: fills n29 median 0.79
    ('Possessed Grimoire', Rolls(2, ((400, 3),)), 2),  # 2os +3 Sigil: Death: contested, asks n3 9.32, a fill of 1.43
]


@pytest.mark.parametrize('mode', MODES)
@pytest.mark.parametrize(
    ('name', 'rolls', 'quality'), LEFT, ids=[f'{n} {r.sockets if r else "unread"}os q{q}' for n, r, q in LEFT]
)
def test_a_base_on_no_allowlist_entry_is_left(mode, name, rolls, quality):
    found = base(name, (2, 2), rolls, quality=quality, unit=41)
    assert kept(Loot(drops=(found,), game=GAME, room=EMPTY), mode).drops == ()


@pytest.mark.parametrize('mode', MODES)
def test_one_plain_eth_4os_archon_is_taken_while_none_is_owned(mode, monkeypatch):
    """Off the allowlist (eth 4os normal fills n83 median 2.58), the own-use row (loot/base_floor.py OWN_USE; the
    player, 2026-10-25: "I want to keep at least one 4os Archon Plate") takes it as a must-have while the collection
    counts none; once one is owned it is left."""
    archon = base('Archon Plate', (2, 2), Rolls(4, ethereal=True), quality=2, unit=41)
    monkeypatch.setattr(loot_value, 'owned_bases', lambda _facts: 0)
    [taken] = kept(Loot(drops=(archon,), game=GAME, room=EMPTY), mode).drops
    assert taken.prized
    monkeypatch.setattr(loot_value, 'owned_bases', lambda _facts: 1)
    assert kept(Loot(drops=(archon,), game=GAME, room=EMPTY), mode).drops == ()


TAKEN = [
    ('Flail', Rolls(4, damage=15), 3),  # market-flail-superior-15ed-4os: asks 4.05 Ist (n5, 2026-09-18)
    ('Sacred Targe', Rolls(4, resists=45), 2),  # sacred-targe-45-res: asks 5.89-18.5 Ist (n9)
    ('Sacred Targe', Rolls(4, resists=45, ethereal=True), 2),  # the Exile base: asks 57.1-74.2 Ist (n4)
    ('Kriss', Rolls(3, ((402, 3),)), 2),  # a grey 3os Kriss +3 Abyss: the Void row's 4.05-17.3 Ist (n37)
    ('Kriss', Rolls(0, ((402, 3),)), 2),  # 0os +3 Abyss (Larzuk)
    ('Legend Spike', Rolls(3, ((389, 3),)), 2),  # 3os +3 Hex: Purge
    ('Monarch', Rolls(4, defense=15), 3),  # spirit-monarch-superior-15ed: 9.32-17.1 Ist (n4)
    ('Giant Thresher', Rolls(4, ethereal=True), 2),  # merc-insight-gt-eth-4os: 5.89-11.4 Ist (n20)
    ('Phase Blade', Rolls(5, damage=15), 3),  # market-phase-blade-superior-15ed-5-6os: 11.4-22.8 Ist (n5)
    ('Possessed Grimoire', Rolls(2, ((376, 3),)), 2),  # +3 Summon Tainted: 0.67-5.89 Ist (n11)
    # Added from rca/2026-10-23/base-candidates.md §1 (fills first)
    ('Kriss', Rolls(3, ((402, 3), (399, 2))), 2),  # +3 Abyss + Miasma Chain 2
    ('Blade', Rolls(3, ((402, 3), (397, 2))), 2),  # + Enhanced Entropy
    ('Legend Spike', Rolls(0, ((389, 3),)), 2),  # 0os +3 Hex: Purge: fills 18.6 (n8)
    ('Sacred Targe', Rolls(3, resists=42), 2),  # 40-44 res 3os: fills 9.32 (n5)
    ('Sacred Rondache', Rolls(4, resists=45, defense=15), 3),  # superior 15 ED 4os 45: 68.5 (n3)
    ('Wire Fleece', Rolls(3, defense=15), 3),  # superior 15 ED 3os: 11.4 (n10)
    ('Dusk Shroud', Rolls(4, defense=15), 3),
    ('Sacred Armor', Rolls(0, ethereal=True), 2),  # eth 0os: 9.32 (n7)
    ('Lich Wand', Rolls(2, ((84, 3), (93, 3))), 2),  # fills 22.8 (n16)
    ('Divine Scepter', Rolls(5, ((121, 3), (123, 2))), 2),  # +3 FoH and +2 Conviction: n9 median 9.32
    ('Divine Scepter', Rolls(5, ((112, 3), (113, 2))), 2),  # Hammer + Concentration: fills 43.6, 57.1
    ('Archon Staff', Rolls(5, ((58, 3),)), 2),  # +3 Energy Shield 5os: 34.3 (n4)
    ('Mask', Rolls(3, defense=15), 3),  # superior 15 ED 3os: 4.05 (n7)
    ('Demonhead', Rolls(3, defense=15, ethereal=True), 3),  # eth superior 15 ED Cure: 11.4 (n4)
    # The verifier's MISSED (rca/2026-10-23/base-pickups-verify.md)
    ('War Pike', Rolls(6, ethereal=True, damage=15), 3),  # a 15 ED copy of the ordinary key (119.9)
    ('Archon Staff', Rolls(6, ethereal=True, damage=5), 3),  # a superior copy of the normal key (22.8)
    ('Grim Wand', Rolls(2, ((92, 3),)), 2),  # +3 Poison Nova: fills 11.4 (n4)
    ('Greater Talons', Rolls(3, ((278, 3),)), 2),  # +3 Venom: asks 206 at the fill ratio
    ('Runic Talons', Rolls(3, ((273, 3),)), 3),  # +3 Mind Blast: 86 x 0.1
    ('Sacred Armor', Rolls(0, defense=15), 3),  # superior 15 ED: 5.89 (n7)
    ('Sacred Armor', Rolls(3, defense=15), 3),  # 28.6 (n6)
    ('Sacred Armor', Rolls(4, defense=15), 3),  # 18.6 (n7)
    ('Colossus Blade', Rolls(0, ethereal=True), 2),  # eth 0os: 11.4 (n3)
    ('Phase Blade', Rolls(0, damage=15), 3),  # 0os 15 ED: 8.23 (n3)
    ('Archon Plate', Rolls(3, defense=5), 3),  # superior 3os: 9.32 (n3)
    ('Gilded Shield', Rolls(4, resists=45), 2),  # 45 res: fills 4.97 (n8)
    ('Sacred Rondache', Rolls(4, resists=42, ethereal=True), 2),  # the Exile base, eth
    ('Great Poleaxe', Rolls(4, ethereal=True, damage=5), 3),  # eth 4os superior: 34.3 (n6)
    # The base-price ruling (2026-10-23 ~17:20, "Sales-backed now"): the sales-backed adds
    ('Kriss', Rolls(3, ((402, 2), (399, 2))), 2),  # Abyss 2 and Miasma Chain 2: fills n23 median 171
    ('Sacred Rondache', Rolls(3, resists=45), 2),  # 3os 45 normal: fills n33 median 8.23
    ('Archon Plate', Rolls(4, ethereal=True, defense=5), 3),  # eth 4os superior: fills n18 median 14.4
]


@pytest.mark.parametrize('mode', MODES)
@pytest.mark.parametrize(('name', 'rolls', 'quality'), TAKEN, ids=[f'{n} {r.sockets}os q{q}' for n, r, q in TAKEN])
def test_an_allowlisted_base_is_taken_in_every_level(mode, name, rolls, quality, monkeypatch):
    from inventory_tracking.loot import value

    monkeypatch.setattr(value, 'owned_bases', lambda facts: 0)
    found = base(name, (2, 2), rolls, quality=quality, unit=42)
    assert [d.unit_id for d in kept(Loot(drops=(found,), game=GAME, room=EMPTY), mode).drops] == [42]


def test_a_material_white_base_goes_through_the_allowlist_too(monkeypatch):
    """A 3os +3 Apocalypse-alone dagger read as 'material' was taken by the old path (the verifier, 2026-10-23)."""
    from inventory_tracking.loot import value

    monkeypatch.setattr(value, 'owned_bases', lambda facts: 0)
    apocalypse = replace(base('Kriss', (1, 3), Rolls(3, ((401, 3),)), unit=46), source='material')
    abyss = replace(base('Kriss', (1, 3), Rolls(3, ((402, 3),)), unit=47), source='material')
    for mode in MODES:
        assert kept(Loot(drops=(apocalypse,), game=GAME, room=EMPTY), mode).drops == (), mode
        assert [d.unit_id for d in kept(Loot(drops=(abyss,), game=GAME, room=EMPTY), mode).drops] == [47], mode


def test_a_taken_base_is_remembered_under_its_game(monkeypatch):
    from inventory_tracking.loot import base_floor, value

    monkeypatch.setattr(value, 'owned_bases', lambda facts: 0)
    kriss = base('Kriss', (1, 3), Rolls(3, ((402, 3),)), unit=48)
    assert kept(Loot(drops=(kriss,), game=GAME, room=EMPTY), MOST).drops
    assert base_floor.remembered(48, GAME) is not None
    assert base_floor.remembered(48) is not None  # the town asks within the game the pickup saw last
    assert base_floor.remembered(48, ('game-2', 8)) is None


def test_wirts_leg_is_never_left_by_the_allowlist():
    from inventory_tracking.macros.pickmode import plain_base

    assert plain_base(base("Wirt's Leg", (1, 3), Rolls(0), unit=45)) is None


def test_every_allowlist_entry_is_worth_four_ist_by_dated_evidence():
    from inventory_tracking.loot import base_floor

    found = base_floor.pickups()
    assert found['rows']
    assert found['kb']
    for name, entry in [*found['rows'].items(), *found['kb'].items()]:
        evidence = entry.get('evidence', entry)
        assert evidence['median_ist'] >= base_floor.PICKUP_IST, name
        assert evidence['n'] >= 3, name
        assert evidence['observed'], name
        assert evidence['source'], name


def test_the_switch_off_takes_what_the_filter_shows_at_most(monkeypatch):
    from inventory_tracking.loot import base_floor

    flail = base('Flail', (2, 3), JUNK_FLAIL, quality=3, unit=33)
    monkeypatch.setattr(base_floor, 'BASE_FLOOR', False)
    monkeypatch.setattr(base_floor, 'PLAIN_BY_RULES', False)
    assert kept(Loot(drops=(flail,), game=GAME, room=EMPTY), MOST).drops == (flail,)
