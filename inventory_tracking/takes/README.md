# Takes: the format and the recorder (record.py)

The take format, key by key and schema by schema, and the recorder's design: record.py's module docstring until 2026-10-19.

Stage 1 of combat/plan.md: takes of real play, sampled at the game's frame rate.

A take is one stay in a recorded level (Chaos Sanctuary first, user 2026-10-09) under
`runs/combat/<timestamp>-<area>/`: `manifest.json` (character, skills, slots, rate, key names,
the level map in `level.json` when the guide has one), `frames.jsonl` (one line per frame: the
player, every monster with its life, dead ones included, every missile raw, the pointer with its
button mask and the keys down, the macro state), `units.jsonl` (each monster's full stat list on
first sight: level, defence, resistances for stage 3), `missiles.jsonl` (each missile's whole
record on first sight: the layout research of stage 1) and `events.jsonl` (casts, hits, kills,
unloads, button and key changes, derived while recording). Reads only; nothing touches the game.

Since 2026-10-12 a take also holds what hurts the character (user: "we need to record such things"):
each unit's enchantments (`mods`, monumod ids) in `units.jsonl`, the character's own stat list in the
manifest (`character_stats`: its resistances, which a blow's size is cut by) and a `hurt` event at
every drop of its life, with who was striking, what flew by (takes/hurts.py) and the character's
resistances at that frame (`resists`: physical, fire, lightning, cold, poison as the stat list holds
them, so a curse on it shows). Since 2026-10-13 (schema 3) the same list is in a frame as `r`, in the
first frame that has the character and in every frame it differs from the one written last: a curse is
seen when it lands and when it ends, not only at a drop of life (takes.py `resists_by_frame`).

Since 2026-10-13 afternoon (schema 4; user: "if we need to record more information, then we can update
recorder ... put all we need") a take holds what replaying a whole run in the arena lacked, each written
in the first frame that has it and in every frame it differs from the one written last (takes.py
`carried`):

- `o`: the level's objects a mark may name and its containers (seals, chests, portals), as
  [unit, class, mode, x, y, selectable]: a seal's change of mode is the moment it was opened, which a
  seal boss's pack is timed from;
- `s`: the character's state words, raw hex (game/layout.py STATE_RUN): curses, poison, a skill's delay (a
  Blade Warp the game refuses);
- `w`: the Teleport staff as [charges, most, in hand]: the weapon set held and what a hop costs;
- `b`: the belt's cells by item class: a potion drunk by anyone;

and the macro's own word as events: `request` (the routine a key asked for, what ran then), `press`
(what became of it: the latency trace's record with its outcome), `said` (each line the macro says to
the player) and `log` (every line the macro logs: its decisions), so a take can be cut into an incident
with its presses without the session log. They carry their own time, so the events of a take are not
written in order of time (takes.py sorts them); what is asked and said within NOTE_SECONDS before a take
opens (town, the way in) is written at its start.

The same day, after a review of the recorder against the goal of re-creating any moment of any game
(rca/2026-10-13/recorder-review.md), still schema 4:

- `f`: the character's buffs as the reader has them, [Psychic Ward, Hex: Purge, Consume] (None: unread);
- `g`: what lies on the ground that the pickup step would go for, as [unit, x, y, kind, label, width,
  height, prized]; `i`: the inventory's rows ('.' free, '#' taken): a pickup press replays against these;
- a `state` event when a take opens and whenever it changes: what the macro carries between its looks
  (takes/macro_state.py: attack mode, the routine, the build and its settings, the route's facts and
  stages, the card's mark);
- `records.jsonl`: the character's and each monster's unit record raw (0x1C0 bytes, and the 0x58 of
  monster data after them), its state words and, in a striking mode, the skill it is using (game/
  `skill_in_use`), as [unit, record, states, skill] in hex, at every change of its mode and once in
  RECORD_SECONDS. What the client's code says lies in them (rca/2026-10-13/re-findings.md: the animation
  frame at +0x5C, its length at +0x64, the boss's row at +0x2A of the monster data, state 185 `cooldown`)
  can be read out of every take that has them, also after it is found;
- `h`: the unit the game holds under the pointer, as [unit type, unit id] (None: nothing), at a change
  (game/memory.py `hovered`): what a click landed on (a seal's click that did not take, 12:36:28 that day);
- `k`: the head of the client's clock object, raw hex, in every frame (game/memory.py `tick`): the game's own
  tick, to tell a frame sampled twice or never;
- `units.jsonl` holds the companions too (the mercenary, the pets), with their stat lists;
- the manifest: `clock` (the frame clock and the wall clock read together), `game` (its name),
  `previous` (the take before it in the same game), `code` (the commit, the files that differed);
- towns are recorded like any level (`town`), so a game's takes follow one another without a gap but
  the loading screens.

The leftovers of that review, the same evening (rca/2026-10-13/recorder-review.md, "Leftovers,
implemented"), still schema 4 and each optional to a reader:

- `a`: the Psychic Ward's pool as [left, most] in points (itemstatcost 361 `psychicward`, 362
  `psychicwardmax`, x256 like life; [0, 0] with no ward), from the stat list the vitals are read from:
  a blow the ward took whole shows here and in no `hurt`;
- a `hurt` also carries `absorb` (the ward's pool: [left before, left now, most]) and `companions` ([unit, txt, life
  before, life now, most life] of the mercenary and the pets): what the ward and a Health Link took of
  the same blow;
- `sf`: the server's frame (+0x28) of the last life message the client took, read only in a frame
  whose life differs from the frame before (`server_frame`), and in that frame's `hurt`: two drops of
  one message, or one drop of two;
- a monster whose state words change (a curse lands or ends) has its record written again at once,
  and its stat list read again: a `stats` event when the list differs from the one written last
  (units.jsonl at first sight), so its resistances under a curse are on record;
- `g` rows end with the item's code (the game's tables by the class the item's unit record holds) and
  its quality (item data +0x00), read once a drop;
- the `state` event carries the macro's memory (takes/macro_state.py `memory`).

The game's input mode (rca/2026-10-13/controller-mode.md, 2026-10-13 night), still schema 4, each optional:
the manifest's `input_mode` ('keyboard' or 'controller' when the take opened; None: unread); an `input_mode`
event on each change (`mode`, `pending`, and with a finished flip `flip`: its times in ms,
tracking/input_mode.py `Flips`); in controller mode a `ctl` event when the client's own target or the pressed
record changes (`target` [unit type, unit id] or None, `record`, `skill`).

The macro's own input (2026-10-13 night; rca/2026-10-13/recorder-review.md, "Macro inputs recorded"), still
schema 4, optional: a `sent` event for every input the service sends (input/sent.py), with the time it was sent
and `input` 'key' (`code`, `down`, `name` where the manifest's `keys` names it), 'move' (`xy` in root coordinates,
`f` as fractions of the game window of the frame it is written with), 'button' (`button`, `down`) or 'pad'
(`name`, `value`, `ev` the raw [type, code]), `by` (the sending thread: 'macro' for a macro run, 'MainThread' for
the service loop's own) and `routine` (the macro run's). A change in a frame's `in` that no `sent` explains is
the player's (or the healer's, whose presses are in its own log: `make osd` is not recorded here); the d2-rca
skill's `session.py inputs` lists them. The manifest's `keys` name the belt keys '1'-'4' too.

The service's own load (rca/2026-10-13/latency-findings.md, "Fix 1, built"), still schema 4, optional: a `load` event
once a second while the character is out of town (appraisal/load.py: the process's CPU, the main
loop's, the host's load average, involuntary context switches, the main loop's passes and their time by step, the
macro's looks and their time), and the manifest's `switch_interval` (sys.getswitchinterval of the service).

`Recorder.step` is the per-frame logic with the clock injected; `Recorder.run` paces it on its
own thread with its own memory handle and display connection (`LiveSampler`), bound to the game
by `poll` from the service loop as the macro runner is.
