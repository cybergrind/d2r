# Runtime layout research — 2026-09-21

Research evidence only; no controller-ready state or supported-build guarantee.

## Executable and table

- Disk SHA-256: `1e2ac459feb3f4bbfa818cdff49800480502beae9f90cfa4cba9e7e1f8bfa3b7`.
- Disk resource strings report FileVersion/ProductVersion `3.3.93787`.
  The fixed resource structure encodes `(3, 3, 28251, 0)`; its 16-bit third field
  equals `93787 & 65535`. Preserve the hash as the build identity.
- Runtime image candidate: `0x140000000`.
- Signature `48 03 C7 49 8B 8C C6` at `0x1400705a8`; following displacement
  `70 d4 ea 01` gives table RVA **`0x1ead470`**, address **`0x141ead470`**.
- Subsequent runtime instruction `48 8b 99 58 01 00 00` reads the next-unit link
  at **`+0x158`**. This agrees with d2go, rather than the `+0x150` hash-link
  claim in the other reference. Do not silently mix those layouts.
- Capture `20260920T213737Z-f87e5a68`: 28,213,248 readable image bytes,
  no read errors or changed captured mappings, one unit-table signature.
  Other image ranges remain absent; capture is sequential, not atomic.

## Unit evidence

Run `20260920T214122Z-ef1b565e`: seven type-0 units and 331 type-4 units.
All type/bucket checks passed; table heads, unit identities and read mappings
were stable. The player/item table groups start at `table + type * 1024`, with
128 pointer buckets each. Unit ID modulo 128 matched each bucket.

The belt's owner was unit ID `2018320017`, named `CybergrindAA`, at
`0x8614ca20`. Other type-0 units share the name, so **name alone cannot identify
the active character**. All pointers below are observations from this session,
not constants to reuse after a new game or process restart.

| Field | Unit offset | Observed pointer/value |
|---|---|---|
| Type | `0x00` | player `0`, item `4` |
| Item table ID | `0x04` | belt items `531` / `606` |
| Unit ID | `0x08` | checked against bucket |
| Item mode | `0x0c` | belt `2` |
| Type-specific data | `0x10` | player `0x56001e90` |
| Path | `0x38` | player `0x69cd9ec0` |
| Stat list | `0x88` | player `0x2b648490` |
| Inventory | `0x90` | player `0x56001d70` |
| Next unit | `0x158` | runtime code and live traversal agree |

## Belt candidates

Item data `+0x0c` matched the active belt owner's unit ID. Path `+0x10` (u16)
contained distinct cell indices 0–15; path `+0x14` (u16) was zero. All 16 cells
were occupied: IDs `531` in indices `0,1,4,5,8,9,12,13`, and `606` in
`2,3,6,7,10,11,14,15`. Column = index modulo 4 is consistent with the column-1 move below;
later controlled samples below support bottom-to-top row ordering and low-index
consumption/compaction. Capacity and mixed columns remain unvalidated.

Verified against cached `pricing/raw/d2data-misc.json` on 2026-09-21:

| Class ID | Code | Name |
|---|---|---|
| 531 | `rvl` | Full Rejuvenation Potion |
| 606 | `hp5` | Super Healing Potion |

