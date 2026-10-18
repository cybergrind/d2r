# Terror Zone leveling loop — draft (2026-10-18)

## Goal and boundary

Run terrorized areas in repeated games, maximizing **champion, unique, super unique and Herald leaders killed per wall-clock hour**. Record XP per hour as a separate leveling outcome once the player XP read is verified. Kill nearby ordinary monsters when combat, safety or Herald progress makes that worthwhile, but do not require a white-monster full clear. Complete a known route boss or target chest in any selected area, then take worthwhile drops under the loop's pickup policy.

Two sources of terrorization share the same area runner:

1. **Current active TZ:** upon entering each game, identify the current terrorized levels **and the TZ effect** (for example, Extra Fast or Extra Strong) before choosing a route. Recheck both at level changes and before another game. A change of active zone invalidates the next route choice, not the fight already under way.
2. **Worldstone Shard:** use a chosen shard to terrorize its act, verify the actual terrorized level list after use, and run either all eligible zones in that act or an ordered set selected by the player. The five shard-to-act mappings are in `guides/worldstone-shards.html`; the *use action, duration and per-game persistence* need played evidence before automation.

The loop is separate from the KP_6 Lower Kurast loop. It must not inherit LK's chests-first rush, its fixed waypoint path, or its game-exit criteria. Keep the existing single-run/cancellation and player-intervention behavior.

## Existing pieces and the gaps

| Concern | Reusable today | Needed for this loop |
| --- | --- | --- |
| TZ detection | `terror/monsters.py` reads the client's terrorized level list; `ZoneTracker.terrorized` reconciles it with monster evidence; town rotation and location names were player-confirmed on 2026-10-18 | Expose a fresh, game-scoped list to the loop, including an unread/stale state and source of evidence |
| TZ effect | `terror/monsters.py` now reads the low-byte modifier ID from each TZ service entry; a 2026-10-18 town game confirmed ID 18 is Cold Enchanted; `make serve` logs decoded and raw values | Confirm other effects and rotation behavior, then expose a fresh game-scoped value to the route planner; report `unknown` if the read fails |
| Elites and Heralds | `terror/tracker.py` remembers leaders, kills, dangerous packs, Heralds and explored rooms; `terror/shards.py` logs `elite_kill` | A target queue and reliable per-game/per-area leader counts, distinguishing seen, killed, lost and unreachable |
| Level movement | `routes/progress.py`, `levels/routes.md`, waypoints, doors and KP_1 pursuit cover many route stages | Plan entrance and exit between *selected* TZ levels; audit missing route marks, locked waypoints and area transitions before enabling each route |
| Clearing | KP_1 defaults to full clear in a TZ: sighted and remembered monsters, then unexplored rooms, then route stages | An **elite hunt** mode: visit promising unexplored rooms, take nearby leaders, avoid long backtracks for isolated white monsters, then do the area's boss/chest stage |
| Repetition | LK `loop.py` has game creation, prebuff, supplies, pickup, portal, stash and Save and Exit | A separate coordinator with a chosen zone itinerary, progress across areas, refresh/new-game policy and its own HUD and stop reasons |
| Measurement | Combat takes and `d2-loop-watch/tools/tz.py` report kills/minute in a level; shard watch reports elite kills | End-to-end wall-clock totals, elite/champion/Herald counts, travel/town/loot time, XP delta, boss/chest completion and shard consumption |

## Proposed run contract

**Configuration.** Source `active` or `shard`; for shard, shard type/act and itinerary `all` or an explicit ordered area/zone list. Each itinerary entry carries an entry waypoint/route, any target boss or chest, and an exit. Configuration also sets pickup policy, a minimum supply reserve, maximum games/time, and whether to finish the current area when the active TZ changes. Start with explicit itinerary selection; automatic ranking can follow measured runs.

**Per game.** Read the character and difficulty, then determine and display the current TZ and its effect (Extra Fast, Extra Strong, etc.) before route selection; prebuff and restock. In shard mode verify possession of the requested shard, use exactly one through a guarded action, and confirm both inventory change and the resulting TZ list **and effect**. Select the next eligible itinerary entry. Travel to its entrance, run its area(s), take desired drops, then continue the itinerary or reset the game. A failed verification stops with a specific reason; it never silently spends another shard.

