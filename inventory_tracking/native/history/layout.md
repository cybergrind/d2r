# native/layout.py — evidence moved out of the code (2026-10-19)

Most layout evidence is in `inventory_tracking/history/layout_notes.md`. Only these were in comments alone:

- `COLLISION_BLOCK_MISSILE = 0x0004`: the Catacombs takes of 2026-10-10 11:44 UTC (combat/plan.md). The
  recorded blades crossed 931 cells with only 0x0001 set 148 times, and the 26.8k cells with 0x0004 set 26
  times (7 of those at door units whose state had changed after the masks were read).
- Level/room chain: two Win+C dumps in Arcane Sanctuary (runs/level/) confirmed it on 2026-09-30. The LvlPrest
  527 room predicted from the entrance held the Summoner and the Journal.
- Room2 neighbours: in 80 of 80 Lower Kurast rooms every entry was a Room2 of the level, except at the level
  edge.
- Preset object: the DS1 file index is 0/1 for two-file presets and 3 of 4 for Vaught's Nihl*. Whole-preset
  bounds are 40x40 for the Temple quadrants and 84x84 for the Vaught level.
- Enigma Teleport stat (97, 54, 1) on the worn Mage Plate: live capture of 22:26 on 2026-10-17. Call to Arms
  (97, 149, n): 22:58 the same day.
