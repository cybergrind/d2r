# Win+D shop check and the automatic stock watcher

The existing appraisal worker accepts `request --shop`. Win+D scans loaded NPC
stock across all four tabs in one pass, then evaluates local stat rules. No
hovering, tab switching, market lookup, purchase, or input injection is involved.
Restart `make serve` after changing the worker code.

Since 2026-09-26 the worker also watches vendor stock by itself (`--shop-auto`,
default on; `--no-shop-auto` restores hotkey-only behaviour):

1. About once a second in town (every five seconds elsewhere, configurable with
   `--shop-poll-seconds`) it reads the vendor grids and **remembers the first
   non-consumable item** — the first weapons/armor item in vendor, tab, cell order.
   Its key is base, quality, cell and native stats; unit IDs and addresses are
   excluded, so closing and reopening Trade keeps the same key.
2. Stock is scanned automatically only when that item changes: first load, or a
   stock refresh after leaving and returning to town. Nothing is rechecked while
   the item stays the same, and a result is shown once per stock: a shop that was
   merely closed and reopened shows nothing again.
3. Win+D always scans and shows, whether or not the stock changed, and re-arms the
   watcher after failed automatic attempts (three quiet retries per stock key).

The watcher stays silent for consumable-only stock (no gear to check), for gamble
stock (the sentinel is unidentified) and outside town. It never runs while an
Alt+D appraisal is being retrieved or displayed, and never shows failures — only
Win+D does. Each probe reads the grids plus one item record, not the whole stock.

The OSD shows target item names, bonuses, vendor, tab and one-based cell position,
or an explicit no-target result. Empty/unloaded inventories, incomplete reads,
unsupported stats and changing stock are reported separately. Full results go to
`inventory_tracking/runs/alt-d/<run>/shop-latest.json` (`manual` records whether
Win+D or the watcher produced it). A result with targets stays on the OSD for ten
seconds, a no-target result, status line or failure for five; any of them also
disappears on focus loss or as soon as its stock leaves memory (Trade closed).
Incomplete results also save the raw capture and result to `shop-diagnostics.json`
in the same run directory, so decoder failures can be replayed offline.
Alt+D dismisses a shop result. Scans share the appraisal/collection memory lock
but run in their own executor. Repeated requests cannot overlap or queue scans;
a Win+D that arrives during a probe is run as the manual scan right after it.

## What can be checked without opening Trade?

Only stock actually present in the client can be read. Having an NPC unit or an
allocated inventory is insufficient. Host captures on 2026-09-26:

- `shop-probe/20260926T084248Z-11bbe20d`, `084252Z-8a4ab0bf`, and
  `084259Z-c1f19709`: Drognan has four 10x10 grids, all empty.
- `shop-probe/20260926T084304Z-6bc59abc`: Drognan has 54 items across grid indices
  2/3/4/5 (6/24/16/8 items). Item pages are 0/1/2/3, owner ID is `0xffffffff`, and
  captured ItemData flags contain `0x2000`. All 54 decode without issues.

The user confirmed the open/closed/refreshed checks and working in-game OSD in
appraisal run `20260926T085816Z-a673077f`. Unloaded checks at 08:58:19, 08:58:35
and 08:59:40 UTC returned zero items; open shops returned 54 Drognan items,
8 Lysander items and 58 Fara items. Stock is cleared on the tested close/refresh
path, so open Trade first on this setup. The reader itself does not require a
visible panel, but cannot read stock that is no longer in client memory. It never
reports unloaded stock as a successful empty scan.
The diagnostic command remains available as
`uv run --offline python -m inventory_tracking.shop.probe`; it saves a bounded
stock dump and displays a five-second in-game OSD with completion/failure.

NPC grid membership, item mode/page/owner, valid ItemData, supported executable hash,
process identity and stable traversal are checked. NPC grids and item identities
are rechecked after the stat pass. Ownerless stash materials, mercenary equipment,
drops and player trade items cannot qualify merely by their flags.

## Targets

Since 2026-09-26 (evening) the scan primarily alerts on blue patterns that sell in this
economy, taken from `guides/pricing.html` §2 (blue table), `guides/pricing-primer.html`
§3.3 and the Anya rows of `guides/pindle-anya.html` §4.1 (Traderie asks 2026-09-18/19).
Everything the earlier build-list catalog added — starter and pre-runeword pieces
("Before Spirit" daggers, survival belts, resistance gloves/boots/rings, all-res
grimoires), Teleport / Life Tap / Lower Resist charges, Echoing weapons (1-Ist median
behind 63 sellers), Cruel/Quickness weapons, +3 tree circlets/amulets without a class
prefix, charms and jewels (never vendor stock) — no longer alerts. The compiled catalog
(`magic_targets.json`, [MAGIC_COVERAGE.md](MAGIC_COVERAGE.md), `build_catalog.py`)
remains an offline audit tool, reachable with `match_item(..., build_candidates=True)`.

