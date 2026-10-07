"""Deadly packs: threat per monster from the game's tables, raised by modifiers, auras and density."""

import pytest

from inventory_tracking.terror.danger import DANGER, STATES, Unit, packs, table, threat


DARK_RANGER, HELL_BOVINE, GLOAM, OBLIVION_KNIGHT, FALLEN = 160, 391, 118, 312, 19
GHOUL, VENOM_LORD, TAINTED = 7, 362, 11  # speeds 4 and 16; lightning 2.0 against the Gloam's 1.9
STRONG, FAST, CURSED, TELEPORT, MULTISHOT, AURA = 5, 6, 7, 26, 29, 30
MIGHT, FANATICISM, CONVICTION, HOLY_FREEZE = 98, 122, 123, 365


def group(txt_id, count, *, start=1, x=1000, y=1000, **traits):
    """`count` monsters two units apart in a row."""
    return [Unit(start + n, txt_id, x + 2 * n, y, **traits) for n in range(count)]


def top(units):
    return packs(units)[0]


def test_the_bundled_table_knows_the_monsters_the_auras_and_the_modifier_names():
    threats = table()

    assert threats.monsters[DARK_RANGER].name == 'Dark Ranger'
    assert threats.monsters[DARK_RANGER].ranged
    assert not threats.monsters[HELL_BOVINE].ranged
    assert threats.monsters[OBLIVION_KNIGHT].curses == ('Decrepify',)
    assert {skill: name for skill, (name, *_range) in threats.auras.items()} == {
        98: 'Might', 108: 'Blessed Aim', 122: 'Fanaticism', 123: 'Conviction',
        365: 'Holy Freeze', 368: 'Holy Fire', 369: 'Holy Shock',
    }  # fmt: skip
    assert (threats.modifiers[STRONG], threats.modifiers[MULTISHOT]) == ('Extra Strong', 'Multiple Shots')
    assert threats.aura_range(MIGHT, 12) == 16 + 11 * 2  # skills.txt: Param1 + (level - 1) x Param2


def test_a_plain_archer_pack_is_not_marked():
    pack = top(group(DARK_RANGER, 4))

    assert (pack.band, pack.name, pack.count, pack.reasons) == (None, 'Dark Ranger', 4, ())


def test_archers_under_fanaticism_are_deadly_and_say_why():
    archers = group(DARK_RANGER, 8, aura=(FANATICISM, 9))

    pack = top(archers)

    assert pack.band == 'deadly'
    assert pack.label == 'Dark Ranger x8 · Fanaticism'
    assert pack.score > 1.5 * top(group(DARK_RANGER, 8)).score


def test_an_aura_owner_gives_its_aura_to_the_monsters_within_its_range_only():
    owner = Unit(99, FALLEN, 1000, 1010, modifiers=(AURA,), aura=(MIGHT, 12), owner=True)  # range 38
    inside, outside = group(DARK_RANGER, 6), group(DARK_RANGER, 6, start=50, x=1100)

    found = {pack.members[0]: pack for pack in packs([owner, *inside, *outside])}

    assert 'Might' in found[1].reasons
    assert found[50].reasons == ()


def test_density_adds_up_two_archer_packs_standing_together_are_one_pack():
    near = [*group(DARK_RANGER, 5), *group(DARK_RANGER, 5, start=20, y=1020)]
    apart = [*group(DARK_RANGER, 5), *group(DARK_RANGER, 5, start=20, y=1200)]

    assert [pack.count for pack in packs(near)] == [10]
    assert top(near).score == 2 * top(apart).score
    assert [pack.count for pack in packs(apart)] == [5, 5]


def test_melee_counts_for_less_and_only_as_many_as_reach_the_player():
    lords = group(VENOM_LORD, 30)

    assert top(lords).score == top(lords[: DANGER.melee_count]).score
    assert top(lords).band is None
    assert top(group(VENOM_LORD, 30, modifiers=(STRONG,), aura=(FANATICISM, 9))).band == 'deadly'


def test_melee_too_slow_to_reach_the_player_is_no_burst_whatever_raises_it():
    # Zombies were marked for Extra Strong + Cursed alone; they never catch anyone (user, 2026-10-07).
    raised = {'modifiers': (STRONG, CURSED), 'aura': (MIGHT, 9)}

    assert [pack.band for pack in packs(group(GHOUL, 8, **raised))] in ([], [None])
    assert top(group(VENOM_LORD, 8, **raised)).band == 'deadly'
    # In between: a cow walks at 5 against the player's run of 9.
    cows, lords = top(group(HELL_BOVINE, 8)), top(group(VENOM_LORD, 8))
    assert 0 < cows.score / 1.8 < lords.score / 1.6


