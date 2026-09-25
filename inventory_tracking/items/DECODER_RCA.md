# Why captured item stats still remain unreadable

2026-09-23. Guardian Angel fixes are now implemented: owned local defense,
active-viewer level formulas, and internal armor-penalty classification. The broader
corrective plan below still describes remaining work. See guardian_angel.json regressions.

Evidence: `inventory_tracking/runs/alt-d/20260923T194941Z-821dd8c5/request-6/frozen.json`
and the matching Guardian Angel screenshot. Item unit 263695978; active player
123741752, level 91. No additional live probe is needed to reproduce these gaps.

## Guardian Angel: three independent causes

| Tooltip / log | Captured evidence | Failure |
| --- | --- | --- |
| +187% Enhanced Defense missing | Owned +0xD0 list contains stat16=187; total +0xE8 contains defense789 but no stat16 | `items/modifiers.py` forwards only IDs17/18 and requires that pair. `items/decode.py` only merges that weapon-ED exception. |
| +227 Attack Rating against Demons (based on character level) unresolved | stat245=5; metadata op2, op_param1, op_base=level; active player level91 | `StatContext` has no player level. No per-level strategy evaluates floor(5*91/2)=227. |
| velocitypercent raw -10 reported unreadable | stat67=-10; Templar Coat source armor record has speed10 | Internal base movement penalty is mixed with tooltip modifiers; no classification distinguishes these roles. |

The modifier node's owner tuple is exactly (1704037088, 4, 263695978), matching
selected item address/type/id. Enhanced defense is not inferred from the catalog:
it is present in the captured owned node. KB identity218 already contains the
180–200 enhanced-defense range and the scalar decoder already knows its label.
The missing connection is between captured local modifiers and decoding.

The per-level value must use the active viewer's level, not the shared-stash owner:
this item's stash owner is 15467719. Tooltip requirements and class-specific block
or attack-speed categories similarly need more context than a flat stat list.

## Architectural root cause

The implementation still treats the total stat array as a near-tooltip inventory.
It is not one. Totals, local modifiers, base values, encoded payloads and internal
engine effects have different meanings. Successive fixes added narrow exceptions
(weapon ED, poison aggregation, plain base defense) without a complete normalization
layer that resolves those meanings before rendering.

The metadata generator only turns a conservative subset of description functions
into scalar templates. Parameterized/secondary-string descriptions intentionally
stay unlabeled. Specialized strategies cover several families, but not all:

- per-level stats: IDs216/217/241/245 share op2 with different scaling;
- skill tabs: ID188 uses description function14 and a parameterized layer;
  now implemented for the seven established classes, with range keys retaining the layer;
- elemental damage/duration: related entries require aggregation;
- local armor ED: needs source selection rather than another string template;
- inherent movement penalties: readable diagnostics, not unknown tooltip affixes.

`decode_stats()` receives item base and stat entries, but no viewer context, and
readable labels also influence market-facet projection. A blanket fallback that
prints or merges every numeric field would introduce double counting, wrong values,
or search facets for internal totals. Copying catalog values would hide capture
failures and misreport variable rolls.

## Why prior checks did not prevent this

The 573-record catalog test verifies that every unique/set definition and its raw
source fields are retained. It does not prove runtime stat capture, formula evaluation,
range attachment, or tooltip completeness. The range audit explicitly reports gaps.
Snapshot regressions preserve previous decoded output, including intentional unknowns;
passing them prevents regressions but does not expand semantic coverage. My earlier
completion summaries did not make this distinction prominent enough.

## Corrective work, in order

1. Normalize sources by stat family: base, totals and owned local modifier lists.
   Generalize ownership-checked local extraction and explicit merge rules; local ED
   must not be added on top of a total that already includes it. Preserve provenance.
2. Pass a validated viewer context to formula strategies. Capture/revalidate the
   active player's level; absent/stale context remains an explicit unresolved reason.
   Implement the op2 per-level family together, not just Guardian Angel's ID245.
3. Classify output as tooltip modifier, base property, internal diagnostic or unknown.
   Recognized armor movement penalties should not inflate undecoded-tooltip counts.
4. Add remaining parameterized/aggregate families (skill tabs, elemental damage,
   durations), keeping rendering independent of market-property mapping.
5. Add screenshot-derived semantic contracts. Guardian Angel must show captured187
   with range180–200 and derived227 at level91; the known movement penalty must not
   be reported as an unknown affix. Test missing viewer level, changed ownership,
   duplicate contributions and existing-total/local overlap explicitly.
6. Track separate coverage measures: source catalog completeness; supported decoder
   families; captured-source completeness; expected tooltip lines reproduced. Do not
   use catalog counts or total passing-test counts as a substitute for the last two.

Existing captures suffice for regression fixtures. Additional probes should only be
requested for unverified layouts or semantics not settled by those captures.
