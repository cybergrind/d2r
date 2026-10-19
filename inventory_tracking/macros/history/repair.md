# repair.py — tuning history (moved out of the code, 2026-10-19)

All on 2026-10-17 unless dated otherwise.

- REPAIR_BELOW: visits at half charges cost 3.9 s a cycle (15:28-15:43) with Teleport in the loop (~7.5 charges a
  stay); lowered to 0.3 (21 of 69 charges, ~1.5 stays over travel.py LOW_CHARGES), then 0.2 at 17:25 since each errand
  is a whole session (loop.py `errand`).
- WEAR_BELOW: Enigma (22:26) gave the character its own Teleport, so the staff's charge repairs no longer mended the
  rest of the gear; Enigma read 33 of 60 then.
- RETRY_GAMES = 3: with Teleport in the moves the charges run out in about three games (16:32).
- CARRIED_SHARE: 0.9 refused 101,803 with 107,753 carried (12:41:43); 0.98 refused 102,206 with 104,270 (13:12:13).
- Cost scales with charges: 62,918 for 37 (12:08:37), 101,677 for 60 (12:04:09).
- OCR: "Tae ee" read from a clear "Repair all equipment: 47449" (16:25:12), eight misses that day; psm 7 read nothing
  at 12:39:19 where psm 6 read all twelve pictures; a wide 1400 x 330 picture read noise (10:31:02); "1Q1677"
  (11:54:16, 11:59:59), "5@548" (13:24:09).
- Lifts: none of four clicks 0.184-0.218 over him took (01:50); ten lifts failed in 34 s at 16:31:30-16:32:02 with the
  learned lift working all day, so only the learned one and its neighbours are tried.
- Gold settle: carried gold read at once had not moved (208,801 for a 69,696 repair, 12:09:40); at its first move
  165,932 -> 165,323 for a 61,006 repair (18:44:57).
- `back`: the waypoint from beside Halbu is 37 units off and drawn where no aim reaches it (12:39:25 a recovery); the
  walk ran out of clicks at 12:10:04.