def test_what_makes_slow_melee_fast_is_what_makes_it_a_threat():
    fast = top(group(GHOUL, 8, modifiers=(FAST,)))

    assert (fast.score > 0, fast.reasons) == (True, ('Extra Fast',))
    assert top(group(GHOUL, 1, modifiers=(TELEPORT,))).score > 3 * top(group(GHOUL, 1)).score
    # A monster that reaches the player anyway gains only the faster attacks.
    for reaching in (VENOM_LORD, DARK_RANGER):
        plain = top(group(reaching, 1)).score
        assert top(group(reaching, 1, modifiers=(FAST,))).score == pytest.approx(1.25 * plain, abs=0.01)


def test_holy_freeze_slows_the_player_so_melee_reaches():
    owner = Unit(99, FALLEN, 1000, 1040, modifiers=(AURA,), aura=(HOLY_FREEZE, 9), owner=True)
    cows = group(HELL_BOVINE, 8)

    frozen = next(pack for pack in packs([owner, *cows]) if pack.name == 'Hell Bovine')

    assert frozen.score > 1.5 * top(cows).score
    assert frozen.reasons == ('Holy Freeze',)


def test_a_few_hard_hitters_are_marked_without_any_aura():
    # Four Gloams took 18% of the life within a second (probe log 20261006T161833Z, area 77).
    assert (top(group(GLOAM, 4)).band, top(group(GLOAM, 6)).band) == ('caution', 'deadly')
    assert top(group(TAINTED, 4)).band is None


def test_own_modifiers_raise_the_monster_that_carries_them():
    plain, strong = top(group(DARK_RANGER, 1)), top(group(DARK_RANGER, 1, modifiers=(STRONG,)))
    multishot = top(group(DARK_RANGER, 1, modifiers=(MULTISHOT,)))

    assert (strong.score, strong.reasons) == (2 * plain.score, ('Extra Strong',))
    assert multishot.score == 2 * plain.score
    # Multiple Shots is nothing on a melee attacker.
    assert top(group(HELL_BOVINE, 1, modifiers=(MULTISHOT,))).score == top(group(HELL_BOVINE, 1)).score


def test_conviction_raises_elemental_damage_near_its_owner():
    owner = Unit(99, FALLEN, 1000, 1040, modifiers=(AURA,), aura=(CONVICTION, 9), owner=True)
    souls = group(GLOAM, 4)

    with_owner = next(pack for pack in packs([owner, *souls]) if pack.name == 'Gloam')

    assert with_owner.score > top(souls).score
    assert with_owner.reasons == ('Conviction',)


def test_a_curse_source_nearby_raises_physical_damage():
    archers = group(DARK_RANGER, 4)
    knight = Unit(99, OBLIVION_KNIGHT, 1000, 1050)
    cursed = Unit(98, FALLEN, 1000, 1050, modifiers=(CURSED,))

    by_knight = next(pack for pack in packs([knight, *archers]) if pack.name == 'Dark Ranger')
    by_cursed = next(pack for pack in packs([cursed, *archers]) if pack.name == 'Dark Ranger')

    assert (by_knight.reasons, by_cursed.reasons) == (('Decrepify',), ('Cursed',))
    assert by_knight.score == by_cursed.score == 1.5 * top(archers).score


def test_a_monster_of_no_known_type_scores_nothing():
    assert packs([Unit(1, 99999, 1000, 1000)]) == []


def test_a_marked_pack_keeps_its_mark_until_it_is_clearly_weaker():
    # Kills, a monster stepping out of an aura or a pack splitting move the score across the
    # line and back: the marks toggled (user, 2026-10-06).
    eight, seven, five = (group(DARK_RANGER, count, aura=(FANATICISM, 9)) for count in (8, 7, 5))
    deadly = dict.fromkeys(range(1, 9), 'deadly')
    assert (top(eight).band, top(seven).band) == ('deadly', 'caution')

    assert top(seven).score < DANGER.deadly
    assert packs(seven, held=deadly)[0].band == 'deadly'
    assert top(five).score < DANGER.release * DANGER.deadly
    assert packs(five, held=deadly)[0].band != 'deadly'


