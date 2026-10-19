"""Spider Cave and Spider Cavern: the chest room; no 'Prev' preset, so the way out is not marked."""

from inventory_tracking.levels.handler import target
from inventory_tracking.levels.model import EYE_CHEST, SUPER_CHEST


HANDLERS = [
    target('Spider Cave', areas={84}, label='Chest', preset=r'Act 3 - Spider Chest NE', thing=SUPER_CHEST),
    target('Spider Cavern', areas={85}, label="Khalim's Eye", preset=r'Act 3 - Spider Chest NW', thing=EYE_CHEST),
]
