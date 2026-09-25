# Item collection research notes

Dated findings for the Step 0 questions in [plan.md](plan.md). Evidence is the
Alt+D run `inventory_tracking/runs/alt-d/20260925T111336Z-15857918` (15 requests,
one game session, pid 1169407) plus every earlier `frozen.json` under `runs/alt-d/`.
Each Alt+D `frozen.json` keeps the full player/item unit snapshot, so no separate
`probe --units` run was needed for R1–R4.

## R1. Shared stash tab identity — partially resolved (2026-09-25)

Player-type units in the stash-open snapshot (request-8):

| unit_id | txt_id | mode | name | notable stats | page-4 items |
|---|---|---|---|---|---|
| 2211284790 | 7 | 5 | CybergrindAA | life, level 91, 84 stats | 28 (personal stash) |
| 3204843548 | 3 | 5 | Caras | level 95, 74 stats | 0 (22 inventory, 10 equipped) |
| 1105634203 | 7 | 0 | CybergrindAA | goldbank 2 500 000, other_animrate 100, alignment 2 | 40 |
| 2719888953 | 7 | 0 | CybergrindAA | same | 14 |
| 2968728013 | 7 | 0 | CybergrindAA | same | 20 |
| 3363412198 | 7 | 0 | CybergrindAA | same | 18 |
| 1681697907 | 7 | 0 | CybergrindAA | same | 5 |
| 3238992668 | 7 | 0 | CybergrindAA | other_animrate 100, alignment 2; no goldbank; inventory marker 1 | 0 |

- Five shared owner units hold items; a sixth candidate holds nothing and no gold.
  The user's Alt+D presses hit five distinct shared owners (requests 8–12, 15), so
  the RotW stash exposes at least five shared tabs, not three.
- Tab order is **not** in the hovered grid widget: across the five shared-tab
  requests only the tooltip allocation (0x558–0x56F, already excluded by the
  selection code) and the owner id at 0x5C4 differ.
- Tab order is not the walk order, the address order or the unit-id order of the
  units versus the order in which the user pressed Alt+D (2719888953, 1681697907,
  3363412198, 2968728013, 1105634203).
- Reference rule (`third-parties/d2go/pkg/memory/item.go:21-31`): shared stash
  owners are player units with the `Sharedstash` state, ordered by the u64 at
  player unit **+0xD8**. The state lives in the stats-list structure at
  `stats_pointer + 0xAF0`, six u32 words; `Sharedstash` is state 186 → word 5,
  bit 25 (`states.go`, counted from `None = iota`). Our walker already reads 0x160
  bytes per unit, so +0xD8 is a retained-field change, and the state words are one
  24-byte read next to arrays we already validate.
- User-confirmed tab numbers (Alt+D requests 11:15–11:35 UTC, same session):

  | tab | owner unit | evidence |
  |---|---|---|
  | 1 | 1105634203 | Annihilus (9,0) |
  | 2 | 2968728013 | Atma's Scarab (2,9) |
  | 3 | 3363412198 | Guardian Angel (6,9), Raven Grasp |
  | 4 | 1681697907 | Goldwrap (0,0), The Reaper's Toll after its move |
  | 5 | 2719888953 | Lidless Wall (2,1) |

  Host run `runs/collection/20260925T114444Z-cbda18a7` read the +0xD8 field:
  local player 1226, then 1105634203 → 1227, 2968728013 → 1268, 3363412198 → 1289,
  1681697907 → 1308, 2719888953 → 1314, empty 3238992668 → 1329. Sorting by it
  reproduces the table exactly, with the empty unit last (tab 6). **Resolved.**
- The d2go `Sharedstash` state words at stats-list +0xAF0 read as 24 zero bytes for
  every player unit on this build, so the state bit is unusable here. Shared owners
  are recognized instead as type-0 units named like the local player with neither a
  level stat (12) nor life stats (6/7); the party member carries both. The empty
  sixth candidate qualifies, which keeps numbering complete.

