# stash.py — design notes moved out of the code (2026-10-19)

- The player, 2026-10-17: "probably we need to train how to put resources (stones/runes/gems) into stash: opened stash +
  ctrl+ click on item - move it to stash; if we open any item where cube contents is visible (eg. gems tab) - we can
  press ctrl + shift + item click - to move it from cube inventory directly into the stash"; later: "to effectively
  farm - we need to unload inventory into our stash", every game with loot. The cube (12 cells) was full by the ninth
  game of 23:39 on 2026-10-16.
- Cube to stash: "you can move only stackable items/materials/gems runes with shift-ctrl click on cubed item; to move
  items to other spaces - you need to move them to inventory (ctrl+click) and then move back to stash tab (ctrl-click)"
  (the player, 2026-10-17). A Tal Rune stayed in the cube on Ctrl + Shift + click (01:31:48).
- Resource tabs: "you don't need to open appropriate tab. these items automatically gets to correct tab" (the player,
  2026-10-18). The refusal that once had every tab shown first (a Tal Rune at 01:28:46 on 2026-10-17) was the Tal Runes'
  full stack.
- Layout (bankexpansionlayouthd.json, 2026-10-17): tabs 195 x 72 from (82, 146); the cube's grid at (431, 784) on a
  resource tab; StashNavigation at (369, 1211). The player's screenshots of 23:59 and 01:46 on 2026-10-17 confirmed the
  Gems tab, the cube cells, the arrows and "Page 1 / 5". Not yet seen in a game: where a non-resource cube item goes on
  Ctrl + Shift + click.
- Walking: from the waypoint the stash is 33 units off and no aim reached it (01:07:41); aims while the walk moved the
  view missed from 3 units too (01:28:48, 01:35:40). Out of sight from Jamella's place (12:13:16).
- crowded: "proabably we don't need to visit stash every game, maybe only when we have more than 50% occupied" (the
  player, 2026-10-17); the player's own items fill over half the inventory, so the share is of the room they leave.
- Gold: "probably we need to move extra gold to our cube [stash]" (the player, 2026-10-17). The dialog set no flag in the
  0x40 panel bytes (picture of 16:02:26 on 2026-10-17). At 07:38 on 2026-10-19 the Shared/Gems tab held 12,500,000 and
  refused 181,494 twice a visit, ~3 s each (deposit-failed-073808.png, 075352.png).
- Full stacks: seven flawless gems of four full stacks cost ~1.3 s each (06:08:50-55 on 2026-10-18). A Full
  Rejuvenation Potion was once marked a full stack (03:35:18 on 2026-10-17), hence `_potion`.
