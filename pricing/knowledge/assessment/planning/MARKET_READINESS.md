# Offline market evidence readiness — 2026-09-25

Structural prerequisites only. These counts do not establish modifier equivalence,
independent comparable sellers, trade tiers or numerical estimates. All observations
counted here have verified SC / Non-Ladder / PC / RotW scope. Missing facets remain
unknown; this report does not fill them with defaults.

| Policy route | Scoped rows | Structurally ready | Blocked rows | Largest blockers (overlapping) |
|---|---:|---:|---:|---|
| affixed | 8728 | 558 | 8170 | undated: 6430, ethereal: 4789, socket_contents: 3809 |
| base | 3209 | 20 | 3189 | socket_contents: 2947, undated: 2696, ethereal: 2160 |
| named | 7089 | 616 | 6473 | undated: 3982, ethereal: 3381, socket_contents: 3145 |
| runeword | 4391 | 130 | 4261 | base_rarity: 3904, ethereal: 2580, price: 1170 |
| unclassified | 761 | 0 | 761 | rarity: 761, ethereal: 567, socket_contents: 475 |

Priorities:

- Separate missing-source data from parser/policy gaps before changing matching rules.
- Recover dates or facets only from explicit cached evidence; never use a rebuild date as an observation date.
- Completed runewords need actual base rarity and ethereal evidence; recipe identity alone cannot supply them.
- Resolve unclassified rarity using native identity and explicit listing evidence, retaining contradictions.
- Inspect structurally ready rows through exact comparison contracts; readiness alone is not a price.

Reproduce with:

```sh
uv run --offline python -m pricing.knowledge.assessment.maintenance.market_readiness --all-items --as-of 2026-09-25
```

Input: `pricing/data/appraisal-market.jsonl`
SHA256: `23514d7b3caa599eaf2489586820cea1a86340727cc037c0c5cf4ed1fd938b5b`

Raw audit for this run: `tmp/market-blockers-audit.json`. Existing publication and
runtime appraisal output are unchanged. No market collection was performed.
