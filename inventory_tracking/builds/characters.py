"""The characters the macros know: each a layer over its build, with the weapon sets that are its own.

A character's row says which build it plays and which of its weapon sets is for what. As a build of
its own (`played_by`) it is the build below it with those sets, and it is that character's whatever
its keys hold at the moment: listed before the build it is a layer of (builds/__init__.py `BUILDS`),
it is the one chosen for the character, and any other character of the build gets the build as it
is, with no weapon sets.
"""

from dataclasses import replace

from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.builds.warlock.skills import ECHOING_STRIKE
from inventory_tracking.macros.build import Build, Loadout
from inventory_tracking.macros.world import World


# CybergrindAA: Heart of the Oak (Flail) and Spirit (Monarch) for both; the other set holds Naj's Puzzler,
# worn for its Teleport charges only (user, 2026-10-06; codes from the collection capture of the equipped
# items). The two differ once Teleport comes from Enigma and the other set is the prebuff one (user,
# 2026-10-10): what casts Teleport is read from the game (teleport.take_teleport: a worn staff with
# charges, else the skill), so only this table changes then.
HEART_OF_THE_OAK = frozenset(('fla', 'uit'))
CHARACTERS = {'CybergrindAA': Loadout(prebuff=HEART_OF_THE_OAK, battle=HEART_OF_THE_OAK)}
# The build each character plays.
PLAYS = {'CybergrindAA': ECHOING_STRIKE_BUILD}
# Where each character's right-skill selection shows a skill's icon (macros/skillpanel.py: from the window's bottom
# centre, in window heights). CybergrindAA's Echoing Strike: the player's own click that selected it at 22:09:51 on
# 2026-10-14 (take 20261014T190924Z-108, the pointer at (0.669, 0.696) of a 2560x1418 window).
ICONS = {'CybergrindAA': {ECHOING_STRIKE: (0.3046, -0.3039)}}


def played_by(build: Build, name: str) -> Build:
    """`build` as the character `name` plays it: with that character's weapon sets (none for a
    character without a row), and its own by the name alone. Not with no character in the world."""

    def named(world: World) -> bool:
        return world.player is not None and world.player.name == name

    return replace(build, applies=named, weapons=CHARACTERS.get(name), skill_icons=ICONS.get(name, {}))


# One build per character, in the table's order: the layers the registry lists before the builds.
LAYERS: tuple[Build, ...] = tuple(played_by(build, name) for name, build in PLAYS.items())
