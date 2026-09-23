# Inventory hover research — 2026-09-23

Selection remains unvalidated. No Alt+D listener or automatic appraisal is enabled.
The former table at RVA `0x1e010a0` returned zero in correctly performed host runs.
Do not repeat that probe unchanged.

## Runtime analysis

The original D2R.exe open in Binary Ninja matches `layout.SUPPORTED_SHA256`, but
bytes at `0x14009d9f0` differ from the saved runtime capture. The disk view begins
`7b f2 ed 30`; captured code begins `48 83 ec 68`. Analyze captured instructions,
not the on-disk decompilation, for these paths.

An analysis-only derivative is in the ignored run directory:
`runs/hover-appraisal/20260923T154015Z-449adb69/analysis-runtime.exe`.
Its source `image.bin` SHA-256 was checked against `capture.json`:
`7729eb7652c055a589f8a15b72662513e7e4a36b327ee6d20757dc083ee7d6ef`.
Stable captured blocks were placed at their RVAs, section raw offsets rewritten
to RVAs, raw sizes rounded to 512, security/debug directories cleared. The source
executable was not changed. Missing pages are zero placeholders, **not evidence**.
`analysis-runtime.json` preserves the captured RVA ranges. This is not a runnable
PE or a complete atomic snapshot. Some captured code also defeats decompilation;
check instructions and capture coverage before adopting any field.

Binary Ninja currently has this derivative as `view_5`; re-list views rather than
assuming handles persist. Original executable and loader views remain untouched.

Evidence at preferred base `0x140000000`:

- `sub_14009d9f0`, case 9, writes byte table+1 at stride 16 and calls
  `sub_140104a40`. The latter reads active byte at +0, special-cases unit type 5,
  resolves ID/type through `sub_14006ca20`, then clears active. This is not proof
  of inventory hover. The historical parser treats two bytes as active, whereas
  these instructions distinguish +0 and +1; do not promote it to production.
- `sub_1402197f0` calls `sub_1401ed340(widget, &position)` and passes its returned
  item to `sub_14021c6b0`, which builds an item tooltip through `TooltipsPanel`.
- `sub_1401ed340` follows `[image+0x1ee5790] -> +0xd0`, compares widget pointers at
  context+`0x178` and +`0x190`, and uses virtual methods +`0x90` and +`0xc0` in the
  mouse path. The controller path reads widget+`0x544`. It checks carried-item
  state separately through player inventory+`0x40`.
- Widget+`0x5c4`/+`0x5c8` resolves the **inventory owner** in the caller. It is not
  established as hovered-item ID/type. Do not mistakenly use it as selection.
- This establishes a bounded UI path worth sampling, not a validated stored item
  pointer. No game function is invoked by the probe, and no selection is inferred
  from cursor coordinates.

## Next host capture

```sh
uv run --offline -m inventory_tracking.hover_ui_probe
```

Open inventory and choose two distinct items A and B (rings are useful, but are
not required). Follow prompts: **A → empty inventory space → B → A**, without
clicking or moving items. Initial delay 5 seconds, subsequent delays 3 seconds;
hold each position until `CAPTURED`. Flags `--delay` and `--interval` can extend
these delays. The agent must not run this live command under development.md.

The build-gated probe captures at most two 0x700-byte widget records per UI
observation, their in-image vtable entries, pointer-chain anchors and the existing
bounded item/player traversal. It captures UI before/after traversal, preserves
raw differences and checks process/mapping stability. Raw bytes are observations,
not fields with assumed meanings; owner/item mapping must be checked offline.
No heap scan, OCR, grid heuristic, injection, writes or automated input is used.

Artifacts: `runs/hover-ui/<run>/report.json`, `sample-0.json` through
`sample-3.json`, plus ordinary attachment capture files. `state:complete` means
capture finished, **not selection validated**. Errors publish `failed` and
`finished_at`; unavailable UI records remain in samples for diagnosis.

After comparison, trace the captured widget vtable's +0xc0 getter and inspect
candidate pointer/ID changes against each item's owner/location. If a selection
field is found, validate held-item vs hovered-item, inventory closed, movement
during capture, and process restart before wiring a hotkey.

## Host redo and native getter — 2026-09-23

