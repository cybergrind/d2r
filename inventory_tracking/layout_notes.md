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
visual row orientation, drinking order, capacity and mixed columns are unvalidated.

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
