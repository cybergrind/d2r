"""The synthetic battlefields: monster mixes of real levels (threat_table.json `areas`) at the Terror
Zone's monster level, laid out so that the line worth the most life points is not the right one.

Every scene has the wanted decisions as explicit controllers (`wanted`), so a test compares what the
game's decision costs with what the best of them costs in the same model (harness.py). Positions are
world units from the character: x to the east, y to the south.
"""

from collections.abc import Callable
from dataclasses import dataclass

from tests.inventory_tracking.scenarios.threat.harness import (
    HORIZON,
    TICKS,
    Controller,
    Scene,
    Survivor,
    hostile,
    leave,
    order,
    step_then,
)


# txt ids, each a row of threat_table.json (monstats *hcIdx)
GHOUL, AFFLICTED = 7, 10  # Catacombs Level 3 (36), recorded
GLOAM, BRAMBLE_HULK = 118, 128  # Great Marsh (77)
HELL_BOVINE = 391  # Moo Moo Farm (39)
ABYSS_KNIGHT = 311  # River of Flame (107)
OBLIVION_KNIGHT, STORM_CASTER, VENOM_LORD = 312, 306, 362  # Chaos Sanctuary (108), recorded
HELL_WITCH, DEATH_LORD, BURNING_SOUL, UNDEAD_SOUL_KILLER = 478, 510, 641, 691  # Throne of Destruction (131)
GHOST, RETURNED_ARCHER, SLAYER = 631, 578, 682  # Halls of Vaught (124)
CURSE = 1.5  # terror/danger.py DANGER.curse: Amplify Damage or Decrepify on the character
MIGHT = 2.0  # DANGER.aura_physical: Might on the monsters around its owner
HERALD = {'life_factor': 11.0, 'damage_factor': 1.5}  # tier 1: +1000% life, +50% damage (threat_table.json rules)
HERALD_MINION = {'life_factor': 3.5, 'damage_factor': 1.1}  # +250% life, +10% damage; six of them


@dataclass(frozen=True)
class Spec:
    scene: Callable[[], Scene]
    wanted: dict[str, Callable[[], Controller]]  # the candidate right decisions, by name
    horizon: int = HORIZON


def gloams_behind_hulks() -> Scene:
    """Four slow Bramble Hulks in a line, 46,000 points on one line and seconds from their first swing;
    three Gloams apart from each other, a line each, shooting from the first tick."""
    hulks = [hostile(n, BRAMBLE_HULK, 10.0 + 3.0 * n, 0.0) for n in range(4)]
    gloams = [hostile(10, GLOAM, 0.0, -16.0), hostile(11, GLOAM, -13.0, -9.0), hostile(12, GLOAM, -15.0, 6.0)]
    return Scene('gloams behind hulks', 77, hulks + gloams)


def witch_and_soul_beside_tanky_elite() -> Scene:
    """A unique Death Lord, twice the life and twice the worth of a point, walking in; a Hell Witch whose
    curse raises everything's damage and a Burning Soul, both frail."""
    return Scene(
        'witch and soul beside a tanky elite',
        131,
        [
            hostile(1, DEATH_LORD, 12.0, 0.0, elite=True),
            hostile(2, HELL_WITCH, 0.0, 14.0, boost=CURSE),
            hostile(3, BURNING_SOUL, -12.0, 8.0),
        ],
    )


def dying_gloam_fresh_hulk() -> Scene:
    """A Gloam at a tenth of its life, one cast from dead and shooting; a fresh Bramble Hulk not yet near."""
    return Scene(
        'dying gloam, fresh hulk', 77, [hostile(1, BRAMBLE_HULK, 12.0, 0.0), hostile(2, GLOAM, 0.0, 15.0, share=0.1)]
    )


def equal_lines_far_and_in_contact() -> Scene:
    """Two lines of two Hell Bovines, the same points: one pair 18 units off, the other swinging already."""
    far = [hostile(1, HELL_BOVINE, 16.0, 0.0), hostile(2, HELL_BOVINE, 19.0, 0.0)]
    near = [hostile(3, HELL_BOVINE, -1.6, 0.0), hostile(4, HELL_BOVINE, -2.8, 0.0)]
    return Scene('equal lines, one in contact', 39, far + near)


