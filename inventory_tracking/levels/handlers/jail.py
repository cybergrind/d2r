"""Barracks → Jail 1-3 → Inner Cloister: the next level, the waypoint and the way back.

Jail 1-3 confirmed 2026-09-30 (fixtures jail_1..3); Jail 3's exit is 'Jail Cath'. The Barracks is
from lvlprest names only, unconfirmed.
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
