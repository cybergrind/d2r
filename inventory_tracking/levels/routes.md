# Farming routes for the teleport step: plan

Drafted 2026-10-12; architecture and tests added the same day after the user's review. Status:
**Phases 1 and 2 built 2026-10-12 (not run in game); phases 3–6 not started**. Companion to [plan.md](plan.md) (the level guide) and
[../macros/plan.md](../macros/plan.md) (the macro actions).

## Goal

Encode **repeatable farming routes**. A route starts at a waypoint, runs through its levels to the
thing it is for, and ends by leaving the game for the next one. Every level has a script, so in any
level the tooling knows where the character is going next and where the route ends.

Three examples the design must carry (user, 2026-10-12):

- Black Marsh → Forgotten Tower → Tower Cellar 1–5 → kill the Countess → leave and repeat.
- Cold Plains → Cave 1 → Cave 2 (the super chest).
- Durance 2 → Durance 3 → Blade Warp to a spot by the red portal (this raises the bridge, the way
  out after the fight) → Death Mark on Mephisto so the demons hold him → Sigil: Lethargy → kill →
  pick up → through the portal → leave and repeat.

## Decisions (user, 2026-10-12)

1. Routes are linear and end by leaving the game. Nothing walks back out of a dead end: a level with
   two side levels (Black Marsh: the Tower and the Hole) has one main route and the other is a route
   of its own.
2. Cold Plains goes to the Cave. The Burial Grounds are a separate route.
3. Mephisto is the sequence above, not a single mark.
4. Seals: west, north, east, then the star. The step clicks the seal; the fights are attack mode's.
5. A structured design with tests at every layer, written before the code they cover.

## Architecture

Four layers. Each depends only on the ones above it in this list, and each is tested alone.

| Layer | Package | Holds | Knows nothing of |
| --- | --- | --- | --- |
| 1. Facts | `levels/` | Where things are: the preset table, warp tiles, and a new table of object spots per preset layout, built from the install like `terror/data/elites.json`. Handlers turn a level's rooms into named marks | order, progress, input |
| 2. Catalogue | `routes/catalog/` | What a route is: plain data, one file per act. A route is a chain of level scripts; a level script is an ordered list of stages, each naming a handler mark by its label | memory reading, input |
| 3. Progress | `routes/progress.py` | What is done in this game: levels entered, objects used, bosses dead. One pure function gives the current stage of a level from the script and those facts | how facts are read, input |
| 4. Execution | `macros/route.py` | One press performs the current stage with the routines that exist: the teleport step, the object click, attack mode, the pickup request, the macro request | — |

The level card and the step both ask layer 3 for the current stage, so the arrow on the HUD and the
hop never disagree.

### Stages

| Stage | A press does | Done when |
| --- | --- | --- |
| `enter(mark, to)` | a hop toward the door, gap or border, then the walk in | level `to` was entered this game |
| `use(mark)` | a hop toward the object, then the click | the object shows as used (chest open, seal active); for a portal, the level changed |
| `stand(mark, by=…)` | a move onto the spot, with the named skill when one is given (Blade Warp by the portal) | the character has stood within reach of it this game |
| `fight(boss, opener=…)` | the opener casts once (Death Mark, Sigil: Lethargy), then attack mode on | the boss is dead |
| `clear()` | the seek step: the nearest elite, else the next unexplored room | no elite is known and no room is unexplored |
| `loot()` | the pickup request | nothing valuable is left on the ground in reach |
| `leave()` | the macro request (save, exit, next game) | — (the game ends) |

`enter`, `use` and `stand` reuse the teleport step as it is today. `fight`, `clear`, `loot` and `leave` call
the routines behind the existing keys; those keys keep working on their own.

One press performs one stage step, as the teleport step does now. Whether a route may also run on
its own from one press is left open; nothing in the layers depends on the answer.

### The catalogue

`routes/catalog/act1.py` … `act5.py`. A stage names a mark by the label the level's handler gives it
and the level it leads to by number:

```python
Route(
    'Countess',
    (6,),  # may start at Black Marsh
    (
        level(6, enter('Forgotten Tower', 20)),
        level(20, enter('Tower Cellar 1', 21)),
        *(level(area, enter('Next level', area + 1)) for area in (21, 22, 23, 24)),
        level(25, fight('The Countess', 'Countess'), loot(), leave()),
    ),
)
```

Every level has one **main** script. Another route's way through the same level (the Hole from Black
Marsh, the Burial Grounds from Cold Plains) is a script marked `alternate`; choosing an alternate is
a later step and not needed for the main routes. A stage that cannot be acted on yet carries
`pending` with the reason; the check refuses a pending stage whose mark has come to exist.

### What the layers add to the code

