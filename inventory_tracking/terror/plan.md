# Terror Zone tracker — plan (2026-10-02)

Goal: while farming a Terror Zone, show how close the next Herald is: the tier to spawn, mobs
killed vs total in the Herald group, progress to the tier's breakpoint, and once past it the
chance on the next kill and over the mobs left. Then shade the level map by visited rooms and
seen mobs. Red/green TDD for every step (development.md).

## What the client gives us (probe, 2026-10-02, Black Marsh, Hell, online)

`probe.py` logs (runs/alt-d/<run>/terror-probe.jsonl) answered:

- Monsters are streamed: seen from ~50-85 map units, dropped again at ~47-91 when their rooms
  unload, same unit id when they come back. Whole-level positions are not available.
- The client holds every Room2 of the level (Black Marsh 94); 90 of them got loaded on a clear.
- Kills: alive -> mode 0/12. Allies carry stat 172 `alignment` = 2 (Warlock summons, the
  mercenary): not kills.
- **Herald: stat 367 `heraldtier` (itemstatcost.json) holds the tier** — on the Herald (unit
  470220961, a Returned, Tier 1, 17:00:03) *and on its 6 minions*. Monster data +0x1A tells
  them apart: 0x08 on the Herald, 0x10 on the minions, 0x00 on plain monsters.
- That Tier 1 spawned after ~187 Black Marsh kills: ~94% of the article's 199 mean.
- Monster level stat (12, full list) stays at the area's normal Hell level (69) at character
  level 93, though the user sees 90+ in game; the level struct showed no flag.
- **Terrorized signal (R1, solved 2026-10-02):** every plain monster (data +0x1A == 0) of a Hell
  Terror Zone carries one forced modifier at data +0x20 from desecratedzones.json's
  `always_unique_mod_pool` (5, 6, 7, 9, 17, 18, 25, 27, 28), the same for the whole zone:
  'manahit' 25 in Black Marsh, 'fast' 6 in the Lut Gholein sewers. Outside, plain monsters
  have 0. Sewer monsters first seen after the 17:30 UTC rotation had 0, and the replays give
  Black Marsh yes, Tamoe no, Catacombs (17:10-17:20) no, sewers yes until 17:30:00 then no,
  Ancients' Way yes from 17:32 (the next zone).

## Model (article, terror_zones/diagnostic.py)

Superseded on 2026-10-03 by the game's own formula (Phases, item 6); kept for the record.

- One roll per kill in a Herald group: p = hazard(next tier, completion), completion =
  kills since the last Herald in this group / group population, floored to whole percent
  (the article's cow example matches floor: 358/511 -> 70% -> 1.764%).
- A Herald resets that group's counter; dead monsters stay dead (mobs left = population - all
  kills in the group this game). Tiers advance per game 1 -> 5, then stay at 5.
- Breakpoint = first completion where hazard > 0 (T1 52%, T2/T3 43%, T4 31%, T5 6%).
- Chance over the mobs left = 1 - prod(1 - p_j) over the remaining kills, each at its own
  completion (1 mob at 2% -> 2%; 2 mobs at 1.9% and 2% -> 1 - 0.981 x 0.98 = 3.86%).
- Population: the article's mean per group (flattened, equal level weights); raised to the
  hostile monsters actually seen when that is larger.

## Herald groups (zones.py)

All 74 article groups with their level ids (d2data levels.json) and the d2data Terror Zone
they belong to. Multi-level groups (Catacombs + Cathedral + Inner Cloister, Jail 1-3, ...)
count together. Assumptions: Monastery Gate goes with Tamoe/Outer Cloister, Valley of Snakes
with Lost City, Forgotten Tower with Tower Cellar, Harem 1 with Harem 2 (no group of their
own in the article); each Tal Rasha tomb is its own group at the small-false 124 (which tomb
is real/big varies per game).

## Phases

1. **Text card — done 2026-10-02** (tests/inventory_tracking/terror; replaying the Black
   Marsh logs shows Tier 1 next, 186/199 killed, 3.55% next kill, 38.8% over the 13 left just
   before the Herald, then Tier 2 with its breakpoint out of reach)
   1. zones.py: groups table + lookup by area; tests: every area in at most one group, names
      and populations match article-zones.json, Black Marsh alone, Catacombs group spans 6 areas.
   2. chance.py: breakpoint kills, next-kill chance, chance over the mobs left (floored
      percent); tests incl. the 1-mob / 2-mob examples and the article cow example.
   3. tracker.py: per game: next tier (Herald stat 367 seen -> tier + 1), Heralds seen, per
      group kills since reset / all kills / hostile seen; allies (stat 172 != 0) never count;
      reset on leaving the game. Fed by the probe ledger's events.
   4. card: lines for the current area's group; nothing outside a group or when the gate says
      not terrorized. HUD slot `terror`, producer layer `terror`.
   5. Gate: until R1, show the group with "(unconfirmed)" unless a Herald was seen this game in
      the same Terror Zone (then confirmed); `APPRAISAL.terror_card` turns the card off,
      `terror_card_unconfirmed = False` hides it until a Herald confirms the zone.
   6. Herald minions (stat 367 + minion flag) are neither a spawn nor a kill; a breakpoint that
      needs more kills than mobs left is shown as out of reach (move on).
2. **R1 — terrorized signal — done 2026-10-02**: the tracker keeps the last 6 plain-monster
   sightings per Terror Zone (forced modifier or not) and the majority decides; a Herald marks
   its zone when no plain monster was seen. Unknown (no monster seen yet in the zone) shows
   nothing unless `terror_card_unconfirmed`. Pool is the Hell one; Nightmare TZ unverified.
