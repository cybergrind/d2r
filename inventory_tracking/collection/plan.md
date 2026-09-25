# Item collection plan — Win+S capture, cross-character database, searchable HTML

2026-09-25. Plan only; nothing below is implemented. Decisions confirmed by the user
the same day are folded into the body (see "Resolved decisions"). Companion to the Alt+D
[appraisal notes](../APPRAISAL.md) and the [package overview](../README.md).
Rules for every step: red/green per [development.md](../../development.md), then
`uv run pytest tests -q` and `uv run pre-commit run --all-files`. Host probes are
run by the user; agents read the run artifacts. Commit only when asked.

## Goal

Every mule's inventory indexed and searchable. One hotkey (**Win+S**, Niri `Mod+S`)
records every item the game currently exposes for the logged-in character — main
inventory, Horadric Cube, equipped items, mercenary equipment, personal stash, all
shared stash tabs — into a durable database keyed by item content, with the
character name, container, tab and grid cell for each placement. From that database
a single self-contained HTML file lists every item with its name, base, decoded
stats, sockets and socket contents, runeword name and location, searchable by set
name, unique name, stat text, socket count/contents and runeword.

Workflow: log into each mule in turn, open the stash if R2 says it is required,
press Win+S once, log out. The shared tabs are re-read on every press, so the last
capture is authoritative for them; personal containers are authoritative per
character. Re-export the HTML whenever the database changed.

**No assessment in this scope.** Valuable/trash tiers, build roles, set-completion
suggestions and any knowledge-base retrieval are deferred to the appendix at the end
of this plan and are not a dependency of any step below.

Out of scope for this plan: moving items automatically, live price refresh,
ground/vendor items, multiplayer characters, the belt (potions only).

## What already exists and is reused unchanged

| Need | Existing code | Status |
| --- | --- | --- |
| Enumerate every item unit with owner, page, grid cell, body slot, mode | `native/unit_probe.sample_units` → `native/units.walk_units` / `describe_item` (quality, owner_id +0x0C, page +0x55, body +0x54, x/y) | production |
| Read one item's three stat arrays, 0x60 item-data bytes, local damage/defense modifiers, socket children | `native/resource_probe.read_item_arrays`, `native/socket_items.read_socket_items`, `appraisal/capture.verify_item` | production, selected-item only |
| Decode base, rarity, identity (unique/set/rare/runeword), flags, affixes, roll ranges, sockets | `items/decode.decode_items` and `items/*` | production; ilvl unknown ([research](../item_level_research.md)) |
| Container naming, owner validation | `items/containers.container_for_page`, `hover/selection._resolve` (page 4: personal if owner == player else "Shared stash") | production, but every shared tab collapses to one label |
| Local player identity and name | `tracking/state.select_player` (unique plausible-life unit), `native/units.describe_player` (name) | production |
| Hotkey → worker: Unix datagram socket, focus guards, run directories, OSD, notifications, result cache | `appraisal/service.py`, `appraisal/worker.py`, `appraisal/cache.item_key`, `appraisal/overlay.py` | production; datagram body is a bare monotonic float |
| Niri binding pattern | `~/.config/niri/config.kdl:378` (`Alt+D repeat=false { spawn … appraisal_service request }`) | `Mod+S` and `Mod+Shift+S` are unbound (checked 2026-09-25) |

The gap is therefore not decoding. It is: **(a)** reading *all* owned items in one
bounded pass instead of the hovered one, **(b)** naming shared stash tabs and the
character, **(c)** a stable per-item identity across game sessions, **(d)** durable
storage, **(e)** the HTML export. The service's knowledge-base warm-up stays as it
is for Alt+D; a collect request never calls the KB.

## Research pass (Step 0) — what to find out and how

Each item below ends with a dated note in `inventory_tracking/collection/research.md`
and, where a capture is involved, a fixture under `tests/inventory_tracking/fixtures/`.
Run order matters: R1–R3 use one host session; R4 needs two sessions. The old R6
(assessment throughput) moved to the appendix; R7 keeps its number.

### R1. Shared stash tab identity

Observed: `hover_stash_sequence.json` has seven player-type units all named
`CybergrindAA`; only two of them own page-4 items. Current code labels any non-player
page-4 owner "Shared stash" without a tab number.

Lead: d2go (`third-parties/d2go/pkg/memory/item.go:21-44`) treats player units carrying
the `Sharedstash` state as the shared tabs, ordered by unit order, and reads states
from the stats-list structure at `+0xAF0` (`player.go:148`, six u32 bit words). Our
`describe_player` already holds `stats_pointer`; the state words are a bounded read
next to the arrays we already validate.