Use `hover-ui/20260923T160356Z-eb4472f9` as the intended A/empty/B/A sequence;
the user requested a redo after the two earlier runs. All four UI paths were
stable, with complete item/player traversals. Widget `0x38c78d50`, vtable
`0x141712de8`: +90=`0x14021a680`, +c0=`0x14021a6d0`. Widget+558 is a changing
string pointer; +560 lengths are 101/0/57/101. This corroborates tooltip changes,
not item identity. No changing item ID or pointer was found in the widget record.

The native +c0 getter resolves the typed owner at widget+5c4/+5c8, obtains its
inventory, and returns a pointer from the inventory's native cell table. The +90
method calls `sub_14021a2f0` to transform the game's mouse position using native
UI parents, dimensions and scale. This is not the world-hover table.

Relevant paths established by runtime code:

- `sub_14065e530`: follows parent+30, position/size+70, anchor+48/+4c, scale+80,
  and special layout flag+52. `sub_140184620` multiplies ancestor scales.
- `sub_140276e30`: inventory at unit+90, with an alternate +98 guarded by a
  reference object at +a0. Capture both; do not blindly assume +90.
- `sub_14027e820`: inventory magic1020304, array+20/count+28, 32-byte records;
  native getter selects page+2. Record dimensions are bytes+10/+11, cells+18.
- Mouse gate/global position begins image+1ec9c4d, position+1ec9c50; carried-item
  state begins image+1ec9f4c. These are research inputs, not validated semantics.
- Real capture contains a player and an item with the SAME unit ID279514537.
  Owner lookup must match `(type, ID)`, not ID alone. The widget owner type is0.

Probe revision2 adds these bounded raw inputs under sample.after.native:
up to16 ancestors, typed owner header, both inventory candidates and native cell
records (max16x16). All read blocks are retained and rechecked, with process and
mapping checks through ResearchReader. No coordinate-based selection algorithm
has been enabled. Repeat the same host command and sequence once to acquire
these newly identified pointed-to records. report.probe_revision distinguishes
new captures. Inspect raw stability/errors before interpreting any native result.

## Native lookup replay established — 2026-09-23

Revision2 run `20260923T161018Z-77c342c8` resolves as follows, saved in its
`selection-replay.json`:

| Sample | Native cell | Result |
| --- | --- | --- |
| A | 3,0 | Magic Ring, unit71604348, pointer0x10c5e3040 |
| empty | 4,1 | Null cell pointer |
| B | 5,1 | Full Rejuvenation Potion, unit1114609378, pointer0x10c5dff40 |
| A | 3,0 | Same ring pointer and ID |

Owner110569843 and item inventory page0 agree. Native memory supplied the mouse
position, UI parent transforms, scale and inventory cell pointers. No screenshot,
OS cursor query, fixed screen rectangle or guessed inventory spacing is used.
The widget's text allocation changed in sample0 at +558/+559. It is not consumed
by the getter; replay compares all other widget bytes and all other native blocks.

`hover_selection.resolve_selection` reproduces the observed ordinary mouse path
with float32 arithmetic; helper1415707ec rounds half away from zero and15989b8
is floorf (checked using saved runtime instructions and constants +/-1).
Special layouts, alternate inventories, carried items, other widget vtables,
changed inputs, incomplete traversal, and owner/page disagreement abstain.
This is still a research result: sequential snapshots are not atomic and selected
unit headers/stats need revalidation when a production request is frozen.

Binary Ninja endpoint became unavailable during this pass. Saved PE instructions
were inspected using objdump; no live process was read by the agent.
The compact fixture `tests/inventory_tracking/fixtures/hover_native_sequence.json`
preserves raw observations and a projected two-item traversal with source metadata.

Revision3 prints automatic selection results. Next controlled host command:

```sh
uv run --offline -m inventory_tracking.hover_ui_probe --scenario controls --interval 5
```

Prompts: hover A; close inventory; reopen and hover A; pick up A and hover B while
holding A; put A back and hover A. Expected: ring, abstention, ring, abstention,
ring. These controls distinguish a usable selection from a stale or carried item.
Defaults for ordinary sequence stay5/3/3/3. A fresh process restart and a repeat
ordinary sequence remain desirable before production integration. No Alt+D yet.

## Host controls passed within tested scope — 2026-09-23

Revision3 `20260923T161802Z-7b05872c` completed the five controls:
ring71604348 → unavailable (closed inventory) → same ring → unavailable
(carrying A over B) → same ring. All UI paths were stable. Closed inventory
was rejected as unsupported focus; carrying A over B was rejected as a different
widget vtable. This demonstrates abstention in that controlled state, not proof
that the carried-item guard alone was exercised for every possible widget.

