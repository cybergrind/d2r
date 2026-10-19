# Buff expiration reminders

## Accepted best-effort implementation (2026-09-21)

The user authorized a timer when start and applied level are known, otherwise
a configurable 30-second message on observed removal. Implemented for Consume
in `consume.py` and `osd/widgets/consume.py`; the historical “not enabled” notes
below describe the research stages before this decision.

The build-gated optional reader uses the verified bit/list path and individual
effect level. The widget estimates duration only on a fresh inactive-to-active
transition. It uses the applied level, not aggregate stats/current gear. A
15-second warning lead and 30-second removal notice are configured in
`OSD.consume`. Removal includes summon cancellation. Startup already active
uses removal-only behavior; unknown level, tracking gaps, changed effect identity
or level discard the estimated deadline. Observed removal still emits the notice.
Death/session resets clear tracking. Undetectable active-to-active refresh is
a best-effort limitation, and elapsed estimates are explicitly labelled.
Reduced live fixtures verify absent, level 9, level 7, and restored-armor cases.

## Gear-change validation: cast level survives re-equipping (2026-09-21)

Run `runs/consume/20260921T161529Z-a527e6c0` completed: 58 captures, no sampling
exceptions; 37 stable, 21 unstable. A new game process was used (PID 2992880,
start ticks 277373204). The supplied tooltip shows Consume level 7, 160 seconds;
the user cast with a -2 skill gear change and then restored the armor.

Stable samples corroborate the sequence:

- +23.15 s: armor defense stat changes 894 -> 656; class-skill stat 83/layer 7
  with value 2 disappears. Consume remains absent.
- +30.53 s: Consume effect `0x83C638A0`, state 208, appears with its own stat
  350=381 and 351=7. Buff bonuses match the level-7 tooltip (31 speed, 11 max
  life percent, 16 magic damage, 10 resistance reduction).
- +44.26 s: defense returns to 894 and the +2 class-skill stat returns. The same
  Consume effect still has 351=7 and unchanged bonuses. Aggregate player stat
  351 changes 25 -> 27; this further demonstrates why aggregate level is wrong.

The effect record therefore preserves the applied level across this gear swap.
Combined with the level-9 test, this supports deriving duration from individual
Consume effect level instead of current equipment or a fixed 200-second value.
Level 7's tooltip matches the same formula (160 seconds). Natural expiry at
level 7 was not measured in this short test. The recording ends while Consume
is still present; it is not a cancellation or active-to-active refresh test.

Remaining-time calculation still needs an observed activation time: no direct
expiry timestamp has been recovered. Mid-buff attachment and refresh without
an observed inactive transition remain unknown-time cases, not full-duration
casts. No production warning has been enabled yet.

## Short online capture: applied skill level (2026-09-21)

User confirmed Online/Battle.net. Run `runs/consume/20260921T161158Z-5e1fda6b`
used probe version 2: 26 captures over 26.73 seconds, no sampling exceptions;
19 passed overall stability checks. All 26 dedicated effect-list captures
completed without traversal errors. Generic discovery is a separate bounded
capture and does not establish global absence of a timer.

Consume appears by +3.23 seconds and is absent by +22.45 seconds after the
requested summon cancellation. The complete chain retains state 208 at
`0xA5F269C0` throughout the active interval. Across 14 stable active samples,
its entire captured 0xD0-byte header and stat array are identical. Candidate
header expiry/skill words +0x24/+0x28/+0x2C are zero. This rules out a ticking
counter in those captured fields, not timers elsewhere or a fixed deadline.

Crucially, its own +0x30 stat array contains:

| Layer-zero stat ID | Raw value | Meaning |
| --- | --- | --- |
| 350 | 381 | modifierlist_skill: Consume |
| 351 | 9 | modifierlist_level: matches supplied level-9 tooltip |
| 67 | 33 | velocitypercent |
| 76 | 13 | item_maxhp_percent |
| 357 | 18 | observed Defiler damage bonus |
| 358 | 10 | observed Defiler resistance bonus |

