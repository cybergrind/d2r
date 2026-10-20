# D2R — session starting point

Local gameplay tooling and appraisal knowledge for **Softcore · Non-Ladder · PC ·
Reign of the Warlock**, currently playing an Echoing Strike Warlock.

**Working on macros? Start with the [macro framework guide](inventory_tracking/macros/README.md)**
for runtime flow, terminology, code ownership, extension points and tests.

## Enter the work

1. Read [AGENTS.md](AGENTS.md) for repository rules and the task's skill, and
   [development.md](development.md) for code changes.
2. Check `git status --short` and `git branch --show-current` before editing;
   preserve existing work. Do not commit unless asked.
3. Pick the entry below and read only the relevant area. For code discovery,
   use CodeGraph first when `.codegraph/` exists; text searches use `rg --no-config`.
4. Check current code and relevant tests before relying on an older plan's status.
   Follow the current task; a document's unfinished queue is not a request to resume it.

## Find the right area

| Work | Entry point |
| --- | --- |
| Macros, combat, movement, builds | [Framework starting guide](inventory_tracking/macros/README.md) |
| The KP_6 loop's live state: rounds, rulings, restarts | [Loop journal](inventory_tracking/macros/loop-journal.md) (the [d2-loop-watch skill](.agents/skills/d2-loop-watch/SKILL.md) keeps it) |
| Macro implementation planning | [Stage summary](inventory_tracking/macros/framework-plan.digest.md), then the relevant [plan section](inventory_tracking/macros/framework-plan.md); [incident/decision history](inventory_tracking/macros/plan.md) |
| Inventory reader and host tooling | [Inventory tracking](inventory_tracking/README.md) |
| Overlay, potion automation, host startup | [OSD runbook](inventory_tracking/osd/README.md) |
| Input guards and delivery | [Input design](inventory_tracking/input/design.md) |
| Level navigation and route stages | [Routes](inventory_tracking/levels/routes.md) |
| Offline item knowledge | [Knowledge base](pricing/knowledge/README.md); select the appraisal/KB skill in [AGENTS.md](AGENTS.md) |
| Assessment engine development | [Code map](pricing/knowledge/assessment/README.md), then [Current contract](pricing/knowledge/assessment/planning/COMPLETION_CONTRACT.md) — use its **Current contract** section; older review artifacts are frozen |
| Pricing, builds, filters, mules, listings | [Task-to-skill table and guide map](AGENTS.md) |

Keep detailed behavior and progress in each area's documents. This file is the
navigation map for a new session, not a duplicate status log.

Historical documents are labeled at their entry. Read them for a specific incident,
source or design decision; their old “next” instructions do not start new work.
The frozen `handoff.md` and assessment `STATUS.md` are archived in `pricing/archive/2026-10-19/`. Keep current behavior in the
area guide and dated evidence in its history, so corrections replace stale claims
instead of accumulating contradictory updates in an entry point.
