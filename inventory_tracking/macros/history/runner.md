# runner.py — history

Evidence behind tuned numbers and rules, moved out of the code comments (phase 4 cleanup, 2026-10-19).

- `EXPIRES`: of the teleport presses that waited for a step, 90 % had their key within 0.48 s; the slowest two took
  0.7 and 1.5 s (21:26 and 21:35 on 2026-10-11). User, 2026-10-12: "teleporting after 2 seconds is way too late, maybe
  even lower".
- `TRAVEL_QUIET`: a travelling player's next press came 40–700 ms after the step before (30 presses, 21:26 on
  2026-10-11), found attack mode running and waited for it, a strike in flight up to 0.4 s longer; half took over
  250 ms to their Teleport key. The mode needs 0.3 s to its first strike anyway. 0.2 s first: 8 of 34 presses came
  within it (134–205 ms to key); most came 200–600 ms after (21:35), hence 0.5.
- `FLIP_SETTLE`: the game of 22:04 on 2026-10-14 had its four input-mode flips done 10–12 ms after they were asked.
- Teleport press during a pickup cancels the pickup: a Ring was left when a press cancelled its pickup and the next
  steps left the level (17:35:18 on 2026-10-11); in Tower Cellar 5 (22:51:00) a press to get out waited behind a 5 s
  potion pickup among eight monsters and the character died 0.4 s later.
- The sweep ends on a teleport/seek/macro press: in Tower Cellar 3 (00:49 on 2026-10-11) it walked 25 units back
  between two teleport steps to the stairs.
- `_gheeds_swap` ignores the stop's words: at 13:36–13:39 on 2026-10-18 the stop was a stand-by ("has not moved for
  45 s") and the room rules made room, a trip to town and dropped an item instead of the swap.
- `_go_back` moves to the drop when within a click but not at it: 15:53:05 on 2026-10-18 a set Ring 5 away took
  11 clicks from one place for nothing; both trips back found it given up and the loop stopped. On restart the trips
  back start over (15:53:19: a Ring past its 2 trips would have stopped the restarted loop at once).
- `poll`'s stand-by check is limited to `standing` in a game: a pickup.py "left on the ground" warning carried into
  the lobby and cancelled the next game's creation twice (12:45:39 on 2026-10-17).
- Waiting for focus: legs tried while the player was at another window only counted up to a stop (01:30:39 and
  01:33:26 on 2026-10-17).
- `wear` sets the weapon sets on every run: the teleport step's "staff is empty: main weapons" did nothing in a run
  that held none (12 s with the empty staff in hand through 20 steps, 12:33 on 2026-10-13).
- Transmute room: 19 gems kept, no transmute had room, a trade session every game (09:22–09:45 on 2026-10-18); the
  player at 09:53: "drop on the ground then pickup and move to cube".
