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

## Win+S inventory collection

The same worker handles **Win+S** (Niri `Mod+S`, installed 2026-09-25): it reads every
item of the focused character — inventory, cube, equipped, mercenary equipment, personal
stash and all shared tabs — and the character sheet into the collection database
(`inventory_tracking/runs/collection/collection.sqlite`, `--collection-database`) and
notifies "<character>: N items · new · moved · gone". Reports land under
`inventory_tracking/runs/collection/<run>/` (`capture.json`, `report.json`). Each capture
also regenerates the searchable page (`--collection-html`, default
`inventory_tracking/runs/collection/collection.html`; `make open`) and records free
cells per grid (`… collection space --fits 2x4` lists mules with room). Query with
`uv run --offline python -m inventory_tracking.collection query <words>`. Plan and
research notes in `inventory_tracking/collection/`.

## Automatic collection when the stash closes

With `--stash-auto` (default since 2026-09-27; `--no-stash-auto` disables it) the
worker polls the game's open-panel flags twice a second (`--stash-poll-seconds`,
`layout_notes.md` "Open-panel flags") and runs the Win+S collection by itself every
time the stash panel goes from open to closed: sort the stash, close it, and the
database and page are refreshed without a key press. One visit yields one capture;
a game exit with the stash open is logged, not announced. Reports carry
`trigger: stash-closed`; the log line is "Stash closed; collecting".

## Automatic assessment after "identify all"

With `--identify-auto` (default since 2026-09-27; `--no-identify-auto` disables it) the
worker reads the identified flag of every magic-or-better item in the main inventory
and the Horadric Cube (tagged `[cube]`) once a second (`--identify-poll-seconds`; every five seconds outside town
while nothing unidentified is carried). Items that
were unidentified on the previous read and are identified now — Cain's identify all,
or a scroll — are read in full, decoded and run through the same offline KB Alt+D
uses. The OSD shows "Identified N — k keep · c check · v vendor" and, per item, the
verdict, its best-rolled stats (abbreviated: FCR, FR, @, life…) and the reason: keep
for a value watch, a confirmed farming build use, a high/mid trade tier or asks of one Ist or
more; check for an evidenced conditional build use, a leveling use, a low tier or small asks;
vendor otherwise, with the failed-rule count. Only keep/check items get a row; vendor
items are counted in the header and nothing else, and the desktop notification is
sent only when there is something to keep or check. Since 2026-09-28, the automatic
farming attention policy keeps starter-only roles quiet (Before Spirit, Starter,
Starter alternative, early, FoH Starter and Holy Bolt Starter progression labels).
Other conditional roles need positive matched evidence and an explicit remaining
condition; their reasons include progression and the conditions to review. Full
role assessments remain available in Alt+D. Independent value-watch, trade-tier,
price or reviewed leveling evidence can still justify an alert. Here the vendor
bucket means no supported reason for a farming alert, not a proof of zero value.
An unavailable price is described as "no supported estimate", not "no listings".
Slot-pattern leveling uses
("a ring with any life, mana or resistance", `generic: true` in the report) never
count and are no longer shown by Alt+D either. `identify-latest.json` in the run
directory holds every row and a `timing` block (since 2026-09-27: reader-lock wait,
memory read, decode and per-item KB retrieval in milliseconds, with the slowest
item); the worker logs the same as one `Identify timing:` line per pass and each
poll as `Identify probe:` (DEBUG, or INFO when a read took 250 ms or more or found
newly identified items). Alt+D closes the summary at once (over an empty cell it
closes it and shows nothing else). Since 2026-10-06 the
field is watched too and the comparison lasts for the whole game: a scroll used outside town
is assessed, an item picked up and identified between two field reads counts as well, and
neither a portal nor a failed read drops the earlier read (Cain right after the portal used
to be missed). Only the first read of a game (another player unit id, or attaching) is a
baseline, logged as `Identify baseline:`; `Identify probe:` names `town` or `field`.
Stash pages are not watched: a scroll used on an item lying in the stash is not assessed.
The poll skips while Alt+D owns the reader or the OSD.

## Owned copies and roll comparison

