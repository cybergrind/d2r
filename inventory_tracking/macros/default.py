"""The build taken where none is handed in. Temporary until the runner chooses the build: framework-plan.md Task 3.9.

The framework is handed a build and imports none (macros/build.py). Until the runner does the
handing, the hunt, the pickup and the teleport step take the one build there is from here. It is a
module of its own, below all three, because the runner calls the pickup and the teleport step without
the hunt (pickup.py `collect`, teleport.py `moving`) and neither may import hunt.py. This is the one
import of a build in the framework (the ratchet lists it), made late so that a build can import the
framework first.
"""

from inventory_tracking.macros.build import Build


def default_build() -> Build:
    """The one build there is: the Echoing Strike Warlock."""
    from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD

    return ECHOING_STRIKE_BUILD
