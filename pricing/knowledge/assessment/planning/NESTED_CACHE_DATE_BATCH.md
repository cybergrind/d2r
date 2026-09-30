# Explicit nested cache collection date — 2026-09-25

Offline evidence maintenance after Duress base batch; no demand/tail slot consumed.
Cache audit found153 bare-list files and7 files without collection metadata, plus
Razortail's200listings with _meta.pulled=2026-09-20. Missing dates are not inferred
from filenames, filesystem times or listing update timestamps.

Razortail update timestamps range2026-09-19T23:54:34.227Z through
2026-09-20T16:46:02.401Z, consistent with the explicit collection day. The existing
importer read only top-level pulled and discarded this evidence.

collection_day_evidence now returns validated day/error/exact source field.
collection_day retains its two-value compatibility API. Both /pulled and
/_meta/pulled are accepted only as canonical calendar dates. Conflicting values or
invalid non-null values reject the collection date rather than selecting a fallback.
Listing updates after the claimed collection day still invalidate it. Provenance
records cache path, hash and the actual field. Scope/facet/price gates unchanged.

Red:four new failures (nested date and conflicting/invalid nested date). Green:
22cache-date/market tests. Raw caches unchanged; offline import/rebuild results and
published saved-item checks are recorded in STATUS.md. Evidence tmp/nested-cache-date-*.
Collection date means ask observation date, not a confirmed sale or price validity.
Most undated cache files still have no explicit date evidence.


Offline re-import retained41135rows and increased explicitly dated rows19776→19976.
All200Razortail rows preserve every non-date field (seller/scope/facets/prices).
Scope split unchanged:54verified,139rejected,7unknown.46market/refresh/comparison/
publication tests passed8.11s. All18saved reports and numeric estimates unchanged;
published/staged parity. Generation6a28e579ff28ffb0b03de2c8e4607cc4e94a4bc30715b494a21c7900aa64c937.