Method (host, one session, stash open): put a distinctive count of items in each tab —
1 item in shared tab 1 at cell (0,0), 2 in tab 2, 3 in tab 3, 4 in the personal
tab — then run `uv run -m inventory_tracking probe --units --resources` and Alt+D one
item per tab so `frozen.json` records the selection's `owner_id`. Deliverable: the
owner-unit → tab mapping rule (state bit + ordering, or another marker), whether the
personal tab's owner is the main player unit, how many shared tabs RotW exposes, and
a fixture. If the state read is unverifiable, fall back to ordering by unit order
and mark tabs "shared A/B/C" until verified.

### R2. When are stash units present?

Question: do the stash owner units and their items exist in memory when the stash
panel is closed, or outside town? This decides whether Win+S must be pressed with
the stash open (and the UX text on the OSD).

Method: `probe --units` three times — stash open in town, stash closed in town,
in the field — and count page-4 items per owner. Deliverable: the precondition
Win+S enforces, and the rejection message when it is unmet.

### R3. Character class and level

The name is read; class and level are not. Level is stat 12 in the player's full
stat array (verify against the character screen); class is expected in the player
unit's `txt_id` (verify: d2go reads class from the unit header; compare across two
characters, including a Warlock). Deliverable: `describe_player` additions with
their evidence, and the Warlock class id.

### R4. Stable item identity across sessions

Unit ids and pointers change between games; the database needs a content key.
Lead: the D2R item-data record matches the legacy `D2ItemDataStrc` for its first
0x1C bytes (quality +0x00, owner +0x0C, flags +0x18 are already host-verified), so
`pSeed` (+0x04, 8 bytes) and `dwInitSeed` (+0x10) are the candidate seed fields
(`third-parties/D2MOO/source/D2Common/include/Units/Item.h:17-24`).

Method: capture the same stash in two separate game sessions (R1 layout kept),
diff every item's `item_data_hex` and stat arrays. Deliverable: which bytes are
constant per item (seed candidates), which vary (owner, cell, pointers), and the
fingerprint definition — recommended: sha256 over base code, quality, the constant
item-data bytes, the +0xE8 stat array, and socket-child fingerprints. If no seed
survives, fall back to the content hash alone and accept that two identical
perfect items collapse into one row with a count.

### R5. Full-pass read cost and stability window

`ResearchReader` caps 8 MiB per pass and 8 KiB per read; Alt+D enforces a
one-second freeze window. A full pass reads ~(40 inventory + 12 cube + 13 equipped
+ 100 × tabs) items × (three stat arrays + 0x60 bytes + socket scan).

Method: a probe that walks all owned items with `read_item_arrays` and reports
bytes, milliseconds and instability count; run with a full stash. Deliverable:
the batch capture budget and whether one pass can be treated as a consistent
snapshot (table heads and unit headers rechecked at the end, as `sample_units`
already does) or must be chunked per container.

### R7. Hotkey delivery

Confirm `Mod+S` reaches the compositor while D2R (X11 under Proton) is focused, the
same way `Alt+D` does; confirm Steam's overlay does not claim it. Method: bind to a
`notify-send` first. Deliverable: the config.kdl line.

## Resolved decisions (user, 2026-09-25)

- Win+S reads main inventory, Horadric Cube, equipped items, personal stash, all
  shared stash tabs, and the mercenary's equipment when the merc unit is readable
  (labeled `merc of <character>`).
- The existing appraisal service is extended; one process registers both hotkeys
  (Alt+D appraise, Win+S collect). No second worker process.
- The database lives under the git-ignored `inventory_tracking/runs/` tree.
- Scope is indexing only: the HTML carries names, bases, stats, sockets, runewords
  and locations. Assessment, tiers and organization views are deferred (appendix).

## Design (to be confirmed by Step 0 findings)

### Package

```
inventory_tracking/collection/
  plan.md, research.md        this plan; dated research notes
  models.py                   pydantic: Character, Placement, ItemRecord, CaptureRun, AssessmentRow
  capture.py                  full-pass read of owned items → list of observations + placements
  containers.py               tab naming (R1), precondition checks (R2)
  fingerprint.py              stable item key (R4)
  store.py                    SQLite (stdlib sqlite3) open/upsert/query; schema migrations
  export.py                   single-file HTML generator
  __main__.py                 collect / status / query / export
```

The Win+S request is handled **by the existing appraisal service**, not a second
process: it already owns the game attachment, focus guards, KB backend, OSD and
run directories. The datagram protocol grows from a bare float to
`collect <monotonic>` (bare float stays Alt+D). Worker gets a second request kind
with its own lock so a running collection never blocks Alt+D beyond the capture
itself.

