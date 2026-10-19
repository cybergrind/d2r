"""The characters the macros know: each a layer over its build, with the weapon sets that are its own. Listed before
the build (builds/__init__.py `BUILDS`), a layer is chosen for its character; any other character of the build gets
the build with no weapon sets.
"""

from dataclasses import replace

from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.builds.warlock.skills import ECHOING_STRIKE
from inventory_tracking.game.records import World
from inventory_tracking.macros.build import Build, Loadout


# CybergrindAA: Heart of the Oak (Flail) + Spirit in the main set, Call to Arms + Spirit in the other (since
# 2026-10-17; Teleport from Enigma). The CTA reads as game/memory.py CTA_CODE, so `fla` alone tells the main set.
HEART_OF_THE_OAK = frozenset(('fla',))
CHARACTERS = {'CybergrindAA': Loadout(prebuff=HEART_OF_THE_OAK, battle=HEART_OF_THE_OAK)}
# The build each character plays.
PLAYS = {'CybergrindAA': ECHOING_STRIKE_BUILD}
# Where each character's right-skill selection shows a skill's icon (macros/skillpanel.py: from the window's bottom
# centre, in window heights; the player's own click in take 20261014T190924Z-108).
ICONS = {'CybergrindAA': {ECHOING_STRIKE: (0.3046, -0.3039)}}


def played_by(build: Build, name: str) -> Build:
    """`build` as the character `name` plays it: with that character's weapon sets (none for a
    character without a row), and its own by the name alone. Not with no character in the world."""

    def named(world: World) -> bool:
        return world.player is not None and world.player.name == name

    return replace(build, applies=named, weapons=CHARACTERS.get(name), skill_icons=ICONS.get(name, {}))


# One build per character, in the table's order: the layers the registry lists before the builds.
LAYERS: tuple[Build, ...] = tuple(played_by(build, name) for name, build in PLAYS.items())
