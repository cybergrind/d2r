"""Tower Cellar: stairs down on levels 1-4, confirmed 2026-09-30 (one 'Crypt Next' per level in
evidence, fixtures tower_cellar_1..4; the user checked the arrows); the Countess on level 5
(unconfirmed).

Level 5 is one 'Crypt Countess X' preset in two DS1 variants (CryptCountess1/2) covering the
whole level, so the preset itself gives no direction. The mark is where the variant's DS1 file
places her (terror/data/elites.json: 21, 70 and 65, 15 units from the preset origin), the level's
first mark, so the teleport step goes to her room (user, 2026-10-10). In the run log of 2026-10-10
(variant 1) she fought at (12565, 11037), 22 units from her spot (12565, 11015).
"""

from inventory_tracking.levels.handler import stairs_down, target


HANDLERS = [
    stairs_down('Tower Cellar 1-4', areas={21, 22, 23, 24}, family='Act 1 - Crypt', confirmed=True),
    target('Tower Cellar 5', areas={25}, label='Countess', preset=r'Act 1 - Crypt Countess X', boss='The Countess'),
]
