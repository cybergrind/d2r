# levels/exits.py — design notes

Moved out of the module docstring on 2026-10-19 (phase 4 cleanup).

**Warps.** A preset's DS1 file numbers each warp with the level's link slot (levels/ds1.py), and levels.txt
names the level behind that slot (Vis0..7, bundled as LEVEL_LINKS). So a room whose preset has warp tiles is a
way out to a known level, marked on the warp itself. Checked on 2026-10-05 against the saved evidence: in all
1152 warp rooms whose far side was readable (Room.leads_to), the slot's level was the one read from memory.
The Forgotten Tower's one preset holds both directions (slot 0 Black Marsh, slot 1 Tower Cellar 1), hence ways
on sort before ways back.

**Borders.** Levels joined without a warp or an open border gap (Rogue Encampment, Monastery Gate, the Act 2
deserts, the Outer Cloister behind the Barracks) show only as rooms whose neighbours belong to the other level.
Such a level is marked at the room nearest the middle of those rooms, once any of them has been read
(levels/session.py keeps them for the game).

**Handler marks win.** A way out a handler already marks (by kind, or an entrance it keeps as a side trip with
PoiSpec.warp) is not repeated, so its label and colour stand; a level its border gaps are waiting to name
(ExitsHandler.exits) is left to them. The kind is a guess from the area numbers, which grow along the story:
a lower-numbered level is the way back.

**Open passages.** A way out with no warp behind it (presets.open_passage: levels.txt, or a border) is crossed
by walking, not clicked: the River of Flame's bridge into the Chaos Sanctuary, the Outer Cloister's gate into
the Barracks, every border. `through` gives the place a walk goes to so that the level changes, PASSAGE_PAST
inside the next level (macros/goals.py `route_goal`). Evidence for PASSAGE_PAST = 1 tile: the River of Flame's
bridge on 2026-10-14 (takes 20261014T190527Z-107 then 190924Z-108, 192208Z-107 then 192338Z-108): the level
changed at the rooms' edge (tile row 1120: y 5600.3 in the River, 5599.6 in the Sanctuary a frame later), on
walks that went on to y 5595.9, a tile in.

**Towns.** A town marks only its way out to the wilderness (user, 2026-10-06): Lut Gholein's sewer ladders and
the Harem were noise; its gate to the Rocky Waste is in one of two places. And its waypoint (user,
2026-10-07), an object the town's DS1 file places (presets.waypoint_spot): known on entry, before the game
streams the object (the Rogue Encampment has four layouts).