Source: [d2data misc dump](https://github.com/blizzhackers/d2data/blob/master/json/misc.json).

## Health candidates

The stat-list descriptor at `+0x30` yields 22 base stats. Entries are eight bytes:
u16 layer, u16 stat ID, i32 value. Layer-zero life (ID 6) is `440832 / 256 = 1722`;
base maximum life (ID 7) is `258560 / 256 = 1010`. **Do not use this pair as
current/max HP**: base maximum excludes bonuses. The d2go `+0xa8` descriptor is
empty here. A bounded descriptor search is implemented to investigate the
current build's effective stat array.

### Controlled validation

The user confirmed 1722 displayed HP and the initial 8/8 potion arrangement.
Run `20260920T214459Z-21ea3335` caught full rejuvenation unit `133700180`
moving from belt mode `2`, cell index `12`, to inventory mode `0`, page `0`,
coordinates `(3,1)`. The remaining 15 belt items comprise 7 full rejuvenations
and 8 super healing potions; ownership stayed unchanged. The move was requested
from the bottom of column 1, so do not assume visual row direction from index
ordering without further observation.

The descriptor at **stat list `+0xe8`** supplies effective stats, including both
life and maximum life. It had 68 entries initially and produced:

| Run | Current raw | Max raw | Display conversion (`raw >> 8`) | User report |
|---|---:|---:|---|---|
| `20260920T214459Z-21ea3335` | 440832 | 441067 | 1722 / 1722 | 1722 |
| `20260920T214644Z-f445000d` | 435200 | 435333 | 1700 / 1700 | 1700 after gear change |
| `20260920T214659Z-c839a949` | 395520 | 395520 | 1545 / 1545 | 1545 after another change |

All three unit snapshots passed chain, identity, mapping and table-head checks.
This validates the effective-stat location across these equipment changes,
not combat damage, healing, death or session restarts. Preserve raw fixed-point
values for later ratio decisions; displayed integers discard the fractional bits.

Observed descriptor address: `0x2b648578`; array pointer in the initial sample:
`0xe5a06b60`. Life/max value addresses then were `0xe5a06b84` / `0xe5a06b8c`.
Follow the player/stat-list/array pointers and search IDs each sample: array
storage and entry positions can change, so these absolute addresses are not a
reader implementation.

## Sources and next validation

- [d2go offsets](https://github.com/relentlessricktrinidad/d2go/blob/main/pkg/memory/offset.go)
- [d2go player](https://github.com/relentlessricktrinidad/d2go/blob/main/pkg/memory/player.go)
- [d2go item](https://github.com/relentlessricktrinidad/d2go/blob/main/pkg/memory/item.go)
- [d2go stat reading](https://github.com/relentlessricktrinidad/d2go/blob/main/pkg/memory/game_reader.go)

Compare a controlled belt move, refill and drink; confirm current/effective max
life against the display and a gear/health change. Repeat through new games and
process restarts. Local-player selection, stale-pointer rejection and complete
belt capacity/consumption semantics remain prerequisites for a usable reader.


### Belt-key sample — 2026-09-21

Run `20260920T220447Z-1c0cbce6` passed consistency checks with the same process
identity. Compared with the pre-key baseline `20260920T220350Z-e785d99d`,
column-1 items `534817104` (cell 0) and `267400360` (cell 4) disappeared from
the item traversal; item `2592217162` moved from cell 8 to cell 0. Other belt
items were unchanged. Totals: 5 full rejuvenations, 8 super healing potions;
effective HP still 1565/1565. This demonstrates cell compaction toward index 0,
and the user confirmed pressing `1` twice, accounting for the two missing
potions. This supports consumption from the low-index end with compaction;
the intermediate state was not sampled. Visual row orientation remains open.


Run `20260920T220644Z-25a9fb89` completed with stable checks after the requested
single additional `1` press. The remaining column-1 item `2592217162` at cell 0
was absent; column 1 was empty, with 4 rejuvenations and 8 healing potions total.
Effective HP remained 1565/1565. Together with the user-confirmed two-press
sample, this supports key `1` consuming from the low-index end of column 1.
Visual row mapping, mixed columns, refill and capacity changes remain open.


Refill run `20260920T220745Z-e0e00dfb` passed consistency checks. Following the
instruction to place one full rejuvenation in the lowest visible column-1 slot,
new item `1512026217` appeared at cell 0; other belt cells were unchanged.
Totals returned to 5 rejuvenations / 8 healing potions; HP stayed 1565/1565.
This supports bottom visual row = indices 0–3, subject to correct requested
placement. Next requested action is moving that same item to the highest visible
column-1 slot to cross-check orientation.


Row check `20260920T220840Z-e4a53156` passed: the same item `1512026217`
moved from cell 0 to cell 12 following the instruction to move it from the
lowest to the highest visible slot. These controlled placements support
column-1 visual rows bottom-to-top = 0, 4, 8, 12. This supersedes the ambiguous
"bottom" wording in the older manual-move sample. A key-use test with only
cell 12 occupied is pending to check gaps below a potion.


Gap sample `20260920T220954Z-ee251a0c` passed checks, but item `1512026217`
remained at cell 12, with lower column-1 cells empty and HP 1565/1565.
User confirmed pressing `1` with the game focused and observing the potion
stay in place. In this controlled case the key did not skip the empty lower
slots to consume cell 12. An occupied column is not necessarily usable; retain
individual cells when deriving next-potion availability.


### Damage validation — 2026-09-21

Host run `20260920T221144Z-bad7ad0f` completed with stable checks. Effective
life/max raw values were 390656/395520 (8-bit fractional format), displaying
1526/1545, exactly matching the user's report. This validates one below-maximum
health sample. Effective maximum differs from the preceding 1565 baseline;
its cause was not established. Next requested sample is after healing to full
without further gear changes. Regeneration and update latency are not measured.


Healing follow-up `20260920T221233Z-a19c71a0` completed with stable checks and
effective HP 1545/1545 after the request to heal without gear changes. The
sample pair shows current life recovering from 1526 to 1545 with max 1545
unchanged. The damaged display was explicitly user-confirmed; the healed
sample is memory evidence after the requested action. Next: character selection,
new game, then process restart to establish lifecycle behavior.


Character-selection sample `20260920T221324Z-0fa21cef` completed with stable
empty player and item tables (0/0); both candidate summary lists were empty.
No previous session's HP or belt candidates were retained. `complete` here means
research traversal completed, not gameplay readiness: the production reader
must publish unavailable/outside-game state rather than zero HP or zero stock.
Next requested sample: same character after joining a new game.


New-game run `20260920T221417Z-f81f2565` passed in the same process. The table
was rescanned at `0x141ead470`; belt owner/player ID changed from `2018320017`
to `44171616`, and player address changed from `0x8614ca20` to `0x8617a920`.
Effective HP was 1545/1545. Seven player-like units remained, but only the
belt-owner candidate had effective life/max stats. Its inventory marker `+0x70`
was 4032 (earlier 8800); other candidates had zero. This correlation is research,
not a robust selector or a fixed marker value. No local-player rule is adopted.
Next requested experiment: fully close/reopen D2R, enter a game, then probe.


### Process restart — 2026-09-21

Run `20260920T221700Z-a2ce2a59` completed after fully restarting D2R. New
process identity: PID 2532947, start ticks 270903159 (previous PID 2487980,
start ticks 270397116). Both memory interfaces succeeded without permission
changes. Disk SHA-256 is unchanged; image candidate `0x140000000` and scanned
table `0x141ead470` were rediscovered. Seven player-like units and
330 items passed traversal/header/mapping checks. New belt-owner/player ID
44347742 at `0x7b53bfc0` had effective HP 1545/1545; belt candidates
contained 5 full rejuvenations and 7 super healing potions. The top-only
column-1 potion remained at index 12. These are fresh post-restart research
readings, not reused pointers or a production reconnect implementation.

Live validation now covers column-1 consumption/compaction, bottom/top placement,
refill, a top-only gap, one below-max HP display match, healing, character
selection, a new game and one full process restart. Remaining reader work:
robust local-player identification (including empty belt/multiple players),
build gating, explicit unavailable/stale state, in-place mutation checks,
mixed columns/other keys and belt capacity. No overlay or controller exists yet.