def stone_skin_elite_soaks() -> Scene:
    """A unique Ghoul with Stone Skin, immune to the blades (32 of them in the Catacombs takes), in front;
    three Afflicted shooting from apart."""
    return Scene(
        'stone skin elite soaks the line',
        36,
        [
            hostile(1, GHOUL, 6.0, 0.0, elite=True, immune=True),
            hostile(2, AFFLICTED, 0.0, 12.0),
            hostile(3, AFFLICTED, -10.0, 8.0),
            hostile(4, AFFLICTED, -13.0, -3.0),
        ],
    )


def ghosts_in_front_of_archers() -> Scene:
    """Three Ghosts (immune by their type) in a line in front, two Returned Archers and a Slayer that can die."""
    ghosts = [hostile(n, GHOST, 6.0 + 3.0 * n, 0.0) for n in range(3)]
    rest = [
        hostile(10, RETURNED_ARCHER, 0.0, -14.0),
        hostile(11, RETURNED_ARCHER, -14.0, 0.0),
        hostile(12, SLAYER, 0.0, 12.0),
    ]
    return Scene('ghosts in front of archers', 124, ghosts + rest)


def bovines_closing_from_two_sides() -> Scene:
    """Three Hell Bovines from the east and three from the west, a second and a half from surrounding."""
    east = [hostile(n, HELL_BOVINE, 10.0 + 2.0 * n, -3.0 + 3.0 * n) for n in range(3)]
    west = [hostile(10 + n, HELL_BOVINE, -10.0 - 2.0 * n, 3.0 - 3.0 * n) for n in range(3)]
    return Scene('bovines closing from two sides', 39, east + west)


def low_life_in_melee() -> Scene:
    """A third of the life left, three Hell Bovines swinging from three sides."""
    cows = [hostile(1, HELL_BOVINE, 1.6, 0.0), hostile(2, HELL_BOVINE, -0.8, 1.4), hostile(3, HELL_BOVINE, -0.8, -1.4)]
    return Scene('low life in melee', 39, cows, life=500.0)


def low_life_two_dying_gloams() -> Scene:
    """Little life left, but both Gloams die to one cast each: fighting on is right, running is death."""
    gloams = [hostile(1, GLOAM, 0.0, 14.0, share=0.15), hostile(2, GLOAM, 14.0, 0.0, share=0.1)]
    return Scene('low life, two dying gloams', 77, gloams, life=400.0)


def low_life_under_knights() -> Scene:
    """A third of the life left and four fresh Oblivion Knights shooting from an arc: eight casts to clear."""
    knights = [
        hostile(n, OBLIVION_KNIGHT, x, y)
        for n, (x, y) in enumerate(((-12.0, -12.0), (-4.0, -17.0), (5.0, -17.0), (13.0, -11.0)), 1)
    ]
    return Scene('low life under knights', 108, knights, life=600.0)


def dolls_running_in() -> Scene:
    """Three Undead Soul Killers running in (their corpses explode) and five Death Lords on a richer line."""
    lords = [hostile(n, DEATH_LORD, 0.0, -9.0 - 3.0 * n) for n in range(5)]
    dolls = [hostile(10 + n, UNDEAD_SOUL_KILLER, 12.0 + 4.0 * n, 3.0 * n) for n in range(3)]
    return Scene('dolls running in', 131, lords + dolls)


def dolls_on_the_character() -> Scene:
    """Three Undead Soul Killers already stabbing: killing them here blows them up on the character."""
    dolls = [
        hostile(1, UNDEAD_SOUL_KILLER, 1.6, 0.0),
        hostile(2, UNDEAD_SOUL_KILLER, 1.3, 1.0),
        hostile(3, UNDEAD_SOUL_KILLER, 1.3, -1.0),
    ]
    return Scene('dolls on the character', 131, dolls, life=900.0)


def might_elite_beside_minions() -> Scene:
    """A unique Venom Lord with Might and four minions in a line: the aura doubles what they hit for while
    it lives, the line of minions is worth twice the elite's points."""
    minions = [hostile(n, VENOM_LORD, 9.0 + 3.0 * n, 0.0) for n in range(4)]
    return Scene(
        'might elite beside minions', 108, [*minions, hostile(10, VENOM_LORD, 0.0, -13.0, elite=True, boost=MIGHT)]
    )


