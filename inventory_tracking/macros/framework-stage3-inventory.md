# Framework Stage 3 inventory

The inventory of where today's code leans on Echoing Strike or the Warlock inside the framework-to-be,
made 2026-10-12 for Task 2.1 of [framework-plan.md](framework-plan.md); line numbers as of commit c688712.

---

## 2. Deviations from the plan's sketch, with evidence

| # | Sketch | Now | Why (evidence) |
| --- | --- | --- | --- |
| 1 | `Attack.policy() -> Policy` | `Attack.aim(seen, through=()) -> Choice \| None` | `controller.py:63-66` needs more than a `Policy` can say: the best cast laid through given units (`policy.choose(seen, through=first)`), with the yield test and `MIN_SCORE`. That is why it does `isinstance(policy, LinePolicy)`. With `through` in the method, `aim_choice` becomes `attack.aim(seen, first)` then `attack.aim(seen)` with identical results. The bound method `attack.aim` is itself a `Policy`, so `LiveAim(policy=attack.aim)` still works (`controller.py:90`). |
| 2 | `dealt(origin, focal, foes: Sequence[Foe]) -> Mapping[int, float]` | `foes: Mapping[int, Foe]`; uncapped and unweighted by contract | `Foe` has no unit id (`policy.py:54-60`); ids are the keys of `Observation.foes` (`policy.py:70`), so a mapping keyed by int needs them. The cap by life left and the elite weight are the framework's loop in `stance.py:236-254`, so `dealt` must return raw points for that loop to stay identical. |
| 3 | `Attack.skills() -> tuple[int, ...]` | `Attack.skill: int` | The only user is `strike_input` (`hunt.py:278-296`), which needs the one skill to test against the right button, the slots and the left button. Nothing today checks a set of skills "for the mode to fight". |
| 4 | — | `Attack.sees(seen, companions)` | `policy.observe` (`policy.py:275-277`) fills `Observation.linked/share` from `link_table()` and the `DEFILER` class: a Warlock summon's Health Link inside the framework's observation. It is on the play path (`hunt.py:632, 1224, 1267`; `rotation.py:166`). See trade-off T2 for why it is a hook and not a new field on `Observation`. |
| 5 | `MovementSet`: `applies`, `leg`, `eta` | + `jumps(facts, intent)` | `camp(jumps=)` prices each of about 289 places by the first `Jump` that reaches it (`stance.py:304-313`, `336`), and `Travel.make` re-checks a step's skill against the list (`travel.py:222-225`). `leg`/`eta` cannot reproduce that: `stride` picks among longest, 0.75 and 0.5 of it with a footing test (`travel.py:112-119`), a different rule from camp's `least <= straight <= reach` and line test. |
| 6 | — | `MovementSet.wait(facts, goal, intent)` | `may_wait` is in the sketch's `Intent`, but a pure `leg` cannot sleep. Today the caller sleeps and reads the world again before asking (`hunt.py:458-464`, `540-554`, `575-577`). `wait` returns the seconds, so the same order is kept. |
| 7 | `Intent.reserve` only | + `sparing`, `walks_under` (soft thresholds) | One int cannot say both rules in the code. `Travel.jumps` is hard: never a Teleport under 10 (`travel.py:172`). `warp_hop` is soft: under 15 the blade first, but Teleport still where the blade has no line (`hunt.py:538-558`). `afoot` has a third: a walk before a hop only under 10 (`hunt.py:450`, `466-467`). Stage 5's "one rule at 15" removes these two fields. |
| 8 | — | `Intent.short`, `Intent.shot` | `stride(..., short, shot, shuns)` (`travel.py:86-88`); the sweep passes `STAND_OFF, shot=True, shuns=` (`hunt.py:796-798`). Moving the goal `short` nearer instead changes float rounding of `at(stride)`, and `shot` needs the true goal (`travel.py:124`). |
| 9 | `Buff.due: Callable[[World, float], bool]` | `due: Callable[[BuffFacts], bool]`, with `BuffFacts(world, now, foes, reachable, prey, cast_at)` | (world, now) cannot express today's tests: seconds since the last cast live in the executor (`rotation.py:58-64`), per unit for the sigil (`rotation.py:74-75`); Consume needs the mode's hostiles, not `world.monsters` (`hunt.py:1184`, `345-348`); the sigil needs the monster of the strike's line (`hunt.py:1432`); Death Mark the reachable ones (`hunt.py:1425`). |
| 10 | `worth(world, target)`, no word on who picks the target | `target: Callable[[BuffFacts], Monster \| None]`; `worth(facts, target)` | Two different rules today: Death Mark takes the strongest in reach (`hunt.py:1425`), the sigil takes the line's monster (`hunt.py:1432`). The row has to say which. |
| 11 | — | `Buff.state` | Architecture 4.2: "retry and distrust become one rule for every buff whose state can be read". The executor needs the reader: `player.hex_purge`, `player.ward`, `player.consume` (`rotation.py:175-179`, `196-200`; `hunt.py:1174`). |
| 12 | `needs: frozenset[str] \| None` | `needs: Literal['prebuff', 'battle'] \| None` | Buff rows are per build; the item codes of a set are per character (`routines.py:90-106`, `CHARACTERS` by name). A build row can only name the role; `Loadout` resolves it. |
| 13 | — | `Buff.also` | Consume's due-test wants two skills in slots (`hunt.py:1176`) and its caster needs keys for three (`hunt.py:1192`). Without it "every skill of a buff plan resolves to a key" (Task 2.3) cannot see the summon. |
| 14 | `settings: BuildSettings = BuildSettings()` | `field(default_factory=BuildSettings)` | ruff RUF009; same value. |
| 15 | `shuns` and `worth` defaults as lambdas | named `nowhere`, `always` | Readable in a repr and in the tests; same behaviour. |

