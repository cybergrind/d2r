# Item metadata

Player skill names are localized through `skills.skilldesc` → `skilldesc.str name`
using the checked-out English strings and cached planner translations. Native skill
IDs remain unchanged; differing internal names are retained as `internal_name`.
Non-player variants and missing translations retain their internal names. The
metadata provenance records hashes for all three localization inputs. After changing
skill names, regenerate `pricing.knowledge.assessment.maintenance.market_projection`
before rebuilding and publishing the index: market labels use displayed skill names
(for example, Fissure rather than the internal Eruption).

`item_metadata.json` is an offline snapshot generated on 2026-09-23. Runtime
appraisal does not download data. It includes 692 bases across weapons/armor/misc,
367 distinct stat IDs and 428 skill names. Stat ID 213 has conflicting source
names; both are retained and its interpretation remains unresolved.

Sources and SHA-256 hashes for downloaded static tables are in `provenance`:
- [d2data ItemStatCost](https://raw.githubusercontent.com/blizzhackers/d2data/master/json/itemstatcost.json)
- [d2data skills](https://raw.githubusercontent.com/blizzhackers/d2data/master/json/skills.json)
- Existing `pricing/raw/d2data/{weapons,armor,misc}.json` class IDs/names/codes.
- Existing `pricing/raw/mr/planners/game-strings.json` description strings.
- Existing `pricing/data/appraisal-properties.json` market property labels.

Rebuild from explicitly supplied local exports (no network in the builder):

```sh
uv run --offline -m inventory_tracking.items.build_metadata \
  --stats tmp/itemstatcost.json --skills tmp/item-skills.json
```

Simple description functions 19/29 are eligible only without parameter encodings
or level/time suffixes. Description function 12 (Hit Blinds Target, Freezes target)
carries a level: the label is the market wording `<effect> +{{value}}`, decoded text
omits the `+1` suffix like the in-game tooltip (Deathspade, 2026-09-25) and shows
`+N` above level 1; non-positive or parameterized values stay unresolved. Scaling uses ValShift; fractional values remain unresolved.
Market property labels must match uniquely after punctuation-preserving
normalization. Identical market properties arising from multiple memory stats
are withheld from facets rather than overwritten. Total defense/damage and item
counters are displayed as totals, not bonus affixes. Unknown or ambiguous entries
are retained in decoded_stats as named raw values and in unresolved_stats.

Charges use the layout already verified by the repository's Teleport staff probes.
Skill, aura, class-skill and chance-to-cast formatting uses table metadata and the
packed skill/level convention. New non-ring outputs still require host tooltip
comparison. D2MOO's [item routines](https://github.com/ThePhrozenKeep/D2MOO/blob/master/source/D2Common/src/Items/Items.cpp)
provide supporting charge-layout evidence. Metadata describes game fields; it
is not proof that every runtime stat list exactly reproduces the tooltip.

## Wand fixes verified against the host tooltip

The 2026-09-23 self-repair wand capture has stat252=3. Its tooltip displays
“Repairs 1 durability in 33 seconds.” Decoder uses integer100/rate for the displayed
interval (positive rates1..100 only); this is a tooltip interval, not a timer.
[D2Game item regeneration](https://github.com/ThePhrozenKeep/D2MOO/blob/master/source/D2Game/src/ITEMS/Items.cpp)
schedules repairs using2500/rate game frames. Invalid/parameterized entries stay
unresolved. This interpretation does not create a market price facet.

Base metadata now includes weapon speed and the inherited blunt classification
from local itemtypes Equiv1/Equiv2. Blunt weapons have an inherent50% undead bonus,
separate from stat122's rolled modifier, as shown in
[D2Game damage calculation](https://github.com/ThePhrozenKeep/D2MOO/blob/master/source/D2Game/src/UNIT/SUnitDmg.cpp).
The derived row is labeled base_type and never passed as a rolled affix. It matches
both supplied Bone Wand tooltips. Other implicit bonuses are not inferred.

Stat68 is described as base weapon speed only when it equals the negation of the
local weapon speed value; D2Game item initialization sets it that way. It is not
IAS(stat93), nor the character-dependent tooltip category. Class-specific skill
labels use full class names. Title, level requirement and speed category remain
explicit review fields.

## Audited decoder gaps (2026-09-25)

Signed defense (including Dimoak's Hew -8) is readable without creating a market
bonus facet. Stat219's op5 coefficient is rendered as enhanced maximum damage
percentage at the active viewer's level. Stat358 uses ModStrMagPierce from the
local English strings, retaining positive native magnitude for negative enemy
resistance wording and definition ranges.

`items/effects.py` handles Tomb Reaver's verified reanimate target and internal
quest difficulty, blood/fade visuals and catalog set states. Parameters outside
the reviewed monster/state mappings stay unresolved. Set effects are decoded only
when captured, not inferred from owning a set item. These handlers emit no market
facets. See [the audit](../STAT_DECODER_AUDIT.md) for evidence and replay scope.

## Named identities and possible rolls (2026-09-23)

Shared builder: `pricing.knowledge.definitions`; portable KB artifact:
`pricing/data/appraisal-definitions.json`. The bundle contains set, unique and
runeword names, compatible bases and conservative scalar roll ranges, with input
hashes. Set/unique IDs come from captured ItemData +0x34 and require identified
flag +0x18, matching quality and base. Tancred's Crowbill ID30 is host-verified.
Unique naming uses the same layout and is covered by synthetic checks; additional
unique screenshots remain useful. See local `third-parties/diablo2utils` ItemData
structure and `third-parties/d2go/pkg/memory/item.go`.

Runewords require flag0x04000000, normal/superior quality, a known first-prefix
ID at +0x48, compatible base and the recipe's socket count. Spirit ID20635 matches
the captured Monarch. Explicit ID mappings come from the pinned d2go runeword
table; unmapped entries remain unknown. Rune order is recipe information, not a
claim that socket contents have been independently read.

Ranges appear only for decoded scalar values within a known variable definition
range. Fixed stats get no redundant range; raw values and market facets remain
unchanged. Conditional/compound properties and unknown identities stay unannotated.
The Crowbill's 80% enhanced damage is absent from the captured arrays; it is
flagged as not captured rather than filled from the catalog. `stat_diagnostics`
contains bounded candidate linked lists for research only; those stats are never
merged into the appraisal until validated for this build.

Magic charm affix definitions now share the offline KB builder. Prefix IDs depend
on the current suffix-table record count; JSON numeric keys contain expansion gaps.
Runtime resolves captured IDs against compatible bases, never from rolled values.
Ranges support scalar modifiers only. The captured Stout Small Charm of Vita
regression checks 5 defense (4–8) and 20 life (16–20, perfect).

See [RANGE_COVERAGE.md](RANGE_COVERAGE.md) for the exhaustive local unique/set
property audit and explicit remaining gaps. Plain armor base-defense ranges are
only displayed when non-ethereal base and total captured defense agree. Local
weapon enhanced damage can come from the guarded +0xD0 owner-linked modifier list.

Rare titles now use guarded rare-prefix/suffix IDs. Automagic definitions are
included with a separate slot and tier family. Skill-tab ranges use `stat:layer`
keys so different class trees cannot overwrite one another; runtime tab decoding
currently covers the seven established classes, with unknown layers left explicit.

Staffmod ranges are stored in the portable definitions and runtime metadata.
Eligibility follows the base's primary item type `StaffMods` class from local
itemtypes.json, matched to the captured skill's class. Native class-specific
skill stat107 uses the D2MOO `sub_6FC52650` magnitude rule:1–3, or1 only for
inferior modern-format items. These are roll ranges, not magic/rare affix tiers.
Ordinary eligible staffmods use existing perfect/low colors; runeword or
out-of-range totals show contextual bounds without claiming contribution splits.
Named unique/set skill bonuses do not inherit this generic range.

`fixed_socket_scalars` is compiled from the pinned gems/properties tables and
recipient base `gemapplytype`. It covers only the reviewed additive intrinsic
scalar set; explicit zeros mean the audited socket effects do not modify that
stat. Unknown functions or nonfixed target effects fail compilation. Regenerate
native market projection after metadata changes, then rebuild and publish as usual.

`comparison_socket_effects` compiles the reviewed fixed filler whitelist from the
same pinned gems/properties/stat tables: helm31, armor31, shield20, weapon10.
Only fixed, unparameterized, supported direct effects are accepted; unknown or
empty property functions fail compilation. Runtime comparisons use this bundle
and do not fall back to independently maintained numeric constants.
