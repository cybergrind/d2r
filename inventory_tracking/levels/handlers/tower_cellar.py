"""Tower Cellar: stairs down on levels 1-4; the Countess on level 5 (terror/data/elites.json)."""

from inventory_tracking.levels.handler import stairs_down, target


HANDLERS = [
    stairs_down('Tower Cellar 1-4', areas={21, 22, 23, 24}, family='Act 1 - Crypt', confirmed=True),
    target('Tower Cellar 5', areas={25}, label='Countess', preset=r'Act 1 - Crypt Countess X', boss='The Countess'),
]
