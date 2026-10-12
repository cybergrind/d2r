"""The build taken where none is handed in. Temporary until the runner chooses the build: framework-plan.md Task 3.9.

The framework is handed a build and imports none (macros/build.py). Until the runner does the
handing, the hunt, the pickup and the teleport step take the one build there is from here. It is a
module of its own, below all three, because the runner calls the pickup and the teleport step without
the hunt (pickup.py `collect`, teleport.py `moving`) and neither may import hunt.py. This is the one
module of the framework that imports a build (the ratchet lists it), late so that a build can import
the framework first: the build itself, the old names of its buff memory that tests still ask by
(`old_rotation`), and its attack made of a cast policy that tests and harnesses still hand in
(`as_attack`).
"""

from typing import TYPE_CHECKING, Any

from inventory_tracking.macros.build import Attack, Build


if TYPE_CHECKING:
    from inventory_tracking.macros.buffs import Buffs


def default_build() -> Build:
    """The one build there is: the Echoing Strike Warlock."""
    from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD

    return ECHOING_STRIKE_BUILD


def old_rotation(buffs: Buffs) -> Any:
    """The executor's memory and due-tests under the names they had in rotation.py (`hunter.rotation`):
    the Warlock's, for the tests and the golden adapter written against those names. Nothing in the
    framework asks it; it goes with this module."""
    from inventory_tracking.builds.warlock.buffs import Rotation

    return Rotation(buffs)


def as_attack(policy: Any) -> Attack:
    """The one build's attack with the reach and the damage table of a line sweep made on its own:
    for the tests and harnesses that hand `combat/stance.py` `camp` and `taken` a bare `LinePolicy`,
    as they did before the attack was the build's. Nothing in the game's own path asks it."""
    from inventory_tracking.builds.warlock.echoing_strike.attack import EchoingStrike

    return EchoingStrike.of(policy)
