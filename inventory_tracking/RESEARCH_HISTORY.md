# Inventory tracking — historical research

Preserved 2026-10-13 from the package README. These dated probes describe the
implementation at the time, including limitations later resolved. They are not
startup instructions or the current capability list. Start at [README.md](README.md)
or [APPRAISAL.md](APPRAISAL.md); use local [third-party sources](../third-parties/README.md)
for implementation research.

## Other projects and research references

Reviewed 2026-09-21. These are source/design leads, not validated offsets for our
installed D2R build. See the [merc HP comparison](merc_health_research.md) for
commit-pinned source links, calculations and limitations.

| Project | Why it is useful |
| --- | --- |
| [d2go — accessible fork](https://github.com/relentlessricktrinidad/d2go) | D2R memory structures and stat readers. Merc HP uses the same normalized /32768 estimate as ours, with an ordinary-HP fallback. Original hectorgimenez repository was inaccessible during this review. |
| [D2R-AutoPotion-Go](https://github.com/Apethor/D2R-AutoPotion-Go) | Potion watcher and related d2go code lineage; same merc HP heuristic, not an independent exact-HP solution. |
| [Koolo — accessible fork](https://github.com/dulingzhi/koolo) | Player/merc health policies, belt use and recovery workflows; consumes d2go's merc percentage. Original hectorgimenez repository was inaccessible during this review. |
| [MapAssist — accessible fork](https://github.com/dglEnraged/MapAssist) | C# unit/stat-list readers and overlay architecture; generic monster life/max ratio is not validated for our merc encoding. |
| [d2r-mapview](https://github.com/joffreybesos/d2r-mapview) | AutoHotkey memory readers and HUD implementation; useful comparison for unit/area/stat layouts, without an exact merc HP solution. |
| [Botty](https://github.com/johannes-do/botty) | Visual alternative: estimates merc health from filled pixels in the portrait health bar. Useful for an independent display cross-check. |
| [D2BS](https://github.com/noah-/d2bs) | Legacy Diablo II client integration. Merc HP calls the game's unit-ID-based percentage function, suggesting a separate client health source to investigate. Old addresses do not apply to D2R. |
| [D2MOO](https://github.com/ThePhrozenKeep/D2MOO) | Reconstructed legacy game code: 128-step monster life, throttled updates, owner-facing percentage and explicit merc-stat delivery. Explains possible mechanisms; does not prove current RotW behavior. |
| [Cartographer / Wanderer](https://github.com/cartographerwanders/d2rmanager-cartographer-wanderer) | Modern HUD reference advertising merc HP. The inspected snapshot contains documentation/images only, so its health algorithm could not be inspected. |
| [D2tools / ReadMem](https://github.com/antoinemalloc/D2tools/tree/main/ReadMem) | Earlier Windows/Rust player HP/mana reader lead; not established as a merc HP source by this comparison. |
| [diablo2utils](https://github.com/ChrisTitusTech/diablo2utils) | Earlier Linux memory-structure/signature and patching references. Layouts remain build-specific and must be checked against local evidence. |

Production changes require supported-build validation; related forks should not
be counted as independent confirmation. External sources are now checked out under [third-parties](../third-parties/README.md),
with origins and exact revisions recorded. Search these local copies first; no
third-party runtime was installed or run.

### Appraisal item-stat research

To capture rings as well as the existing resource items (class ID 537 verified
against cached d2data/misc.json), run on the host:

```sh
uv run --offline -m inventory_tracking --output inventory_tracking/runs/ring-appraisal probe --item-class 537
```

This opt-in diagnostic reuses bounded unit traversal and stat-array consistency
checks; it does not change OSD polling. It requires the supported executable hash.
`units.json` includes ring records under `resources.items`, with raw stat arrays
at each candidate descriptor offset. They are research observations, not decoded
or approved appraisal facts. Owner/page/coordinates identify candidate items;
multiple rings must not be collapsed into one or matched solely by quality.
Missing/changed arrays or no selected item prevent successful probe completion.
The existing report watcher detects completion without another chat message:

```sh
uv run --offline -m inventory_tracking --output inventory_tracking/runs/ring-appraisal watch --timeout 60 --include-existing
```

The first validated decoder covers inventory magic rings' faster cast rate and
maximum stamina only. Replay a completed probe without accessing the game:

```sh
uv run --offline python -m pricing.knowledge snapshot inventory_tracking/runs/ring-appraisal/RUN_DIRECTORY
```

It selects the captured player's inventory rings and retrieves local candidate
KB evidence. Title/required level and unsupported stats remain unresolved.
The capture is historical, not proof of current inventory state. Hover selection
and hotkey-triggered reports are not implemented yet.

### Hover selection prototype

Run `uv run --offline -m inventory_tracking.hover_probe` on the host. After the
initial build-gated connection it prompts for three samples: ring, empty space,
same ring again. Default delays are 5, 3, 3 seconds (`--delay` for the first,
`--interval` for later samples). Keep the cursor stationary during each capture.
Results are in `runs/hover-appraisal/<run>/report.json` and sample-0/1/2.json.

This scans the captured executable for a hover-layout candidate and checks its
unit type/ID against the existing item traversal, reading hover before and after.
Changed selection or unstable unit data is rejected. Empty hover ignores stale
unit IDs. Success means the requested sequence matched, not general hover-layout
validation; `validated` remains false. A ring-to-different-item test is still
needed before enabling a hotkey report. No Alt+D binding is installed yet.

Layout lead: https://github.com/relentlessricktrinidad/d2go/blob/main/pkg/memory/offset.go
and game_reader.go, inspected 2026-09-23. Our saved supported-build executable
contains one candidate at RVA 0x1e010a0; it is discovered rather than hardcoded.

## Inventory hover research

The original hover-table probe did not identify inventory items. The replacement
[UI-path research probe](hover_research.md) captures **item A → empty → item B → A**:

```sh
uv run --offline -m inventory_tracking.hover_ui_probe
```

Run on the host with inventory open; follow the 5/3/3/3-second prompts and hold
until `CAPTURED`. Output is under `runs/hover-ui/`. This records raw evidence only;
item selection and Alt+D appraisal are not enabled yet.