Since 2026-09-30 Alt+D and the identify summary look the item up in the collection
database (`--collection-database`, read-only; the data is only as fresh as the last Win+S or
stash-close capture) and compare it against the copies you still own.
"The same item" means the same unique/set (definition id), the same runeword, the same
normal/superior base (ethereal flag and socket count included), or a magic/rare/crafted item on
the same base with the same kinds of stats. Ethereal and non-ethereal copies never match. The
item under the cursor is not counted as its own copy. Every variable stat the two items share is compared
using its roll range and direction. The new item is **better** only when it beats every copy.
It is **worse/equal** when any copy rolls at least as well, and **mixed** otherwise. **Same**
means an owned duplicate with nothing variable to compare. Alt+D adds
"Owned: N x … — relation; rolls P% of max" after the stats, followed by the best-rolled copies
with per-stat differences ("new better: +165% Enhanced Defense vs 160"). The OSD shows the header and the top copy.
The identify reason gains "owned N: …". A keep that rests only on a matched build use becomes
**check** when an owned copy rolls at least as well. Trade reasons (value watch, tier, asks) stay
keep, because a second copy still sells. The Alt+D cache key includes the database's modification
time, so a new capture invalidates cached comparisons. Code: `appraisal/owned.py`.

## Character sheet and the equipped-only pass

Every collection also records the character sheet (since 2026-09-27): the player
unit's full stat list decoded into readable lines (attributes, life/mana/stamina,
defense, attack rating, resistances, gold, and every item/skill bonus such as faster
cast rate or magic find) plus the raw stat triples, one row per capture in the
`character_stats` table (schema 4) so the sheet has a history. Resistances are raw
stat values: the game subtracts the difficulty penalty and caps at the maximum before
display. Attack rating is the `tohit` stat, not the dexterity-derived sheet total,
and skill damage is not a stat. The notification's last line reads
"Level 92: str …; life …, mana …, defense …"; the page's "Characters" panel and
`uv run --offline python -m inventory_tracking.collection stats [name] [--history]`
list the lines. `collect --equipped` (`make equipped`, or `request --equipped` to the
worker; no key bound) records only what the character and the mercenary wear, still
with the sheet, and leaves inventory/stash placements untouched. Win+D stays the shop
scan (`shop/README.md`).

## Run on the host

```sh
uv run --offline -m inventory_tracking.appraisal serve
```

The worker may start before the game: while no `D2R.exe` is running it prints
**Waiting for D2R.exe**, and while the game sits in its menus with no character in a
game (no unit table yet) it prints **Waiting for a character in game**; both publish
`report.json` with state `waiting` and retry every `reconnect_delay` seconds (default
2), and menu-time image captures are removed rather than kept as attachment evidence.
Other attach failures (unsupported build, memory access) still abort. Wait for **Ready for Alt+D**, focus D2R, hover an item, press **Alt+D**
and hold the hover until the assessment appears in the right-side OSD. The installed Niri binding disables key
repeat. It is a global binding; the worker requires D2R compositor focus and exact
X11 process ownership before reading a request and before publishing its result.

Reports live under `inventory_tracking/runs/alt-d/<run>/`:

- `report.json`: attachment waiting/readiness or service completion/failure;
  `attachment_directory` identifies the latest successful attachment.
- `attachment-*/image.bin` and `capture.json`: per-attempt image evidence. New
  attachments use fresh directories, including retries after partial failures.
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

`ItemAssessment` in `inventory_tracking/appraisal/presentation.py` builds one
immutable document of semantic `StyledLine` entries. Its `to_text()`, `to_rich()`
and `to_osd()` methods feed saved reports, terminal logs and the OSD respectively.
The compatibility functions in `appraisal/text.py` delegate to this model; shared
section wording lives in `appraisal/sections.py`. Pricing/demand calculations
remain in the KB assessment engine.

The shared palette in `inventory_tracking/presentation.py` controls both terminal
and OSD colors: magic blue, rare yellow, unique/runeword gold, set green, crafted
orange, normal white and socketed/ethereal normal bases gray. Perfect rolls are
green, low rolls red, unreadable stats yellow, valuable candidates magenta and
build demand cyan. Color describes the stated fact; item rarity alone does not
imply value. Styles attach to individual lines, so identical stat text can carry
different roll grades.

OSD IPC carries text plus semantic tones; GTK renders escaped Pango markup.
Terminal logs use Rich spans from the same model. `NO_COLOR` disables terminal
colors; redirected output, `probe.log` and `appraisal.txt` stay plain text.
Restart the worker to load presentation or palette changes.

The click-through assessment card is drawn on the HUD canvas (`inventory_tracking/hud`,
started by `serve`; plan in `hud/plan.md`). It sits in slot `assessment` of
`HUD.slots`, positioned in fractions of the D2R window (default 20% from its left, 12%
from its top), and is at most 45% of the window wide; longer lines wrap and output
longer than the window is ellipsized. The canvas follows the game's output via Niri
(`OSD.monitor` can pin a monitor index) and hides while D2R is unfocused. The card
appears only after Alt+D and hides when the item, stats, viewer context or game focus
changes, or after 30 seconds from completion. Hover checks run every 0.2 seconds; a
stalled worker's layer lease expires after 1.5 seconds. Returning to the item does not
reopen the card: press Alt+D again. The complete text remains in `appraisal.txt`.
`hud.log` in the run directory records canvas startup/display errors.