3. **Map — done 2026-10-02 (except the Herald mark)**: card 338x234 (+30%); rooms shaded from
   the tracker's room marks (every level, also without the Terror card): never loaded
   slightly dimmer (rgb x0.82, alpha x0.8), redder with hostile mobs seen there (up to 50%
   mix at 12). Walkable floor takes its room's tint. Still open: a live Herald mark.
   2026-10-03: the room tint by mobs is replaced by a small dot per hostile monster alive at
   its last seen position (`ZoneTracker.map_dots`, positions followed every pass), so a pack
   shows where it is in a big room (user). Plain mobs and minions (r 2 px), uniques,
   champions and super uniques bright magenta (3.5 px), plain mobs a toned-down red, no rings
   (user: white rings looked bad), Heralds keep their own 5.5 px dot; monster dots
   draw under the level's POIs. Rooms keep only the never-loaded dimming (`visited_rooms`).
   Type flags at monster data +0x1A in the probe logs: 0x08 unique, 0x0c champion, 0x0a super
   unique, 0x4c ghostly champion, 0x10 minion. A monster that walked off unseen keeps its last
   position until it is seen again or dies.
4. **Game data — done 2026-10-02**: `terror_zones/game_files.py` reads the Steam install's
   static container (TVFS manifest, keys that are their own address, BLTE); the extracted
   `terror_zones/data/desecratedzones-game.json` confirms the five tier curves and the
   article's groups, and adds what was missing: five levels belong to no group (Forgotten
   Tower, Valley of Snakes, Harem 1, Duriel's Lair, Worldstone Chamber) and every level has a
   `zone_completion_weight`. zones.py is tested against that file. Group completion is now the
   weighted mean of per-level completion (chance.py); a level's population is the hostile
   monsters seen plus the unexplored share of its part of the article mean (tracker.py).
   Ancients' Way run: 203 seen there vs 58 in Icy Cellar (3.5 : 1, weights 3 : 1). Map card
   390x270.
5. **Herald mark and tombs — done 2026-10-02**: a live Herald (not its minions, not a corpse)
   is a 'herald' dot on the level map (own colour) at its last seen position until it dies,
   and the card points at it ("↗  Herald T1 alive: north"). A Tal Rasha tomb takes its size
   from its Room2 count on entry (>= 60 rooms 390, >= 36 rooms 270, else 124; evidence: Orifice
   tomb 72, Kaa tomb 48, chest tombs 24-28).
6. **Game code (2026-10-03)**: D2R.exe's code is encrypted on disk and decrypted page by page
   as it runs; two read-only memory dumps (character select, then an offline Terror Zone game)
   gave the config parser, the per-kill roll and the hazard (helpers in the git-ignored
   `pricing/raw/re/`). What the code does, per game:
   - Config structs: level entry +0 level id, +4 waypoint, +8 `zone_completion_weight` (float,
     0 if missing), +0xC FNV-1a of `zone_data_id`; Herald tier +0xD0 slope, +0xD4 midpoint,
     +0xD8 asymptote, +0xDC vertical shift; `herald_base_chance_to_spawn` (defaults +0x14,
     absent from the shipped file, so 0).
   - Per level (game + 0x1D0 + id*8, null entries skipped): rooms = +0x14 populated rooms /
     (+0x18 override if > 0, else +0x10 the level's room count; negative -> 0, zero -> 1);
     kills = +0x2DC killed / +0x2D8 hostile monsters spawned so far (0 spawned -> 1, no cap).
     Level completion = rooms x kills. +0x2D8/+0x2DC are the Den of Evil quest's counters;
     the room count skips Room2s with flag 0x800000, and rooms count as populated when they
     first activate.
   - Group completion % = 100 x sum(w x level) / sum(w) over levels with w > 0: the weighted
     mean, as in chance.py, but **not floored**.
   - x = max(0, completion % - completion % stored when this group's last Herald spawned);
     p % = asymptote / (1 + exp(-slope (x - midpoint))) + shift + base chance, clamped 0..100.
     The roll runs in the monster-death handler: the unit's seed gives r in [0, 100), and a
     Herald spawns if p >= r. Then the group stores the completion, and the game's tier becomes
     min(tier + 1, `max_herald_tiers`).
   - The kill counter has no Herald or minion exclusion (only allies via a check and monster
     data +0x30 bit 2). The spawned count goes up when a unit turns hostile and down when it
     turns ally.
   - Differences from our model: our population uses the article mean, while the game
     extrapolates its own density (spawned x rooms / populated rooms); our completion is
     floored and theirs isn't; we skip Herald and minion kills and the game probably counts
     them; and the reset is a subtraction, which is the same as our since-reset counter once
     the level is fully explored.
     Open: whether unvisited levels have an entry (counted at 0 with their weight) or are null
     (left out); the allocator is still encrypted.
   - **Tracker switched 2026-10-03** (chance.py, tracker.py): rooms ever loaded (or the probe's
     `loaded_ever`) stand for populated rooms, hostile monsters seen for spawned, the Room2 count
     for the room total; Herald and minion kills count; a Herald stores its group's completion
     (`ZoneTracker.offsets`); completion isn't floored; each kill rolls after it is counted. A
     level not entered yet counts at 0 with its weight, and its population for the kills ahead
     is its article share. Replay of the 2026-10-02 Black Marsh runs: the Tier 1 Herald came at
     99.5% (186 kills of an extrapolated 187; 179 seen in 90 of 94 rooms).
7. **Later / open**: the 90+ monster level (base stat list logged since 17:30, unanalysed;
   config says level = character + 2 within 70-96); Nightmare Terror Zones;
   guides/terror_zones.html §2/§4 still use flattened populations. Herald and minion kills
   are assumed not to count (user, 2026-10-02). A service started mid-game knows the tier only
   once it sees a Herald (assumes Tier 1).
