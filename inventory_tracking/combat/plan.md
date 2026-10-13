# Combat work and recent evidence

Start with [the framework guide](../macros/README.md) for code ownership and
[the stage summary](../macros/framework-plan.digest.md) for current implementation work.
Recorder/take infrastructure and shared decisions live here; Echoing Strike mechanics,
policy and simulation live under `inventory_tracking/builds/warlock/echoing_strike/`.
The dated entries below are evidence, not a separate task queue.

## Older evidence

The [history through 2026-10-12](history-through-2026-10-12.md) preserves the original
stages, model measurements and review dispositions. Search the relevant symbol/take:

```sh
rg --no-config -n '<symbol>|<take>' inventory_tracking/combat/plan.md inventory_tracking/combat/history-through-2026-10-12.md
```

- [Historical contract (2026-10-10; relocation note added 2026-10-12)](history-through-2026-10-12.md#historical-contract-2026-10-10-relocation-note-added-2026-10-12)
- [Note, 2026-10-11: where a monster will be (the client's code, the path record, the lead)](history-through-2026-10-12.md#note-2026-10-11-where-a-monster-will-be-the-clients-code-the-path-record-the-lead)
- [Note, 2026-10-12: monsters that walk and strike by themselves (`sim/monsters.py`), first fit](history-through-2026-10-12.md#note-2026-10-12-monsters-that-walk-and-strike-by-themselves-simmonsterspy-first-fit)
- [Note, 2026-10-12 (later): Lightning Enchanted damage, and recording what hurts the character](history-through-2026-10-12.md#note-2026-10-12-later-lightning-enchanted-damage-and-recording-what-hurts-the-character)
- [2026-10-12 10:10 — no place in the middle of a pack (stance.py CROWD_MOST)](history-through-2026-10-12.md#2026-10-12-1010--no-place-in-the-middle-of-a-pack-stancepy-crowd_most)

## Recent entries

## 2026-10-13 — the resistances in the frames (schema 3)

- Why: the fight at the Infector seal (take 20261012T182157Z-108, architecture.md §6.2.3) was under a
  curse from its first second, and a take showed the resistances only at a drop of life: when a curse
  lands and how long it lasts were bounded, not seen (arena/evidence/CURSES.md).
- Now: a frame holds `r` (physical, fire, lightning, cold, poison, as the stat list has them) in the
  first frame with the character and in every frame they differ from the last written. The stats were
  read every frame already, so the recorder reads nothing more. Readers: takes.py `resists_by_frame`;
  the scene cutter takes a frame's reading before a `hurt` event's.
- Next: with a few Chaos Sanctuary games recorded this way, fit the curses (who casts, how soon, how long).
