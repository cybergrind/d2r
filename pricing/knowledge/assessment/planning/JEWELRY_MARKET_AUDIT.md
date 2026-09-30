# Exact jewelry cohorts and representative sellers

## Offline jewelry cohort audit and seller examples — 2026-09-26

Maintenance batch, not a demand/tail scheduling slot. Audited existing scoped
jewelry evidence and eleven reference Mara's Kaleidoscope resistance contracts,
20 through30, without network collection or treating references as captured items.
Durable audit: pricing/data/appraisal-jewelry-price-audit-2026-09-26.json, with input
hashes, contracts, listing/seller IDs, publication gates and exact price results.

30res: six matching listings from three sellers,9.32Ist ask estimate based on
2026-09-18 observations/conversion, low confidence.26/27/28/29res have1/5/17/22matched
listings but only1/1/2/1sellers respectively, so remain thin.20-25have no eligible
matches.232scoped Atma observations are undated; no date recovered. Appearance1265
remains an exact-comparison facet, not discarded to manufacture a larger cohort.
These are cache/reference results, not a new item appraisal or current sale price.

Found/fixed example selection bug: summary counted independent sellers correctly
but selected its first three examples from arbitrary listing order, allowing two
examples from one seller. Representatives now use each seller's actual minimum
eligible ask, with deterministic ordering. Numeric votes, matching, dates, scope,
unit and seller-count gates are unchanged. Full accepted listings remain diagnostics.

Red: repeated seller in published price examples. Green28market/valuable/refresh/
comparison tests7.96s; lint/format/diff pass. All11reference numeric estimates/seller
counts unchanged; examples now distinct. All18saved reports/prices unchanged from
the prior Magefist generation. Rebuilt valuable/index offline and published
b4fe1a9e6186750c5e98f3a9fd0fa110623b9969157f974d8c161c100f78716c.
Runtime market.py changed: restart worker to load this fix. No new role/stat/tier
coverage;528roles/520stat configurations,115leveling recommendations retained.
Evidence tmp/jewelry-examples-*; final parity/coverage checkpoint follows.

Scheduling unchanged: one more demand/family batch after Magefist, then tail.
Missing dates/appearance and independent sellers remain specific research gaps;
broader base, named-tier and affixed coverage is still incomplete.
