# Framework plan — current entry

Checked against code and the full plan on **2026-10-13**.
Start with [README.md](README.md) for the running framework and terminology.
Use [framework-plan.md](framework-plan.md) only for the stage being worked on.

## Implemented

- Stages 0–3: golden decisions, arena, build contracts/registry and the framework/build
  split. Builds supply attack, movement and buffs; the service injects the registry.
- Stage 3½: recorded-take evidence and monster-model refitting; arena moves take time.
- Stage 4 is in progress: macro potion judgement/delivery, OSD burst handling and
  crowd-escape positioning exist. These do not establish completion of the full safety stage.
- The teleport step handles a pack at its destination before hopping into it.

## Continuing work

The user authorized Stage 4 behavior changes on 2026-10-12; see
[Stage 4](framework-plan.md#stage-4--safety-detailed-at-entry-2026-10-13).
Do not ask for that authorization again or repeat completed preparation because
an older snapshot describes it as pending. Check the current code/tests against the
specific stage task before implementing it; stage tables include original proposals.

The remaining design includes threat-based position scoring/veto and survival
reactions, navigation refinements, goal arbitration/leashes, tactic composition and
swap/buff extensions. Stages 5–8 remain outlines, not descriptions of live behavior.

Use arena distributions across seeds/scenes and incident calibration for behavior
changes; individual simulated plays are not proof of live safety. Follow the relevant
regression gates in the full plan. Historical test totals and calibration ratios are
in the dated records; obtain fresh results for the change in hand.

The original Stage 0 tree-freeze precondition applied to its recorded baseline;
it is not a new-session approval gate. Check `git status --short` and
`git branch --show-current` for today's checkout. Preserve unrelated work and do
not commit unless asked. Read only the stage relevant to the user's current task.
