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
