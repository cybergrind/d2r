# Item-level inspection research — 2026-09-25

Result: actual ilvl is a separate item-data field in legacy Diablo II references,
not a normal affix/stat-array entry. No verified usable ilvl reader was found for
our supported D2R build in the inspected local checkouts. Runtime remains unchanged;
`item_level` must remain unknown until verified.

## Source evidence

Reference revisions are pinned in `third-parties/repos.json`.

- `third-parties/d2bs/JSUnit.h`: exposes `ilvl` via `ITEM_LEVEL`.
- `third-parties/d2bs/JSUnit.cpp:487`: returns
  `pUnit->pItemData->dwItemLevel`; the separate `ITEM_LEVELREQ` branch calls
  `D2COMMON_GetItemLevelRequirement`. These are different quantities.
- `third-parties/d2bs/D2Structs.h:486` and
  `third-parties/D2MOO/source/D2Common/include/Units/Item.h:28`: legacy
  `dwItemLevel` is a uint32 at item-data +0x2C.
- `third-parties/D2MOO/source/D2Common/src/Items/Items.cpp:305`:
  `ITEMS_GetItemLevel` accesses that field, clamping values below one to one.
  The item bitstream reader at line 5065 reads seven bits into it; the writer at
  line 6719 writes seven bits. This is legacy serialization evidence, not a
  verified packet/save layout for current D2R or proof of online availability.
- `third-parties/diablo2utils/packages/map/map/d2_structs.h:305`: ItemData is
  explicitly labeled `1.13?`; its +0x2C field is not independent D2R validation.
- `third-parties/MapAssist/Structs/Items.cs:23`: D2R ItemData exposes quality,
  ownership, flags, identity at +0x34, rare/auto/magic affixes and locations, but no
  item level. This also demonstrates why legacy offsets cannot be copied blindly.
- `third-parties/d2go/pkg/memory/item.go:630`: calculates required level from base
  and affix requirements. It does not recover actual ilvl. Its item memory reader
  does not expose a verified ilvl field. d2r-mapview's item_levelreq/stat 92 is also
  required level. D2tools' STAT_LEVEL usage found in the search is player level.
- Other search hits in d2data concern static cube recipe ilvl parameters; the
  diablo2utils session.ts variable `itemLevel` refers to an area/level structure.
  Neither supplies a captured item's generation level.

## Captured evidence

Our `verify_item` already saves 0x60 item-data bytes as `item_data_hex`, but
`decode_items` emits no item_level. The assessment capture adapter accepts
`item.get('item_level')`, so carrying a verified value downstream is feasible.

Offline examination of 19 distinct fixture buffers found:

| Offset, uint32 little-endian | Observed values |
|---|---|
| +0x28, +0x2C, +0x30 | Zero in all 19 |
| +0x34 | Varies with known identity data |
| +0x38 | One in all 19 |
| +0x3C | Zero in all 19 |

The latest three alt-d run directories examined also contained 68 saved buffers
across 30 JSON files with +0x2C zero. These include repeated buffers, not 68
independent items. The +0x38 position is a layout hypothesis suggested by the
nearby shifted identity field, not a source-verified D2R ilvl offset. A constant one
cannot establish the actual level of these high-level items. Do not label it ilvl.

## Bounded next investigation

1. Obtain a controlled single-player item with independently known ilvl (validated
   save parsing or known creation provenance) and compare captured item data across
   distinct levels on the same supported game build. Keep required level/base level
   separate. The host user runs live probes under the project workflow.
2. Verify any candidate across multiple items and level boundaries, identity changes,
   container moves and repeated captures. Inspect a wider bounded structure or the
   current-build deserializer only if existing bytes cannot resolve it.
3. Independently verify online availability; a single-player/server value does not
   prove the online client receives the true field. Do not assert server-only status
   from missing reader support or constant values alone.
4. Once established, add build-gated decoding, stability checks, provenance and
   regression fixtures, then pass item_level into assessment. Unknown stays unknown.

