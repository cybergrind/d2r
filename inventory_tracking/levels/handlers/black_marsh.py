"""Black Marsh: the Forgotten Tower entrance.

Confirmed 2026-09-30 (fixture black_marsh from evidence; the user checked the direction). The
first outdoor level: its Room2 list holds 8x8 chunks named 'Wild Border N' (level edge),
feature presets such as 'Tower 1', and Def 0 (generated terrain with no layout information).
"""

from inventory_tracking.levels.handler import target


HANDLERS = [
    target('Black Marsh', areas={6}, label='Forgotten Tower', preset=r'Act 1 - Tower 1', kind='stairs', confirmed=True)
]