Unchanged from the sketch: `NoWay`, `Leg`, `Tactic`, `Build`'s field list, `choose`.

---

## 3. Every place today's framework-to-be leans on Echoing Strike or the Warlock

### `macros/hunt.py`

| file:line | What it does | Replaced in Stage 3 by | Risk to "no change" |
| --- | --- | --- | --- |
| hunt.py:62-71 | imports `REACH`, `STRIKE_REACH`, `LinePolicy`, `MIN_FOCAL` | `attack.reach`; the rest per rows below | none by itself |
| hunt.py:100-109 | imports `BLADE_WARP, CONSUME, DEATH_MARK, ECHOING_STRIKE, ENGORGE, SUMMON_DEFILER` | gone once the rows below move | ratchet list |
| hunt.py:148-149 | `FIRST_STRIKE_SECONDS`, `DEATH_MARK_SECONDS = 8` | the first stays (executor's "struck" rule); the second into the Death Mark row's `due` | low |
| hunt.py:162-163 | `WARP_CHARGES = 15`, `WARP_RETRY = 3` | `Intent` PLAYER_STEP: `sparing=15`, `distrust=3` | see 523-567 |
| hunt.py:173 | `STAND_OFF = 14` ("the player engages at 12 to 14") | stays a framework number now; `Intent.short` carries it; a `BuildSettings` field later | none if the number is kept |
| hunt.py:204-211 | `CONSUME_CLEAR/SOON/RETRY`, `INPUT_SECONDS` comment naming the strike | Consume row's `due` in `warlock/buffs.py` | low |
| hunt.py:278-296 | `strike_input`: the input that has `ECHOING_STRIKE`; Abort text names it | stays in `macros/`, parameterised by `attack.skill`; text by `skill_name` | texts are in logs; check the replay-log goldens compare them |
| hunt.py:313 | `self.policy = policy or LinePolicy()` | `build.attack` (`aim`) | `Hunter()` with no build is used by `golden/cases.py:140` and `arena/driver.py:130`: needs a default build or an adapter edit |
| hunt.py:315 | `Rotation(lambda: self.policy)` | the buff executor + rows (3.5) | see rotation.py |
| hunt.py:316 | `consumed_at` | executor memory (`BuffFacts.cast_at`) | the back-dating at 1202 has to be kept |
| hunt.py:396, 510, 517, 954, 989, 1360 | `in_reach(..., REACH, ...)`: the blades' range decides what is "in reach" | `attack.reach` | none (same number, 22) |
| hunt.py:443-483 | `afoot`: Blade Warp first whatever the staff holds, delay waited (458-464), walk only under `LOW_CHARGES`, else falls to a hop, `around` at 0 | `MovementSet.wait` + `leg` under intent SEEK (`sparing=inf`, `walks_under=10`, `may_wait`) | high: the return value False means "let `hop_toward` plan it", which is a Teleport with a swap outside `leg`; and 466 tests `found.skill != BLADE_WARP` by id |
| hunt.py:523-567 | `warp_hop`: KP_4 by Blade Warp under 15 charges, clear line, delay waited, failed warp left 3 s; **pops** the failure (547) | `leg` under PLAYER_STEP; the `warp` callback of `teleport.step_toward` | medium: the pop also clears the sweep's 30 s distrust as a side effect; a pure `distrust=3` does not, so the caller must still pop from `Travel.jump_failed` |
| hunt.py:569-590 | `empty_hop`: staff at 0: blade (delay waited, failure popped at 578), else walk, else `around`; says "the Teleport staff has 0 charges left" | the `Empty` set's `leg`; `NoWay(reason)` for the Abort at 586 | medium: the Abort text becomes the `NoWay` reason |
| hunt.py:592-597 | `foot_step` → `afoot` | same as 443-483 | — |
| hunt.py:632, 1224, 1267 | `observe(...)`: fills `linked/share` from the Defiler's Health Link (`policy.py:275-277`) | generic observe, then `attack.sees(seen, companions)` | low; at 1224 `tough` passes no companions, so `sees` is not needed there |
| hunt.py:633 | `policy = self.policy if isinstance(self.policy, LinePolicy) else LinePolicy()` for `camp` | `camp(seen, attack, ...)` using `attack.reach` and `attack.dealt` | see stance.py:211-256 |
| hunt.py:634 | `self.travel.jumps(run, world)` | `set.jumps(facts, OWN_MOVE)` | `golden/cases.py:195` calls `travel.jumps` directly: adapter edit in 3.1 |
| hunt.py:796-798 | sweep's stride: `STAND_OFF`, `shot=True`, `shuns` | `leg(facts, goal, replace(OWN_MOVE, short=..., shot=True, shuns=...))` | `stride` returns None with no reason; each None needs a `NoWay` text and the callers that test `is None` (657, 465-468, 582) change shape |
| hunt.py:927-946 | Hex: Purge and Psychic Ward kept up outside a fight; on Abort sets `purged_at/warded_at` | rows with `phase='upkeep'`, `state=` | medium: order (purge, ward, then Consume at 951) and the `run.pause('key')` after each are loop order the goldens' loop counts see |
| hunt.py:951-953, 1170-1203 | `consume_due`, `consume`: Consume recast; focus test (1178), "a key was pressed" back-dating (1200-1202) | row `phase='upkeep'`, `caster='consume'`, `also=(summon,)`; due from `state` and `foes` | medium: the focus test reads `run.actuator`, not facts, so it stays in the executor or the caster; the 3 s retry after a key is a caster result the executor must honour |
| hunt.py:974, 1319 | `strike_input(...)` calls | same function with `attack.skill` | none |
| hunt.py:1020 | `firing_spots(..., STRIKE_REACH, ...)` (20: where to stand for a shot) | stays a number; settings candidate | none |
| hunt.py:1079-1099 | `main_weapons`: `CHARACTERS.get(player.name)` | `build.weapons` | low: an unknown character returns True today (1086); `weapons=None` must do the same |
| hunt.py:1205-1228 | `tough`: `ELITE_LIFE` from rotation.py, `TOUGH_POINTS`, `HARD_SCORE` | stays (Stage 7 replaces it); `ELITE_LIFE` must stay importable when rotation.py moves | low |
| hunt.py:1271 | `aim_choice(self.policy, seen, reachable, first=bosses)` | `aim_choice(attack, ...)` → `attack.aim` | see controller.py:63 |
| hunt.py:1275-1310 | `off_labels`: moves the pointer along the line, assuming a cast flies its length whatever the pointer's distance | **not covered by the contract**; stays as an assumption of a line attack | none for the Warlock; wrong for a build whose cast lands at the pointer. Named residue or a later `Attack` fact |
| hunt.py:1346, 1462 | texts "Echoing Strike not on…", "Echoing Strike (how) at…" | `skill_name(attack.skill)` | text only |
| hunt.py:1414-1423 | purge, ward under the strike (`fighting=True` → `WARD_SECONDS`) | rows `phase='fight'` | the ward's 5 s floor applies only in a fight: two rows of one skill sharing one memory |
| hunt.py:1424-1431 | Death Mark every 8 s on the strongest in reach, if `worth_a_mark` | row `on='monster'`, `target=`, `worth=` | `marked_at` is set only on a real cast (`rotation.py:218-224`): off screen or dead it is asked again next frame |
| hunt.py:1432-1437 | Sigil under the line's elite, 10 s per unit | row `on='ground'`, `target=prey`, `since(skill, unit)` | off screen it back-dates to retry in 1 s (`rotation.py:84`) |
| hunt.py:1438-1443 | Engorge, tested `ENGORGE in world.slots` here | row `on='corpse'`, `caster='engorge'` | `aim.forget()` and `cast.excuse()` only when the caster returns True |
| hunt.py:143-147 | `VULTURES`/`AIRBORNE` ("the blades pass through") | stays: monster knowledge, not a skill | none |

### `macros/rotation.py` (the whole module is the Warlock's)

| file:line | What it does | Replaced by | Risk |
| --- | --- | --- | --- |
| rotation.py:12-13, 18, 21 | imports `LinePolicy`, `BLADES_A_CAST`, five skill ids, `DEFILER_CLASS` | moves to `builds/warlock/` | — |
| rotation.py:25-50 | every constant per skill; `ELITE_LIFE` is generic and used by `hunt.tough` | rows' numbers; `ELITE_LIFE` stays in the framework | low |
| rotation.py:56-65 | last-cast times, unseen counts, `let_go` | executor memory (`BuffFacts.cast_at`) | the unseen counters (`HEX_TRIES`, `HEX_DISTRUST`) are per buff |
| rotation.py:67-72, 150-157 | `key`, `resume`: the generic part | the shared executor in `macros/` (3.5) | none |
| rotation.py:74-88 | sigil due and cast | row + shared caster | see hunt.py:1432 |
| rotation.py:90-148 | Engorge due (demons out, hurt 4 s, else 15 s; `run.corpses is None` → never) and cast | row + `casters['engorge']` | medium: `due` cannot see `run.corpses`; the caster back-dates `engorged_at` (118, 147); returns True without a cast when the pointer moved (148) |
| rotation.py:159-168 | `worth_a_mark`: substitutes `LinePolicy()`; `MARK_CASTS * BLADES_A_CAST * damage_of` | build code calling its own attack (`Buff.worth`); no framework call needed | covered by goldens `due:mark:*` (`golden/cases.py:380-414`); if routed through `dealt`, a target standing exactly on the character differs |
| rotation.py:170-209 | purge/ward due and cast, with the retry rule | rows with `state=`; the retry rule in the executor | the rule must match for both skills, including the warning at `HEX_TRIES` |
| rotation.py:211-225 | Death Mark cast: body aim, not ground; re-reads the world for the target | shared caster with `on='monster'` | `screen_fraction` (body) against `ground_fraction` (sigil): `on` decides |

### `macros/routines.py`

| file:line | What it does | Replaced by | Risk |
| --- | --- | --- | --- |
| routines.py:1-10 | docstring: the Pindleskin routines for this character | — | — |
| routines.py:21-28, 31 | imports four skill ids, `DEFILER_CLASS` | move | — |
| routines.py:86 | `SKILLS` (prebuff keys) | derived from the build's prebuff rows (`skill` + `also`) | key set must stay the same or "the skill keys changed" (765) fires |
| routines.py:90-106 | `Loadout`, `HEART_OF_THE_OAK` (item codes), `CHARACTERS` | `Loadout` to `build.py`, the row to `builds/characters.py` → `Build.weapons` | import cycle, see section 5 |
| routines.py:109-134 | `SUMMON_SPOTS`, `NEAR_SPOTS`, `CLEAR`, `COVER_*`, `CONSUME_ATTEMPTS` | `warlock/casters.py` | — |
| routines.py:249-266 | `defilers`, `bystanders` | casters | — |
| routines.py:269-420 | `in_the_way`, `crowd`, `log_crowd`, `open_spots`, `summon_defiler`, `aim_at`, `log_miss` | casters | `standable` (293) is generic |
| routines.py:420-468 | `consume` | `casters['consume']` | — |
| routines.py:580-585 | `log_consume` (research) | casters | — |
| routines.py:587-608 | `prebuff`: weapons, Defiler, Consume, Defiler again, purge, ward | rows `phase='prebuff'`, `needs='prebuff'`; the Defiler dance is one caster | order is behaviour; `fresh` (a new game's load limit) is an argument only this caster takes |
| routines.py:610-621 | `renew_consume` | `casters['consume']` in upkeep | — |
| routines.py:707-715 | `character_keys`: "no macro for {name}", sets `run.prebuff_hands/battle_hands` | `build.weapons` | an unknown character aborts the prebuff today; keep |
| routines.py:751-773 | `run_macro` → `prebuff` | executor's prebuff phase | — |
| routines.py:166-243 | `quick_cast_over`, `press_skill`, `press_through`: generic; skills named only in comments | stay | none |

### `macros/travel.py`

| file:line | What it does | Replaced by | Risk |
| --- | --- | --- | --- |
| travel.py:22 | imports `BLADE_WARP`, `TELEPORT` | Blade Warp to `warlock/movement.py`; `TELEPORT` is generic | — |
| travel.py:32-46 | `WARP_DELAY`, `WARP_SECONDS`, `WARP_SPEED`, `LOW_CHARGES`, `JUMP_DISTRUST` | the blade's numbers to the build; `LOW_CHARGES` → `Intent.reserve`; `JUMP_DISTRUST` → `Intent.distrust` | — |
| travel.py:76-77 | `warped_at`, `jump_failed` | stay as the impure memory; copied into `MoveFacts.last_used/failed` | — |
| travel.py:79-126 | `stride(run, world, ground, aspect, goal, short, shot, shuns)` | pure over `MoveFacts` + `Intent` | 117 tests `skill == BLADE_WARP` for the line: must become `Jump.line` |
| travel.py:128-157 | `around`: 143 `skill == BLADE_WARP` | pure; the `Empty` set | `barred is None` returns None (139-140): needs a reason |
| travel.py:159-174 | `jumps`: blade first (in slots, trusted 30 s, delay over), Teleport in hand with ≥ 10 or as own skill | `MovementSet.jumps(facts, intent)` | `run.teleport is None` and `run.teleport() is None` both mean "own skill" (171-172): `MoveFacts.staff=None` keeps that, including the unreadable-staff case |
| travel.py:176-179 | `jump_by(warp=False)` names `BLADE_WARP`; no caller passes `warp=False` | drop the flag | none |
| travel.py:181-209 | `jump`: 193 sets `warped_at` only for `BLADE_WARP` | `last_used[skill]` for every jump | low: Teleport's time is recorded but never read |
| travel.py:211-229 | `make`: re-checks against `jumps`, drops `BLADE_WARP` on a wall (224) | asks `set.jumps(facts, intent)`; drop by `Jump.line` | it needs the intent the step was chosen under |

### `macros/teleport.py`

| file:line | What it does | Replaced by | Risk |
| --- | --- | --- | --- |
| teleport.py:53, 134 | `MOVING = {TELEPORT, BLADE_WARP}`: casts that end elsewhere | the skills of the movement set's jumps (from the build) | 877: `settled` treats a cast not in `MOVING` as standing; a missing jump skill changes where a hop is planned from |
| teleport.py:491-513 | `take_teleport`: the only place that swaps to the staff | stays (framework; Teleport is generic) | `may_swap` only describes it in Stage 3 |
| teleport.py:793-847 | `step_toward(afoot=, warp=)`: callbacks into `Hunter` for the blade and the empty staff | the navigator's `leg` | 833-845: with 0 charges, `warp` first, `afoot` on Abort: an order the set must keep |
| teleport.py:918-960, 994 | `hop_toward(..., warp)`: asks `warp(target, player, landing)` first; 994 comment on the blade's light read | same | the landing is planned by `Way` first, then offered to the blade: `leg` gets the landing as its goal, not the mark |
| teleport.py:323-400, 434-463 | `Way`, `landing` | generic; stay | — |

### `macros/pickup.py`

| file:line | What it does | Replaced by | Risk |
| --- | --- | --- | --- |
| pickup.py:50, 341-345 | gold: `BLADE_WARP in world.slots`, its key, pressed directly | `leg(facts, pile, intent)` for a free jump, or `set.jumps` | medium: it bypasses `Travel` today: no delay test, no failure memory, no `warped_at` update |
| pickup.py:61, 169 | `GOLD_UNITS = 26.0  # travel.JUMP_REACH`: gold "within one jump" | the reach of `set.jumps(...)[0]` | with no free jump, gold is not chosen at all: keep 26 for the Warlock |
| pickup.py:63, 359 | `GOLD_SECONDS` and a log line naming the blade | follow | text |
| pickup.py:6-7 | docstring names the Warlock's materials | loot rules; out of this scope | — |

### `combat/controller.py`, `combat/stance.py`, `combat/policy.py`

| file:line | What it does | Replaced by | Risk |
| --- | --- | --- | --- |
| controller.py:26-36 | imports `LinePolicy`, `REACH` | — | — |
| controller.py:63-66 | `isinstance(policy, LinePolicy)`; `policy.choose(seen, through=first)`; `policy.yields`; `MIN_SCORE` | `attack.aim(seen, first)`, then `attack.aim(seen)` | none if the build's `aim` applies yield and `MIN_SCORE` on the `through` path exactly as 63-65 do |
| controller.py:70-80 | fallback: straight at the nearest reachable, `AIM_BEYOND` past | stays (framework) | none |
| controller.py:84-105 | `LiveAim.reach = REACH` default | `attack.reach` given by the caller (`sim/policy.py:54`) | simulator scores (`GATE-base.txt`) |
| stance.py:25 | imports `LinePolicy` | `Attack` | — |
| stance.py:49 | `CAST_SECONDS = 0.36` (from `sim/input.py` cast frames of this strike) | stays a number; settings candidate | none |
| stance.py:52 | `ENGAGE = 14` ("at the end of the blades' flight a step is a miss") | stays; settings candidate | none |
| stance.py:59-61 | `BLADES_A_CAST = 2.8` | inside the build's `dealt` | — |
| stance.py:211-256 | `taken(seen, policy: LinePolicy, ...)`: `policy.reach` (222), line geometry by `CONTACT_RADIUS` (233), `policy.damage_of * BLADES_A_CAST` (237), `policy.elite_weight` (238) | `attack.reach`; `attack.dealt(spot, foe.at, near)` once per near foe gives lines and blows; the weight becomes the framework's `ELITE_WEIGHT` | **highest risk**: `decisions.json` is byte-identical only if `dealt` repeats the arithmetic of 220-237 (same `hypot`, same `dx*ux + dy*uy > 0`, same product) and the framework sums in its own `near` order. More Python work per place (a dict per foe per place, about 289 places) |
| stance.py:259-338 | `camp(seen, policy: LinePolicy, ...)`: 327 `policy.reach` | `attack.reach` | none |
| stance.py:109-121 | `Jump`: names no skill | stays | — |
| policy.py:1-24 | docstring: "Where to cast Echoing Strike now" | — | — |
| policy.py:31-35 | imports `DEFILER`, `damage_table`, `link_table`, the blades' constants | move | — |
| policy.py:39 | `DUPLICATE` from `BLADES` | build | `arena/game.py:56` and `sim/engine.py` import it |
| policy.py:41 | `REACH = RANGE` | `attack.reach` | — |
| policy.py:42-44 | `OFFSETS`, `MIN_FOCAL`, `MIN_SCORE` | build, except `MIN_FOCAL` (`hunt.py:1291`) and `MIN_SCORE` (`stance.py:321`), which the framework also reads | keep both importable |
| policy.py:45, 48-49 | `ELITE_WEIGHT`, `STRIKE_REACH`, `AIM_BEYOND` | framework numbers; stay | — |
| policy.py:54-90 | `Foe`, `Observation`, `Choice`, `Policy` | stay. `Observation.linked/share/marked` are Warlock facts under generic names | residue by name |
| policy.py:93-138 | `virtual_cast` | `echoing_strike/attack.py` | — |
| policy.py:141-151, 229-246 | `clear_line`, `walls` ("stops a blade": the missile flight layer) | stay: generic for any missile | wording only |
| policy.py:154-200 | `LinePolicy` | build; `Attack.aim` wraps it | — |
| policy.py:203-226 | `NearestPolicy`: default `damage_of=damage_table()` (this strike's damage file) | stays as the generic baseline; its default must not read the build's table | the dummy build of Task 2.2 uses it |
| policy.py:249-255 | `linked_set` | build | `sim/engine.py` imports it |
| policy.py:258-278 | `observe`: 275-277 `link_table`, `DEFILER` | generic part stays; link via `attack.sees` | low |

Also outside the list you named, found on the way: `macros/world.py:130-136, 151-159, 626-651` reads the Consume, Hex: Purge and Psychic Ward states into `Player.consume/hex_purge/ward`, and `Monster.raw` is kept "Defilers only" (330). That is Warlock state in the framework's world record; `Buff.state` reads it but does not move it. `macros/sight.py:3` only names the strike in its docstring. `macros/runner.py:503-511` passes `boss_step`, `foot_step`, `warp_hop` as callbacks.

### Per module: play-time or offline

| Module | Verdict |
| --- | --- |
| `combat/mechanics/echoing_strike.py` | Build-specific model, used at play time through `policy.virtual_cast` and by the arena (`arena/game.py:12`). Moves wholesale under the build (3.8). |
| `combat/mechanics/damage.py` | Build-specific data lookups (points per blade contact, Health Link, Death Mark, Hex Purge, companions). Play-time through `LinePolicy.damage_of` and `observe`. Moves with the build. |
| `combat/mechanics/hits.py` | `CONTACT_RADIUS` is read at play time (`policy.py:100`, `stance.py:233`); the rest matches emulated blades to recordings: offline. The constant goes with the attack. |
| `combat/mechanics/validate.py` | Offline (emulation against a take). Stays build-specific, moved wholesale. |
| `combat/mechanics/movement.py`, `tables.py` | Generic (monster routes, game tables). Framework. |
| `combat/sim/engine.py` | Offline replay of takes with the blades emulated and Health Link (`:147-149`). Build-specific; 3.8's "cast model as a parameter". Feeds the combat gate's scores. |
| `combat/sim/policy.py` | Offline candidates (`LinePolicy`, `NearestPolicy`, `LiveAim`). Build-specific; it is where `LiveAim` gets its reach. |
| `combat/sim/input.py` | Offline model of this strike's presses to casts. Build-specific. Its cast frames are where `stance.CAST_SECONDS` comes from. |
| `combat/sim/situation.py` | Offline (a situation cut from a take; uses `echoing_strike.focal_point`). Build-specific. |
| `combat/sim/monsters.py` | Generic and play-time-to-be: the arena uses it now (`arena/mobs.py:35`), Stage 4.4 uses it as the look-ahead. Names no skill. Framework. |
| `combat/hurts.py` | Recording-time and offline (what took the character's life). Names no skill in code. Framework; the plan's residue note is about its report text. |
| `combat/score.py` | Play-time (`LiveScore` in `hunt.py:314`), generic (`points_of` only). Framework. |
| `combat/scoreboard.py`, `combat/compare.py` | Offline over takes. `compare.py:32` uses `NearestPolicy()`. May stay with the build's analysis. |
| `combat/viz.py`, `combat/viz_moments.py` | Offline export for the viewer. `viz.py:32` imports the blade model: build-specific, moved wholesale. `viz_moments.py` only has a `blade_life` parameter. |
| `combat/analysis.py` | Offline analysis of recordings; names no skill in code. May stay. |
| `combat/record.py`, `takes.py`, `timeline.py`, `retain.py` | Recorder and readers: generic. |

---

## 4. Trade-offs flagged (one implemented each)

**T1. Target choice: `Attack.policy()` or a method.** Options: (a) `policy() -> Policy` plus a second method for "through these units"; (b) one method `aim(seen, through=())`. Implemented (b): one place to ask, the `isinstance` goes away, and `attack.aim` is still a `Policy` for the simulator. Catch: `Hunter(policy=...)` and tests that hand a bare `LinePolicy` need an adapter in Stage 3.

**T2. Health Link: a hook or a field.** Options: (a) `Attack.sees(seen, companions)`, called by the game side only; (b) give `Observation` a generic `companions` field and let the build's `aim` derive the link. Implemented (a). With (b) the simulator's observations, which already carry `linked` (`sim/engine.py:149`) and no companions, would have the link recomputed as empty unless `aim` guesses who built the observation. That would move the gate's scores.

**T3. Who owns reach.** Options: the build (`Attack.reach`), or a framework setting. Implemented the build's: 22 is the blades' range (`policy.py:41`). The other distances that are tuned to this build — `STRIKE_REACH` 20, `STAND_OFF` 14, `ENGAGE` 14, `CAST_SECONDS` 0.36 — I left as framework constants and kept `BuildSettings` empty, because no stage before 4 reads them per build. They are the first candidates for `BuildSettings` fields; say if you want them in now.

**T4. Who weights elites when a place is priced.** `taken` uses `policy.elite_weight` (`stance.py:238`). With `dealt` returning raw points the weight becomes the framework's `ELITE_WEIGHT` (2.0, `policy.py:45`). Identical unless a `LinePolicy(elite_weight=...)` with another weight is handed to `camp`; the stance and threat harnesses construct `LinePolicy` themselves, so Stage 3.7 should grep them first. Alternative: `dealt` returns worth, but then the cap by life left cannot be the framework's.

**T5. Waiting out a delay.** Options: (a) method `wait(...) -> float`, `Leg` stays `Step | NoWay`; (b) a third `Leg` variant `Wait(seconds)`. Implemented (a) because the brief fixes `Leg`. I would lean to (b) at Stage 7, when the swap contract adds `Swap` as an explicit leg anyway and the union grows.

**T6. `short`/`shot` on `Intent`.** Options: on `Intent` (next to `shuns`, which the same single caller passes), or extra arguments of `leg`. Implemented on `Intent`; the sweep's stride is `replace(OWN_MOVE, short=…, shot=True, shuns=…)`.

**T7. Soft charge thresholds on `Intent`.** `sparing` and `walks_under` exist only to reproduce today's three rules. The values Stage 3.2 needs:

| Intent | reserve | sparing | walks_under | may_swap | may_wait | distrust |
| --- | --- | --- | --- | --- | --- | --- |
| PLAYER_STEP (KP_4) | 0 | 15 | 0 (walk only at 0 charges) | True | True | 3 |
| SEEK | 0 | inf | 10 | True (through `hop_toward`) | True | 30 |
| OWN_MOVE (sweep, stance) | 10 | inf | 0 | False | False | 30 |

**T8. `Buff.needs` as a role, not codes** (deviation 12). The alternative, codes on the row, puts a character's items into a build's plan.

**T9. `Build.weapons: Loadout | None`** stays as sketched: a character is a layer (`dataclasses.replace(build, weapons=…, applies=by name)`), listed before its build. An unknown character of the same build gets `weapons=None`.

---

## 5. What Stage 3 will find hardest

1. **Import cycles, both certain.** `build.py` imports `Step` from `travel.py`. Stage 3.1 makes `travel.py` take `MoveFacts`, so it must import `build.py`: travel → build → travel. Moving `Loadout` into `build.py` adds routines → build → travel → routines (`travel.py:20`). There is no cycle today, and `hunt.py` importing `build.py` is fine. Proposal: in 3.1 move `Step` into `build.py` (it depends only on `stance.Camp`) and have `travel.py` re-export it. `build.py` then imports only `world`, `stance`, `policy`, `levels`, `danger`, `config`, all below `travel`, `routines` and `hunt`. I did not move it.
2. **`stance.taken` behind `dealt` with byte-identical goldens.** The simplified line model (not `virtual_cast`) has to be reproduced float for float, and the plan's text "prices a place by `virtual_cast`'s blades" is not what the code does (`stance.py:226-237`).
3. **The seek step is not one `leg`.** `afoot` returns False to mean "let `hop_toward` plan a Teleport with a swap" (`hunt.py:466-472`), and that hop has its own planner (`Way`, `landing`) and its own failure handling. The SEEK intent only reproduces the part before the fall-through.
4. **Failure memory is mutated by callers.** `warp_hop` and `empty_hop` pop the blade's failure (`hunt.py:547, 578`), which also shortens the sweep's 30 s distrust. Pure facts need the caller to keep doing that.
5. **`stride`/`around` return None in seven shapes with no reason** (`travel.py:109, 123, 125, 140, 157`). Each needs a `NoWay` text, and some callers treat None as "try the next thing", not as a stop.
6. **Buff rows against back-dated timestamps.** Sigil off screen (`rotation.py:84`), Engorge with no corpse (118, 147), Consume stopped by a key (`hunt.py:1202`), purge/ward on Abort (`hunt.py:935, 945`) all write a time in the past or present without a cast. The executor needs a "try again in N seconds" result from a caster; `Buff` has no field for it and I did not invent one.
7. **`Hunter()` without a build** is constructed by `golden/cases.py:140`, `arena/driver.py:130` and `appraisal/service.py:673`. The goldens call `hunter.travel.jumps` and `hunter.rotation.worth_a_mark` directly (`cases.py:195, 385`).
8. **`Tactic.applies(pack)`**: `Pack` holds unit ids, a type name and reason strings (`danger.py:219-228`), not txt ids, rank or tier. Stage 7 will need more than `Pack` to match "by type, family, rank, enchantment, tier". Left as sketched.


## Corrections after Stage 3.1–3.3 (2026-10-12)

- T7's intent values were wrong for what the sets are asked: every stride and every re-check today
  runs with a floor of 10 charges and 30 s of distrust; "spent to the last" belongs to
  `hop_toward`'s Teleport, which no set makes. As built (`macros/travel.py`):

  | Intent | reserve | distrust | sparing | walks_under | may_swap | may_wait | waits_blind |
  | --- | --- | --- | --- | --- | --- | --- | --- |
  | PLAYER_STEP | 10 | 3 | 15 | 1 | True | True | True |
  | SEEK | 10 | 30 | inf | 10 | True | True | False |
  | OWN_MOVE | 10 | 30 | inf | 0 | False | False | False |

  `Intent.reserve` means the fewest charges a staff jump is still made with (`charges >= reserve`).
- §5.1's second cycle does not exist while `Loadout` stays in `routines.py`.
- The skill ids cannot move out of `macros/skills.py` (plan Task 3.4) before their last user in
  the framework is gone: a re-export from `builds/` would be the framework importing a build.
  3.4 runs after 3.7.
- Kept as today and listed for Stage 5 ("would change with the new design"): a stride asks one
  jump and never falls to the next; the way round a wall is asked by the caller only at zero
  charges; `empty_hop` waits out the blade's delay with a wall in the line; pickup's gold jump
  ignores the delay, failures and walls; the generic build has only `Walk`.
- Until Task 3.9 the framework reaches the build through `macros/default.py` (the one allowed
  `<builds import>` in the ratchet); `pick_up` and `step_toward` take it only at their leaves.
