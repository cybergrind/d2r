"""Spider Cave and Spider Cavern: the chest room.

Unconfirmed (D2MOO DRLGMAZE_GetRoomPreset, 2026-10-01; no evidence yet). Both are Spider mazes
of 16x16 rooms. In Spider Cave (84) the 'Spider NE' dead end becomes 'Spider Chest NE'; in
Spider Cavern (85), where Khalim's Eye is, the 'Spider NW' dead end becomes 'Spider Chest NW'.
There is no 'Prev' preset: the way out is not a named room.
"""

from inventory_tracking.levels.handler import target


HANDLERS = [
    target('Spider Cave', areas={84}, label='Chest', preset=r'Act 3 - Spider Chest NE'),
    target('Spider Cavern', areas={85}, label="Khalim's Eye", preset=r'Act 3 - Spider Chest NW'),
]
