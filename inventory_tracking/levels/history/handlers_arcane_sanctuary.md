# Arcane Sanctuary handler: how the Summoner mark was placed

Moved from `levels/handlers/arcane_sanctuary.py`'s docstring (phase 4 cleanup, 2026-10-19).

- Confirmed 2026-09-30 by two Win+C dumps (fixtures arcane_summoner_s / _w): the room was preset 527 in one
  game and 525 in another; the Summoner was found in it in game.
- The mark is where he stands, not the room's middle (user, 2026-10-11: the mark "is far too away to damage
  him"). That game (15:43, preset 527 'Summoner S' at tile (5084, 1000)): the teleport step stopped at
  (25458.5, 5037.5), 11 from the room's middle with no footing nearer; he stood at (25440.7, 5020.9), 25 away
  with the blades reaching 22, i.e. (20.7, 20.9) from the preset's origin. SummS.ds1 has its one monster at
  (20, 20); E was seen in game at (20.5, 35.5) (15:57). W and N are unconfirmed in game.
- The mark is a stand beside him (user, 2026-10-11: "for all boss farms ... teleport not in boss and his
  group, but slightly offset the point"). In the four takes of that day (three S, one E) he stands in the
  south-east corner of a 20 x 20 platform, the same in both files; two ramps lead down to a landing 16 south
  and 10 east of him, and a pack stood in the hall below in two takes. From the landing he is 18 away with a
  clear line; of that pack 16 of 18 and 10 of 16 were in reach, with one, none and 4 nearer than 10 units.
  `STAND` = (10, 15) is the landing's tile: its middle is a unit short of footing, and the hop lands on the
  footing beside it. W and N take the same offset by the files' likeness, unseen.