def test_a_pack_to_be_careful_with_is_held_too_and_a_mark_is_not_passed_on_by_a_few_monsters():
    plain = group(DARK_RANGER, 8)
    assert top(plain).band is None
    assert DANGER.release * DANGER.caution <= top(plain).score < DANGER.caution

    assert packs(plain, held=dict.fromkeys(range(1, 9), 'caution'))[0].band == 'caution'
    assert packs(plain, held=dict.fromkeys(range(1, 9), 'deadly'))[0].band == 'caution'
    assert packs(plain, held={1: 'deadly', 2: 'deadly'})[0].band is None  # most of the pack was unmarked


AMPLIFIED, CHILLED, CONVICTED, DECREPIFIED, LOWER_RESIST = 9, 11, 29, 60, 61  # states.txt ids, on the player


def test_a_curse_on_the_player_raises_every_pack_and_is_named():
    archers, souls = group(DARK_RANGER, 5), group(GLOAM, 2)

    amplified = packs(archers, player={AMPLIFIED})[0]
    lowered = packs(souls, player={LOWER_RESIST})[0]

    assert (amplified.score, amplified.reasons) == (2 * top(archers).score, ('Amplify Damage on you',))
    assert amplified.band == 'caution'
    assert (lowered.score > 2 * top(souls).score, lowered.reasons) == (True, ('Lower Resist on you',))
    assert packs(souls, player={AMPLIFIED})[0].score == top(souls).score  # lightning is not physical
    assert packs(archers, player={208})[0].score == top(archers).score  # the player's own Consume


def test_the_curse_on_the_player_is_counted_once_with_its_source_nearby():
    archers = group(DARK_RANGER, 4)
    knight = Unit(99, OBLIVION_KNIGHT, 1000, 1050)

    cursed = next(pack for pack in packs([knight, *archers], player={DECREPIFIED}) if pack.name == 'Dark Ranger')

    assert (cursed.score, cursed.reasons) == (1.5 * top(archers).score, ('Decrepify on you',))


def test_conviction_on_the_player_counts_without_its_owner_in_sight_and_only_once():
    owner = Unit(99, FALLEN, 1000, 1040, modifiers=(AURA,), aura=(CONVICTION, 9), owner=True)
    souls = group(GLOAM, 2)

    by_owner = next(pack for pack in packs([owner, *souls]) if pack.name == 'Gloam')
    both = next(pack for pack in packs([owner, *souls], player={CONVICTED}) if pack.name == 'Gloam')

    assert packs(souls, player={CONVICTED})[0].score == 3 * top(souls).score
    assert both.score == by_owner.score


def test_a_slowed_player_is_reached_by_melee():
    cows = group(HELL_BOVINE, 8)

    chilled, decrepified = packs(cows, player={CHILLED})[0], packs(cows, player={DECREPIFIED})[0]

    assert (chilled.score > 1.5 * top(cows).score, chilled.reasons) == (True, ('Chilled',))
    assert decrepified.score > 1.5 * chilled.score  # slower, and physical damage raised
    assert packs(group(DARK_RANGER, 4), player={CHILLED})[0].score == top(group(DARK_RANGER, 4)).score


REANIMATED_HORDE, PROWLING_DEAD_SPEED, HELL_LORD, ABYSS_KNIGHT, UNDEAD_STYGIAN_DOLL = 437, 5, 509, 311, 216


def test_what_is_known_of_nasty_monsters_is_in_their_threat():
    threats = table()
    horde, lord = threats.monsters[REANIMATED_HORDE], threats.monsters[HELL_LORD]

    # Charge: a horde walks at 5 and still arrives.
    assert (horde.speed, horde.closes) == (PROWLING_DEAD_SPEED, True)
    assert top(group(REANIMATED_HORDE, 1)).score == pytest.approx(horde.physical * DANGER.melee * DANGER.arrives)
    # Frenzy: half as many swings again; a plain pack stays unmarked, an Extra Strong one is deadly.
    swing = lord.physical + lord.elemental * DANGER.resisted
    assert top(group(HELL_LORD, 8)).score == pytest.approx(8 * swing * DANGER.melee * DANGER.frenzy)
    assert (top(group(HELL_LORD, 8)).band, top(group(HELL_LORD, 8, modifiers=(STRONG,))).band) == (None, 'deadly')
    # Six Abyss Knights took 18% of the life within a second, twice (probe log 20261006T175752Z).
    assert top(group(ABYSS_KNIGHT, 6)).band == 'caution'
    # Undead dolls blow up when killed.
    assert top(group(UNDEAD_STYGIAN_DOLL, 8)).score == pytest.approx(8 * 1.05 * DANGER.melee * 2)