### Storage

SQLite at `inventory_tracking/runs/collection/collection.sqlite` (git-ignored,
`--database` override), plus per-capture JSON evidence under
`runs/collection/<run>/` like Alt+D. Tables:

- `characters(name, class, level_seen, first_seen, last_seen)`
- `items(fingerprint PK, base_code, name, rarity, identified, ethereal, sockets,
  observation_json, first_seen, last_seen)` — observation is the same structure Alt+D freezes
- `placements(fingerprint, character | 'shared', container, tab, x, y, capture_id,
  seen_at, gone_at)` — one open row per current location; closed when a later full
  capture of that container no longer shows the item
- `captures(id, character, containers_json, started_at, item_count, status)`

No assessment table in this scope; a later schema migration adds one.

Sighting semantics: a capture is authoritative for the containers it fully read. Shared
tabs seen from any character update the shared rows; personal containers update
only that character. Items never seen again keep history through `gone_at`.

### HTML export

`export --html <path>` writes one file: embedded JSON of items and placements plus
inline CSS and vanilla JS. No external assets so it opens from `file://` offline.

Per row: item name (unique/set/rare title or magic name), set name
where the item belongs to a set, base name and code, rarity, ethereal/unidentified
flags, decoded stat lines as the Alt+D text shows them, socket count, socket
contents (rune/jewel/gem names) and runeword name, character, container, tab and
cell, last seen. One search box matches all of those as text, so "Tal Rasha",
"Enigma", "+2 to All Skills", "Ber" and "Sacred Armor" all work; a socket filter
accepts an exact count or "empty". Filters for character and container/tab;
sort by name, base or last seen. Row expands to the full decoded stat list and
unresolved fields.


## Execution status

- 2026-09-25 — Step 0 folded into [research.md](research.md) from the Alt+D run
  `20260925T111336Z-15857918`: R2 (town) answered, R3 answered (class = player
  `txt_id`, 7 = Warlock; level = stat 12), R4 answered (no seed in D2R item data;
  content fingerprint is final). R1 needs a live read of player unit +0xD8 and the
  `Sharedstash` state bit (word 5, bit 25 at stats +0xAF0) in Step 2, validated by
  the user's tab numbers for four named items. R5 and R7 move into Step 2/3 gates.
  New questions: a probable materials tab (73 unowned page-4 stacks at (0,0)) and a
  second player unit `Caras`.

- 2026-09-25 — Step 1 implemented: `models.py`, `fingerprint.py`, `store.py`,
  `__main__.py` (`status`, `query`), 26 tests under `tests/inventory_tracking/collection/`
  driven by the Insight, Spirit and magic-ring fixtures plus one synthetic set item.
  Full suite 2766 passed / 3 skipped; ruff and pyrefly clean for the package.
  Provisional choices awaiting Step 0: the fingerprint is a content hash (seed bytes
  are stored in `items.seed_hex` but not hashed, R4); shared tabs are recorded with
  `tab=None` until R1 names them; character class/level columns exist but are
  filled only when R3 supplies them.

- 2026-09-25 — Step 2 implemented: `capture.py` (`collect_inventory` live pass:
  unit snapshot, per-player +0xD8 order and `Sharedstash` state, merc equipment
  grid, every candidate item's data/arrays/diagnostics/socket children, end-of-pass
  unit recheck; `build_sightings` pure: one `decode_items` call per item, tabs from
  the order field, materials stash via the new `decode_items(materials=True)`),
  `collect` CLI writing `runs/collection/<run>/capture.json` and `report.json`.
  Quantity (stat 70) is excluded from the fingerprint so stacks keep one row. 47
  collection tests; full suite 2812 passed / 3 skipped. Host gate pending: the
  printed owner→tab mapping must reproduce the research.md R1 table.

- 2026-09-25 — Step 2 host gate (`runs/collection/20260925T114444Z-cbda18a7`): 89 ms,
  1.7 MB, zero issues; +0xD8 order reproduces the user's tab table; the d2go state
  bit is zero on this build (replaced by name/stat recognition); the 74 owner-less
  page-4 stacks are the material catalogue without quantities (not indexed).
- 2026-09-25 — Step 3 implemented: `collection/service.py` (`Collector`, shared
  `record_collection`), `appraisal/service.py` `dispatch` of `collect <t>` datagrams,
  `request --collect`, `--collection-database/--collection-output` options, Niri
  `Mod+S` binding installed next to `Alt+D`. Host gate pending: Win+S in game with
  the worker restarted must notify "<character>: N items · …" and list six tabs.

