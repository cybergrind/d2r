# Offline item assessment — start here

Code map checked **2026-10-13**. This package converts decoded item facts into
comparison contracts, utility/build-role evidence and trade assessment. Market
research is a separate workflow; ordinary appraisal stays offline.

## Current work and authority

Read the **Current contract** in [COMPLETION_CONTRACT.md](planning/COMPLETION_CONTRACT.md)
for the objective, measures, queue and stopping rule, then the relevant section of
[PLAN.md](planning/PLAN.md). Progress is measured by `inventory_tracking/corpus` score
files. Dated numbers are snapshots, not fresh verification.

`planning/STATUS.md`, root `handoff.md`, per-item formal reviews and the old gates
below the contract's frozen boundary are historical references. Do not append to
those logs, regenerate their receipts or resume their queues. A feature's presence
or a passing unit suite does not establish the current contract's completion.

## Runtime path

1. Native item capture/decoding lives in `inventory_tracking/hover/` and `items/`;
   [APPRAISAL.md](../../../inventory_tracking/APPRAISAL.md) describes the host service.
2. [engine.py](engine.py) exposes `assess_result(extraction)` and the compatibility
   projection `assess`. It normalizes facts, classifies the family, asks the handler
   for a contract, and assembles roles, base/leveling utility and comparison requests.
3. [pipeline.py](../pipeline.py) exposes `retrieve_draft`. It pins the date and local
   evidence snapshots, checks their generations, retrieves comparison evidence and
   calls [pricing.py](pricing.py) to finalize the assessment.
4. Host presentation and verdict integration live in `inventory_tracking/appraisal/`;
   corpus scoring measures the product behavior rather than a single engine return.

## Where changes belong

| Concern | Source |
| --- | --- |
| Facts, provenance, known/unknown fields | [domain/](domain/), [adapters/capture.py](adapters/capture.py) |
| Family dispatch and comparison contracts | [registry.py](registry.py), [handlers/](handlers/) |
| Reviewed build/utility/trade rules | [profiles.py](profiles.py), [policies/](policies/), [rules/](rules/) |
| Socket, upgrade and other derived mechanics | [mechanics/](mechanics/) |
| Scoped comparable retrieval | [market_repository.py](market_repository.py), [comparables.py](comparables.py) |
| Commodity amounts and basket references | [commodities.py](commodities.py), [commodity_sets.py](commodity_sets.py) |
| Maintenance and replay tools | [maintenance/](maintenance/) |
| Data restore, index and publication workflow | [Knowledge-base guide](../README.md), [update-kb skill](../../../.agents/skills/update-kb/SKILL.md) |

Named items, bases, affixed items, completed runewords and commodities have implemented
paths. That does not mean every variant or modifier is supported, or that each item
has enough market evidence for a numerical estimate. Keep unknown facts explicit;
keep own-use, guide demand, liquidity and comparable pricing distinct. Do not turn
missing market evidence into zero value or vendor advice.

## Verification

Run focused tests for the changed policy/mechanic and a saved capture that exercises
it. For the package regression suite:

```sh
uv run --offline pytest tests/pricing/knowledge/assessment -q
```

Follow the current contract's corpus measures for behavioral progress and the KB
skill's publication/replay checks for changed runtime data. Do not rebuild evidence
or publish a generation merely to read documentation.

## Historical implementation detail

[IMPLEMENTATION_HISTORY.md](IMPLEMENTATION_HISTORY.md) preserves the former README
in full: dated implementation slices, assumptions, coverage counts and examples.
Its “current”, “next” and incomplete-feature statements apply to their original
slice; consult current code before using them. The history is a targeted reference,
not a prerequisite for every session.

### Completed runeword records

The [historical runeword section](IMPLEMENTATION_HISTORY.md#completed-runeword-records)
records identity and comparison requirements. Check the current runeword handler,
mechanics and tests before changing those contracts; recipe recognition alone does
not prove complete roll or base/ethereal evidence.