| Layer | New | Changed |
| --- | --- | --- |
| Facts | `levels/build_objects.py`, `levels/data/objects.json`, `levels/objects.py`; `PoiSpec.thing` (a mark on an object the files place, by layout variant, with its click) | handlers for one-preset levels (Pit 2, Drifter Cavern…); object ids in `levels/model.py` |
| Catalogue | `routes/model.py` (Route, Level, the stage types), `routes/catalog/act1.py`…`act5.py`, `routes/check.py` (the validation below), `python -m inventory_tracking.routes` (prints the table) | — |
| Progress | `routes/progress.py` | `levels/guide.py` takes the current stage's mark as the card's first mark (injected, so `levels` does not import `routes`) |
| Execution | `macros/route.py`; `USES` entries for the chest, the seals and the portals | `macros/runner.py` routes the teleport key through it; `game/` reads the new object ids |

## Tests

Written first in every phase (red/green, `development.md`). All offline; in-game runs come last.

| # | What is tested | How | Guards against |
| --- | --- | --- | --- |
| T1 | Object table | Built from the install; pinned against the spots read by hand on 2026-10-12 (the chest table below, the seals, the red portal); a unit test of the builder on a small DS1 | a wrong spot or object id |
| T2 | **Catalogue is complete** | Generated from levels.txt: every level that is not a town has a script, or is in a short list of exemptions each with a reason | a level with no known destination |
| T3 | **Every route ends** | From every level, following its `enter` and portal `use` stages reaches a `leave()` with no loop; each step goes to a level that levels.txt links to it, or through a named portal | a route that stops halfway or circles |
| T4 | Stages name real marks | Every stage's mark label is one the level's handler declares; every `use` names an object the click table knows; every `fight` names a boss the elite table places in that level | a typo, a mark the step cannot act on |
| T5 | Marks resolve | For every handler: its patterns match a preset of that level; a mark on an object has a spot for **every** layout variant of every preset it matches (the existing generated handler tests, extended) | a layout the table does not cover |
| T6 | Progress | Table tests of the pure function: facts in, current stage out; a new game forgets; a stage done out of order stays done | skipped or repeated stages |
| T7 | Execution, per stage | With the fake game (`tests/…/macros/fakes.py`): each stage kind does its one action, says what it does, and stops with a reason when it cannot | a press that does nothing silently |
| T8 | **Whole routes** | The fake game given a chain of levels built from levels.txt rooms (as the Chaos Sanctuary and Throne tests build theirs) and from real evidence fixtures where they exist; the key is pressed until `leave()`, within a bound on presses; run for every main route | routes that work stage by stage and fail as a whole |
| T9 | In game | Each route run once by the user; the evidence the guide saves becomes a fixture for T8; only then is the route `confirmed` | everything the fakes assume |

The route tables further down are generated from the catalogue
(`python -m inventory_tracking.routes --write`), and a test keeps this file equal to that output.

## Phases

Each phase lists its tests first and ends with the suite green and the named routes run in game.
In the third column of the Phase 3 row, "to the last level's door" means the chest click is Phase 4.

