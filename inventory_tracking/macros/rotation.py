"""What is left of the casts under the held strike once they became a build's buff plan: the plan is
the build's (builds/warlock/buffs.py for the Warlock, with its casters), and macros/buffs.py runs it.

`Rotation` is the executor under the name the replays patch it by (`Rotation.key`); `ELITE_LIFE` is
the hunt's own number.
"""

from inventory_tracking.macros.buffs import Buffs as Rotation


__all__ = ['ELITE_LIFE', 'Rotation']


ELITE_LIFE = 2.0  # a unique's or champion's life in Hell, in its type's points (the tables hold the plain monster's)