Negative captured fixtures are in `hover_native_controls.json`; positive ring
sequence coverage remains in `hover_native_sequence.json`. Unit lists are omitted
from the control fixture because both rejections happen before unit lookup.
Next host dependency: full D2R restart, reopen inventory, repeat normal A/empty/B/A
with `uv run --offline -m inventory_tracking.hover_ui_probe`. Compare process
identity and recomputed owner/item pointers; don't require old unit IDs to persist.

## Restart confirmed, inventory scope — 2026-09-23

Run `20260923T162028Z-8d6de964`: old process4077750/start294622313 changed to
4083221/start294681925. New owner3362948688, ring3014701145, pointer0x6fff6480.
A/empty/A resolved correctly with new identifiers. B was rejected as a different
widget; user confirmed B was in equipment or another panel. It is not a failed
main-inventory restart observation, nor evidence of equipment support.
Runtime getter1402178e0 reads widget+5d8 and inventory grid0, unlike the supported
main inventory getter; this equipment path remains unimplemented.

Alt+D request worker implementation and current limitations: [APPRAISAL.md](APPRAISAL.md).

## Cube capture — 2026-09-23

Host run `hover-ui/20260923T164340Z-ecbea3c1` (user confirmed open Cube)
resolved A3885838183 / empty / B3014701145 / A3885838183, cells (0,0), (1,0),
(2,0), (0,0). All UI paths stable. Same vtable image+1712de8 and native getter
image+21a6d0; widget+630=3 selects inventory grid index5 via page+2. Grid3x4,
cell size98x98, origin437,485, player owner3362948688. RingB is the same unit as
the previous main-inventory Alt+D success, now page3. No new getter needed.

Selector now explicitly allows verified pages0/3 only, checks Cube3x4 dimensions,
and emits container provenance. Decoder accepts the selected page explicitly,
retains current-player ownership and page equality checks; default stays page0.
Frozen observation and readable report name Horadric Cube. No other container
support inferred. Projected raw fixture preserves the four native block captures.
Cube close/reopen, carried-item controls, Alt+D stats and fresh-process Cube
verification still pending host runs; this sequence alone does not validate them.

### Cube controls passed

Host `hover-ui/20260923T170535Z-c043dc5d`, same process4083221/start294681925:
A3885838183 / closed Cube rejected (`Unsupported focus state`) / same A /
carrying A over B rejected (`Carried item unsupported`) / same A. All five UI
paths stable, no native capture errors. Carried sample retains supported vtable
141712de8 and exercises the inventory+40 carried-item guard, unlike the earlier
main-inventory control that rejected through its widget guard. Captured regression
`hover_cube_controls.json` covers the full sequence and recovery. Cube Alt+D and
fresh-process checks remain pending.

### Cube Alt+D and readable logging confirmed

Host `alt-d/20260923T170842Z-2d23c68d` completed normally. Requests3/5/6/7
completed for ring3014701145, owner3362948688, Cube page3 cell2,0, observing
10%FCR/+11stamina. Price remains unresolved; review draft only. Requests1/2/4
rejected (magic-ring-only decoder / unsupported widget / unsupported widget).
No rejected snapshot exists to establish their exact UI contexts.
All seven appraisal.txt files exactly match the formatter and occur once each in
probe.log; latest.json equals request7/report.json. Confirms persisted multiline
output and Cube provenance, not visual notification delivery. Process is still
4083221/start294681925; fresh-game Cube validation remains pending.

### Cube selection after full restart confirmed

Host `hover-ui/20260923T171145Z-7e234660`: new process4104866/start294991045
(previous4083221/start294681925), new player284532388. A3730245230 pointer1704084576
at0,0 / empty1,1 / B2628652253 pointer1704084128 at2,0 / same A. All paths stable,
no native capture errors, Cube page3 in all four results. Offline replay verified
and saved as selection-replay.json in the run. This validates selection after
restart; Alt+D stats/publication in the new process still needs a host request.

### Cube Alt+D after restart confirmed

