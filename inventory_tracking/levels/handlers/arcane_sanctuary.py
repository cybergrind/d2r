"""Arcane Sanctuary: the Summoner sits at the end of one of four arms.

Confirmed 2026-09-30 by two Win+C dumps (fixtures arcane_summoner_s / _w): the room was
preset 527 in one game and 525 in another; the Summoner was found in it in game.
"""

from inventory_tracking.levels.handler import target


HANDLERS = [
    target('Arcane Sanctuary', areas={74}, label='Summoner', preset=r'Act 2 - Arcane Summoner [NSEW]', confirmed=True)
]
