# macros/pursuit.py — design notes moved out of the module (phase 4 cleanup, 2026-10-19)

Sources: rca/2026-10-13/kp4-findings.md §3.2 design B, §6; rca/2026-10-13/architecture-goals-navigation.md §2.1, Q4;
rca/2026-10-13/kp1-level-run.md; rca/2026-10-13/run-2110-findings.md moment 2.

## Why a press is an intent

Before the pursuit, a press of the teleport key during attack mode was a routine of its own: it cancelled the mode,
ended the sweep, made its step or none, and held the mode back half a second after. Mashed by a pack the mode never
reached a strike (6.2 s by Vizier seal 1 at 09:06 on 2026-10-13), and with the route at a fight whose boss stood out of
reach nothing moved at all (48 presses, 25 s).

Now the press posts a `Pursuit` (which key, when) and returns: nothing is cancelled. The one loop that makes the inputs
(attack mode, hunt.py) looks at the game, names the goal the key means now (macros/goals.py `goal_of`) and asks
`decide`:

- a fresh press whose goal is not near enough: `Move`, the navigator's next move (macros/travel.py `Travel.toward`);
  the strike is given up for this act alone;
- a fresh press whose goal the route's own press still performs (a door, a border, the loot, the leaving): `Defer`; a
  door or a border only once the character is at it (`entering`);
- a fresh press whose goal is near enough: `Operate` (an object used, a stand noted, a drop taken), or for a fight
  `Hold`;
- no fresh press: `Hold` with something in reach. With nothing in reach and the goal a fight whose boss has a known
  place: `Move` toward it ("attack mode idles with the boss 52 units away"). Otherwise `NoWay`, and the loop does what
  it did before (the sweep, the idle look).

Whatever is neither a move nor a strike is a `NoWay` with its reason, said once per change (`Told`). A press is fresh
for FRESH seconds; a newer one replaces it, so a held or mashed key only moves the stamp.

## The leash

The teleport key's press is `advance` (its goal now, before what is in reach) and leaves the leash as it was. The
pickup key's sets the leash FULL on its level (the player, 2026-10-13: "one press of KP_1, then it runs the whole level
automatically"): with no fresh `advance` press, the loop holds what is in reach, takes a drop worth it on the way, and
otherwise goes for the route's stages of this level as if pressed. How much of the level it works is the run mode's
(macros/runmode.py, 2026-10-14). A door (a warp) ends the run (going through costs a press, U13); an open passage is
walked through (`through`, 2026-10-15) and the run carries into the next level (`carried`; the player, 2026-10-15: "it
should carry into the Chaos Sanctuary run"). It ends (`Ended`) when what is left is not this loop's (the loot, the
leaving, a door), when nothing is known to go to, or when the level is left another way; the runner ends it for attack
mode off (KP_3) and the macro request (Mod+X). A fresh pickup press whose goal is the route's own press or none goes to
the old pickup step (`Defer`).

## The player's hand pauses a run

The player, 2026-10-13: "we shouldn't prevent user from sorting"; asked whether the run should resume on its own:
"yes". The hand wins at once (I7): the record is `paused`, and the loop only strikes what is in reach (a fresh teleport
press still asks for its goal). The run resumes once the hand has been still SETTLE seconds with no panel open
(`settled`); a fresh pickup press restarts it at once.

SETTLE evidence: the game of 21:10 on 2026-10-13 (take 20261013T181240Z-108, run2110_hands.py): while the player sorted
and walked back by hand, the hand was never still longer than 0.43 s with the panels closed (21:14:08.7-11.4,
21:15:28-31.5) nor 1.01 s with the inventory open (21:14:04.7-05.7); the first KP_1 press came 0.31 s after the hand's
last move.

## A valuable with no room for it

The player, 2026-10-13: "when valuable doesn't fit: we need to stop near it". A `WAIT` goal by the drop, in the run's
order where a drop to take would be: the character goes next to it and stays, saying so, until there is room or a
fresh press lets it go.

## Evidence behind tuned rules

- FRESH 0.7 s: 0.2-0.4 s between presses of a mashed key, 40-700 ms from a step's end to the next press
  (kp4-findings.md §2.4, §2.5); under runner.py EXPIRES (1.0 s).
- `Pursuit.looped`: a game's last run held into the next — two posts 0.35 s apart switched the run to a full clear of
  Catacombs Level 2, 80 s (10:26:40 on 2026-10-18).
- RUSH_THE_BOSS (F1 of rca/2026-10-18/andariel-cadence-findings.md §5; "F1: ok", 18:00 on 2026-10-18): after A1 the
  Teleport toward Andariel landed among her pack 0.6-0.9 s after the last strike, the gap left only the hold, and every
  hop cost a strike: 1.34 s a hop cycle vs ~0.6 s chained, 1.96 s a fight (§2.1; 11:41:45.63, take 084143Z-37).
  Baseline: arrival -> Andariel dead, median 7.60 s on 23 games.
- Rush firing spots dropped: a stand to fire from outpriced the chest (22:04:12 on 2026-10-16: 16 walks to one in
  17 s, none taken; rca/2026-10-16/loop-shack-stalls-findings.md §1).
- Rush holds dropped while unhurt: 94 % of the loop's strikes followed no life loss in the 3 s before, 3.5 s a stay
  (rca/2026-10-17/movement-findings.md §4 #1); at 02:22:26 on 2026-10-17 the run stood 1.7 s by a shack's chest and
  then struck; a move dearer than RUSH_HARM_SHARE is still fought for (300 of 1,784 life, 2026-10-16).
- Rush has no strike gap: not every Hell Buzzard in the blades' 22 units (rca/2026-10-16/loop-chests-findings.md §1).
- Dodges keep out of the gap: Diablo's stream is under 1.9 s (rca/2026-10-14/diablo-handling.md fix 1); a strike
  there gave its place to the hold (R2: 5 of 6 priced fights).
- Retreats that keep reach first: one out of reach only defers the harm (rca/2026-10-14/baal-sim.md weakness 2: 4.5 s a
  fight out of Baal's reach).
- Rush operates with idle hostiles in reach: offered only a hold, it stood and then struck, ~4 s a chest (19:21:34 on
  2026-10-17: 1.7 s standing, 2.3 s of strikes; 30 of 31 strikes 19:20-19:35 followed no life loss). The player,
  2026-10-17: "we don't even need to kill some trash mobs and can loot and leave"; "strikes on hp loss". Arrival by
  `moved` too: 2-3 units off a chest whose `near` is less (19:41:17 on 2026-10-17).
- ENTRY_REACH: the run stood 48 s 5.4 units off a door entry with "no footing in view brings the character nearer by
  hops" (12:46:41 on 2026-10-18).
- `entering` uses the navigator: handed on from 43 units with the staff empty, the old step walked into a pocket 276
  units by the walked way from the door, three times (rca/2026-10-14/run-1932-findings.md §1.2.2).
- `moved` beyond < least_move: the River's door, 23 s standing 0.5 units past its 5 (22:08:45 on 2026-10-14,
  run-1904-findings.md §3.4).
- ENTERING 3.0 s: the level guide polls every 0.5 s (config.py level_guide_poll_interval), then reads rooms and walls;
  until then the card is the level left (hunting/choice.py `goal`: none).