- 2026-09-25 — Step 3 host gate passed (Win+S run `20260925T122139Z-476c8ff0`: 166
  items, six tabs, zero issues). Step 4 implemented: `export.py` + `template.html`
  (embedded JSON, inline CSS/JS, word-start matching with quoted phrases, owner /
  container / rarity / socket filters, sort, group by location/set/rarity, stat
  preview per row, expandable stats with unresolved fields and issues), `export`
  CLI writing `runs/collection/collection.html`; rendered headlessly and checked
  against the live database (166 rows, 157 KB). Host gate: user opens the file.

- 2026-09-25 — Gems/Materials/Runes tabs: the 74 owner-less units are held types,
  count = u32 at item data +0x9C (research.md); indexed with `quantity`, schema
  version 2 (migration from 1). Win+S now regenerates the HTML page after every
  capture (`--collection-html`, default `runs/collection/collection.html`);
  `Makefile` adds `export`, `open`, `serve`, `collect`, `status`, `test`.

- 2026-09-25 — Free space: every Win+S also records each grid's occupancy (inventory,
  cube, personal stash, shared tabs) from the owner grid cells — free cells, a row
  bitmap and greedy fit counts per item size — into the `spaces` table (schema 3),
  and each item's size from the cells holding its pointer. `collection space
  [--fits 2x4]` and the page's "Free space" panel answer which mule has room.

## Steps and gates

0. **Research pass** (R1–R7) → `research.md`, fixtures, updated `layout_notes.md`.
   Gate: tab mapping and fingerprint rule verified on two sessions.
1. **Models and store**: pydantic models, SQLite schema, upsert and sighting
   closure rules, tested on fixtures. Gate: replaying two fixture captures produces
   the expected placements and `gone_at` rows.
2. **Full-pass capture**: `capture.py` on top of `sample_units` + `read_item_arrays`
   + `read_socket_items` + `decode_items` for every owned item and container,
   with the R5 budget and end-of-pass rechecks. Host gate: one Win-less CLI run
   (`collection collect --once`) captures inventory, cube, equipped, personal and
   all shared tabs with counts matching the game; frozen evidence saved.
3. **Service integration**: `collect` datagram, worker request kind, OSD summary
   ("312 items · 4 new · 2 moved"), notification, rejection messages for
   unfocused/stash-closed (R2), Niri `Mod+S` binding next to `Alt+D`. Host gate:
   Win+S from the game on two characters; shared tabs match across both captures.
4. **HTML export**: generator plus a smoke test that the file parses and the
   embedded JSON round-trips; `export` CLI and a `query --name … --stat …
   --sockets …` terminal fallback. Host gate: user opens the file and finds items
   by set name, unique name, stat text, sockets and runeword across at least two
   mules.
5. **Docs**: `inventory_tracking/COLLECTION.md` runbook (like APPRAISAL.md), README
   package table row.

Done means: every mule captured once, the HTML answers "where is my X" for sets,
uniques, stats, sockets and runewords, and a second Win+S on an unchanged mule
adds no rows.

## Open decisions for the user

None for this scope.

## Appendix — deferred: assessment and organization views

Not part of the current work. Kept so the schema and HTML leave room for it.

### Deferred research: assessment throughput

Per-item retrieval today: 26 ms (cache-warm unique) to 1070 ms (Insight base).
Method: replay `decoded_items.json` and the fixtures through `retrieve_draft` in a
loop, 300 items, and time it; check what `AssessmentContext` loadout input changes
so a character's equipped set can be passed as context. Deliverable: whether batch
assessment runs inline (progress on OSD) or as a background queue, and the cache
policy (fingerprint + publication generation, persisted in the database rather than
the 300-second in-memory `ResultCache`).

### Deferred design: naming and organization (views.py)

Labels are derived at query time from the stored assessment and definitions, never
hand-typed: set membership and completion (owned/total pieces per set across all
characters), class-restricted items, mercenary-usable gear, leveling band from the
KB's leveling rows, socketed bases matching runeword recipes, charms, unidentified,
duplicates by fingerprint or by name+base, "trash candidates" (low tier, no role,
no leveling use). `suggest` prints a move list ("Sigon's Shield: shared tab 2 →
character X, completes 3/6") — advisory text only.

### Deferred steps

- Batch assessment: `assessments(fingerprint, publication_generation, as_of, tier,
  verdict, result_json)` filled by a background queue reusing
  `PublishedAppraisal.retrieve`; re-run only for new fingerprints or a new
  publication.
- HTML columns for tier, verdict and estimate with date and "ask"/"fill" wording
  per repository rule 5; `sets`, `trash` and `suggest` commands.
- Open decision then: embed the full Alt+D text per item or only the compact
  build-use summary.
