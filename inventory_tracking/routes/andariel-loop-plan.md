# The Andariel loop: KP_6 runs Andariel games until toggled off (plan, 2026-10-18)

**Goal** (the player, 2026-10-18): "I want to build andariel loop that will be similar to lower kurast loop, we're
going to use the same KP_6 run start/stop it. So, rebuild loop start to accept what type of run we're going to run."
The main goal is Sunder charms (unique grand charms). "inventory management and trading - same as LK."
Gheed's Fortune: "we cannot pickup it while having another gheed charm in our inventory; to pickup another - we need
to go to the shared stash tab and put our current charm there, then go back and pickup another gheed charm. go to
shared stash tab, put new there and bring our's back."

The Lower Kurast loop's plan (`lower-kurast-loop-plan.md`) and journal ([../macros/loop-journal.md](../macros/loop-journal.md)) hold the
machinery this one shares: the trade session, the gems, the guards, the watch.

## Facts this plan stands on (2026-10-18)

- **Where a game starts:** the town of the act the last game was left in (LK plan, phase 0). The player's own
  Andariel games at 10:07–10:10 left from Catacombs Level 4 and began the next in the Rogue Encampment; from the
  start to Catacombs Level 2 took 11 s (the walk to the waypoint, the panel, the load); level 2 took 14 s, level 3
  15 s, level 4 with her fight 29 s (probe.log of `20261018T065826Z-21d3e825`).
- **The route exists:** `routes/catalog/act1.py` Andariel: Catacombs 2 (35, waypoint tab I row 9) → stairs → 3 (36)
  → stairs → 4 (37): `fight('Andariel')`, `loot()`, `leave()`. Marks: `levels/handlers/catacombs.py` (stairs,
  confirmed 2026-09-30), `levels/handlers/boss_lairs.py` (Andariel at (46, 46) of `Andy3.ds1`, unconfirmed). Her
  death is the terror tracker's (`terror/bosses.py` 156), which `Progress` judges the fight by.
- **Charms, the d2data dump (`third-parties/d2data/json/uniqueitems.json`):** the Sunders that drop are the "Latent"
  rows 426, 428–432 (`cm3`, class 620, Hell only, item level 75: Andariel's in Hell is 75), **no `carry1`**. Gheed's
  Fortune is row 359, `cm3`, `carry1` 1001: the only grand charm the game refuses while one is carried. The
  "Renewed" Sunders (cube-made, `cs2`) share carry-one group 1004 and do not drop.
- **A ground unique's row is unreadable until identified** (ItemData +0x34 reads 0; every unidentified unique in the
  logs). On the ground a Gheed's and a Latent Sunder are both "Unique Grand Charm": told apart only by a refused
  pickup.
- **Consume cannot take townsfolk** (`routines.py` TOWN_NPCS): a prebuff in the Rogue Encampment, where Kashya,
  Warriv and Cain stand at a game's start, fails (10:20:17 on 2026-10-18, the loop's first game).

## Design

### The run's kind (done)

`macros/loop.py` `Kind`: `LK` and `ANDARIEL` (`KINDS`). KP_6 stays the toggle:
- one press: the loop on or off; two: the pickup mode (as before); **three: the run's kind** ("Loop run: Andariel").
- Started without a kind chosen by hand, the loop runs the kind of where the character is (`kind_of`): the Rogue
  Encampment and the Catacombs are Andariel's, Kurast Docks and Lower Kurast LK's; the Fortress (both kinds' town)
  and the lobby keep the kind chosen.
- A restart keeps it (`resume_state` `loop_kind`); `restart.py --kind lk|andariel` sets it.
- The HUD badge: `LOOP SURE ANDARIEL`.

### An Andariel game (done, playing)

| Where | Leg | What |
| --- | --- | --- |
| lobby | `next game` | create; no prebuff when the game starts in the Rogue Encampment |
| Rogue Encampment | `to the Catacombs` | waypoint to Catacombs Level 2 |
| Rogue Encampment, a session due | `to Pandemonium Fortress` | the room low with anything a session takes, keys or scrolls short, the staff to repair: the waypoint to the Fortress, its trade session as LK's (Cain, the stash, Jamella, Halbu), then `to the Catacombs` from there |
| Fortress | as LK's | a game begun there (an LK game's end) or a session: `to the Catacombs` in place of `to Lower Kurast` |
| Catacombs 2, 3 | `down the Catacombs` | the prebuff on arrival at 2; the level run to the stairs, rushed (no fight with what does not attack); at the stairs the press through them |
| Catacombs 4 | `Andariel` | the level run, fighting (not rushed), to her and through her |
| Catacombs 4 | `what is left` | one pickup a leg, then the valuables seen and not taken (sightings) |
| Catacombs 4 | `Save and Exit` | there: the next game starts in the Rogue Encampment |

No Town Portal and no Fortress at a game's end: one waypoint and the portal less than LK's end.

### Gheed's Fortune swap (built 10:38, fakes only: not seen in a game)

Trigger: on an Andariel level, a ground unique grand charm (class 620, quality 7) the pickup gave up on ("under the
pointer at N aims and no click picked it up"), while the inventory holds the player's identified unique grand charm
(row 359 at ItemData +0x34: `Carried` reads it). Today that ends in `make_room`, `drop_room`, then "the loop stops
here" with the charm on the ground (safe, slow).

1. `swap out`: Town Portal; the stash; the player's Gheed's by a Ctrl + click onto the **personal** page (its grid is
   the character's grid 6, read exactly; a shared page's contents are not read by the macros, so with no room on the
   personal page the swap is refused and the loop stops with the charm carried); back through the portal.
2. The pickup legs take the new one (nothing blocks it now) and the rest.
3. `swap back` once the level is looted: Town Portal; the stash: the new Gheed's by a Ctrl + click onto the shared
   page (the loop's item, kept: never sold, a unique); the player's taken back by a Ctrl + click on its stash cell
   (`bankexpansionlayouthd.json` grid at (89, 219), 10 x 10); its new inventory cell replaces the old in `Loop.own`
   (the player's items are told by class and cell: a Gheed's elsewhere would read as the loop's).
4. Save and Exit from the Rogue Encampment (an Andariel game starts there anyway).

Guards: nothing of the player's is sold or left (rule: "remember, that we shouldn't sell our own equipment"); a step
that fails stops the loop with the player's Gheed's where it is, said in the log; a second refusal in one game stops
the loop for the player.

### Also built on the first games (journal, 2026-10-18 10:05-10:40)

- The prebuff waits for Catacombs Level 2 (townsfolk crowd the Rogue Encampment's start: Consume fails there).
- A town trip for room: a valuable on an Andariel level with no room, the cube tried: portal, the Fortress's session,
  the Rogue Encampment's waypoint, back through the portal (played, 20 s).
- The loop's level-run posts are no KP_1 double press (one switched Level 2 to a full clear, 80 s).
- Full material stacks (essences, shards, keys) are not picked up (the player, 10:37).

## Open

- Andariel's mark (46, 46) is unconfirmed: the first games' takes confirm or move it.
- A Latent Sunder is not carry-one, so two in one game are both taken; a Renewed one is never on the ground.
- Speed: measured per game (Andariel kills an hour), the watch's chests columns do not apply.
