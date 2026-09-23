# Appraisal storage research — 2026-09-23

## Decision
Use versioned JSON evidence as the reviewable source of truth and a rebuildable SQLite database with typed relational facets and FTS5 for offline retrieval. Query exact identity and hard item constraints before text ranking. No embedding server or vector database is required for the initial implementation.

SQLite documents application-local databases and data analysis as suitable use cases. FTS5 supports token/prefix/phrase searches and ranked results; JSON functions support preserving evidence payloads alongside indexed scalar columns. Elastic documents hybrid search as lexical plus semantic retrieval. These are capabilities, not proof that semantic ranking improves this particular task.

Primary references inspected 2026-09-23:
- https://www.sqlite.org/whentouse.html
- https://www.sqlite.org/fts5.html
- https://www.sqlite.org/json1.html
- https://www.elastic.co/docs/solutions/search/hybrid-search

## Why structured retrieval first
Socket counts, ethereal status, rarity, skill identity, item level and numerical affixes change applicability and value. Semantic similarity must not allow a 3-socket base to inherit 4-socket prices or a weak rare to inherit a chase-roll median. Build demand, leveling utility and market value are separate relations. Each assertion needs its source locator and date. Existing JSON must remain usable without raw caches being present.

Exact identity -> eligible conditions -> matching evidence -> bounded report is the appraisal path. FTS is a discovery tool for prose and unfamiliar patterns, not a price comparator. Keep original labels and unresolved aliases so normalization never destroys distinctions. Missing evidence means unresolved, never zero.

## Alternatives
- JSON scans alone: minimal dependencies, but current repeated fragmented reads increase retrieval volume and reasoning cost (see appraisal-speed-review-2026-09-21.md). Keep JSON as inputs, index once.
- SQLite + FTS5: local, inspectable, transactionally rebuildable, supports facets and joins. Chosen pending fixture validation and measured query performance.
- Vector-only RAG: rejected as the authority for numerical conditions and item identity; approximate similarity cannot establish eligibility.
- Hybrid lexical/vector RAG: optional later for explanatory prose if a held-out synonym/recall test demonstrates improvement. Exact predicates still gate prices. No cloud dependency in appraisal.
- Hosted Elasticsearch: capable hybrid search but unnecessary service operations for this single-player local corpus.

## Acceptance measurements
Measure command startup + query latency, output bytes, retrieval rounds and exact-condition correctness separately. Report measured values, do not infer end-to-end screenshot speedup from SQL timings. Offline tests must fail any attempted network connection, including missing-cache paths. Rebuild must be deterministic from portable data with hashes and schema version; preserve last usable DB on failure.