Host `alt-d/20260923T171314Z-e29ac06f` attached to new process4104866/start294991045,
completed normally. Request1 selected A3730245230 at0,0 (no supported affixes;
unknown stats preserved), request2 B2628652253 at2,0 (10%FCR/+11stamina), both
owner284532388 and Cube page3. Captures91.27/94.43ms; local retrieval75.31/58.64ms.
Both are REVIEW drafts with unresolved prices. Both appraisal.txt files match the
formatter and occur exactly once in probe.log; latest.json equals request2 report.
This completes the planned Cube restart selection + appraisal check. Other
containers and general stat decoding remain outside this verified scope.

### Ring A screenshot correlation — 2026-09-23

User supplied tooltip after the restart Alt+D run: **Ring of Wizardry**,
**Required Level: 33**, **+16 to Energy**. This identifies ring A from
`alt-d/20260923T171314Z-e29ac06f/request-1`, unit3730245230 in Cube cell0,0.
Its sole unresolved stat is {layer:0,id:1,raw:16}, matching displayed Energy16.
This is one screenshot-correlated observation for extending stat coverage; the
current decoder still leaves it unresolved. Verify the local market property
mapping before implementation and add a captured regression. Required level33
and title are screenshot evidence only; no memory offsets/decoding inferred.

## Personal/shared stash — 2026-09-23

Host hover-ui/20260923T172942Z-6bfa931e: same native inventory vtable/getter,
page4 -> grid6,10x10, origin213,279. Personal owner284532388, shared owner142258002;
both typed player units, inventory+90, no alternate pointer. Sequence resolves
personal3996387037 (class461, magic, multi-cell item hovered at1,0 with anchor0,0),
empty2,0, shared985832484(class535, rare) at0,0, original personal at0,0.
All paths stable/errors empty. All29 personal and37 shared grid items match their
native owner IDs. No need to weaken item-owner equality. Projected fixture preserves
both selected items, player-selection stats and native blocks.
Selector allows page4 with10x10 dimensions, labels personal/shared by local-player
identity. Decoder receives alternate owner only after selected_observation replays
native selection against the same snapshot and checks the exact resource record.
Item owner and local player are separate source fields; non-stash alternate owners
remain rejected. Tests cover no-provenance and changed-owner rejection.

User also requested shops/equipment and minimal probe iterations. Probe revision4
adds --scenario panels: equippedA/equippedB/vendorA/vendorB, includes monster
traversal and all bounded grid records/cells (<=32 grids,16x16 each) for native
getter research. Default probe/production capture remain targeted. Equipment/shop
are NOT enabled by this probe change; consume host evidence before decoder changes.

## Equipment and NPC shops — 2026-09-23

Two host panels runs:173451Z-a82603dc captured equipment during its first shop
prompt; prefer173519Z-f2e27ce2, which has four stable intended samples and no
native errors. Equipment vtable1417129d0/getter1402178e0, local owner284532388,
widget5d8 slots3/4 -> inventory grid0 (13x1) -> item848037454(class373,quality2)
and2029165619(class235,quality7). Both mode1/page255/body_location matching slot.
Saved runtime disassembly confirms signed slot load, unsigned <=12 check, grid0,
then direct cell pointer at slot*8. No screen transform used for this getter.

Shop widget uses existing141712de8/getter14021a6d0, NPC(type1)492907658,
inventory+90, page1/grid3 (10x10), origin214,288. Hover cells9,1 and8,1 resolve
606745366(class42) and44446050(class17), both magic. Each can occupy multiple
cells; item anchor differs correctly from hovered cell. All27 items in that grid
have mode0/page1/item-ownerFFFFFFFF. Exact captured NPC grid membership establishes
inventory ownership; do not substitute the local player's ID or treat the item
owner sentinel as an NPC ID. Other captured vendor grids2/4/5 are also10x10;
shop pages0..3 use the same native getter, but only page1 was directly hovered.

Implementation: equipment bypasses grid coordinate transform and validates slot,
local owner/mode1/page255; shop requires complete typed monster traversal,10x10
grid and sentinel owner on its item. Native capture targets grid0 for equipment.
Production traversal includes monsters. selected_observation replays exact native
selection before passing shop owner type/id to decoder; decoder handles mode and
page by context, records owner_id/owner_type/item_owner_id separately. Publication
recheck now compares inventory owner/type/container as well as item identity/stats.
Projected captured fixture/regressions cover all4 selections, wrong slot/owner and
end-to-end decoder context. Actual new Alt+D outputs still await user review;
use user's varied-item checks instead of another long fixed probe sequence.