def herald_with_minions() -> Scene:
    """A tier 1 Herald (an Abyss Knight with eleven times the life) in front, its six minions in an arc."""
    arc = ((-15.0, -8.0), (-9.0, -15.0), (0.0, -18.0), (9.0, -15.0), (15.0, -8.0), (17.0, 1.0))
    minions = [hostile(n, ABYSS_KNIGHT, x, y, **HERALD_MINION) for n, (x, y) in enumerate(arc, 1)]
    return Scene('herald with minions', 107, [hostile(10, ABYSS_KNIGHT, 0.0, -8.0, elite=True, **HERALD), *minions])


def stone_skin_zone() -> Scene:
    """A Terror Zone whose forced modifier is Stone Skin: every Hell Bovine (50% physical resistance) is immune."""
    return Scene(
        'stone skin zone', 39, [hostile(n, HELL_BOVINE, 12.0 + 2.0 * n, -4.0 + 2.0 * n, immune=True) for n in range(5)]
    )


def venom_lords_and_casters() -> Scene:
    """The recorded Chaos Sanctuary mix at the Terror Zone's level: Venom Lords in a line, casters apart."""
    lords = [hostile(n, VENOM_LORD, 9.0 + 3.0 * n, 0.0) for n in range(3)]
    casters = [
        hostile(10, OBLIVION_KNIGHT, 0.0, 15.0, boost=CURSE),
        hostile(11, STORM_CASTER, -14.0, 5.0),
        hostile(12, STORM_CASTER, -12.0, -10.0),
    ]
    return Scene('venom lords and casters', 108, lords + casters)


SECONDS_10 = 10 * TICKS
SCENES: dict[str, Spec] = {
    'gloams_behind_hulks': Spec(gloams_behind_hulks, {'gloams first': lambda: order(10, 11, 12)}),
    'witch_and_soul_beside_tanky_elite': Spec(
        witch_and_soul_beside_tanky_elite,
        {'soul, witch, elite': lambda: order(3, 2, 1), 'witch, soul, elite': lambda: order(2, 3, 1)},
    ),
    'dying_gloam_fresh_hulk': Spec(dying_gloam_fresh_hulk, {'gloam first': lambda: order(2)}),
    'equal_lines_far_and_in_contact': Spec(
        equal_lines_far_and_in_contact, {'the pair in contact first': lambda: order(4, 3)}
    ),
    'stone_skin_elite_soaks': Spec(
        stone_skin_elite_soaks, {'afflicted, then leave': lambda: order(2, 3, 4, then=leave)}, SECONDS_10
    ),
    'ghosts_in_front_of_archers': Spec(
        ghosts_in_front_of_archers, {'the killable, then leave': lambda: order(10, 11, 12, then=leave)}, SECONDS_10
    ),
    'bovines_closing_from_two_sides': Spec(
        bovines_closing_from_two_sides, {'step north, then fight': lambda: step_then((0.0, -14.0))}
    ),
    'low_life_in_melee': Spec(low_life_in_melee, {'survivor': Survivor}),
    'low_life_two_dying_gloams': Spec(low_life_two_dying_gloams, {'fight on': lambda: order(2, 1)}),
    'low_life_under_knights': Spec(low_life_under_knights, {'leave': lambda: leave, 'survivor': Survivor}, SECONDS_10),
    'dolls_running_in': Spec(dolls_running_in, {'dolls first': lambda: order(10, 11, 12)}),
    'dolls_on_the_character': Spec(dolls_on_the_character, {'survivor': Survivor}),
    'might_elite_beside_minions': Spec(
        might_elite_beside_minions, {'elite first': lambda: order(10), 'minions first': lambda: order(3, 2, 1, 0)}
    ),
    'herald_with_minions': Spec(
        herald_with_minions, {'minions first': lambda: order(1, 2, 3, 4, 5, 6), 'survivor': Survivor}, SECONDS_10
    ),
    'stone_skin_zone': Spec(stone_skin_zone, {'leave': lambda: leave, 'survivor': Survivor}, SECONDS_10),
    'venom_lords_and_casters': Spec(
        venom_lords_and_casters, {'casters first': lambda: order(10, 11, 12), 'lords first': lambda: order(2, 1, 0)}
    ),
}
