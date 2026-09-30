# Missing embedded planner set: Echoing Strike / Mirrored Blades

Checked 2026-09-28. This is an unresolved source conflict, not an excluded item.

The cached Echoing Strike guide has 37 tooltip references to planner `ucgz20le`,
set UID `qJ8YXfFZ`. The cached planner has only these profile UIDs:
`ZWcxvtFt` (Starter), `LmIammQ8` (Standard), `1ikVhvXU` (Magic Find),
`Khw26jKQ` (Ubers), `uOk8UnY1` (Skill Tree). No profile matches the referenced UID.
The same missing UID also occurs in the Mirrored Blades guide. A targeted search
of `pricing/raw/mr` and `pricing/data/wp-a-variants` found the UID only in these
two guide HTML files, not in a cached planner or extracted variant record.

This includes Echoing span160, the Hardcore Ars Dul'Mephistos with Eld example.
Its item definition exists, but existence does not repair the missing set link.
Do not substitute the Standard UID or approve a same-name item in another setup.
`validate_embedded_evidence` correctly rejects this source chain. Those references
remain queued as `missing_set`; the two other Hardcore tooltips (Void/Obsession)
use the existing Standard set and have separately validated exclusions.

Resolution needs a compatible cached/archive planner containing the exact UID,
or an explicit reviewed source correction preserving the old evidence and its
relationship to a replacement. A fresh unrelated planner cannot silently replace
this pinned source. Independent source/configuration work can proceed meanwhile.
