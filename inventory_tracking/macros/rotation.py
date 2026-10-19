"""The buff executor (macros/buffs.py) under the name the replays patch (`Rotation.key`); the plan is the build's
(builds/warlock/buffs.py). `ELITE_LIFE` is the hunt's own number.
"""

from inventory_tracking.macros.buffs import Buffs as Rotation


__all__ = ['ELITE_LIFE', 'Rotation']


ELITE_LIFE = 2.0  # a unique's or champion's life in Hell, in its type's points (the tables hold the plain monster's)
