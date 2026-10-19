# macros/pad.py — design notes moved out of the module (phase 4 cleanup, 2026-10-19)

Source: rca/2026-10-13/controller-mode.md (plan step 9), rca/2026-10-13/controller-gaps.md.

## Input mode per run

A run plays in one input mode, the game's at its start (`input_policy`, asked by runner.py); a flip during the run
ends it at the next act (`Flipped`, wherever it is caught), and the runner makes the same request again in the new
mode. Keyboard mode is the keyboard back end: the code of every routine as it was. The game's mode is followed and
never changed by the run: a flip asks for a click or a movement key (which acts in the world as well) or a pad press
(which is thrown away by the client), takes 1-2 s by players' reports and is not measured yet (plan step 8a); flips
by the macros are step 10.

## The acts

- a cast: `aim_unit` (the client picks its own target, +0xD10: the character is turned toward the unit and the
  target must name it, else nothing is cast) or `aim_place` (a heading: a ground cast lands at its skill's own
  distance along the character's facing at the button's down, so the stick is held AIM_LEAD toward the heading
  before the button, and through it), then `cast` (the record's button, LT with it for records 6-11); a jump that
  still lands more than ASTRAY degrees off has the next leg walked (`walk_owed`);
- the held strike: `hold`, steered by `steer`;
- a walk: `walk` (the left stick held toward the place, aimed again at every look, centred in every `finally`);
- an object or a door: `interact` (stand by it, the target names it, A); an item: `pick_up` (stand on it, so it
  is the nearest, the Loot record: Loot, else Loot to Cube);
- what the run may cast: `slots` (the skills on the pad's records stand for the skills on keys), `keys` (the
  record's label per skill, as skills.py `skill_keys` gives the key).

## Records 12-15 and the key route

Records 12-15 have no pad button: with Quick Cast on, the key of keyboard skill slot n casts controller record n
in controller mode (controller-gaps.md section 2, read in the client, not yet seen in a game). A session uses them
only after a probe showed it (`KeyRoute`, `PadActs.probe_key`): once a game, at a quiet moment, a buff whose state
the character shows is cast by its record's keyboard key instead of its button, and the state appearing opens the
route. In controller mode every skill key casts a controller record, not the keyboard slot's skill: the only skill
keys the pad back end presses are this route's.

Belt keys and the weapon swap key are keyboard keys, which flip nothing (gamepad-proton.md §5); whether they act in
controller mode is measured (`Pad drink:`, `Pad swap:`).

## What a log of a game in controller mode answers (stable prefixes)

- `Pad target:` how long the controller's target took to name the unit a cast was meant for, or what it held
  instead after TARGET_WAIT (the auto-target's rule and its settling time);
- `Pad walk:` the world heading the stick was given against the way the character went over its first
  MEASURE_UNITS (the stick's sign and its turn into the world: STICK_TURN, STICK_SQUASH, STICK_Y);
- `Pad jump:` where a jump (Teleport, a build's own) landed against the heading and its fixed reach (`reach`);
- `Pad drink:` whether the belt cell emptied after a belt key pressed in controller mode;
- `Pad swap:` whether the weapons changed after the swap key pressed in controller mode;
- `Pad key:` whether a keyboard skill key cast its controller record (the probe), and so whether records 12-15
  are used in this session;
- `Pad act:` each press: the skill, its record and what it was aimed at.

## Evidence behind the tuned numbers

- AIM_LEAD 0.08 s: the game of 22:04 on 2026-10-14 (rca/2026-10-14/run-1904-findings.md §3.1, its take's `sent`
  rows): the stick and the button went out in the same millisecond for all 53 landed Blade Warps (the button held
  47-99 ms with the stick held through it), and 36 landed along the character's facing before the press, 3 along
  the stick alone. A pushed stick shows in the game 6-58 ms after it is sent (23 pad walks from a centred stick,
  median 29 ms; the frames are 40 ms apart): two such frames.
- ASTRAY 60 degrees: one wrong landing re-plans from the wrong place, and the next jump went the same wrong way (14
  in a row at 90 degrees, 22:06:56-22:07:10). The walk is accurate (off -18..+8 degrees over 22 walks).
- STICK_SQUASH 1.0 is the pure 45-degree turn; 0.5 would be the direction the heading is drawn in on the screen
  (the isometric view halves the height). STICK_Y -1.0 flips the stick's y, should the uinput axis come out the
  other way round in Wine. Both inferred: `Pad walk:` lines measure them (plan step 8e).
