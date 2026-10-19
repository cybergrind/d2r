# Halls of Vaught handler: how the Nihlathak mark was placed

Moved from `levels/handlers/halls_of_vaught.py`'s docstring (phase 4 cleanup, 2026-10-19).

- The level is one 84x84 preset, 'Act 5 - Temple Final Room', in four DS1 variants (lvlprest File1..4:
  NihlE, NihlN, NihlS, NihlW); the player enters at its centre. The variant index is read from the preset
  object (dump 20260930T082410Z-54658110: 3 = NihlW).
- The letter names the side Nihlathak is on. Confirmed 2026-09-30: the user saw him west and north in two
  games; the NihlW game rules out "the side the layout opens to", which would be east.
- Game 3 (NihlE, dump 20260930T144010Z-ca3068d4) saw him at 94 % across the preset, mid-height: the marker
  sits 6 % inside the edge (the generic 15 % left it 40 units short, so a Win+C next to him pointed back).
  The four layouts mirror each other; only NihlE is measured.
- The mark is a place to fight from (user, 2026-10-11: "position our last jump somewhere off the main mob
  pack, to avoid heavy damage"; the teleport step ends there and returns there after a pickup or a sweep).
  In the twenty takes of that day he stood in a pillared pavilion of about 20 x 20 units with his pack, the
  same way round in all four layouts: from 14 west and north of the side's spot to 6 east and south of it,
  himself 0.5–4.5 west and 3.5–4.5 north. East of the pavilion a strip 12 wide was empty of monsters on
  arrival in each layout. `stand=(3, -1)` (3 tiles east, 1 north of the spot) is 15.5–19.5 units from him,
  with footing and a clear line to every part of the pavilion in each layout's take (pillars do not stop a
  blade).