Override the display duration and cache expiry when starting the worker:

```sh
uv run --offline -m inventory_tracking.appraisal serve --osd-seconds 30 --cache-seconds 300
```

Defaults live in `APPRAISAL` in `inventory_tracking/config.py`. `--no-osd` retains
the desktop notifications. With the OSD enabled, reports and rejections remain
in the terminal/files without a second desktop notification.

The in-memory cache holds up to 128 results for five minutes (not extended on
hits), using SHA-256 of the decoded observation, game identity and KB file
revision. Capture timestamps are excluded; item identity, raw unresolved stats,
viewer context and all other facts remain part of the key. A cache hit skips KB
retrieval but still captures and rechecks the hovered item, resets the display
timer and records `cache_hit` in the report. Errors are not cached; restarting the
worker clears the cache. KB and SQLite WAL changes invalidate matching keys.

An unresolved price remains unresolved. Ctrl+C stops the worker and its overlay.
After D2R restarts, the next Alt+D request reattaches with fresh process pointers
and a separate capture directory. If attachment takes over one second, press Alt+D
again to capture the current hover. Restart the worker after Python code changes.

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

### Published offline KB (default)

Build and validate the offline artifacts/index first, then package them:

```sh
uv run --offline python -m pricing.knowledge.publication
uv run --offline -m inventory_tracking.appraisal.service serve
```

The worker warms the publication before reporting ready. Since 2026-10-06 a passed
validation is recorded in the generation directory (`validated.json`: generation plus
a fingerprint of the validating code, `published_runtime.validation_code`), so a
restart validates again (~13 s) only after a new publication or an edit under
`pricing/knowledge` or `inventory_tracking/items`; otherwise it loads in ~2.5 s. The
lookup processes start first and warm up while the worker loads the KB and waits for
the game. Each hotkey pins a runtime
and UTC appraisal date through capture/decoding, asynchronous retrieval, cache hits
and hover rechecks. Cache keys include generation, date and update diagnostics.
A malformed update can retain the previous valid runtime; no valid initial bundle
or a changed retained index rejects appraisal. Publication details remain in JSON.
Use --publication-store to select a different store. Explicit --database selects the
legacy/test-index workflow; it is mutually exclusive with --publication-store.
Publishing updates a running published worker at the next request boundary. Restart
for Python changes or to migrate an existing legacy worker. A missing initial bundle
requires the publication command above; there is no silent working-tree fallback.

### Per-level weapon damage display

The physical damage pair includes a verified native218 maximum-damage bonus at
its recorded viewer level. The renderer preserves original rows and the separate
per-level modifier line. Invalid, unknown or duplicate formula evidence is not
added. Dread Edge's saved capture now matches its22–91 tooltip instead of22–46.
This is a display calculation; comparison facts and market coefficients do not change.

### Compact build uses and full saved-record details

Terminal and OSD share the compact Build use summary. Inspect a saved record with:

```sh
uv run --offline -m inventory_tracking.appraisal.build_use_summary path/to/record.json
uv run --offline -m inventory_tracking.appraisal.build_use_summary path/to/record.json --full
```

Accepts a worker record containing `result`, or the result itself. `--full` retains
all uses, including failed/unknown roles, conditions, alternatives and source
locators. The full view is available even when the OSD cannot expand details. No matching
or pricing is recomputed. Restart the worker to load the updated Python formatter.


Prepared stat annotations use an independent marker: `● [desirable]` in green or
`● [supporting]` in blue. The stat text retains its roll-quality color, so a useful
stat can still have a red low-roll value. Plain text retains the labels. Terminal
and OSD share the same styled segments; markup is escaped literally. Unknown requirements produce no positive marker, and no default grey/trash marker is
assigned. Multiple-stat display lines remain unmarked until their attribution is
reviewed. Reviewed amulet skill/FCR combinations can carry markers while their overall
build fit remains conditional on the full loadout. Advisory reviews never bypass
typed socket, skill, equipment or other dependency checks.

### Value-focused leveling output (2026-09-29)

The shared text/Rich/OSD report displays only the strongest reviewed leveling
recommendations (`high`). Ordinary `med`/`mid`, `low` and generic slot-pattern
recommendations stay in structured assessment evidence and are omitted from
visible reports. Trade tiers, item stats, roll ranges and pricing are independent
of this display filter. Retained high recommendations still show set companions,
other conditions and verified equip-requirement shortfalls. The user's scope is
Non-Ladder trade value plus valuable/exceptional leveling items, not a generic
leveling walkthrough. High-review coverage still requires the broader value-scope
migration; hiding a line does not establish a completed item assessment.
