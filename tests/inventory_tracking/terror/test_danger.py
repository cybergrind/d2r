"""Deadly packs: threat per monster from the game's tables, raised by modifiers, auras and density."""

from inventory_tracking.terror.danger import DANGER, Unit, packs, table


DARK_RANGER, HELL_BOVINE, GLOAM, OBLIVION_KNIGHT, FALLEN = 160, 391, 118, 312, 19
STRONG, CURSED, MULTISHOT, AURA = 5, 7, 29, 30
MIGHT, FANATICISM, CONVICTION = 98, 122, 123


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
    cows = group(HELL_BOVINE, 30)

    assert top(cows).score == top(cows[: DANGER.melee_count]).score
    assert top(cows).band is None
    assert top(group(HELL_BOVINE, 30, modifiers=(STRONG,), aura=(FANATICISM, 9))).band == 'deadly'


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