Until then, observed stats remain assessable; ilvl-dependent recipe/socket/affix
potential stays conditional unless independently established by other evidence.


## User-supplied test candidate — Ring of the Locust, 2026-09-25

Screenshot `/tmp/codex-clipboard-zTkt3r.png`: magic Ring of the Locust,
required level 35, 6% life stolen per hit. User reports a Terror Zone origin and
estimates ilvl 91+. Treat this as a high-ilvl hypothesis, not an exact level or
verified lower bound; required level 35 is not ilvl.

Alt+D requests 31–36 in run `20260925T060029Z-bbe4c89d` failed during reattachment
with FileExistsError for the original image.bin. No matching successful ring
capture was found in saved Alt+D frozen observations. Request 7's “of the Locust”
is a Kriss with 6% life leech and 70% enhanced damage, not this ring; do not use its
bytes as ring evidence. The reconnect fix gives each attachment attempt a fresh
subdirectory, retaining previous evidence. Restart the worker and capture the ring
before testing candidate fields against the reported origin.

### Follow-up capture received

Host run `inventory_tracking/runs/alt-d/20260925T094314Z-af7cd150`, requests 1 and 2,
both completed successfully after the worker restart. Both select the same magic
Ring, unit 2992783264, with stat 60/layer 0/raw 6 (life leech), matching the
screenshot's observed modifier. Viewer context records character level 91; this
is not the item's level. Both item-data buffers are identical.

The 0x60-byte record has +0x2C = 0, +0x38 = 1, +0x3C = 0. None of its bytes are
91–99, so this capture supplies no plain byte/16-bit/32-bit representation of an
ilvl in that range within the sampled record. This does not exclude another
location, a packed/encoded representation, or a different actual ilvl. Stat arrays
at +0x30/+0xA8 are empty; +0xE8 contains only the observed life-leech modifier.
The Terror Zone origin remains a user-reported hypothesis; do not infer or publish
ilvl from viewer level, required level, or this constant-one candidate.

### Level-93 Terror Zone follow-up

User reports two new items from a level-93 Terror Zone. In the same run, request 3
was rejected as `Unstable UI/process` and has no frozen observation. Request 4
successfully captured Iratha's Collar (Amulet, unit 215422929), poison resistance
30 and poison length reduced 75. Its 0x60-byte item-data record again has
+0x2C = 0, +0x38 = 1 and +0x3C = 0, with no byte in 93–97. This is another
negative result for a plain integer ilvl in the sampled header, not proof that
ilvl is unavailable elsewhere.

Blizzard's published Hell Terror Zone rules use game-creator level +2 for standard
monsters, +4 for champions and +5 for uniques (caps 96/98/99), retaining a monster's
original level if higher. For displayed zone level 93, the ordinary monster-drop
candidates are consequently 93/95/96, rather than 93–97. This is source-derived
provenance, not a memory measurement; the particular dropper remains unknown.
Higher-original-level bosses and other drop sources need separate treatment.

Source: https://news.blizzard.com/en-gb/article/23827590/diablo-ii-resurrected-ladder-season-two-has-concluded
(checked 2026-09-25).

### Weapon follow-up from the same reported TZ 93

Request 5 in run `20260925T094314Z-af7cd150` completed at
2026-09-25T09:59:27Z. The selected weapon is a superior ethereal Rondel,
unit 3408702359, with +1 attack rating and +2 Eldritch Blast in the captured total
stats. Its 96-byte item-data record has +0x2C = 0, +0x34 = 5 (superior quality
table identity), +0x38 = 1 and +0x3C = 0. No byte is in 93–97, so the expected
93/95/96 cannot be a plain byte/16-bit/32-bit integer in this sampled record.
The stat diagnostics report stable reads. This repeats the negative header result
for a weapon; it does not rule out a field beyond the sampled bytes or a packed
representation. Additional captures using this same header alone are unlikely to
locate the field; the next investigation should expand the bounded item-data sample
or establish the current-build layout against independently known-ilvl items.
