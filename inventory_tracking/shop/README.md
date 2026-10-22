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

Since 2026-10-22 only really good buys alert ("notify on a really good items ... not just any +2 skills", the
player). Before, every appraisal verdict but VENDOR alerted, and 48 of the 52 alerts of 2026-10-06..22 were CHECK
without a price ("+2 Warlock skills", "+3 Chaos Skills", "+3 Warcries"). Now an item alerts when (`service.py`):

- a reviewed pattern of `rules.py` matches, whatever the appraisal says (the appraisal has no price for most of
  them and called some VENDOR), or
- the appraisal sells it (SELL or SELL slow) at asks of 2.5 Ist or more (lower quartile; the High tier's floor,
  `pricing.html` §4.2). CHECK without a price, SELF-USE and cheaper sales stay quiet.

The reviewed patterns, each confirmed on the scoped Traderie asks (SC/NL/PC/RotW, caches 2026-08-19 to 10-09, asks
only: no fills are cached) and the d2data affix tables on 2026-10-22; one example per class is in
`tests/inventory_tracking/shop/test_premium.py`:

- Jeweler's body armor of the Whale: 4 sockets and 90+ life on any base tier (28 sellers, Q1 45.7). Amicae,
  Stability, Precision, 81-89 life and plain 4-socket Monarchs or Archon Plates no longer alert (thin or a wall).
- Jeweler's of Deflecting (4 sockets, 20 block, 30 FBR) on a Monarch, Aegis, Ward or Paladin shield.
- Circlets: +3 Fire / Lightning / Cold / Poison and Bone / Combat (Paladin) / Eldritch / Chaos with 20 FCR, or a +3
  tree with 80+ life, 25+ strength or dexterity, 30+ MF or 20% damage reduction; any 30 FRW; a 3-socket Diadem, or a
  3-socket Tiara with 25+ MF. A +2 class circlet, with or without 20 FCR, is not kept (2026-10-21).
- Gloves: +3 Bow, Javelin or Martial Arts with 20 IAS (of Alacrity; 20 is the most a magic glove rolls). +3 Passive
  asks a median of 1.
- Amazon javelins: +5 Javelin skills (the base's automod included) and 40 IAS, +6 and 30 IAS, or +2 Amazon, +3
  Javelin and 40 IAS.
- A paid skill's staffmod with its class prefix or its own tree prefix, +5 or more in all (`staffmods.py` PAID: the
  triage's paid skills, the claws' Death Sentry / Wake of Fire / Phoenix Strike and the Warlock's paid list). Claws
  with a prefix and IAS but no paid staffmod no longer alert; IAS is named in a claw's label. IAS on a Warlock dagger
  counts for nothing: Echoing Strike is cast.
- Amulets: a reviewed +3 tree with 80+ life, 25+ strength or dexterity or 30+ MF (vendors rarely stock amulets).

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
