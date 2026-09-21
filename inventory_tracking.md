# D2R inventory, health and potion automation

Implemented and live-accepted on 2026-09-21. Start at the
[package README](inventory_tracking/README.md) for operation, evidence and external
references; [handoff.md](handoff.md) records current status and remaining research.

Delivered scope: supported-build host memory reader; player/merc health and belt
stock; transparent alert OSD; Teleport charges/repair and portal refill reminders;
player/merc healing and rejuvenation with focus/freshness checks, independent
cooldowns, consumption acknowledgement and persisted suspension/reservations.

```text
Host reader → timestamped domain state → presenter/widgets → OSD
                                      → healing policy → potion coordination → key delivery
Recorded fixtures → reader/domain/controller/presenter tests
```

Acquisition, domain parsing, policy, input and rendering are separate; the
[runbook](inventory_tracking/osd/README.md#runtime-structure) maps modules and
[widget contracts](inventory_tracking/osd/design.md) describe extension points.
Known limits and future research live in the handoff, without an active milestone
checklist. The original implementation plan has been retired.
