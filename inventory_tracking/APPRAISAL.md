# Alt+D memory appraisal prototype

Supported: main inventory, Horadric Cube, personal/shared stash, equipped items
and NPC shop grids using the tested native widgets on the executable hash in
`layout.py`. Item selection is memory-based. The decoder accepts all 692 locally
catalogued item bases and qualities 1–9, including nonmagical items with no stats.
It reads only the selected item's stats. Offline metadata provides ordinary stat
descriptions, Energy, skill bonuses, auras, charges and chance-to-cast descriptions.
Every stat entry is retained; unsupported encodings remain named raw values.
Reports are review drafts, not automatic trade valuations. Other widgets are
rejected. Runtime uses no OCR, price refresh, downloads or input.

This is **not complete tooltip decoding**: unique/set/runeword titles,
identification/ethereal flags, socket contents, final requirements, skill tabs,
per-level/time modifiers and other compound encodings still need work. Base
identity is not a named unique identity. Broad non-ring decoding awaits host
tooltip comparison. See [metadata sources and limits](items/data/README.md).

Cube selection passed the host A/empty/B/A sequence using the same native getter,
player-owned page 3 and its 3×4 grid. Cube appraisal decoding is enabled with
explicit container provenance. Host controls also passed: closing the Cube and
carrying an item both reject selection, then reopening/putting the item back
restores it. Four live Cube Alt+D requests completed in host run
`20260923T170842Z-2d23c68d`, with matching multiline text files and logs.
Cube selection also passed A/empty/B/A after a full game restart in host run
`20260923T171145Z-7e234660`, with a new process, owner and item pointers.
Alt+D also passed in that new process in run `20260923T171314Z-e29ac06f`:
both Cube rings produced review drafts; ring B retained its 10% FCR/+11 stamina,
and ring A's unsupported stats remained explicitly undecoded. Both text reports
matched the persisted log.
Stash capture `20260923T172942Z-6bfa931e` verified page 4, 10×10 grids, personal
and shared owners, empty space and return to the original item. The shared owner
is taken from the verified native selection, not substituted for the local player
globally. Decoding replays that selection and checks it against the stat record.
Stash Alt+D with the expanded decoder awaits user tooltip comparisons.
Equipment/shop capture `20260923T173519Z-f2e27ce2` verified equipment slots 3/4
through grid 0 and two shop items through an NPC-owned 10×10 grid on page 1.
Equipment slots 0–12 follow the native getter; shop pages 0–3 share its grid
path, with page 1 directly tested. Shop item-owner fields are unset; ownership
comes from exact pointer membership in the captured typed NPC inventory.
The production reader includes NPC traversal and rechecks inventory owner/type
and container before publishing. Live Alt+D with these newly enabled paths
awaits the user's varied-item review; no further fixed probe sequence is required.

## Run on the host

```sh
uv run --offline -m inventory_tracking.appraisal serve
```

Wait for **Ready for Alt+D**, focus D2R, hover an item, press **Alt+D**
and hold the hover until the notification. The installed Niri binding disables key
repeat. It is a global binding; the worker requires D2R compositor focus and exact
X11 process ownership before reading a request and before publishing its result.

Reports live under `inventory_tracking/runs/alt-d/<run>/`:

- `report.json`: attachment readiness or service completion/failure.
- `latest.json`: newest request only, including rejection reasons.
- `request-N/frozen.json`: frozen observed selection, stats and provenance.
  New captures also preserve a double-read 0x60-byte item-data record for further
  identity/flag research; it is revalidated before publication.
- `request-N/report.json`: local KB evidence or explicit rejection.
- `request-N/appraisal.txt`: readable multiline draft or rejection, also written
  to the terminal and `probe.log`. JSON artifacts retain the complete evidence.

The text includes observed stats, unresolved fields, review/price status and a
short offline evidence summary. Dated market asks are candidate comparisons, not
an approved item price. Undated asks are omitted from the text. Only requests
that pass the worker's current-request checks publish text; older results are
suppressed along with their JSON output.

Rich renders unresolved stat lines and undecoded-property review notes in bright
yellow in an interactive terminal. `NO_COLOR` or redirected output disables color.
Saved `probe.log` and `appraisal.txt` stay plain text; terminal rendering does not
alter their contents. Restart an existing worker after installing this update.

The desktop notification summarizes supported stats and identifies the report
folder. An unresolved price remains unresolved. Ctrl+C stops the worker. After
restarting D2R, restart this worker to attach to the new process; it will reject
requests for a stale process rather than reuse its pointers.

The agent must not launch the live worker: `development.md` reserves live memory
probes for the user. Agent-side verification uses captures, fakes and local IPC.

## Request guarantees and limits

Niri sends a small message to a private Unix socket. Requests older than one
second or repeated within350ms are discarded. A worker already running owns a
file lock; a second worker cannot remove its socket. Attachment checks executable
fingerprint and rescans unit tables. The one-second capture window includes focus,
UI reads, item traversal and stat capture. Failed/unsupported reads are explicit.

