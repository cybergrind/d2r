# Appraisal item bank

Run `uv run --offline pytest tests/pricing/knowledge/assessment/item_bank -q`.
These tests use the selected published generation, native stat decoding, actual
SQLite retrieval/comparison, appraisal and report rendering. They do not replace
role matching with mocks or pass a hand-picked profile list to the engine.
For red/green before publication, add `--item-bank-staged` to use rebuilt working-tree
artifacts and SQLite; rerun without that option after selecting the generation.

Add `--item-bank-receipt pricing/data/appraisal-item-bank-run.json` to retain
executed-case outcomes, covered targets, generation and source hashes. Each case
must pass setup, call and teardown. Skips, failed attempts, interruptions, mixed
generations, staged execution or changed sources prevent a full-bank pass claim.
A filtered run records its passed and unexecuted cases without claiming complete
execution. Receipts currently require a single pytest process and an existing
output directory. They do not replace the coverage audit or independently reviewed
report/stat expectations, and do not automatically close completion-ledger rows.

`models.Item` constructs an extraction from a canonical base name and explicit
native raw stats. Metadata resolves the base code. Leave `complete=False` when
only selected properties are supplied; incomplete input must not acquire an exact
price. This exercises stat decoding and downstream appraisal, not process-memory
selection or the full snapshot identity decoder; retained real-capture replays
cover those boundaries. `SocketItem` supplies explicit linked-child fixtures and
uses the production child-payload decoder. Child capture completeness is independent
of the parent; aggregate parent bonuses cannot substitute for child stats. This does
not test native pointer linkage, which remains covered by capture tests. Named fixtures resolve their explicit native identity through
production identity/range enrichment and preserve the resolved table identity in
capture provenance, including upgraded named bases. Base-defense ranges additionally require
explicit `owned_stats` matching the total and known non-ethereal status; the
factory never infers that proof from total defense alone.

Add independently reviewed scenarios under `cases/`, then register them in
`cases/__init__.py`. Each `Case` declares its evidence, context, covered use IDs,
positive/negative/unknown scenario and partial expected result. Use `dirty-equals`
(`IsPartialDict`, `Contains`, etc.) to check meaningful stable outcomes without
snapshotting unrelated fields. Do not generate expected values from the production
rule being tested. Cite the guide/native evidence instead.

An annotation shared by several builds must identify the expected configuration
in `configuration_ids`. Negative cases can forbid that particular configuration
while allowing other independently valid uses. Exhausted charges may instead
forbid the annotation entirely. `absent_stat_configurations` forbids a configuration
at one particular stat while allowing its other valid contributions and other
builds using that stat (for example, attack rating helps Zeal but not Smite).
Add report expectations where presentation matters.

Run `uv run --offline python -m tests.pricing.knowledge.assessment.item_bank.coverage`
to persist the remaining target inventory in
`pricing/data/appraisal-item-bank-coverage.json`. It includes every compiled
build/use quality, named high/mid or leveling target, and stat-qualified valuable
trade watch. The watch artifact is pinned alongside the profiles and named gate. A named-tier target uses
`named:<quality>:<name>`; ordinary IDs refer to reviewed role IDs. A test for one
quality cannot cover another. Use `watch:<watch_id>` for a conditional trade-watch
target; invalid-rarity rejection cases remain useful but cannot cover another
quality. Positive, negative and unknown cases are all required.

For a role's wrong-rarity rejection test, use the explicit target
`role:<role_id>:<intended_quality>` (for example, a normal shield tested against
a magic-shield role targets `role:example:magic`). Only a negative scenario may
have a different input rarity from this target; it cannot supply positive or
unknown coverage. Unrecognized role/quality targets remain audit failures.
Planner evidence locators beneath `/data/` refer to the JSON-decoded planner
payload; the evidence check resolves that payload and validates every path segment.

This is an inventory of authored cases, not proof they passed. Completion also
requires a passing run against the final generation and coverage of all important
variants, mercenaries, companions, socket/base outcomes and pricing/report behavior.
As the remaining source and family reviews add targets, expand the bank alongside
them. Current bank coverage is intentionally incomplete; do not claim all-build
coverage from the initial scenarios or a green sample.
