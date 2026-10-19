# Worldstone Keep handler: how the Throne mark was placed

Moved from `levels/handlers/worldstone_keep.py`'s docstring (phase 4 cleanup, 2026-10-19).

- WSK evidence (Win+C dumps, fixtures worldstone_keep_2 and _3, 2026-09-30): one 'Baal Next', one 'Baal Prev'
  and, in WSK 2, one 'Baal Waypoint', each a 16x16 preset in four 8x8 chunks. WSK 3's stairs down lead to the
  Throne of Destruction, a single whole-level preset ('Act 5 - ThroneRoom'). Confirmed in game 2026-09-30 by
  the user (WSK 1 has no fixture of its own).
- 2026-10-10 night: the mark was the hall before Baal's throne, so teleport steps rush there. The layout file
  (expansion/baallair/wthrone.ds1, read from the install 2026-10-10) seats `baalthrone` at (90, 11) from the
  preset's origin, at the head of a hall whose torches stand at x 89 and 99 from y 24 to 64; the mark was the
  hall's middle, (94, 40). In the two runs of that night the waves were fought from (74–102, 26–50).
- Since 2026-10-11 the mark is a place to fight the waves from, north-west of where they appear (user:
  "west-north off actual throne"; the teleport step ends there and returns after a pickup). In the takes of
  2026-10-11 (00:12 and 00:18) 153 wave monsters were first seen around (90, 25), nine in ten within x 77–97
  and y 18–31. From `THRONE_STAND` (82, 14) nine in ten of those places are in a clear line, 85 % within
  20 units and 1 % within 8; the nearest was 5.7 away.
