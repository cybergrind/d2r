# macros/hunt.py — design notes

Moved out of the module docstring in the phase 4 cleanup (2026-10-19). The rule history is in macros/plan.md.

## The module docstring as it stood

Attack mode and the seek step. The toggle turns attack mode on and off; the seek step goes toward
the nearest unique or champion and leaves attack mode on. The history of each rule is in macros/plan.md.

Attack mode (`Hunter.attack_mode`, a run that lives until cancelled): everything within the reach of
the build's attack (macros/build.py `Attack.reach`) with a clear shot (sight.py: the flight layer of
the read grids, closed doors) is fought while the player moves about as they like. The mouse, the
keyboard and the character's own moves and casts are not cancels: only its toggle or the macro request
ends it, the game being left, or MISSES_IN_A_ROW fights
that stopped one after another. The player's hand is on the mouse all along, so the actuator aims
once and casts at once (`Actuator.steady` off). the teleport and seek steps work meanwhile: the runner pauses the
mode for the step and resumes it after (runner.py).

A fight (`Hunter.fight`) is one hold of the input that has the attack's skill (the Warlock's Echoing
Strike): the right mouse button when it holds the skill, else its skill key, else a left click with
Shift. The game casts at its own rate; an input idle RETAP_SECONDS is released and pressed again. The
pointer is kept where the attack aims (`Attack.aim`; for the Warlock the line of combat/policy.py, the
decision the simulator scores); a monster in reach the attack finds no cast for is aimed at directly,
the elite first, then the nearest, AIM_BEYOND past it. The
build's buffs are cast under the strike and kept up between fights by its buff plan (buffs.py; for the
Warlock builds/warlock/buffs.py: a sigil under an elite, Death Mark on the strongest monster in reach).
The main weapon set is swapped in for a tough or hard-hitting pack (`tough`).

What the fight decides from what it sees and the clock (where to cast, whose the pointer is, the
held input, the move asked for) is combat/controller.py, apart from the game; this module reads the
game, asks it and acts.

The player's move comes before any strike (`sense`, `serve_move`): a left click releases the strike
and blocks it until the character has gone and stands again; a click made while a cast ran, which
the game may have swallowed, is made again for the player. A held key or a running character makes
the mode wait.

The step inside a fight (`asked_step`, `take_step`, `step`; combat/stance.py decides where): the mode
never moves the character on its own. The pickup request while hostiles are near asks for one step
to a better place to stand: in a fight the strike is let go, the spot is walked to and the fight
goes on from there, and the press still picks up afterwards when something worth it lay on the
ground; with nothing in reach and nothing to pick up the step goes to where the hostiles near can
be struck from.

The seek step (`Hunter.seek`, one request one step): toward the nearest elite the game holds in memory or the
terror tracker remembers alive in this level, onto the nearest spot with a shot at it
(sight.firing_spots, within STRIKE_REACH), by a click when that is within WALK_UNITS over clear
ground, by a teleport hop otherwise (teleport.hop_toward). None known: the unexplored room nearest by
the way (the potential from the character's own tile). An elite already in reach is only named.

## Evidence behind some rules

- `tough`: the swap to the main weapons for a pack leader or a Herald's own. Tower Cellar 5, 2026-10-11: the
  whole fight with a tier 2 Herald, and the death, on the staff's set, its 13 times the life not counted in the
  life sum. HARD_SCORE: reached by two Gloams, four Dark Rangers or eight Extra Strong Blood Clan, not by eight
  plain ones or a herd of cows. The swap costs most of a second there and back.
- `off_labels`: Drifter Cavern, 09:52:34 on 2026-10-12 (user: "it aimed off and continued shooting there until I
  started steer with mouse myself"): the pointer stood on the ground of a Hell Temptress 5 units off for 13.8 s;
  the 115 blades of 21 casts flew toward potions lying there.
- Fight start: the mark and sigil cast before the strike's press held the first strike back 0.3 to 0.7 s on 190
  of 405 fight starts (logs of 2026-10-10, tests/inventory_tracking/scenarios/loop).
- The KP_6 loop's rush: 95 of 97 strikes followed no loss of life after the arbiter's hold was gone (02:15 to 02:25
  on 2026-10-17); a warp chain with a strike in it took 1.47 s a warp against 1.01
  (rca/2026-10-17/movement-findings.md §2).
- `untouched`, bosses: Baal's random teleports made the strikes count casts that could not land; 20 s alone left
  him unkilled in 60 s on 2 of 10 arena seeds (rca/2026-10-14/baal-sim.md).