| Phase | Builds | Tests | Routes that work after it |
| --- | --- | --- | --- |
| 1. Facts | The object table and `PoiSpec.thing`; handlers for the one-preset levels in the chest table | T1, T5 | none yet (marks appear on the HUD card) |
| 2. Catalogue | The model and a script for **every** level; missing marks are declared `pending` with a reason and counted | T2, T3, T4 | none yet; the table shows every level's destination |
| 3. Progress and `enter` | Progress, the card's first mark from it, `enter` through the step | T6, T7, T8 for chains of doors | Glacial Trail → Drifter Cavern, Crystalline Passage → Frozen River, Ancients' Way → Icy Cellar, Cold Plains → Cave 2, Outer Cloister… → Pit 2, Dark Wood → Underground Passage 2 (to the last level's door) |
| 4. `use` | Chest, seal and portal clicks | T7, T8 | all super chest routes; Chaos Sanctuary through the five seals to the star |
| 5. `fight`, `loot`, `leave` | The boss signal, the opener, the hand-over to attack mode, pickup and the macro request | T7, T8 | Countess end to end; then Mephisto with `stand`; Andariel, Nihlathak, the council, Baal |
| 6. The rest | Levels still `pending` (Monastery Gate, Forgotten Tower, Palace Cellars, Kurast temples and sewers, the hell-pit portals, the jungle clearings); alternate routes | T2's pending count reaches zero | every zone |

## Status

**Phase 1, 2026-10-12.** Built and tested offline; nothing of it has been seen in the game.
- `levels/build_objects.py` → `levels/data/preset_objects.json`: 63 presets, 107 objects of the 21
  kinds in `levels/model.py` `MARKABLE`; `presets.object_spots` reads it.
- `PoiSpec.thing`: the mark sits on the object the room's layout places. A room whose layout is not
  read yet keeps the room mark; a whole-level preset with no layout read is a logged problem. The
  layout is taken from whichever chunk of the preset has read it.
- New handlers (`handlers/treasure_levels.py`): Cave 2, Underground Passage 2, Hole 2, Pit 2, Swampy
  Pit 3, Flayer Dungeon 3, Kurast Sewers 2, Frozen River, Drifter Cavern, Icy Cellar, and the three
  hell pits (every dead end holding a chest). The chest marks of the Mausoleum, the Ancient Tunnels,
  the Arachnid Lair, the Spider Cavern and Kurast Sewers 1 moved from the room centre onto the chest.
- Tests: T1 (builder on a made-up DS1; 16 spots pinned to the hand-read ones) and T5 (validation:
  an object mark has one spot in every layout of every preset it matches).
- Not in this phase: the click. The step hops to these marks and stops there (`use` comes in Phase 4).
- To see in game: the card in any of these levels shows the mark on the chest. The six Ice Pool
  layouts and the six Dungeon Treasure ones each need one sighting.

**Phase 2, 2026-10-12.** Built and tested offline; no behaviour in game changes yet.
- `routes/model.py` (Route, Script, the seven stage kinds), `routes/catalog/act1.py`–`act5.py`
  (52 routes), `routes/links.py` (waypoint levels; outdoor levels joined without a door),
  `routes/check.py`, `routes/table.py` and `python -m inventory_tracking.routes`.
- Every level has a main script or an exemption: the five towns, Duriel's Lair, the Pandemonium
  levels and the Colossal Summit. From every level the main scripts lead to `leave`.
- Marks added for the routes (facts layer): the red portal on Durance of Hate 3, the five seals in
  the Chaos Sanctuary (after Diablo's star, so the first mark is unchanged), the Worldstone Chamber
  portal in the Throne. `Handler.labels()` says which marks a level can give.
- Tests: T2, T3, T4 on the real catalogue; the check itself on catalogues made wrong one fault at a
  time; the tables of this file against the catalogue.
- Ten stages are `pending` (the last table above): four levels without a mark (Catacombs 4, Claw
  Viper Temple 2, the Worldstone Chamber, the Ruined Temple), the council's place in Travincal, the
  Arcane portal, Lower Kurast's chests, and the three hell-pit portals.
- Changed from the draft: `clear` is a stage (levels farmed for their monsters: the Cow Level, the
  Great Marsh, the false tombs, the plain temples); a border crossing is an `enter` like a door,
  because the step already treats both by the mark it follows.

**Phase 3, 2026-10-12.** Built and tested offline; not run in the game yet.
- `routes/progress.py`: `current(script, facts)` (pure) and `Progress`, which the service tells the
  game and the level about once a second (`MacroRunner.noted`, beside the journey). The one fact so
  far is the levels entered: a way on is done once its level was entered; a new game forgets.
- `levels/guide.py` `lead_first`: the card puts the mark of the level's stage first (`LevelGuide.lead`,
  given by the service, so `levels` does not import `routes`). It is asked at every card and every
  target, so the arrow and the step agree. A way back that a route goes through is shown as a way on.
- `macros/route.py` `card`: the teleport key goes through it. It logs the route and stage; when the
  stage's mark is not on the card yet it says so on the HUD and follows the card's own first mark.
- Only `enter` is performed (`route.PERFORMED`). At a stage of any other kind the card keeps its
  handler's order and the press is the plain step, as before. A stage that is not judged yet (a
  fight, a chest, loot) holds its script: Cave 1 waits at Coldcrow, so its door is first only
  because the handler already puts it first. The same holds for Kurast Sewers 1 and Travincal; the
  Burial Grounds keep leading with the Graveyard.
- What changes in game, from the cards of the level dumps: Cold Plains leads with the Cave (was
  Stony Field), Dark Wood with the Underground Passage (was Black Marsh), the Outer Cloister with
  the Monastery Gate once its border is read (was the Barracks). The other 27 dumps keep their
  first mark.
- Tests: T6 (`tests/…/routes/test_progress.py`, with the lead checked on all 30 level dumps), T7
  and T8 for chains of doors (`tests/…/macros/test_route.py`: the key pressed in made-up levels
  from every level that has a door to take, until none leads on; seven chains pinned).
- Changed from the draft: an `enter` whose mark is missing does not stop the press. The card may
  lack it for a while (a border not read, a gap not named), and stopping would take the key from a
  level where it works today.
- Not in this phase: a border has no door to click, so the step stops beside the border mark as it
  does today and the crossing is made by hand (Outer Cloister → Monastery Gate → Tamoe Highland);
  choosing an alternate script (the Barracks from the Outer Cloister, the Burial Grounds from the
  Cold Plains, the Hole from Black Marsh).
- To run in game (T9): Glacial Trail → Drifter Cavern, Crystalline Passage → Frozen River, Ancients'
  Way → Icy Cellar, Cold Plains → Cave 2, Dark Wood → Underground Passage 2, Black Marsh → Tower
  Cellar 5, Tamoe Highland → Pit 2.

