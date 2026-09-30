# Supported memory layout and evidence

Updated 2026-09-21. These fields support the current reader; evidence below records
controlled samples. Raw probes are research snapshots, not an atomic or universally
validated game state. Current operation: [runbook](osd/README.md).

## Build and access

- Disk SHA-256: `1e2ac459feb3f4bbfa818cdff49800480502beae9f90cfa4cba9e7e1f8bfa3b7`.
- Resource strings: version `3.3.93787`; fixed version tuple `(3, 3, 28251, 0)`
  truncates the third field to 16 bits. Gate on the hash.
- Observed image `0x140000000`, unit-table RVA `0x1ead470`. Runtime signature
  `48 03 C7 49 8B 8C C6` at `0x1400705a8` precedes displacement `70 d4 ea 01`.
  The reader rescans on attachment; historical pointers/PIDs are not constants.
- Units have next link +0x158, corroborated by instruction `48 8b 99 58 01 00 00`.
  Do not adopt other references' +0x150 layout.
- Steam AppID 2536520, Proton Experimental, Steam Runtime 4/pressure-vessel;
  prefix `/mnt/extra/1000/games/steam/steamapps/compatdata/2536520/pfx/`.
  Host UID 1000/no capabilities/Yama 1 read the game without permission changes.
  Reader/game shared PID namespace but differed in mount/user namespaces.
- Wine mappings were anonymous/memfd. Discovery distinguished a writable PE copy
  at `0x3370000` from the loaded executable-entrypoint candidate. Code mappings
  are fragmented; unrelated allocations must not invalidate attachment.

## Unit and stat fields

Table groups are `table + type * 1024`, each with 128 pointer buckets. Observed
unit ID modulo 128 matched its bucket. Types: player 0, monster 1, item 4.

| Unit offset | Field |
| --- | --- |
| +0x00 / +0x04 / +0x08 | Type / class ID / unit ID |
| +0x0c | Mode; belt item 2, inventory 0, equipped 1 |
| +0x10 | Type-specific data pointer |
| +0x38 | Path pointer |
| +0x88 | Stat-list pointer |
| +0x90 | Inventory pointer |
| +0x158 | Next unit |

Stat descriptor = pointer/count (two u64); entries = u16 layer, u16 stat ID, i32
raw value. Player effective stats are at stat list +0xe8, layer-zero life/max IDs
6/7, with 8 fractional bits. +0x30 holds base stats; its max excludes bonuses.
The old d2go +0xa8 effective descriptor is empty on this build. Arrays and stat
positions can move; follow pointers and search IDs every sample.

Several player-like units share the character name. Current selection uses a
unique plausible effective-life candidate; name or inventory markers alone are
not robust multiplayer identity. Markers changed between games (8800 to 4032).

## Belt and mercenary

Item data +0x0c is owner ID. Path +0x10/+0x14 (u16) holds belt cell/zero, or
inventory coordinates. Belt cell = column + 4 * row, both zero-based; row 0 is
bottom. Column 1 samples established 0/4/8/12 bottom-to-top, bottom consumption
and compaction. A potion only at cell 12 remained after key 1: occupied totals
must not imply usable stock. Capacity currently assumes four rows.

