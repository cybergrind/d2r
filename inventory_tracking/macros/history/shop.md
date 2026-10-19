# shop.py — history and evidence (moved out of the code, 2026-10-19)

## The restock visit (routes/lower-kurast-loop-plan.md phase 8)
The player, 2026-10-16: "we need, from time to time, buy portal scrolls and keys - when we visit shop for keys we still
buy scrolls and vice versa. keep 3+ of each before run". Jamella stands about (5083, 5058), 38 units from a game's start
and below the window there, so the character walks toward her until she is drawn well inside it. Her menu's Trade line
is TRADE_ABOVE window heights above her drawn point: the player's two clicks of 21:03 and 21:15 on 2026-10-16 were
0.2155 and 0.2214, the lines 0.0226 apart. The clicks of 00:42 and 01:10 on 2026-10-17 put the line between Trade and
Gamble at 0.218: Trade's middle is 0.229. At 00:37:00 on 2026-10-17 a click at TRADE_ABOVE opened Gamble ("it has opened
gamble window, not trade", "maybe clicks a few pixels off"): hence the lifts tried in turn and the stock check.
Layout: `vendorpanellayouthd.json`, tabs from (82, 162) 249 x 75, the grid from (91, 233), 98 a cell.

## Learned lifts (`known`)
The last lift alone sat on an edge of the line: Cain's took at 0.2052 and 0.2165, half a line apart, and each missed now
and then (9 of 212 visits, ~4 s each, 2026-10-18/19; "looks like we're cannot lick identify all from the first
attempt"); Jamella's at 0.229 and 0.2346. The middle of the hits is clicked first. 2026-10-19: "track/check all failed
attempts to reach required menu (identify all, trade, trade/repair) and make sure that we have generic code" → `menu_line`.

## Opening her menu
"they are moving, so you cannot expect to find them at the same location" (2026-10-16). At 23:07:04 on 2026-10-16 the
hover record never named her at any aim (she stood still, 11 units off) and the loop stopped without a click; the click
is now made at her body anyway. A walk click that lands on her opens the menu mid-walk (23:57:48 on 2026-10-16); lines
aimed after missed it (Halbu, 17:21:57 / 17:22:00 on 2026-10-17): closed and reopened standing. The view moves after the
menu opens while the character walks up (01:38:35 on 2026-10-17).

## Stock read
Read 0.05 and 0.1 s after the window opened (23:57:55, 23:58:04 on 2026-10-16) the stock held neither key nor scroll and
the loop stopped on "not her trade window": wait up to STOCK_SECONDS.

## Walking
WALK_CLICKS: 16 ran out 2 units short of Kurast Docks' waypoint (~130 units) after clicks of 4 units each (12:26:25 and
12:26:53 on 2026-10-17, three recoveries then the loop stopped); beside Halbu turned clicks used them all (12:10:04).
TURNS: beside Halbu at (5082, 5033) every click toward the waypoint moved a unit and back for 32 s (02:00:17-49 on
2026-10-17). `_along`: Kurast Docks' waypoint is behind the dock's walls from a game's start; straight clicks took one
step (01:26 on 2026-10-17). USUAL: Jamella 70 units west of Cain's place was "not in sight" (12:01:23 on 2026-10-17).

## Sales and buys
Sold first, then bought: a purchase's cost landed late and was read as a sale's (-140 gold, 11:41:38 and 11:44:38 on
2026-10-17); a settling wait made the first sale 2.9 s after her stock (12:33-12:57). Gold cap: "selling things over this
gold limit - just drops extra gold on the ground" (2026-10-17). Runes no longer sold since 17:50 on 2026-10-18 ("cubed,
aim to 80 or lower"); a full stack's Tal Runes had been sold here since 2026-10-17. Full-item skip: 0.7 s a kind
(14:38:57-58 on 2026-10-17). Bulk buy: "check inventory number. you can bulk buy with (shift+right click)" (2026-10-16).
Two key stacks: one stack sent the loop to Jamella every 4 games ("we need to carry 2 sets of keys, instead of 12 =>
24", 2026-10-17); one for non-LK runs ("probably we don't need 2x sets of keys for non LK loop", 2026-10-18). The second
key stack comes 3 keys a click between clicks that buy nothing (12 -> 15 at 17:31:59 on 2026-10-17; 2 -> 12, nothing,
15, nothing at 01:47:20 and 01:57:00 on 2026-10-18): BUY_MOST 9.