Gems / Materials / Runes tabs (2026-09-25, resolved): 74 units with owner 0xFFFFFFFF,
page 4, mode 0, all at cell (0,0), quality 2, empty stat arrays — one unit per
**held** stackable type (24 runes including Sur but no Ber/Jah/Vex/Ohm/Zod, 35 gems,
essences, keys, worldstone shards, uber materials, rejuvenation potions). The stash
UI shows Personal, Shared, Gems, Materials and Runes tabs; the three count tabs are
owned by the sixth same-name unit (3238992668, order 1329, no gold), whose widget
class differs from the grid panels (vtable image+0x1712F88, page byte 15, grid 6 is a
10×10 array with no cells filled), so Alt+D rejects it as an unsupported widget.
**Stack count = u32 at item data +0x9C.** Probe `runs/collection/20260925T124336Z-509c617f`
(`materials-probe.json`, 0x100-byte item records) matched all 43 counts the user
supplied (Sur 1, El 10, Eth 43, Ral 25, Ort 30, Western Worldstone Shard 23,
Rejuvenation 96, Full Rejuvenation 99, every gem cell of the Gems tab screenshot);
no other offset in the unit, item-data, stats-root or path blocks was consistent.
Indexed as container `materials` with `quantity`; the count is a stat line
"Quantity: N" (searchable) and is excluded from the fingerprint.

Mercenary: hireling unit 295472961 with monster data[21] = 2211284790 (the local
player), 37 socketed children (mode 6) and 3 equipped items owned by 0xFFFFFFFF
page 255 — consistent with the existing merc path.

## R2. Stash units with the panel closed — answered for town (2026-09-25)

Request-1 (11:13:43, main inventory hovered, a vendor grid with 44 items on pages
0–3 present, so the stash panel was closed) already contains all six shared
candidates and every page-4 item with the same per-owner counts as request-8 with
the stash open. Stash owner units and their items are readable in town with the
panel closed. Outside town: untested; Step 2's CLI records the area id so the first
field capture answers it.

## R3. Character class and level — answered (2026-09-25)

- Level is stat 12, layer 0, in the player's full stat array (+0xE8): 91 for the
  local Warlock, 95 for the second unit.
- Class is the player unit's `txt_id`: 7 for the Warlock (`CybergrindAA`), 3 for
  `Caras` (Paladin by gear: Sacred Targe, Phase Blade, Diadem). Classic ids 0–6 are
  Amazon, Sorceress, Necromancer, Paladin, Barbarian, Druid, Assassin.
- `Caras` (mode 5, own inventory and equipment, no life stat candidate) appeared
  between the 09:43 and 10:04 sessions of the same process. Open question for the
  user: a party member. Step 2 indexes only the local player (unique plausible-life
  unit), the shared tabs and the local player's mercenary; party members' units and
  items are ignored.

## R4. Stable item identity across sessions — answered (2026-09-25)

445 captured 0x60-byte item records across 2026-09-23…25, 43 items seen in two
or more game sessions:

- Between sessions only bytes +0x0C–0x0F (owner unit id) change, plus +0x18
  (flags) and +0x55 (page) when the item was identified or moved in between.
- +0x04 is `01000000` and +0x08 is `9a020000` in **every** record; +0x10, +0x14,
  +0x1C–0x30 and +0x38–0x3C are constant too. The legacy `pSeed`/`dwInitSeed`
  slots carry no per-item value in D2R; MapAssist's D2R layout lists no seed either.
- Per-item variation is confined to quality (+0x00), owner (+0x0C), flags (+0x18),
  identity (+0x34), affix ids (+0x40–0x53), body/page (+0x54) and +0x5C.

Decision: the content fingerprint from Step 1 is final. Two items with identical
base, quality, identity, flags, stats and socket contents share one row and appear
as two placements; there is no seed to separate them. `seed_hex` is removed.

## R5. Full-pass read cost — pending

No probe run measured it. Step 2's CLI reports bytes, milliseconds and instability
count per capture; the first host run is the measurement.

## R7. Win+S delivery — pending

No `Mod+S` binding exists in `~/.config/niri/config.kdl` yet. Folded into Step 3's
host gate with the real `collect` command instead of a notify-send test.