Potion class IDs verified in cached d2data misc JSON: rejuvenation 530/531;
healing 602–606. Data provenance: [d2data misc](https://github.com/blizzhackers/d2data/blob/master/json/misc.json).

Act 2 hireling class 338 is matched by monster data +0x54 to player ID. Effective
max at +0xe8 is ordinary fixed-point HP; current life is a normalized value up to
32768. Estimate current raw HP as `max_raw * life_fraction / 32768`; death is zero
life or modes 0/12. Living animation changes do not invalidate identity, but
crossing the death boundary does. Injured readings remain approximate: panel
2048/2090 disagreed with OSD 1943/2090, then ~2057 lingered. See
[external merc HP research](merc_health_research.md); no exact source is established.

The discarded UI signature `40 84 ed 0f 94 05` at `0x140ce0df4` resolved near
`0x141ebd176`. Interpreting old panel offsets from `0x141ebd16c` read monster-name
text (`Undead`, `Minion`), not flags. Its scanner/reader was removed during cleanup.
No menu state is inferred; the user authorized existing focus/death/freshness/belt
checks without menu detection. Keep this failed lead to avoid repeating it.

## Show Items state (2026-09-21)

Live reader uses one byte at image RVA `0x1ebd164`: 0 means Show Items OFF,
1 means ON. This was isolated by labelled captures, not by interpreting the old
UI panel array. The previously rejected menu layout remains rejected.
The address is bound to `SUPPORTED_SHA256`; a different build must be revalidated.

| Label | Host capture | Byte |
| --- | --- | --- |
| off-1 | `20260921T133808Z-92dc8ff7` | 0 |
| on-1 | `20260921T133830Z-ddd96b43` | 1 |
| off-2 | `20260921T133904Z-cadf55ca` | 0 |
| on-2 | `20260921T133935Z-2caee4ca` | 1 |
| new-game-off | `20260921T134119Z-90d9c47e` | 0 |
| new-game-on | `20260921T134152Z-eb24a8c4` | 1 |

All captures used the same process identity (`2911790`, start ticks `276227122`).
The first four alternations left six boolean candidates in the captured `.data`
section. Of those, only this byte had direct RIP-relative code references in the
captured executable sections. Examples: `0x14007460d` compares it with zero;
`0x140106a4d` loads it into EAX; `0x140d16a8d` loads it into R12D. Code references
support the candidate but do not by themselves prove its meaning; the labelled
user-controlled toggles and new-game reset provide the behavioral evidence.
Raw captures and comparison output are under `runs/show-items/` (Git-ignored).

`observe_show_items` reads the byte twice, checks process identity and the mapping
before/after, and accepts only 0/1. The live reader calls it after the executable
hash gate and only with an in-game domain session. Invalid/changed/unreadable
state becomes unavailable. The OSD shows `loot is not enabled` only for a fresh,
confirmed false observation. It neither sends a toggle key nor infers state from
keypress counts, and does not change healing policy.

Validation covers keyboard Show Items toggles on this build and a new-game reset;
controller behavior and hold-mode behavior have not been established. Reads and
unit snapshots remain non-atomic; rapid changes between samples can be missed.

The external [d2go key-binding reader](https://github.com/relentlessricktrinidad/d2go/blob/1fb1e7a6569fef21e6e3a63749244f65a80673a0/pkg/memory/keybindings.go)
only exposes the binding. Its panel-tree reader was a research lead, but was not
needed for this implementation.

## Open-panel flags (2026-09-27)

A byte array of 0/1 panel flags starts at image RVA `0x1ebd158`; the Show Items byte
above is its `+0x0c`. The layout is d2go's `OpenMenus` (inventory `+0x01`, character
`+0x02`, NPC interact `+0x08`, quit menu `+0x09`, NPC shop `+0x0b`, waypoint `+0x13`,
stash `+0x18`, cube `+0x19`, mercenary `+0x1e`), anchored here not by d2go's code
pattern (its `40 84 ed 0f 94 05` sites on this build target `0x1ebd16d` and
`0x1ebd176`, the discarded lead above) but by the 129 `image.bin` captures of the
supported build under `runs/`:

| Byte | Set in | Not set in |
| --- | --- | --- |
| `+0x01` inventory (`0x1ebd159`) | 81 captures, every hover/Alt+D attachment | Show Items, consume runs |
| `+0x08`/`+0x0b` NPC interact/shop | exactly the 31 vendor captures (`hover-ui/…173451Z`, `…173519Z`, shop Alt+D) | everything else |
| `+0x18` stash (`0x1ebd170`) | the 23 attachments of the 2026-09-23 18:17–22:30 and 2026-09-25 stash sessions, always with `+0x01` | Show Items, consume, vendor runs |
| `+0x19` cube (`0x1ebd171`) | 13 cube-session captures | — |
| `+0x1e` mercenary (`0x1ebd176`) | the one mercenary-panel Alt+D (`alt-d/20260923T203033Z`) | — |

`tracking/panels.py` reads the 32-byte array twice with identity/mapping checks and
accepts only 0/1 bytes. `collection/watch.py` uses the stash flag's open → closed edge
to run a Win+S collection (`--stash-auto`). Host confirmation pending: open and close
the stash with the worker running and check the log line "Stash closed; collecting".

## Optional resources

- Tome class 533, owned inventory mode 0/page 0: layer-zero stat 70 (quantity),
  descriptor +0x30, capacity 20. +0xe8 also contained quantity in the samples.
- Teleport staff: equipped mode 1/body slots 4/5/11/12. Class families were verified
  in local d2data weapons; class alone does not imply charges. Descriptor +0xe8,
  charged stat 204, skill ID `layer >> 6` = 54. Remaining/max charges are raw low/high
  bytes. Observed layer 3457 and raw 8480→8479 decoded 32/33→31/33.
- Path +0x20 → room; room +0x18 → room2; room2 +0x90 → level; level +0x1f8 → area.
  Town IDs are 1/40/75/103/109. Pointer chain and area are rechecked after reading.
- Scope to one owned tome and one equipped charged staff across both weapon sets;
  ambiguity/unavailable traversal is not absence. Resource failures are isolated
  from core health/belt validity. RESOURCE_READER enables these verified sources.

Sources: [d2go items](https://github.com/relentlessricktrinidad/d2go/blob/main/pkg/memory/item.go),
[player/location](https://github.com/relentlessricktrinidad/d2go/blob/main/pkg/memory/player.go),
[stats](https://github.com/relentlessricktrinidad/d2go/blob/main/pkg/data/stat/stats.go),
[skills](https://github.com/relentlessricktrinidad/d2go/blob/main/pkg/data/skill/skill.go),
[areas](https://github.com/relentlessricktrinidad/d2go/blob/main/pkg/data/area/area.go).
These supplied leads; the samples below supplied local validation.

## Controlled evidence — 2026-09-21 local date

Run artifacts are under `runs/<run-id>/`; IDs use UTC, so many begin 20260920.
Older absolute addresses/IDs identify observations only. Unit checks revalidate
headers/table heads/mappings; in-place or reverted mutations can still evade them.

| Run ID(s) | Evidence |
| --- | --- |
| `20260920T210805Z-de6e8b64` | Both memory APIs read 16 bytes at 0xe20000, PID 2487980; watcher detected completion. |
| `20260920T212621Z-621c7470`, `212841Z-06ebd375`, `213011Z-4a49130c` (same date) | Ambiguous headers → mapping/entry evidence → sole executable candidate 0x140000000. |
| `20260920T213737Z-f87e5a68` | Captured 28,213,248 readable bytes, one unit-table signature, no changed captured mappings. |
| `20260920T214122Z-ef1b565e` | Seven players/331 items; belt owner 2018320017, full 8 rejuvenation/8 super healing arrangement. |
| `20260920T214459Z-21ea3335` | Item 133700180 moved cell 12 → inventory (3,1); belt 7/8. Effective raw HP 440832/441067 displayed 1722/1722. |
| `20260920T214644Z-f445000d`, `214659Z-c839a949` (same date) | Gear changes: raw 435200/435333 → 395520/395520, matching user 1700 → 1545. |
| `20260920T220112Z-745625ae`, `220350Z-e785d99d` (same date) | User-confirmed 1565 HP/one missing rejuvenation; second unchanged pre-key baseline. |
| `20260920T220447Z-1c0cbce6` | Two confirmed key-1 presses: cells 0/4 items disappeared, cell-8 item moved to 0. |
| `20260920T220644Z-25a9fb89` | One additional press emptied column 1; 4 rejuvenations/8 healing total. |
| `20260920T220745Z-e0e00dfb`, `220840Z-e4a53156` (same date) | Refill lowest slot = cell 0, move same item to highest = cell 12. |
| `20260920T220954Z-ee251a0c` | Focused key-1 press did not consume top-only cell 12 across empty lower rows. |
| `20260920T221144Z-bad7ad0f`, `221233Z-a19c71a0` (same date) | Damage 1526/1545 matched display; follow-up after healing read 1545/1545. |
| `20260920T221324Z-0fa21cef`, `221417Z-f81f2565` (same date) | Character select had empty tables; new game recovered HP with player ID 44171616/new pointer. |
| `20260920T221700Z-a2ce2a59` | Full restart: PID 2532947/start 270903159, player 44347742; same hash, rediscovered table, 1545/1545 HP. |
| `20260920T224656Z-12747c44` | Merc class 338/unit 2460266851 owned by player 44347742; max 535040/256=2090 matched user, life 32768. |
| `20260921T012249Z-6e86409a` | Staff slot 4, raw charges 8480, tome 18, town 109. |
| `20260921T012338Z-da966c41` | Weapon swap: same staff inactive in slot 11, charges/tome unchanged. |
| `20260921T012457Z-c7fd3e4d` | One Teleport/two portals: charges 31/33, tome 16, field 111. |

Resource fixtures preserve the three complete run IDs in
`tests/inventory_tracking/fixtures/resources_*.json`. Subsequent OSD output showed
14 portals, 29/33 charges, field 110. The user accepted completed live behavior,
including the resource follow-up, on 2026-09-21; no additional raw records were
supplied with that acceptance. Exact merc HP, other belt capacities and robust
multiplayer identity remain open research limitations.

## Inventory keys (2026-09-21)

Ordinary Key is class ID 558, max stack 12, verified against
[d2data misc.json](https://github.com/blizzhackers/d2data/blob/master/json/misc.json).
The live OSD run `20260921T135103Z-4cead4c1` supplied a complete resource snapshot:
owned item `3718130058`, main inventory page 0, quantity stat 70/layer 0 at stat
list +0x30 read **12**, matching the user's stated stock. +0xe8 also read 12;
+0xa8 was empty. Six other owned key stacks were on page 4 and excluded.
The reduced snapshot is `tests/inventory_tracking/fixtures/keys_baseline.json`.

`RESOURCE_READER.key_stats_offset=0x30` enables counting. Sum only class 558,
mode 0, inventory page 0, matching the selected player's owner ID. Unknown or
incomplete records never imply zero; an explicitly complete key scan with no
matching stacks does. The alert is `keys: N` strictly below 5, with no latch.
The live baseline verifies 12; threshold/refill/zero behavior is covered by tests.

## Level rooms (2026-09-30)

Two Win+C dumps (`runs/level/`, Git-ignored) in Arcane Sanctuary (area 74) on the
supported build. The first was taken at the entrance (`20260930T062028Z-4913ad64`), the second
standing on the Summoner (`20260930T062220Z-d76e6f5b`).

| Field | Offset |
| --- | --- |
| Path → Room1 | +0x20 (dynamic x/y at +0x02/+0x06) |
| Room1 → Room2 | +0x18 |
| Room2 → level | +0x90 |
| Level area ID | +0x1f8 (u32) |
| Level → first Room2 | +0x10 |
| Room2 → next Room2 | +0x48 |
| Room2 → preset record | +0x40; first u32 = LvlPrest `Def` (d2data lvlprest.json) |
| Room2 bounds | +0x60 x, +0x64 y, +0x68 width, +0x6c height (u32 tiles; ×5 = world) |
| Room2 seed | +0x08 (low dword repeated at +0x30) |

The Room2 list held all 61 rooms of the level while only 17 had loaded Room1s. The
preset IDs matched the arm geometry: centre 524 NSEW, corridors 512 EW / 521 NS, dead ends
510/511/517. Exactly one room was 527 "Arcane Summoner S", and it was unloaded at the
entrance. In the second dump the player stood in that room; monster 250 (Summoner) at world (25440, 5020) and
object 357 (Horazon's Journal) at (25431, 5011) were inside it. So the client knows the
Summoner's arm from the moment the level loads; monsters and objects are only streamed near
the player (6 → 50 monsters between the dumps). The user reported the arm as map north.

Not confirmed: MapAssist's ActMisc offsets (+0x830 difficulty, +0x870 first level) gave
garbage on this build. No monster/object preset list was found within three pointer hops of
Room2, and the 250/357 matches in the second dump were shared addresses, not placements.
`levels/guide.py` uses the confirmed chain only.

A third dump (`20260930T063353Z-deb2239b`, another game) held the Summoner room as
preset 525 "Arcane Summoner W" at the east tip. The four Summoner presets (525–528) are one per
doorway orientation, so targets are matched by LvlPrest name (`levels/handlers/`, bundled
table `levels/data/level_presets.json`), never by one Def.

## Preset objects and large presets (2026-09-30)

Room2 +0x40 → preset record {u32 Def, pad, +0x08 object}. The object repeats the Def at
+0x00, holds the DS1 file index at +0x04 and the whole preset's bounds (x, y, w, h tiles) at
+0x18. Checked across 10 Win+C dumps: the Def always matched, and the index was always below
lvlprest `Files` when Files > 0 (Temple NE 1 of 2, NW Down 0 of 1, Crypt Theme 0 of 1, Vaught
3 of 4). Large presets are split into 8x8 Room2 chunks sharing one object:

- Halls of Anguish/Pain: four 40x40 quadrants (NE, SE up, NW/SW Down, Waypoint), 25 chunks each.
- Halls of Vaught: one 84x84 'Temple Final Room' (NihlE/N/S/W); the player enters at its centre.
  Dump 20260930T082410Z-54658110 had variant 3 (NihlW). The letter is Nihlathak's side: the user saw
  him west and north in two games (2026-09-30); "opens toward" would have put NihlW east.
- Tower Cellar 5: all 16 chunks are 'Crypt Countess X' (2 variants), i.e. the whole level.

`levels/handler.py` collapses chunks into one POI per preset instance, places variant presets
by `sides`, and refuses targets that are the whole area around the player.

## Object data: shrines (2026-09-30)

Object units keep their data block at unit +0x10. In it, +0x08 is the shrine type byte (d2data
shrines.json code: 14 Stamina, 18 Gem) and +0x10 a shrine table pointer that is set only for
shrines. Evidence: Win+C dump `20260930T121835Z-713d7e8a` (Black Marsh). Object class 83 was at
(14662, 5182), next to the player at (14665, 5183); the user identified it as a Stamina Shrine;
bytes `48e30465 00000000 | 0e 000000 00000000 | 78909e2c 00000000`. MapAssist's packed struct puts
the pointer at +0x0C, which is wrong on this build. The same dump confirms the objects' static-path
position (+0x10/+0x14).

## Room2 neighbours (2026-09-30)

Win+C dump 20260930T124726Z-e166c530 (Lower Kurast): Room2 +0x10 is a pointer to an array of Room2
pointers and +0x18 its count (5-9, the room itself included; +0x20 is a second small count, not
used). For all 80 rooms every entry was a Room2 of the same level, except at the level edge, where
the extra entries are Room2s of the adjacent level. The levels code reads their level (+0x90) and
area (+0x1F8) to name outdoor exits (`levels/memory.neighbour_areas`, `Room.leads_to`); that those
foreign rooms carry a readable level is still to be confirmed live (Cold Plains).

## Room1 collision grid (2026-09-30)

Win+C dump 20260930T135418Z-6b2890e1 (Cave 2): Room1 +0x38 points at the collision grid; grid +0x00
is x, y, width, height in sub-tiles (the Room2 bounds x5, the unit of player positions) and +0x20
points at a width x height u16 mask. Bit 0x1 blocks walking: the set cells drew the cave's walls,
the clear ones its corridors. Other values seen: 0x4, 0x20, 0x11, and 0x8000/0x200/0x400/0x1100
where units stood. 8 of 9 loaded rooms matched; the ninth (the player's) only failed the research
filter (more than 16 distinct values because of units). Room1 +0x00/+0x40 is the loaded-room
neighbour array and count. Also: the glowing (super) chest is object class 397 'sparklychest'
(mode 0 closed).