Selection input is bracketed across traversal, including the game's mouse
position. Selected header, owner/location and raw stat arrays are re-read before
freezing. Heavy KB retrieval runs on a separate thread, outside OSD sampling.
Newer requests invalidate older results; pending retrieval is cancelled when
possible. Focus, hover identity and stats are rechecked before publication.

These sequential reads are **not atomic**. Changes that revert between reads
cannot be universally detected. Host run `20260923T163055Z-1d937ede`, request 1,
completed an Alt+D ring appraisal (10% FCR, +11 stamina; price unresolved).
Request 2 rejected an unsupported owned-inventory context; its snapshot was not
saved, so the exact context is unknown. Cube run `20260923T170842Z-2d23c68d`
confirmed requests 3, 5, 6 and 7 on the same ring in page 3. All seven requests,
including three rejections, have matching readable text in `probe.log` and
`appraisal.txt`. These checks establish saved output, not visual notification delivery.
No general item decoding or pricing claim
is implied by the successful inventory-selection probes.

## Desktop binding

`/home/kpi/.config/niri/config.kdl` contains the Alt+D command using the absolute
uv path and repository directory. A timestamped sibling `config.kdl.before-d2r-alt-d-*`
backup was created before editing; Niri's own validator accepted the result.
Remove that one binding to undo it. No startup service was installed.

## Extending stat decoding

`items.metadata.decode_stats` keeps the public `(decoded, affixes, unresolved)`
contract. It loads the catalog, rejects duplicate/non-integer raw entries, assembles
provenance and unresolved rows, and suppresses colliding market facets.
`items/stat_constants.py` names native IDs, bit layouts and class/total labels.
`items/stats.py` contains stat-family functions and the `STAT_DECODERS` registry;
metadata-defined procs and generic scalars use the dispatcher fallback.

To extend coverage, add a captured tooltip/raw-stat regression and invalid cases,
then add or extend the appropriate family decoder. A decoder receives `StatContext`
and returns row fields, or `None` for an unsupported/invalid payload. Once selected,
a family owns the stat: rejection never falls through to a generic scalar. Only
scalar results carry a market label; derived base-type rows are appended separately
and never acquire invented memory provenance or rolled market facets. Keep Rich,
live reads and KB queries outside these decoders.

`tests/inventory_tracking/fixtures/decoded_items.json` preserves complete outputs
from six historical items before the refactor. Run the metadata tests first, then
`uv run --offline pytest tests -q`. For each new live example, the user runs the
worker, presses Alt+D and supplies a screenshot; compare the selected capture with
its readable log, keep unknown properties visible, and reproduce gaps offline
before changing interpretations.

## Follow-up work

- Extend other containers individually using verified host captures.
- Compare live Alt+D output across inventory, stash, equipment and shop items.
- Compare general decoder output with tooltips for rare/crafted, unique/set,
  runeword/socketed items, charms/jewels, charged items and chance-to-cast effects.
- Extend stat decoding and equipment-widget selection with separate evidence.
- User TODO later: remove superseded `hover/legacy.py`/`probes/hover_legacy.py` and their tests
  once the replacement is accepted, preserving the failed-lead documentation.

Variable scalar modifiers show definition ranges next to observed values. Rich
highlights perfect rolls bright green and the bottom 20% bright red. Unknown stats
and review notes retain their warning color. Magic charm ranges use captured affix
IDs for the correct tier. Fixed and out-of-range values are not ranked.
Socket rows show verified child item names or an explicitly labeled runeword recipe;
missing child evidence does not imply empty sockets. Restart the worker after edits.

For magic charms, the displayed range and highlight colors cover all spawnable
tiers for the same modifier and charm size, regardless of item level. The tier label
uses T1 for the strongest bracket, shows the current tier and the T1 range.
Exact captured-tier bounds remain in structured roll_range evidence. A Large Charm with 20 life (16–20 tier) is not perfect; 35 life is.
Disabled tiers and other charm sizes are excluded from this comparison.

Magic/rare scalar rolls now show eligible affix tiers for the base and rarity.
One tier label does not represent multiple overlapping affixes. Atma's single-source
poison stats combine into a damage/duration line; multiple-source poison stays explicit.

Completed socket scans report empty socket counts explicitly, including partially
filled items. Missing/failed scans stay unknown. Publication rechecks fresh candidates
before accepting the frozen contents; old artifacts without completeness remain unknown.

### Unknown panel discovery through Alt+D

Alt+D uses the usual selection/appraisal path for supported panels. If selection
fails while a mouse widget is present, it makes one additional bounded capture
including monster owners and all inventory grids. It saves both samples to
`request-N/panel-diagnostics.json`, referenced by the report, text log and desktop
notification. Empty slots and closed panels do not trigger expanded discovery.
Discovery failures preserve the original evidence and record the secondary error.

These samples are research evidence, not an appraisal: a later hover cannot
replace the requested item. Use ordinary Alt+D on mercenary/unknown panels and
inspect the resulting diagnostics; a separate timed hover probe is optional.
