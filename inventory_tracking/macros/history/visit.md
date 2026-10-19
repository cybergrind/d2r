# visit.py — design notes and evidence moved out of the code (2026-10-19, cleanup phase 4)

The design is in `macros/town-plan.md` §2.1; these are the rulings and incidents the code's comments used to carry.

## The visit's order

The player, 2026-10-18 12:55: "identify everything with cain; move to the shared stash; put all items that we need to
keep in stash ... after stash visit we should carry only junk/sell items in our inventory or cube; visit store and sell
junk items from inventory and cube; refill the consumables; if we need to repair things - repair things; go to
waypoint; continue activity".

- Cain only when something is unidentified (no walk to him otherwise).
- Halbu before Jamella only when the gold is too near its cap for a sale (15:33:27 on 2026-10-17).
- Exit: the waypoint walked to from Jamella or Halbu (`Exit.WAYPOINT`, `Exit.PORTAL`); none on `Exit.LEAVE`.
- The best copy of a set or unique item is kept (the player, 16:50 on 2026-10-18; macros/copies.py).
- A full stack's runes are no longer sold (the player, 17:50 on 2026-10-18: "cubed, aim to 80 or lower"; sold from
  2026-10-17, "probably we better just sell them"): the stash stop transmutes the stack down to RUNES_AIM.
- Stash full stops the loop (the player, 16:50 on 2026-10-18: "if stash is full - we need to stop loop").
- A cube keeper with no way out waits in the cube (the player, 17:50 on 2026-10-18: "keeper can wait in cube").
- The build's free block (the player, 2026-10-18: "we should have 2x4 inventory space"): a key stack moved out of it.
- `JAMELLA_FIRST` (off): at 15:05:53 on 2026-10-18 a junk Fuscina (2 x 4) held the inventory's only room with the cube
  full, so the set Boots (2 x 2) stayed in the cube. Jamella first would cost ~35 units of walk; asked at 15:06, the
  ruled order is still stash then Jamella.

## The stash stop

- Resources: the cube's by Ctrl + Shift with a resource tab shown, the inventory's by Ctrl + click, each onto its own
  tab whatever tab is shown (the player, 2026-10-18).
- Cube keepers come out tallest first: in page order a Ring for page 2 took the first cell of the only 2 x 3 a
  Serpentskin Armor for page 5 needed (the 15:14 replay on 2026-10-18).
- Probe P1 unknown: whether a Ctrl + click on a cube item in the stash's resource view takes it out; so the stash is
  closed, `unpack` run, and the stash opened again in place.
- Junk into the cube (`_into_cube`): 14:28 on 2026-10-18 a set Amulet kept for Jamella held the one 2 x 3 a unique
  Embossed Plate needed, and the plate stayed in the cube.
- Junk parked on a page (`_park`): 16:35 on 2026-10-18 a junk Fuscina held the only 2 x 2 set Battle Boots could come
  out into, three visits. The player, 16:50: "junk can be temporarily stored in stash, but sold after".
- With the stash unread, inventory junk blocking a cube keeper is moved aside before Jamella (21:03:47 on 2026-10-18:
  two rings blocked a Humongous).
- A refusal with the stash unread is a guess, never a full stack: the Deep Worldstone Shards "full" at 83 were dropped
  and left (22:14 on 2026-10-18 and 01:59 on 2026-10-19; the player: "we need to track this correctly").
- Shared tab: shows the page last looked at, kept between stops (`Remembered`). A put refused on a remembered page is
  tried again from the tab's first page; one that lands elsewhere makes that page the one shown (town-plan.md §5).

## Rune transmutes

- Ctrl + Shift + right click on a resource moves 3 of it into the cube (the player, 14:28 on 2026-10-18; live from
  18:27). Ctrl + Shift + left click moves 1 (the player, 18:48: "when cubing runes and we need to move only 1 gem, we
  don't need to do right click").
- Recipes that take a gem use the stash's gems (the player, 18:31: "yes, loop should use required gems + runes").
- A cube resource onto its stack by Ctrl + Shift + click: proven 2026-10-17.
- Full materials no vendor buys are put down (the player, 10:37 on 2026-10-18: "there is no use for it").
- `_aside` moves a stack as cube.py `arrange_keys` does (14 times live by 2026-10-18).