HOLY_FIRE, HOLY_SHOCK = 368, 369


def test_an_elemental_aura_adds_its_damage_to_every_attack_in_it():
    plain = top(group(DARK_RANGER, 4)).score

    shocked = top(group(DARK_RANGER, 4, aura=(HOLY_SHOCK, 9)))
    burning = top(group(DARK_RANGER, 4, aura=(HOLY_FIRE, 9)))

    assert shocked.score == pytest.approx(plain + 4 * 0.4 * DANGER.resisted)
    assert burning.score == pytest.approx(plain + 4 * 0.3 * DANGER.resisted)
    assert shocked.score > burning.score > plain
    # Lower Resist on the player raises what the aura adds too.
    assert packs(group(DARK_RANGER, 4, aura=(HOLY_SHOCK, 9)), player={LOWER_RESIST})[0].score > shocked.score


def test_the_drops_of_life_in_the_probe_logs_are_marked():
    # 2026-10-06, 15% of the life or more within a second, and what stood there.
    slinger = next(txt_id for txt_id, row in table().monsters.items() if row.name == 'Slinger')

    assert top(group(slinger, 14, aura=(FANATICISM, 9))).band == 'deadly'  # 16% and 21%
    assert top(group(GLOAM, 4)).band == 'caution'  # 18%
    assert top(group(ABYSS_KNIGHT, 6)).band == 'caution'  # 18% and 17%


def test_every_type_of_the_bundled_table_follows_the_three_rules():
    threats = table()
    for txt_id, row in threats.monsters.items():
        unit = Unit(1, txt_id, 1000, 1000)
        value, reasons = threat(unit, [unit], threats, DANGER)
        hit = (row.physical + row.elemental * DANGER.resisted + row.magic) * DANGER.hard.get(row.family, 1)
        assert reasons == {}, row.name
        if row.ranged:  # reach: a ranged hit always lands
            assert value == pytest.approx(hit), row.name
        elif row.speed <= DANGER.still and not row.closes:  # melee that never arrives
            assert value == 0, row.name
        else:  # melee: never more than its share, in full only as fast as the player
            share = DANGER.melee * (DANGER.frenzy if row.frenzy else 1)
            assert 0 <= value <= hit * share + 1e-9, row.name
            assert (value == pytest.approx(hit * share)) == (row.speed >= DANGER.player_run or not hit), row.name


def test_no_state_of_the_player_and_no_modifier_ever_lowers_a_threat():
    threats = table()
    for txt_id in (DARK_RANGER, GLOAM, GHOUL, HELL_BOVINE, VENOM_LORD, ABYSS_KNIGHT, REANIMATED_HORDE):
        unit = Unit(1, txt_id, 1000, 1000)
        plain = threat(unit, [unit], threats, DANGER)[0]
        for state in STATES:
            assert threat(unit, [unit], threats, DANGER, frozenset((state,)))[0] >= plain, (txt_id, state)
        for modifier in threats.modifiers:
            raised = Unit(1, txt_id, 1000, 1000, modifiers=(modifier,))
            assert threat(raised, [raised], threats, DANGER)[0] >= plain, (txt_id, modifier)
        assert threat(unit, [unit], threats, DANGER, frozenset(STATES))[0] >= plain


def test_all_that_raises_a_pack_is_counted_together_and_the_strongest_reasons_are_named():
    # Hit (Extra Strong, Might), rate (Extra Fast) and reach (Extra Fast on slow melee), with a curse on the player.
    cows = group(HELL_BOVINE, 8, modifiers=(STRONG, FAST), aura=(MIGHT, 9))

    pack = packs(cows, player={AMPLIFIED})[0]

    hit = 1.8 * 2 * 2 * 2  # Extra Strong, Might, Amplify Damage
    assert pack.score == pytest.approx(8 * hit * 1.25 * DANGER.melee * 1.0)  # a cow at 5 x 2 runs past 9
    assert pack.band == 'deadly'
    assert set(pack.reasons) == {'Extra Strong', 'Might', 'Amplify Damage on you', 'Extra Fast'}