On 2026-09-27, reviewed +3 skill-tree amulets became an explicit self-use exception.
Plain rolls show `Build use`; useful FCR/life/MF suffixes (gold find for Warcries)
show `Build review`. These labels are not resale-price claims. See
[amulet evidence and matching rules](AMULETS.md).

Other alerts (decoded native stats; thresholds are the priced rolls):

- Jeweler's Monarch of Deflecting (4 sockets / 20 block / 30 FBR); any other 4-socket
  magic Monarch or Archon Plate (4os-magic bucket minimum).
- Jeweler's body armor: 4 sockets with life ≥ 90 (of the Whale, priced band),
  15 damage reduction (of Amicae), 24 FHR (of Stability) or 10+ dexterity (of Precision).
- Circlets: +2 class skills, better with 20 FCR (of the Magus), sockets or 30 FRW;
  any 3-socket magic Tiara / Diadem (Artisan's), 30 FRW noted.
- Gloves of Alacrity: +3 Bow / Passive / Javelin / Martial Arts with 20 IAS
  (+2 Passive "Gymnastic" stays in the shop).
- Claws with +3 Traps (Cunning) or +2 Assassin (Witch-hunter's) and 30+ IAS; the label
  names Lightning Sentry / Death Sentry / Wake of Fire staffmods when present.
- Amazon javelins: +3 Javelin and Spear with 40 IAS plus either +Amazon skills or the
  +6 automod total.
- Reviewed staffmod targets require +2 of the skill's own class / +3 of its own
  tree, plus a native +3 primary skill: +5 / +6 total. Extra utility/mastery
  staffmods can be named as companions, but never qualify the item alone.
  No generic two-staffmod, plain Warcries-helm, plain tree-grimoire, socketed
  +1 Necromancer head, or FCR + lone-staffmod shortcut remains.
  See [the skill review](SKILL_REVIEW.md) for the full 155-skill disposition.

Larzuk outcomes, affix generation chances, item prices and requirements are not
predicted, and a hit is a resale or explicitly labeled self-use candidate, not a BiS claim. Prices are never
matched; when the guides' bands move, edit the thresholds in `rules.py` and cite the pass.

## Validation

The tests replay a four-tab subset of the real Drognan capture and cover ownership,
changed grids/items/location, flag-free buyback stock, invalid ItemData, partial/unloaded stock, skill-tree
mismatches, mastery combinations, hotkey routing, concurrent requests and OSD
expiry. A cold local replay of all 54 captured items took approximately 126 ms
for decoding plus matching on 2026-09-26; this excludes host capture and rendering.
The subsequent live hotkey scans took 110.9–388.7 ms end to end for loaded shops
(including focus checks, capture, decoding and matching; excluding rendering).
Drognan's refreshed stock produced four alerts, including a Blade with +3
Eldritch Blast / +3 Enhanced Entropy. Fara's 58-item scan explicitly reported a
partial result because one Throwing Spear carried an unresolved stat.

The subsequent Fara dump `shop-probe/20260926T090147Z-35fa16b1` identified native
stat 254, Increased Stack Size, with value 23. It is a numeric bonus, although
the game's tooltip label has no number placeholder. Treating such labels as
boolean flags was incorrect. The corrected decoder replays all 58 items without
issues. Regression coverage includes the original Throwing Spear record.

The 2026-09-26 decoder audit also covers Magic/Explosive Arrow levels, RotW
physical resistance piercing, missing RotW localization strings and all defined
per-level operation families. Poison rates, summed durations and source counts
remain explicit when a combined tooltip cannot be inferred safely. Tests check
9,786 range endpoints (1,834 distinct native payloads) from bundled item and affix
definitions, their fixed triggers and level formulas, every native class skill,
and all class/tree bonuses. This is coverage of the pinned definitions and saved
captures, not proof of every possible generated item or future game build.
Unknown IDs and malformed payloads still produce an incomplete scan.


## Larzuk buyback fix and parser census — 2026-09-26

Shop membership no longer requires item flag `0x2000`: sold items can lack it.
Revalidated NPC grids establish ownership. Unreadable flags still fail, with
available rejected rows saved in diagnostics. Unresolved stats now identify the
vendor, unit ID and exact native payload.

[Parser audit and RCA](PARSER_AUDIT.md) includes the evidence, handling checklist,
all 367 native metadata stat IDs and remaining evidence gaps. Run the offline
census with `uv run --offline python -m inventory_tracking.shop.audit --output /tmp/shop-parser-audit.json`.