**Phase 4, 2026-10-12.** Built and tested offline; no click of it has been seen in the game.
- Facts: a mark on a placed object the step clicks carries it (`Poi.use`, `levels/model.py` `CLICKED`):
  the super chest (397), the five seals, the Durance's red portal (342). The Throne's portal (563)
  is left a place: objects.txt gives it no click box.
- Click: `macros/teleport.py` `USES` has entries for them, so the existing object click does the
  work (hop to the mark, click the picture with the object under the pointer, wait for its mode to
  change or the level to). The chest uses the aims that opened two chests on the host; the seals
  use the same aims as a first guess; the red portal its objects.txt box. `world.USED` reads them.
- Progress: `Progress.used` records an object seen operated; a `use` is done once every mark with
  its label was (a hell pit's chests). `Lead.skip` makes the card pass the used ones, and
  `guide.marks(label)` tells the step how many there are. `route.note_used` runs after each step:
  it also notes an object found already open (the pickup key's chest).
- A stage that is neither judged nor performed (a fight, loot) is passed for a later object of the
  same level, never for a way out. So the seals are led with in order past the seal bosses, and
  the red portal is not led with while Mephisto is not judged dead.
- A `pending` stage is not led with and says nothing.
- What changes in game: in the chest levels the press at the mark clicks the chest (also without a
  route: the mark itself carries the object). The Chaos Sanctuary leads with Vizier seal 1, 2, De
  Seis, Infector 1, 2 and then with Diablo's star (was the star from the start). Kurast Sewers 1
  leads with the chest, then the way to level 2. The Icy Cellar leads with the chest.
- Tests: T7 and T8 for objects (`tests/…/macros/test_route.py`: one chest, three chests under one
  label, seals in script order with the card listing them otherwise, an object found open), the
  clicks themselves (`test_teleport.py`), progress and the lead's skip.
- Not seen in game, in the order to try: a super chest by KP_4 (Drifter Cavern), the seals (aims and
  that a seal's mode changes when it is opened), the red portal after Mephisto (reached only with
  Phase 5, or by hand as the first mark is Mephisto).
- Not in this phase: the Throne's portal, the Arcane portal, the hell-pit portals and Lower Kurast's
  chests (still pending); Khalim's chests and the Horadric chests are marks only.

**Phase 5, 2026-10-12.** Built and tested offline; not run in the game.
- The boss signal: `terror/tracker.py` `killed()` names the super uniques (by their superuniques.txt
  row) and the bosses (`SLAIN_BOSSES`: terror/bosses.py's ids and Blood Raven) that died this game.
  The service gives it to `Progress`; without the monster tracker a fight is not performed and
  the card keeps its own order there. A test holds that every boss a route fights has such a name.
- Progress judges `fight` (the boss is dead), `stand` (the character stood within 12 units of the
  mark) and `loot` (a press found nothing left to pick up). `leave` is never done; `clear` is not
  performed (the seek key).
- `macros/route.py` `press` is the teleport key now (the runner gives it the plain step, attack
  mode and the way out):
  - `fight`: the step toward the fight's mark, attack mode on within 40 units of it; a fight with
    no mark (the seal bosses, Lister) is attack mode from where the character stands.
  - `loot`: the pickup step. With nothing left it goes on to the next stage in the same press,
    except before `leave`: it says "the next press leaves the game" and stops.
  - `leave`: anything on the ground is picked up first; else the game is left, the next made and
    the buffs cast (`route.leave`, the macro request's own steps).
  - `stand`: the step to the mark.
- Changed from the draft: the `opener` is not cast by the stage. Attack mode already casts Death
  Mark on the strongest monster and Sigil: Lethargy under an elite (macros/rotation.py). `by` (Blade
  Warp for Mephisto's stand) is not enforced either: the step picks Teleport or Blade Warp by the
  staff's charges, as everywhere.
- What changes in game: the Chaos Sanctuary now waits at each seal boss (attack mode) before the
  next arm's seal. Cave 1 leads with Coldcrow, then the loot, then the door. A level whose script
  ends in `leave` (the Countess, the chest levels, Nihlathak) leaves the game by the key once the
  boss is dead or the chest open and the ground clean. After the red portal the character is in
  town, which has no script: the macro request (Win+X) leaves from there.
- Tests: T6 for the new facts, T7 per stage and T8 for the Countess run from Black Marsh to the
  next game and for Mephisto's level (`tests/…/macros/test_route.py`), the tracker's names.
- To run in game (T9), in this order: the Countess end to end; a chest level to `leave`; Mephisto;
  the Chaos Sanctuary (whether each seal boss's death is seen); Nihlathak.
- Not built: Andariel, Fangskin, Sarina, the council and Baal have no mark (pending): there the
  key is the plain step, and their death still moves the script on to loot and leave.

**Phase 6, 2026-10-12.** Built and tested offline; not run in the game.
- Marks for six pending stages, from the game's files (`handlers/boss_lairs.py`, unconfirmed):
  Andariel at (46, 46) of Andy3.ds1 and Baal at (135, 160) of wstone01.ds1 (read with
  `ds1.monster_presets`), Fangskin and Battlemaid Sarina from the elite table, the council in
  Travincal (Ismail Vilehand's place, after the Durance mark), and the Arcane portal in Palace
  Cellar 3 (the 'Basement SE' room of file 3, clicked like the other portals: `USES`).
  `registry.unplaced` now respects `PoiSpec.variants`. Pending went from 10 to 4.
- Borders (`route.cross`): with the card leading with an `enter` mark that is no door, and the
  character in a room that touches the next level, the press clicks the ground 16 units further
  out, three times, until the level changes. The direction is from the middle of the level to the
  middle of its rooms touching that level, along the nearer axis. A room whose preset holds a warp
  tile in any layout is never walked past.
- Alternates (`Progress.chosen`): a level follows its main script unless none of the levels that
  route goes on to is terrorized and those of another route through the level are
  (`ZoneTracker.terrorized`). So the Outer Cloister leads to the Barracks with the Jail terrorized,
  the Cold Plains to the Burial Grounds, Black Marsh to the Hole.
- Tests: the new marks (`tests/…/handlers/test_boss_lairs.py`), the walk across and its two
  refusals, the choice of script by Terror Zone.
- Still pending (4): the three hell-pit portals (objects the files do not place: one memory read
  each in game) and Lower Kurast's chests (the files place none of class 397 in the camp; the pickup
  key opens them there today). The Throne's portal stays a place without a click.
- 2026-10-15: Lower Kurast's chests are marked (routes/lower-kurast-plan.md). The camp's file places three
  `PlaceUniqueChest` spots, a chest whose class the game rolls (181 or 183 in every level dump), marked by the
  pseudo id `UNIQUE_CHEST` (levels/model.py) and clicked as any of its classes (`Use.kinds`).
- To run in game: Outer Cloister → Tamoe Highland on foot over both borders; a terrorized Jail from
  the Outer Cloister waypoint; Andariel, the council and Baal with the key.

## Open points

- **Mephisto's bridge.** The files place the bridge object (341) at (99, 70) and the portal (342) at
  (102, 69). That standing by the portal raises the bridge is the user's observation; the `stand`
  stage is done on arrival and does not check the bridge. To confirm in the first run.
- **The hell-pit portals** (Abaddon, Pit of Acheron, Infernal Pit) are not in the files: one memory
  read of each in game gives the object id.
- **Jungle clearings**: which holds which cave is unknown (plan.md).
- **Border crossings** are built but unseen in game: the direction is a guess from the rooms, and a
  monster under the pointer would take the click.
- **Alternate scripts** are chosen by Terror Zone only; there is no key to choose one by hand.
- **Auto-run** (one press runs the route to its end) is undecided, and not needed for any phase.

## Objects (installed game files and d2data objects.txt, read 2026-10-12)

| Object | objects.txt id | Where the files place it |
| --- | --- | --- |
| Super chest ("sparkly chest", class ConsolationChest) | 397 | one fixed spot per layout variant of each preset named below |
| Chaos Sanctuary seals (DiabloSeal1–5) | 392–396 | arm E: 392 and 393; arm N: 394; arm W: 395 and 396; two layouts per arm |
| Red portal to act 4 (HellGate) | 342 | Durance 3 at (102, 69) units from the preset origin, on the bridge |
| Portal to the Worldstone Chamber (FinalPortal) | 563 | Throne of Destruction at (90, 5) |
| Kurast sewer lever / stairs | 367 / 366 | 'Act 3 - Sewer Drain' rooms, Sewers 1 |
| Arcane Sanctuary portal | 298 | Palace Cellar 3 (spot not read yet) |
| Horadric Cube / Scroll / Staff chests | 354 / 355 / 356 | Halls of the Dead 3, Radament's Lair, Coldworm's room |
| Khalim's Eye / Heart / Brain chests | 407 / 405 / 406 | Spider Cavern, Kurast Sewers 2, Flayer Dungeon 3 |
| Frozen Anya (DrehyaOutsideTown) | 460 | Frozen River, four layouts |

Not found in the files, so they are runtime objects to read from memory once: the red portals to
Abaddon, the Pit of Acheron and the Infernal Pit (their 'Barricade Hell Portal' presets place no
object).

The super chest's spots, in units from the preset origin:

| Level | Preset | Spots by layout variant |
| --- | --- | --- |
| Cave 2 (13) | Act 1 - Cave Treasure 2 | (112, 22) |
| Underground Passage 2 (14) | Cave Treasure 3 | (23, 38) |
| Hole 2 (15) | Cave Treasure 4 | (32, 103) |
| Pit 2 (16) | Cave Treasure 5 | (110, 59) |
| Mausoleum (19) | Act 1 - Crypt Chest N/S/E/W | W (21, 11), E (20, 11), S (11, 20), N (11, 20) |
| Ancient Tunnels (65) | Act 2 - Sewer Chest N/S/E/W | W (29, 11), E (21, 35), S (12, 19), N (11, 39) |
| Arachnid Lair (84) | Act 3 - Spider Chest NE | (5, 58), (5, 64), (34, 68) |
| Swampy Pit 3 (90) | Act 3 - Dungeon Treasure 1 | (38, 58), (145, 90), (20, 175), (20, 175), (38, 58), (50, 106) |
| Kurast Sewers 1 (92) | Act 3 - Sewer Chest N/S/E/W | W (41, 33), E (28, 32), S (33, 18), N (33, 38) |
| Lower Kurast (79) | Act 3 - Slums 16x16, variant 1 only (`PlaceUniqueChest`, class rolled) | (27, 52), (12, 57), (60, 12); one or two camps a level |
| Drifter Cavern (116), Icy Cellar (119) | Act 5 - Ice Pool A/B | (143, 119), (133, 7), (135, 7), (133, 7), (21, 21), (10, 135) |
| Abaddon, Pit of Acheron, Infernal Pit (125–127) | Act 5 - Lava N/S/E/W, variant 1 only | N (20, 99), S (54, 54), E (65, 100), W (55, 49); a level may hold several |

Frozen River has no super chest: its target is Anya's spot (Frozenstein stands by her).

## Routes

Generated from the catalogue (`routes/catalog/`); a test keeps this section equal to it. Zones are
the installed game's (`terror/zones.py`): a route covers the levels terrorized together where they
lie on one line, and a second side level of a zone is a route of its own.

<!-- routes:begin (generated: python -m inventory_tracking.routes --write) -->
Each row is one route: where it may start, then each level with its stages in order. A level in
*italics* is passed through by this route while its own main script goes elsewhere.

### Act 1

| Route | Start | Levels and stages |
| --- | --- | --- |
| Den of Evil | Rogue Encampment | *Rogue Encampment*: enter Blood Moor<br>Blood Moor: enter Den of Evil<br>Den of Evil: fight Corpsefire → loot → leave |
| Cave | Cold Plains | Cold Plains: enter Cave<br>Cave 1: fight Coldcrow → loot → enter Next level<br>Cave 2: use Super chest → loot → leave |
| Mausoleum | Cold Plains | *Cold Plains*: enter Burial Grounds<br>Burial Grounds: fight Blood Raven → loot → enter Mausoleum<br>Mausoleum: use Chest → loot → leave |
| Crypt | Cold Plains | *Cold Plains*: enter Burial Grounds<br>*Burial Grounds*: enter Crypt<br>Crypt: fight Bonebreaker → loot → leave |
| Tristram | Stony Field | Stony Field: use Tristram<br>Tristram: use Wirt's body → loot → leave |
| Underground Passage | Dark Wood | Dark Wood: enter Underground Passage<br>Underground Passage 1: enter Level 2<br>Underground Passage 2: use Super chest → loot → leave |
| Countess | Black Marsh | Black Marsh: enter Forgotten Tower<br>Forgotten Tower: enter Tower Cellar 1<br>Tower Cellar 1: enter Next level<br>Tower Cellar 2: enter Next level<br>Tower Cellar 3: enter Next level<br>Tower Cellar 4: enter Next level<br>Tower Cellar 5: fight The Countess → loot → leave |
| Hole | Black Marsh | *Black Marsh*: enter Hole 1<br>Hole 1: enter Next level<br>Hole 2: use Super chest → loot → leave |
| Pit | Outer Cloister | Outer Cloister: enter Monastery Gate<br>Monastery Gate: enter Tamoe Highland<br>Tamoe Highland: enter Pit<br>Pit 1: enter Next level<br>Pit 2: use Super chest → loot → leave |
| Andariel | Outer Cloister, Jail 1, Inner Cloister, Catacombs 2 | *Outer Cloister*: enter Barracks<br>Barracks: enter Next level<br>Jail 1: enter Next level<br>Jail 2: enter Next level<br>Jail 3: enter Inner Cloister<br>Inner Cloister: enter Cathedral<br>Cathedral: enter Catacombs 1<br>Catacombs 1: enter Next level<br>Catacombs 2: enter Next level<br>Catacombs 3: enter Next level<br>Catacombs 4: fight Andariel → loot → leave |
| Cow Level | Rogue Encampment | Moo Moo Farm: clear → loot → leave |

### Act 2

| Route | Start | Levels and stages |
| --- | --- | --- |
| Radament | Lut Gholein, Sewers 2 | Sewers 1: enter Next level<br>Sewers 2: enter Next level<br>Sewers 3: fight Radament → loot → leave |
| Stony Tomb | Lut Gholein | *Lut Gholein*: enter Rocky Waste<br>Rocky Waste: enter Stony Tomb<br>Stony Tomb 1: enter Next level<br>Stony Tomb 2: fight Creeping Feature → loot → leave |
| Halls of the Dead | Dry Hills, Halls of the Dead 2 | Dry Hills: enter Halls of the Dead<br>Halls of the Dead 1: enter Next level<br>Halls of the Dead 2: enter Next level<br>Halls of the Dead 3: fight Bloodwitch the Wild → loot → leave |
| Maggot Lair | Far Oasis | Far Oasis: enter Maggot Lair<br>Maggot Lair 1: enter Next level<br>Maggot Lair 2: enter Next level<br>Maggot Lair 3: fight Coldworm the Burrower → loot → leave |
| Ancient Tunnels | Lost City | Lost City: enter Ancient Tunnels<br>Ancient Tunnels: use Chest → loot → leave |
| Claw Viper Temple | Lost City | *Lost City*: enter Valley of Snakes<br>Valley of Snakes: enter Claw Viper Temple<br>Claw Viper Temple 1: enter Next level<br>Claw Viper Temple 2: fight Fangskin → loot → leave |
| Tal Rasha's Tombs | Canyon of the Magi | Canyon of the Magi: tour Tomb → loot → leave<br>Tal Rasha's Tomb: use Orifice → back to Canyon of the Magi<br>Tal Rasha's Tomb: use Orifice → back to Canyon of the Magi<br>Tal Rasha's Tomb: use Orifice → back to Canyon of the Magi<br>Tal Rasha's Tomb: use Orifice → back to Canyon of the Magi<br>Tal Rasha's Tomb: use Orifice → back to Canyon of the Magi<br>Tal Rasha's Tomb: use Orifice → back to Canyon of the Magi<br>Tal Rasha's Tomb: use Orifice → back to Canyon of the Magi<br>Duriel's Lair: fight Duriel → loot → leave |
| Summoner | Lut Gholein, Palace Cellar 1, Arcane Sanctuary | Harem 1: enter Harem 2<br>Harem 2: enter Palace Cellar 1<br>Palace Cellar 1: enter Palace Cellar 2<br>Palace Cellar 2: enter Palace Cellar 3<br>Palace Cellar 3: use Arcane Sanctuary<br>Arcane Sanctuary: fight The Summoner → loot → leave |
| Harem | Palace Cellar 1 | *Palace Cellar 1*: enter Harem 2<br>*Harem 2*: enter Harem 1<br>*Harem 1*: loot → leave |
| Sewers 1 | Sewers 2 | *Sewers 2*: enter Sewers 1<br>*Sewers 1*: loot → leave |

### Act 3

| Route | Start | Levels and stages |
| --- | --- | --- |
| Spider Cavern | Spider Forest | Spider Forest: enter Spider Cavern<br>Spider Cavern: fight Sszark the Burning → loot → leave |
| Arachnid Lair | Spider Forest | *Spider Forest*: enter Arachnid Lair<br>Arachnid Lair: use Chest → loot → leave |
| Great Marsh | Great Marsh | Great Marsh: clear → loot → leave |
| Swampy Pit | Flayer Jungle | Flayer Jungle: enter Swampy Pit 1<br>Swampy Pit 1: enter Next level<br>Swampy Pit 2: enter Next level<br>Swampy Pit 3: use Super chest → loot → leave |
| Flayer Dungeon | Flayer Jungle | *Flayer Jungle*: enter Flayer Dungeon 1<br>Flayer Dungeon 1: enter Next level<br>Flayer Dungeon 2: enter Next level<br>Flayer Dungeon 3: fight Witch Doctor Endugu → loot → leave |
| Lower Kurast | Lower Kurast | Lower Kurast: use Super chests → loot → leave |
| Kurast Sewers | Kurast Bazaar | Kurast Bazaar: enter Sewers<br>Sewers 1: use Chest → loot → enter Sewers 2<br>Sewers 2: stand at Khalim's Heart → loot → leave |
| Ruined Temple | Kurast Bazaar | *Kurast Bazaar*: enter Ruined Temple<br>Ruined Temple: fight Battlemaid Sarina → loot → leave |
| Disused Fane | Kurast Bazaar | *Kurast Bazaar*: enter Disused Fane<br>Disused Fane: clear → loot → leave |
| Forgotten Reliquary | Upper Kurast | *Upper Kurast*: enter Forgotten Reliquary<br>Forgotten Reliquary: clear → loot → leave |
| Forgotten Temple | Upper Kurast | *Upper Kurast*: enter Forgotten Temple<br>Forgotten Temple: clear → loot → leave |
| Ruined Fane | Upper Kurast | *Upper Kurast*: enter Kurast Causeway<br>*Kurast Causeway*: enter Ruined Fane<br>Ruined Fane: clear → loot → leave |
| Disused Reliquary | Upper Kurast | *Upper Kurast*: enter Kurast Causeway<br>*Kurast Causeway*: enter Disused Reliquary<br>Disused Reliquary: clear → loot → leave |
| Mephisto | Upper Kurast, Travincal, Durance of Hate 2 | Upper Kurast: enter Kurast Causeway<br>Kurast Causeway: enter Travincal<br>Travincal: fight Ismail Vilehand → loot → enter Durance of Hate<br>Durance of Hate 1: enter Next level<br>Durance of Hate 2: enter Next level<br>Durance of Hate 3: stand at Red portal → fight Mephisto → loot → use Red portal → leave |

### Act 4

| Route | Start | Levels and stages |
| --- | --- | --- |
| Izual | The Pandemonium Fortress | *The Pandemonium Fortress*: enter Outer Steppes<br>Outer Steppes: enter Plains of Despair<br>Plains of Despair: fight Izual → loot → leave |
| Diablo | City of the Damned, River of Flame | City of the Damned: enter River of Flame<br>River of Flame: enter Chaos Sanctum<br>The Chaos Sanctuary: use Vizier seal 1 → use Vizier seal 2 → fight Grand Vizier of Chaos → use De Seis seal → fight Lord De Seis → use Infector seal 1 → use Infector seal 2 → fight Infector of Souls → fight Diablo → loot → leave |

### Act 5

| Route | Start | Levels and stages |
| --- | --- | --- |
| Abaddon | Frigid Highlands | Bloody Foothills: enter Frigid Highlands<br>Frigid Highlands: use Abaddon (pending)<br>Abaddon: use Super chest → loot → leave |
| Pit of Acheron | Arreat Plateau | Arreat Plateau: use Pit of Acheron (pending)<br>Pit of Acheron: use Super chest → loot → leave |
| Infernal Pit | Frozen Tundra | Frozen Tundra: use Infernal Pit (pending)<br>Infernal Pit: use Super chest → loot → leave |
| Frozen River | Crystalline Passage | Crystalline Passage: enter Frozen River<br>Frozen River: fight Frozenstein → loot → leave |
| Drifter Cavern | Glacial Trail | Glacial Trail: enter Drifter Cavern<br>Drifter Cavern: use Super chest → loot → leave |
| Icy Cellar | The Ancients' Way | The Ancients' Way: enter Icy Cellar<br>Icy Cellar: fight Snapchip Shatter → use Super chest → loot → leave |
| Nihlathak | Halls of Pain | Nihlathak's Temple: enter Halls of Anguish<br>Halls of Anguish: enter Next level<br>Halls of Pain: enter Next level<br>Halls of Vaught: fight Nihlathak Boss → loot → leave |
| Baal | The Worldstone Keep 2 | Arreat Summit: enter The Worldstone Keep 1<br>The Worldstone Keep 1: enter Next level<br>The Worldstone Keep 2: enter Next level<br>The Worldstone Keep 3: enter Next level<br>Throne of Destruction: stand at Throne → fight Lister the Tormentor → loot → use Worldstone Chamber<br>The Worldstone Chamber: fight Baal → loot → leave |
| Halls of Anguish | Halls of Pain | *Halls of Pain*: enter Halls of Anguish<br>*Halls of Anguish*: enter Nihlathak's Temple<br>*Nihlathak's Temple*: fight Pindleskin → loot → leave |
| Worldstone Keep 1 | The Worldstone Keep 2 | *The Worldstone Keep 2*: enter Worldstone Keep 1<br>*The Worldstone Keep 1*: clear → loot → leave |
| Bloody Foothills | Frigid Highlands | *Frigid Highlands*: enter Bloody Foothills<br>*Bloody Foothills*: clear → loot → leave |

### Pending (3)

| Route | Level | Stage | Why |
| --- | --- | --- | --- |
| Abaddon | Frigid Highlands | use Abaddon (pending) | the red portal is not in the map files: its object is not read yet |
| Pit of Acheron | Arreat Plateau | use Pit of Acheron (pending) | the red portal is not in the map files: its object is not read yet |
| Infernal Pit | Frozen Tundra | use Infernal Pit (pending) | the red portal is not in the map files: its object is not read yet |
<!-- routes:end -->

## Farming runs these cover

Every boss or chest run starts at a waypoint and is a tail of one zone route above, so no run needs
a list of its own: Andariel (Catacombs 2), Countess (Black Marsh), Pit (Outer Cloister), Mausoleum
(Cold Plains), Tristram (Stony Field), Radament (Sewers 2), Ancient Tunnels (Lost City), Summoner
(Arcane Sanctuary), Lower Kurast chests, Travincal council, Mephisto (Durance 2), Hephasto and
Chaos Sanctuary (River of Flame), Eldritch and Shenk (Frigid Highlands; the macro request handles
these), Pindleskin (the macro request), Nihlathak (Halls of Pain), Baal (Worldstone Keep 2), and
the hell pits and ice caves of act 5.

Left out on purpose: Duriel (needs the staff; his lair is in no Herald group; since 2026-10-21 on the Tal
Rasha's Tombs route, entered by the true tomb's Orifice: levels/handlers/tal_rasha.py DURIEL), the Cow Level, the
Arreat Summit (the Ancients are a one-time quest), Uber Tristram and the Pandemonium runs.

