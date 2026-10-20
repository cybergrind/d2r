"""The KP_6 loop's pickup mode (macros/pickmode.py; routes/lower-kurast-loop-plan.md phase 7). Item classes by their
items.txt row as the bundled metadata names them (items/metadata.py `item_base`), looked up, not written from memory."""

from dataclasses import replace

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


ABYSS, HEX_PURGE, CONSUME, PSYCHIC_WARD = 402, 389, 381, 387  # skills metadata ids


def test_a_white_void_base_is_taken_only_with_three_sockets_and_a_paid_staff_mod_at_three():
    # The player, 18:56 on 2026-10-17: "it looks like we're storing daggers with 1os ... we need good staff mod and we
    # need 3os; we shouldn't waste shared stash tab"
    kriss = drop('Kriss', source='shown', quality=2)
    assert is_candidate(replace(kriss, rolls=Rolls(3, ((ABYSS, 3),))))
    assert not is_candidate(replace(kriss, rolls=Rolls(1, ((ABYSS, 3),))))  # Void needs exactly three
    assert not is_candidate(replace(kriss, rolls=Rolls(2, ((ABYSS, 3),))))
    # No socket and +3 Abyss: Larzuk's sockets make it one (the player, 19:40: "0 socket +3 abyss - let's pickup them")
    assert is_candidate(replace(kriss, rolls=Rolls(0, ((ABYSS, 3),))))
    assert not is_candidate(replace(kriss, rolls=Rolls(0, ((HEX_PURGE, 3),))))
    assert not is_candidate(replace(kriss, rolls=Rolls(0, ((ABYSS, 2),))))
    assert not is_candidate(replace(kriss, rolls=Rolls(3, ((ABYSS, 2),))))  # a staff mod buyers do not pay for
    assert is_candidate(replace(kriss, rolls=Rolls(3, ((HEX_PURGE, 3),))))
    assert not is_candidate(replace(kriss, rolls=Rolls(3, ((PSYCHIC_WARD, 3),))))
    assert not is_candidate(replace(kriss, rolls=Rolls(3, ((CONSUME, 3),))))  # asked, never paid
    assert not is_candidate(replace(kriss, rolls=Rolls(3)))  # no staff mod
    assert not is_candidate(kriss)  # unread: not taken
    assert not sure(replace(kriss, rolls=Rolls(1, ((ABYSS, 3),))))


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


def test_a_monarch_or_a_sacred_targe_is_taken_by_the_rolls_that_sell():
    # The player, 19:10 on 2026-10-17: "start picking up monarchs (for 4os deflecting) and sacred targes (check what
    # are expensive ones)"; the market study's rule (pickmode.py SHIELD_*)
    monarch = drop('Monarch', source='shown', quality=3)
    assert is_candidate(replace(monarch, rolls=Rolls(4, defense=15)))
    assert is_candidate(replace(monarch, rolls=Rolls(0, defense=15)))  # Larzuk's sockets
    assert not is_candidate(replace(monarch, rolls=Rolls(4, defense=12)))  # asked 2 Ist
    assert not is_candidate(replace(monarch, quality=2, rolls=Rolls(4)))  # a white 4os asked 0.79
    assert is_candidate(replace(monarch, quality=4, rolls=Rolls(4)))  # magic 4os: identified, then appraised
    assert not is_candidate(replace(monarch, quality=4, rolls=Rolls(2)))
    targe = drop('Sacred Targe', source='shown', quality=2)
    assert is_candidate(replace(targe, rolls=Rolls(0, resists=45)))
    assert is_candidate(replace(targe, rolls=Rolls(3, resists=42)))
    assert not is_candidate(replace(targe, rolls=Rolls(2, resists=42)))
    assert not is_candidate(replace(targe, rolls=Rolls(4, resists=38)))
    rondache = drop('Sacred Rondache', source='shown', quality=2)
    assert is_candidate(replace(rondache, rolls=Rolls(4, resists=45)))
    assert is_candidate(replace(rondache, rolls=Rolls(0, resists=45, ethereal=True)))
    assert not is_candidate(replace(rondache, rolls=Rolls(3, resists=45)))
    assert not is_candidate(replace(rondache, rolls=Rolls(4, resists=44)))
    assert not is_candidate(targe)  # unread: not taken