**Per area.** Confirm the area is terrorized. Track observed leader packs and unexplored rooms. Prefer a reachable leader or Herald, then the room with the best expected leaders per travel second; fight ordinary monsters along the way when they block travel, threaten the character, or cheaply advance Herald progress. Handle a Herald omen and live Herald with the existing combat safety. After the hunt's stopping rule, finish the area's known boss or chest target and its loot. Mark the area done only from observed progress, not from a timer alone.

**Stop or move on.** Leave an area when no reachable leader remains and the remaining unexplored rooms have low expected return, or when its time/failed-path cap is reached. Choose the next selected TZ area if its expected kills per minute exceed repeating the current game; otherwise reset. In active mode, do not enter a newly non-terrorized area. In shard mode, never use a second shard without a new game and an explicit policy for doing so. The player can toggle the loop off immediately; manual input pauses it as existing runs do.

## Work packages

1. **Evidence and route inventory.** List every TZ group and level from `terror/zones.py`; map entry waypoint, transition, boss/chest target and exit; mark routes as ready, needs a played check, or unavailable. Check the client's active-list freshness across a schedule change and a new game. The client service's low-byte modifier ID was found statically and confirmed in town for Cold Enchanted on 2026-10-18; `make serve` now logs it with the TZ name and raw word. Verify other effects and rotation behavior before using it for routing. Observe shard use by hand: UI action, item decrement, affected areas, effect, duration and what persists after Save and Exit. Do not automate consumption until those observations are recorded.
2. **Pure itinerary planner.** Given the source, actual terrorized level list, route capabilities and per-game progress, return the next area or a reason to reset/stop. Support `all` and designated subsets, exclusions, inaccessible areas and active-zone changes. Never route to an area merely because it belongs to the same named TZ group; require observed terrorization.
3. **Elite hunt policy.** Add a run mode distinct from goal and full clear. Rank known leaders, Heralds, unexplored rooms and route targets by expected kills/XP over travel and fight time. Set bounded backtracking, failed-target and stale-sighting rules. Keep boss/chest completion as an explicit goal. Verify that the policy does not sacrifice nearby champions while chasing a distant boss.
4. **Coordinator and shard action.** Compose existing game, waypoint, portal, town, pickup and combat steps under a new loop request/key/HUD. Implement a guarded shard action only after work package 1 proves its semantics. Persist enough game identity and progress to resume safely after a service restart, without double using a shard or repeating a target indefinitely.
5. **Measurement and tuning.** Log per-area and per-game leader kills by kind, XP delta, wall time including lobby/town/travel/loot, deaths, potions, bosses/chests, Heralds, shard spent and stops. Compare against manual TZ runs and the current KP_1 full clear on the same zones. Change one routing or combat parameter at a time, keeping it only when the wall-clock objective improves without worse survival.

## First playable slice

Start with **one user-selected active TZ route, one game, no shard use**, using the existing waypoint/route and pickup steps. Add the elite hunt policy and end-to-end counters. Confirm every transition and the boss/chest in play. Then add repeated games, multiple active zones and schedule changes. Shard mode follows the evidence check and uses the same area runner.

## Acceptance checks

- On entering each game the loop identifies and reports the current TZ and its effect before choosing a route; it never reuses an effect from the prior game. The loop enters only areas confirmed terrorized, and reports the evidence and source mode on the HUD/log.
- It kills and counts champions, unique packs, super uniques and Heralds once each; an unread or despawned monster does not count as a kill.
- A selected area's known boss/chest is attempted and its outcome recorded before the area is complete.
- `all` visits each eligible selected shard-act zone once per game; designated mode visits only its configured entries. Unreachable entries get a named skip/stop, not a spin.
- A shard is consumed at most once per intended game, only when available, and the resulting TZ list is verified before movement.
- Cancellation, death, dangerous combat, low supplies, full inventory with a valuable and manual intervention have explicit behavior and stop reasons.
- The report gives elites/hour and XP/hour over **total elapsed time**, with a breakdown that reveals travel, combat, town and loot costs.

## Decisions to settle with the player

1. When the active TZ rotates mid-run, finish the current area (proposed default) or leave immediately?
2. In shard mode, does `all` mean every terrorized level in the act, or every selected zone group with its component levels? The draft treats it as every *eligible itinerary area* and makes the list visible before starting.
3. What is the default boss/chest rule when the target is a long detour? The draft always completes a route target explicitly attached to a selected area; optional targets can later have a time budget.
4. Is the optimization target strictly leader kills/hour, or should measured XP/hour eventually override it when the two disagree? The draft records both and optimizes leader kills/hour first.
