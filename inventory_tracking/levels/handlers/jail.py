"""Barracks → Jail 1-3 → Inner Cloister: the next level, the waypoint and the way back.

The user tracks three POIs per Jail level (2026-09-30): next level, waypoint ("teleport") and
the stairs up, named for where they lead (Jail 1: the Barracks). Jail 1 evidence (Win+C dump
20260930T091905Z-6d876f84, fixture jail_1): one 'Jail Next N', one 'Jail Prev S', one
'Jail Waypoint W' in 12x12 doorway rooms; Jail 2 and 3 evidence (fixtures jail_2, jail_3).
Jail 1-3 confirmed 2026-09-30 by the user. Jail 3's exit is 'Jail Cath', toward the Inner
Cloister. The Barracks comes from lvlprest names only and is unconfirmed (no evidence yet).
"""

from inventory_tracking.levels.handler import previous, stairs_down, target, waypoint


JAIL = 'Act 1 - Jail'

HANDLERS = [
    stairs_down('Barracks', areas={28}, family='Act 1 - Barracks'),
    stairs_down('Jail 1', areas={29}, family=JAIL, extra=[waypoint(JAIL), previous(JAIL, 'Barracks')], confirmed=True),
    stairs_down('Jail 2', areas={30}, family=JAIL, extra=[waypoint(JAIL), previous(JAIL, 'Jail 1')], confirmed=True),
    target(
        'Jail 3',
        areas={31},
        label='Inner Cloister',
        preset=r'Act 1 - Jail Cath [NSEW]',
        kind='stairs',
        extra=[waypoint(JAIL), previous(JAIL, 'Jail 2')],
        confirmed=True,
    ),
]