Stat 350/351 names and network Send Bits are confirmed in
[itemstatcost.json](https://raw.githubusercontent.com/blizzhackers/d2data/master/json/itemstatcost.json)
on 2026-09-21. Read these from the individual effect: the player aggregate can
sum modifier-list skill IDs/levels from multiple effects and is unsuitable.

This is a concrete route to dynamic duration without a hardcoded current level:
use the applied effect's level and Consume's duration formula, then track from
observed activation. The data formula `ln12` with Param1=1000, Param2=500
corresponds to `(1000 + 500*(level-1))/25` seconds and matches the level-9
200-second tooltip/natural-expiry capture. It is still a calculated duration,
not a recovered remaining-time value. Mid-buff attachment and unobserved refresh
remain unresolved and must not receive invented start times.

Next short validation: summon a demon first; start inactive, change +skills gear
to a different tooltip level, cast Consume once, then restore the gear while
the buff remains active. Check whether the effect stores the new cast level
and preserves it after the gear change. After ~10 seconds cancel by summoning,
then stop after five seconds. No natural-expiry wait is needed for this check.

## Dynamic timing requirement and probe revision (2026-09-21)

The user rejected fixed-duration estimates: skill level and duration vary.
The proposed 200-second estimate below is not an accepted implementation.
Prefer a verified live remaining-time or expiry field. Reading cast-time skill
level and evaluating the duration formula would still require verified cast/
refresh detection and clock semantics; current gear level alone is insufficient.

Probe version 2 records dedicated candidate effect chains before generic
discovery. It follows root +0xC8 (hypothesis) and +0xD0 (observed) through
node +0x68 (observed), up to 128 unique nodes, with cycle/budget reporting,
raw headers, stat arrays, and identity/link rechecks. This bypasses the original
three-hop exploration depth and preserves the effect's raw timing/skill fields
even when it is deep in the list. The generic walk now rejects pointers outside
readable mappings before enqueueing them, so stat values cannot consume its
budget merely by looking like aligned addresses. No new timer offset is assumed.

Repeat the isolated single-cast natural-expiry recording with version 2.
The character is online/Battle.net; do not assume an authoritative server-side
timer is present in the local process.

## Natural expiry recording (2026-09-21)

Run `runs/consume/20260921T152752Z-5048ef70` completed by user interrupt.
226 attempts over 232.96 seconds: 218 captures, eight unavailable samples;
194 captures passed stability checks, 24 did not. All candidate neighborhoods
were truncated. The supplied tooltip confirms skill level 9 and 200 seconds,
with +13% max life, +33% run/walk, +18% magic skill damage, and -10% enemy
magic resistance for the Defiler bonus.

Using only stable samples, the same `+0xB48 & 0x10000` candidate is absent
through +15.678 s, present by +17.808 s, remains present through +216.444 s,
and is absent by +217.475 s. The first-active to first-inactive interval is
199.667 seconds; sample-boundary uncertainty permits a duration of approximately
198.636–201.797 seconds. This agrees with the tooltip's 200 seconds. Max-life
and bonus stat changes corroborate the active interval. The capture began
inactive and ended inactive; no active-to-active refresh was tested.

No reliable decrementing timer was identified in captured blocks. This is
evidence for a presence-driven estimated timer, not a verified game countdown:
start a configured 200-second estimate only after observing an inactive-to-active
transition, warn after 185 seconds for a 15-second lead, and clear on confirmed
removal. Do not start a full-duration timer when attaching mid-buff. Skill-level
changes, successful refresh while still active, and offline pause behavior need
separate handling/verification before treating that estimate as generally reliable.
These observations do not enable a production warning yet.

## First live recording (2026-09-21)

Run `runs/consume/20260921T152251Z-2cf5eb23` completed by user interrupt:
51 attempts over 52.35 seconds, 50 captured samples, one unavailable-player
sample. Of the 50 captures, 45 passed stability checks and five did not.
All candidate walks hit the exploration limit; absence from these bounded
neighborhoods is not evidence that a timer does not exist.

Stable samples show a candidate Consume bit at player stat-list `+0xB48`,
mask `0x10000`: inactive initially, active by +5.21 s, inactive by +24.04 s,
active again by +26.12 s, inactive by +39.72 s, inactive at the end.
These are sample timestamps, not exact cast/expiry times. This is consistent
with state 208 in a bitset starting at `+0xB30`. Aggregate max HP and other
buff-related stats rise during both active intervals and return afterward.

Candidate linked records contain state 208 at `+0x20`, reached from the root's
`+0xD0` pointer during early active samples. Their `+0x24`, `+0x28`, and `+0x2C`
words are zero; no reliable countdown was identified in captured blocks.
The root pointer changes while the state bit remains active, so following only
that pointer is insufficient for continuous effect tracking.

The capture contains two active periods separated by an inactive gap, not a
demonstrated refresh of an already-active state. The user confirmed that
summoning another demon immediately removed the buff. Treat the corresponding
gap as user-reported cancellation, not natural expiry; these intervals cannot
establish Consume's duration. The exact action timestamps, final disappearance
cause, and tooltip duration remain unconfirmed. No production state offset or
expiry warning is enabled on this evidence.

Next capture should isolate natural expiry: have the demon ready before
recording, capture an inactive baseline, consume it once, then avoid summoning
or other buff-affecting actions until it expires. Test refresh separately using
an already-present eligible demon if available, without an intervening summon.

## Initial source research

Investigated 2026-09-21. Source research only; no live buff/timer capture yet.
No production offsets or reminders enabled by this investigation.

## Findings

Detecting active buffs is plausible. Reliable advance expiration warnings need
more than an active-state bit: a successful refresh can leave that bit set.
Our reader currently captures player aggregate stats, not buff state flags or
individual effect timers. Existing `units.json` snapshots therefore cannot
establish a countdown or reliably distinguish recasts.

There is a concrete timer research lead. Legacy
[D2MOO's stat-list structure](https://github.com/ThePhrozenKeep/D2MOO/blob/5596f5cb6c5251a0a07c6637d26458b06099d516/source/D2Common/include/D2StatList.h#L465)
contains state, expiry, skill number and skill level. Its
[expiration updater](https://github.com/ThePhrozenKeep/D2MOO/blob/5596f5cb6c5251a0a07c6637d26458b06099d516/source/D2Common/src/D2StatList.cpp#L1830)
decrements expiration on the client for lists carrying the appropriate flag;
the server uses a frame comparison. This does NOT establish that D2R exposes
the same field, that every buff receives a client timer, or that a candidate
value is an absolute deadline rather than a remaining-frame count.

Older D2R readers expose state bits and stat-list links, but their offsets differ:

| Source snapshot | State bitset relative to player stat-list pointer |
| --- | --- |
| [MapAssist](https://github.com/dglEnraged/MapAssist/blob/c503b29d014d0bdb0a8a14667fec2375ffcc2e3a/Structs/UnitAny.cs#L74) | `+0xAC8`, six 32-bit words |
| [d2r-mapview](https://github.com/joffreybesos/d2r-mapview/blob/50131a7651833a468774374b7c7b07c4ff08b7f8/src/memory/readStates.ahk#L1) | `+0xAD0`, six words |
| [d2go](https://github.com/relentlessricktrinidad/d2go/blob/1fb1e7a6569fef21e6e3a63749244f65a80673a0/pkg/memory/player.go#L148) | `+0xAF0`, six words |

These are discovery leads, not supported-build facts. Six words cover IDs 0–191
and cannot represent the Warlock states below. Do not transplant that limit.
MapAssist also exposes previous/last-list links, but does not establish an
expiry reader in the inspected structure.

## Candidate effects

Names and IDs checked against [skills.json](https://raw.githubusercontent.com/blizzhackers/d2data/master/json/skills.json)
and [states.json](https://raw.githubusercontent.com/blizzhackers/d2data/master/json/states.json)
on 2026-09-21. These identify effects; they do not validate memory offsets.

| Skill | Skill ID | Self-state | State ID |
| --- | --- | --- | --- |
| Consume | 381 | consume | 208 |
| Frozen Armor | 40 | frozenarmor | 10 |
| Shiver Armor | 50 | shiverarmor | 88 |
| Chilling Armor | 60 | chillingarmor | 20 |
| Battle Orders | 149 | battleorders | 32 |
| Battle Command | 155 | battlecommand | 51 |
| Hex Purge | 389 | hexpurge | 202 |
| Eldritch Blast | 384 | eldritchblastperiodic | 221 |

The user confirmed “sacrifice” means Consume and selected it for the first live
probe; they do not currently have Frozen Armor. The data's literal Sacrifice
is a Paladin attack, skill 96. Other armor effects remain future work. Bone Armor and
Cyclone Armor use absorption stats instead of a duration formula, so a generic
expiration policy should not be applied to every armor effect.

## Proposed reminder behavior

- Configurable default lead time: 15 seconds, with per-effect enable/override.
- Show e.g. `Consume: recast in 15s` when verified remaining time enters the
  warning window; update the displayed countdown.
- Hide after a verified refresh moves expiry outside the warning window.
- After observed expiration, show `Consume: expired — recast` until reapplied
  or the session ends. Limit this to explicitly tracked effects; never warn
  about every absent skill.
- Clear on character/session change or death. Unavailable/stale observations
  suppress the warning; they must not be interpreted as expiration.
- Treat effects with no verified finite timer separately. A timer based on a
  keypress cannot prove that a cast succeeded, and a timer started when the OSD
  first sees an already-active buff cannot know its remaining duration.

## Required live verification

The optional host research probe `uv run -m inventory_tracking.buff_probe`
records timestamped raw player
stat-list headers, candidate state words, and bounded linked-list entries.
It remains outside the production sampling loop. It reuses executable hash,
process identity, mapping and unit/session checks; cap nodes, bytes and time,
detects cycles, and publishes a completion report for the agent to consume.
The bounded pointer neighborhood is discovery data, not a verified stat-list
traversal. Each record includes stability and truncation flags. Default recording
limit is 30 minutes; Ctrl+C closes the file and publishes completion. Output is
under `inventory_tracking/runs/consume/<run>/`.

First recording: remain inactive for 10 seconds after READY, cast Consume,
wait about 20 seconds, refresh Consume by consuming another demon, then allow
natural expiry and another 10 seconds before Ctrl+C. Stay in the same game,
avoid gear/skill changes, and record the tooltip duration and skill level.

For each exact skill, compare absent → cast → time passing → recast while still
active → natural expiry. Record the tooltip skill level and duration. This must
establish both the state identifier and a timer that progresses at the expected
rate, refreshes on successful recast, and disappears/expires with the effect.
Check whether timers are remaining frames or deadlines and verify the frame
rate instead of assuming either. Also test starting the OSD mid-buff, death,
weapon swap, new game, and offline pause if applicable. Online and offline
behavior must not be assumed identical.

If this build only exposes presence, an accurate 15-second advance warning is
not established. Presence-based missing-buff reminders remain a possible
smaller feature after state verification; duration estimates would require
verified application/refresh detection and cast-time level/synergy information.
