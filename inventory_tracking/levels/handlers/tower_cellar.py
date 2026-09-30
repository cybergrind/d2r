"""Tower Cellar: stairs down on levels 1-4, confirmed 2026-09-30 (one 'Crypt Next' per level in
evidence, fixtures tower_cellar_1..4; the user checked the arrows); the Countess on level 5
(unconfirmed, accepted as is by the user).

Level 5 is one 'Crypt Countess X' preset in two DS1 variants (CryptCountess1/2) covering the
whole level, so the handler reports "whole area around the player" instead of a direction until
her position per variant is known (a Win+C next to her in each variant; then `sides=` or a
per-variant offset).
"""

from inventory_tracking.levels.handler import stairs_down, target


HANDLERS = [
    stairs_down('Tower Cellar 1-4', areas={21, 22, 23, 24}, family='Act 1 - Crypt', confirmed=True),
    target('Tower Cellar 5', areas={25}, label='Countess', preset=r'Act 1 - Crypt Countess X'),
]
