"""The builds that fill the framework of `macros/build.py`, and the one list of them: the composition root. The
framework (macros/, combat/) imports none of this; appraisal/service.py hands the runner `BUILDS` and `FALLBACK`,
asked in this order (macros/build.py `choose`).
"""

from dataclasses import replace

from inventory_tracking.builds.characters import LAYERS
from inventory_tracking.builds.generic import GENERIC
from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.config import with_overrides
from inventory_tracking.macros.build import Build


# In the order they are asked: a character's own layer before the build it is a layer of, so that a
# character the macros know gets its weapon sets and any other character of the build gets none.
BUILDS: tuple[Build, ...] = (*LAYERS, ECHOING_STRIKE_BUILD)
FALLBACK: Build = GENERIC  # for a character no build claims, and while no character is in the world


def pursuing(build: Build, on: bool = True) -> Build:
    """`build` with the pursuit loop on or off (BuildSettings.pursuit, macros/pursuit.py): what the process
    hands the runner as its configuration asks (config.py `macro_pursuit`)."""
    return replace(build, settings=with_overrides(build.settings, pursuit=on))
