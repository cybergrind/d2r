"""Attack mode and the seek step (`Hunter`; its parts in macros/hunting/).

Attack mode (`Hunter.attack_mode`) fights everything within the build's attack reach with a clear shot while
the player moves as they like; only its toggle, the macro request, leaving the game or MISSES_IN_A_ROW stopped
fights end it. A fight (`Hunter.fight`) is one hold of the strike input with the pointer on the attack's aim
(combat/controller.py decides; this module reads the game, asks it and acts), buffs cast under it (buffs.py) and
the main weapons for a tough pack. The player's move comes before any strike (`sense`, `serve_move`). The seek
step (`Hunter.seek`) goes toward the nearest elite, else the nearest unexplored room.
Design notes: macros/history/hunt.md; rule history: macros/plan.md.
"""

import math
import threading
import time
from collections.abc import Callable, Sequence
from contextlib import ExitStack
from dataclasses import replace
from functools import partial

from inventory_tracking.combat import pack as herald_pack, threats
from inventory_tracking.combat.controller import (
    CLICK,
    GAVE_UP,
    MOVE_CLICKS,
    NO_CAST,
    PENDING,
    REAIM_UNITS,
    RETAP,
    Aim,
    CastWatch,
    Move,
    aim_choice,
    serve,
)
from inventory_tracking.combat.mechanics.life import rank_share
from inventory_tracking.combat.policy import MIN_FOCAL, RUN_MODES, STRIKE_REACH, Choice, Policy, observe
from inventory_tracking.combat.score import LiveScore
from inventory_tracking.combat.threats import dolls
from inventory_tracking.common import LOG
from inventory_tracking.game.layout import ITEM_UNIT, LYING_DEAD, MONSTER_UNIT, NO_OWNER
from inventory_tracking.game.records import HEALING, REJUVENATION, Drop, Loot, Monster, Player, World
from inventory_tracking.game.view import Viewport
from inventory_tracking.levels.model import Ground, Level, Room, Target, unpack_cells
from inventory_tracking.levels.presets import display_name
from inventory_tracking.levels.route import room_at
from inventory_tracking.macros import binding, cta, pickup as pickup_module, safety as safety_module
from inventory_tracking.macros.actuator import POINTER_DRIFT, Abort, Cancelled
from inventory_tracking.macros.agenda import Agenda
from inventory_tracking.macros.buffs import Buffs, worn_cta
from inventory_tracking.macros.build import Attack, BuffFacts, Build, Intent
from inventory_tracking.macros.cube import tidy
from inventory_tracking.macros.drinking import Drinker
from inventory_tracking.macros.drop_ledger import DropLedger
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.goals import FIGHT, PLACE_NEAR, WAIT, Goal, boss_ahead
from inventory_tracking.macros.hunting import choice, judging, moves, sweep
from inventory_tracking.macros.hunting.base import (
    AT_ONCE_CLEAR,
    AT_ONCE_HURT,
    AT_ONCE_SETTLE,
    BOSS_AHEAD,
    DECIDE_SECONDS,
    FIGHT_SECONDS,
    FIRST_STRIKE_SECONDS,
    FOLLOW_CHECK,
    FRAME,
    GUARD_COUNTS_HELD,
    HARD_SCORE,
    HERALD_OMEN,
    HURT_SECONDS,
    IDLE_LOG_SECONDS,
    INPUT_SECONDS,
    KEEP_STOP,
    LABEL_SECONDS,
    LABEL_SHIFTS,
    MAIN_AFTER,
    MISSES_IN_A_ROW,
    NEARING_SECONDS,
    NO_HARM_SECONDS,
    OMEN_LOOK,
    OMEN_SECONDS,
    POLL,
    QUIET_UNITS,
    RUN_IN_PLACE,
    RUSH_UNMOVED,
    SIGHT,
    SLICE,
    STOP_KEEP_SHARE,
    STRIKE_BACK_RETRY,
    SWAP_RETRY_SECONDS,
    TOUGH_POINTS,
    UNTOUCHABLE_SECONDS,
    UNTOUCHED_CASTS,
    WAIT_LOG_SECONDS,
    Bearings,
    Judged,
    Judging,
    Remembered,
    Sweep,
    hostiles,
    strike_input,
    threat,
)
from inventory_tracking.macros.hunting.labels import LABEL_CLEAR_AIM, LabelLook
from inventory_tracking.macros.hunting.shrines import ShrineWatch
from inventory_tracking.macros.hunting.throne import Waves
from inventory_tracking.macros.pickup import Refused
from inventory_tracking.macros.pursuit import LEVEL_LEFT, NONE, SETTLE, Facts, Move as Advance, Pursuit, Told, settled
from inventory_tracking.macros.routines import ACTING, DEAD, Dead, take_battle_weapons
from inventory_tracking.macros.runmode import Mode, Taps, tapped
from inventory_tracking.macros.safety import Safety
from inventory_tracking.macros.sight import clear_shot, firing_spots, in_reach, in_reach as in_reach_of
from inventory_tracking.macros.skillpanel import select_right
from inventory_tracking.macros.skills import SWAP_WEAPONS, TELEPORT, skill_name
from inventory_tracking.macros.supply import Potions
from inventory_tracking.macros.teleport import HOVER_SECONDS, MOVED, Way, hop_toward
from inventory_tracking.macros.tour import Bounds, tour
from inventory_tracking.macros.travel import LOOPED, Point, Step, Tally, Travel, label, life, step_line
from inventory_tracking.models import PotionType
from inventory_tracking.native.layout import TILE_UNITS, TOWN_IDS
from inventory_tracking.takes import decisions
from inventory_tracking.terror.bosses import BOSSES
from inventory_tracking.terror.danger import Unit, packs


__all__ = ['Bearings', 'Hunter', 'threat', 'walled']

# The boss the pursuit goes for (the pursued goal's own fight, not a clearing one) is a boss here too (`Hunter.boss`):
# never left alone as untouchable (`untouched`), its fight held from within the engage ring instead. The arena's
# Vizier stall, 2026-10-21: the Vizier, a super unique and the route's fight boss, took no damage from 19.6 units in 4
# casts, was left alone for UNTOUCHABLE_SECONDS, and the pursuit stood "in reach and not struck" to the play's end in
# 3 of 10 seeds (rca/2026-10-21/arena-failures-findings.md S1). False: act bosses, Heralds and dear classes alone.
PURSUED_IS_BOSS = True

# QUIET_HOLD (2026-10-25, rca/2026-10-25/pickup-veto-pingpong-findings.md; the player: "our goal is to have best
# exp/hour we can", "do not die"). Harem Level 2, 03:35:24-03:36:28, take 20261025T003442Z-51: a Magic Alpha Helm lay 18
# units from an idle tier 5 Herald (Extra Fast) and its pack of 13. buffs.py QUIET_BY_THE_BOSS defers a side drop while
# a boss (a Herald is one: `boss`) stands within the strike's reach (22.1) of the character, judged afresh at every
# look: beyond 22.1 the helm was the run's goal and its safe approach landed within 22.1, where the goal was the
# Herald's fight, every landing of which the pack's keep range barred (macros/safety.py PACK_RANGE_LANDED); the retreat
# landed beyond 22.1 again, and the helm was the goal again: 62 Teleports in 64 s, 0 kills, the helm not taken. The
# goal changing at every look also kept the budgets (hunting/judging.py DANCE_BUDGET, STILL_BUDGET; a drop is a kept
# goal) from counting. True: a drop the boss rule deferred QUIET_FLIPS times within QUIET_FLIP_WINDOW s, each within
# QUIET_FLIP_GAP s of a look it was the side drop at, is left alone (macros/pickup.py SHUNNED) while a boss that
# deferred it lives in the read, on that level, for QUIET_HOLD_SECONDS at most: the fight's goal and its safety stand,
# and the budgets count. A potion is never held. False: the boss rule look by look, as before.
QUIET_HOLD = True
QUIET_FLIPS = 3
QUIET_FLIP_WINDOW = 10.0  # seconds
QUIET_FLIP_GAP = 2.0  # seconds from the look the drop was the side drop at to the look the boss rule deferred it at
QUIET_HOLD_SECONDS = 60.0

# The game sends Echoing Strike's blades to the unit under the pointer, not to the ground the line aims at. The
# Arachnid Lair's first T5 Herald, 2026-10-21 20:30: the held line stood on it, but a Flame Spider drawn over its feet
# took the hover on 21 of its 46 casts in reach (7 of them with 3+ blades on the Herald, against 25 of 25 when the
# hover named it), until the minions in front were dead (rca/2026-10-21/arachnid-herald-1-findings.md). Player,
# 2026-10-21 ~20:34: "we had a quite significant hiccups in delivering damage, until later sstage"; ~20:15: "we need
# to do the best aiming when we're trying to focus mob". True: while the attack holds a leader (attack.py
# HOLD_LEADER), a hover naming another monster moves the pointer onto the leader's body, up it, then away from the
# neighbour (HELD_NUDGES, a look HOVER_SECONDS after each), the strike held all along; back on the line when none
# names it. The hover is looked at every HELD_LOOK_SECONDS then. False: the line's ground whatever is drawn over it.
HELD_ON_BODY = True
HELD_NUDGES = 3
HELD_LOOK_SECONDS = 0.15
HELD_UP = 0.025  # window fractions, as buffs.py NUDGE_UP / NUDGE_AWAY
HELD_AWAY = 0.015

# The Fane's arena, 2026-10-22 (tests/.../situations/fane_death.py; rca/2026-10-21/fane-death-sim-findings.md §4):
# Battle Orders ran out at 8.68 s after 3.2 s unhurt at full life inside its renewal window, and the strike bout never
# asked the upkeep, which runs between bouts only; one blow then took 2056 of 1896. The player: "probably we need to
# keep track of battle order and predict when it runs off, retreat and rebuff". True: every look tracks Battle Orders
# (macros/cta.py `orders_look`, for the safety's ORDERS_PREDICT and REBUFF_RETREAT), and a bout yields at once when it
# is due and its cast is (the upkeep's row due: `orders_due`). False: the upkeep between bouts alone.
BOUT_ORDERS = True
# The same arena, under late looks (drawn, rolled, seed 5): the bout held 12 s in the pack while 4 rejuvenations were
# drunk. True: a rejuvenation drunk within ALARM_SECONDS makes the safety's next look one of DANGER_SECONDS
# (macros/safety.py DANGER_LOOK), and the bout asks the safety at once after it, not at the next DECIDE_SECONDS.
# False: as before.
BOUT_ALARM = True
# The player, 2026-10-22, of danger-durance-1956 (seed 9: a tier 1 Herald's unique doll, one melee blow of 2982 against
# 2907 life, while the macro stood for Battle Orders and then blade-warped for its rebuff beside it): "you just aggro
# doll herald with death mark and then kill him VERY fast, because it has relatively low life even T5". The build's
# fight casts are asked before the bout's first strike while one of its rows says so (`Buff.before_strike`: Death Mark
# on the designated monster, the doll Herald among them, builds/warlock/mark.py DESIGNATED_MARK `mark_ahead`), so the
# demons take the aggro first; Battle Orders waits for a doll Herald's kill (macros/cta.py DOLL_HERALD_FIRST).
# DOLL_HERALD_MARK (on since 2026-10-22 ~13:00) retired into it 2026-10-22. Else the first strike flies unmarked.
# FIGHT_CAST_REACH (2026-10-22, the survival agent's round 6 from the pursuit-mode fane-death-20, seed 4, windowed
# speeds: the bout's last bout_reach was at 5.24 s with the elite Night Lord (x3.85, 3581 a blow under Amplify Damage
# against 2393 life) 9.3 off and closing at ~6.7 a second; Death Mark and the Sigil were cast under the strike,
# 5.24-6.24 s, with no look, and the yield at 6.24 found it 2.7 off: the jump was in the air at its blow, 6.68 s): the
# bout's casts under the strike (the mark, the sigil) wait while melee blows that together take the life can come
# within reach in CAST_SECONDS (macros/safety.py CAST_REACH, `BuffFacts.cast_barred`), and go one a look while such
# blows can come within reach in FIGHT_PACE_SECONDS (drawn, seeds 14 and 18, the `fast` pace: Engorge, Death Mark and
# the Sigil back to back, 1.2-1.5 s blind, the x5.75 unique 21-24 off at the first): the bout goes on looking every
# frame and yields at BOUT_REACH. 320 pursuit plays (4 scenes x 20 seeds, late and on-time looks, windowed and `fast`
# paces), with WALK_REACH: 9 deaths before; 2 with the bar alone; 0 with one cast a look always, but the capped t5 Hulk
# Herald dead in 12 of 20 (15 with this off); 0 and 16 of 20 (11 rejuvenations) with the pace bound to 2 s. False:
# they are cast as their rows ask, back to back, blind for the casts.
FIGHT_CAST_REACH = True
# INSTANT_THROUGH (2026-10-23, rca/2026-10-23/arena-red.md: test_mark_recast's Vizier-seal stage, life 1818 under a
# Venom Lord pack, logged `fight casts held` at every look and never cast Death Mark while Echoing Strike struck on
# from the same spot, so the fight was slower, the mark's demon aggro lost with it; so were test_replay's second seal
# and test_herald): Death Mark is an instant cast (~0.37 s, `Buff.instant`) that neither moves nor roots the
# character, as the strike. True: FIGHT_CAST_REACH's hold lets such rows through while the bout strikes on from the
# same spot (the bout yields at BOUT_REACH first), one a look while paced; the other casts (Engorge, the Defiler, Bind
# Demon, the self buffs) stay held. False: every fight cast held. OFF (2026-10-23, measured, rca/2026-10-23/
# survival-findings.md §2): with it on, the pursuit-mode Fane plays (160, 20 seeds) died once (fane-death-20 drawn,
# late looks, `fast`, seed 8: Death Mark on the Herald at 11.46-11.67 s under the strike, the bout's yield at 11.84 s
# with blows of 5928 against 2943 life 2 off, dead at 12.52) where off none die, the Fane cuts' least life fell 64% ->
# 36% and their kills dropped; the mark's own time (its hover check, macros/buffs.py AIM_CHECK) is a blind cast, not
# the strike's. Survival first: off until the mark has its own reach check over its real cast time.
INSTANT_THROUGH = False
# The before-strike rows (`Buff.before_strike`: the designated Death Mark, the sigil opener) asked at the bout's first
# look too, before the strike is pressed (2026-10-23, rca/2026-10-23/sigil-opener-findings.md §7 A): asked from the
# second look, the strike already down, their cast came after its first. False: from the second look, as before.
AHEAD_BEFORE_PRESS = False
# The player, 2026-10-23 ~20:45: "in herald fight we can put it on pack spawn point BEFORE actual pack spawns, so when
# it spawns - it already debuffed / 2. we can start striking with echoing strike before actual pack spawns => when it
# gets spawned mobs lose a lot of hit recovery" (rca/2026-10-23/omen-opening-findings.md). The takes of 2026-10-21..23,
# 350 omens: the pack shows OMEN_SPAWN s after the omen's first frame (p05 4.95, p95 5.04), all of it in one frame, a
# median 3.6 off the spot; blades in the air there hit members in their first frame (0.04 s) and put some in their
# get-hit mode; a strike with nothing under the pointer flies its whole way (10,760 blades, a median 38 frames).
# `omen_open`: in the quiet before a pack (nothing in reach, an omen pending within OMEN_OPEN_REACH) the build's
# 'opening' rows are asked (the Warlock's sigil, buffs.py OMEN_SIGIL). OMEN_STRIKE True: from OMEN_LEAD s before the
# spawn the strike is held on the line to the spot (`omen_strike`), and a fight going on aims its line through the spot
# in that window (`omen_focal`), so the blades are there as the pack shows (a cast's blades are ~0.9 s from its press
# to 20 units: POINTER_LAG 6 frames, 1.12 units a frame). False: the strike waits for the pack, as before.
OMEN_STRIKE = True  # on 2026-10-24 ~09:50 with OMEN_SIGIL, MANA_ESCAPE (the player's ask)
OMEN_SPAWN = 5.0  # s from the omen's first read to its pack (the takes' median; the read lags the first frame <0.3 s)
OMEN_LEAD = 1.2  # s before the expected spawn the strike goes on the spot
OMEN_GRACE = 0.6  # s past the expected spawn the hold waits for the pack before it lets go
OMEN_OPEN_REACH = 28.0  # units: the omen stand (combat/pack.py PACK_OMEN_STAND 24) and its slack (OMEN_SLACK 4)
# Attack mode with no level run reads the omens in its quiet too (`omens_now`; a level run's agenda reads them). The
# arena's attack-mode Herald scenes set it (situations/herald_omen.py). False: attack mode alone reads none, as before.
OMEN_READ_ALONE = False
# OMEN_MARK_FIRST (2026-10-25, rca/2026-10-25/mark-at-spawn-findings.md; the player, ~11:33: "we have a visible and
# significant delays before DM / for example the recet T5 fight: we have put lethargy in advance, waiting for spawn,
# spawned -> waiting for an extended period of time -> DM", "we need near instant cast after pack has appeared";
# ~11:36: "we can both strike firind + cast DM / when I'm playing it by hand it feels way smoother"; ~11:38: "this
# happens after the actual pack is visible in game"). Today's 33 spawns, "the pack shows" to the mark's key: p50 0.72
# s, p90 1.44, max 2.98, the strike first every time, and at 11:20:03 a keep range's hop between (1.19 s). The player's
# hand (the takes of 10-22..24 played by hand): a key tapped during a cast is cast at the cast's end (0.16 s p50, 0.28
# p90, 15 of 16 kept), one tapped with the character free in the next frame (0.04 s). True: the first look that sees a
# pending omen's tier 4-5 pack (OMEN_EARLY before its expected spawn to OMEN_MARK_WINDOW after it, within
# OMEN_OPEN_REACH of its spot, drawn where the mark may be aimed) casts the build's FIRST rows (Death Mark) before
# anything else, the safety's moves included, once an omen (`omen_mark`): in the omen's hold with the strike held on
# (`omen_strike`), else at the top of attack mode's look; on the member nearest the pointer (the pack's order takes
# any), with the quick aim (macros/buffs.py `quick_aim`). Not under the fight casts' hold (FIGHT_CAST_REACH) and not
# past a real threat the safety saw (`Safety.hold_exempt`) other than OMEN_MARK_PAST's. False: as before.
OMEN_MARK_FIRST = True  # on 2026-10-25 ~12:40: arena 0/20 deaths both stands, least life up; key 0.35 -> 0.03 s
OMEN_EARLY = 0.5  # s before the expected spawn a pack near the spot counts as this omen's (the read lags <0.3 s)
OMEN_MARK_WINDOW = 2.0  # s after the expected spawn the omen's mark is still the first thing (then the mark's rules)
OMEN_MARK_PAST = ('a drainer',)  # the safety's real threats the omen's mark goes before (the coordinator, 11:38)
FIGHT_PACE_SECONDS = 2.0  # one cast a look while blows that take the life can come in reach in this time
ALARM_SECONDS = 2.0
# 2026-10-23: the strike aimed during a Teleport's flight from the landing aimed at (teleport.py PREAIM_FLIGHT calls
# `preaim`); the fight's first aim is left out when the pointer is within PREAIM_PIXELS of the aim it would make from
# where the character landed, PREAIM_SECONDS after the pre-aim at most. The player, 2026-10-23: "human will react in
# under 200ms"; the strike's aim (92 ms p50) came after the landing (rca/2026-10-23/lag-findings.md §1). Off: no hook.
# OFF (2026-10-23, arena, rca/2026-10-23/pause-findings.md §4.4): 0 deaths either way, but the pursuit Fane plays' least
# life fell in 8 of 8 variants (fane-death-20 55% -> 39%, fane-death-24 64% -> 53%), medians unchanged; off until why.
PREAIM = False
PREAIM_PIXELS = 12
PREAIM_SECONDS = 1.0
# PREAIM_NOT_REBUFF (2026-10-25, rca/2026-10-25/smoothness-findings.md §6): no pre-aim during a rebuff retreat's flight
# (the safety's `rebuffed_at`, not landed yet): Battle Orders is cast at its landing, not a strike. In the arena's
# fane-death-20 every seed opens with one, and its pointer move alone (the variant with no move plays as off in 100 of
# 100) took the Herald kills 19 -> 8 of 100, a timing placebo 19 -> 16. False: every hop's flight, as PREAIM was built.
PREAIM_NOT_REBUFF = False
# CAST_TAIL (2026-10-24, rca/2026-10-24/realtime-4-findings.md §7; the player: "improve our reaction speed"): a
# Teleport's landing is read ~77 ms before its cast ends, and the cast's Quick Cast keeps Teleport on the right button
# to the end, so the strike's input was "unready": a FRAME nap, then the whole loop and a second pursue look before the
# fight (cast end -> the fight's first look 89/177 ms p50/p90 live, 560 landings). On: the cast's tail is looked at
# every SLICE and the fight starts from the look that sees the strike back. False: the nap as before.
CAST_TAIL = True  # on 2026-10-25 ~17:15 with CAST_TAIL_HOPS (smoothness-findings.md §6: 1420 arena pairs)
# CAST_TAIL_AGAIN (2026-10-24, the arena's 20 seeds: Herald time +2.7 ± 2.0 s, manaburn's least life -0.06 ± 0.05 with
# CAST_TAIL): the look that sees the cast's end starts the loop's next pass at once (the pursuit's fresh look first),
# not the fight. False: the fight from that look.
CAST_TAIL_AGAIN = False
CAST_TAIL_MOST = 0.25  # seconds of a cast's tail so waited (a Teleport's cast ~0.32 s, its landing read ~0.08 s early)
# CAST_TAIL_HOPS (2026-10-25, rca/2026-10-25/smoothness-findings.md §6): CAST_TAIL waits only a Teleport's tail (the
# hop's Quick Cast keeps Teleport on the right button, 50-80 ms in the arena), not a buff's or a mark's: the arena's
# fane-death-20 waited 0.23 s on Psychic Ward's tail with no look of the pursuit's, and the safety's retreat came after
# a strike instead of mid-cast. False: every cast's tail, as CAST_TAIL was built. Gate (2026-10-25, with CAST_TAIL on,
# 1420 arena pairs): deaths on-only 5 / off-only 6, a timing placebo's spread; fane-death-20 Herald 19 -> 21 of 100.
CAST_TAIL_HOPS = True  # on 2026-10-25 ~17:15 with CAST_TAIL
# MARK_WITH_PRESS (2026-10-24, rca/2026-10-24/dm-latency-findings.md; the player, ~17:38: "the delay between teleport
# and DM (when we have a clear target, like herald) is still quite significant. we need to find out why"): live, 1224
# fight landings marked again within 3 s (the takes of 2026-10-24), the strike first in all; its press, a FRAME nap,
# then a whole second look (81 ms p50) decided the mark, 122 ms (p50) after the strike's down, and the mark's key went
# down 9 ms (p50) after the strike's first cast ended (57 % after it, 127 ms on average): the mark's cast waited on the
# key. True: the look that presses the strike also asks the build's FIRST skills (combat/pack.py FIRST: Death Mark)
# whose rows are due before the strike (`Buff.before_strike`: the designated one's mark), and once the strike's cast
# shows (PRESS_CAST_WAIT at most) casts the mark at once, its key queued under the strike's cast; the strike's first
# press is not moved. Not under the fight casts' hold (FIGHT_CAST_REACH). False: from the next look, as before.
MARK_WITH_PRESS = False
PRESS_CAST_WAIT = 0.08  # seconds for the strike's cast to show after its press (live: 29 ms p50, 46 p90)
# LANDING_MARK (2026-10-24 ~19:40, rca/2026-10-24/dm-latency-findings.md §7; the player's ruling ~17:39: "when we're
# repositioning for re-aggro against T5 heralds, the first things we need to do - drop off aggro from us == DM"): take
# 20261024T161813Z-108, 19:20:30.723, a landing with the tier 5 Herald's pack 22.6-29.2 off and only the monster 312 at
# 21.4 within the strike's reach: no member in `reachable`, so neither combat/pack.py HERALD_MARK_FIRST nor the mark's
# rules had one; Psychic Ward (upkeep, 30.824), the strike at 312 (31.353), a hop of 8 in (landed 31.983), and the mark
# at 32.393. Death Mark has no range of its own (skills.txt row 375: range "none"; builds/warlock/mark.py MARK_REACH):
# whatever the pointer can hover. True: after the pursuit's look made no move, at a jump's landing (LANDING_AHEAD, the
# HERALD_MARK_FIRST tests: a T5 Herald's member, the Herald in the read, the burn) with members drawn on the screen
# (game/view.py `on_screen`), the build's FIRST rows are asked with those members as the ones in reach and the first
# due one cast before the upkeep and the fight, once a landing. Not under the fight casts' hold. False: as before.
LANDING_MARK = False
# LANDING_UPKEEP_WAITS (2026-10-24 ~19:40, the same take: Psychic Ward's upkeep cast at 30.824 put the fight's first
# look 0.53 s after the landing): True, at such a landing (`landing_members`) the upkeep waits until the strike is
# pressed after the jump (LANDING_AHEAD at most); the fight's own rows (a broken ward before the strike) are not held.
# False: as before.
LANDING_UPKEEP_WAITS = False
# HERALD_MARK_SHOWN (2026-10-24 ~20:10, dm-latency-findings.md §8): of the 10 Herald marks after a landing that went
# after the strike (18:49-19:31), at 18:53:20.743, 19:02:32.564, 19:07:32.976 and 19:30:51.185 the member designated
# was within the strike's reach but drawn past the aim's limits ("no Death Mark on the elite 82 (3241908774): its body
# is off the screen at (0.93, 0.39)"; game/view.py AIM_LIMITS), so the mark's key was refused and the strike went
# first. True: at combat/pack.py HERALD_MARK_FIRST's look the FIRST rows are asked with the hostiles in reach whose body
# is drawn inside the aim's limits alone (builds/warlock/mark.py PACK_HOP_FREES then frees the pack's order for one of
# them). False: with all in reach, as before.
HERALD_MARK_SHOWN = False
# SETTLE_BEFORE_FIRST (2026-10-24 ~20:10, the same cases at 18:52:58.418 and 19:19:16.169): a mark keyed on a member
# that went onto a neighbour is found out ("did not take ... cast again") only when the row's `Buffs.due` settles it
# (macros/buffs.py `settle`), at the look after the strike's press; HERALD_MARK_FIRST's look asked the stale state, the
# mark counted as lasting and none was designated. True: that look settles the FIRST rows' last casts first. False: as
# before.
SETTLE_BEFORE_FIRST = False


def holding(attack: object) -> int | None:
    """The leader the attack holds until it dies (attack.py HOLD_LEADER), or None: an attack without a hold too."""
    held = getattr(attack, 'holding', None)
    return held() if callable(held) else None


def walled(level: Level) -> set[Bounds]:
    """The rooms of `level` whose loaded grid has no walkable sub-tile: nothing stands or is seen in them."""
    rooms = {(room.x, room.y, room.width, room.height) for room in level.rooms}
    found = set()
    for grid in level.ground:
        bounds = (grid.x, grid.y, grid.width, grid.height)
        cells = unpack_cells(grid.cells, grid.width * grid.height * TILE_UNITS * TILE_UNITS) if grid.cells else None
        if bounds in rooms and cells is not None and '1' not in cells:
            found.add(bounds)
    return found


def forget(build: Build) -> None:
    """Have the build's attack drop what its earlier looks left, where it keeps any (an attack's `forget`: the
    Warlock's leader held, builds/warlock/echoing_strike/attack.py HOLD_LEADER)."""
    dropped = getattr(build.attack, 'forget', None)
    if dropped is not None:
        dropped()


class Hunter:
    """The hunt's state across presses: the level and what is remembered of it come from the level
    guide and the terror tracker (callables, set by the service), sigils and marks from the clock."""

    def __init__(
        self,
        level: Callable[[], Level | None] | None = None,
        remembered: Remembered | None = None,
        explored: Callable[[int], set[tuple]] | None = None,
        policy: Policy | None = None,
        *,
        build: Build,
    ) -> None:
        self.level = level
        self.remembered = remembered
        self.explored = explored
        self.score = LiveScore()  # the last minute of attack mode: damage and kills (combat/score.py)
        # The KP_6 loop's moves: Blade Warp, with Teleport while the gold pays (the runner's: loop.py `teleports`)
        self.looped: Intent = LOOPED
        self.stuck_until = -math.inf  # until when the loop's moves may take Teleport though it is off (`stuck`)
        # The build's attack, moves and buff plan: the fallback until the runner names the character's (`use`).
        self.build: Build = build
        forget(build)  # a build's attack may keep what its looks saw (the Warlock's leader held): not another hunt's
        # A policy asked where to cast in place of the build's attack (a test's, a harness's): see `policy`
        self.aimed_by: Policy | None = policy
        self.buffs = Buffs(self.build)  # the build's buff plan as it is run, and when each cast was made (buffs.py)
        # The jumps the character can make and the moves made with them (travel.py)
        self.travel = Travel(self.build.movement)
        self.route: tuple[int, list[Bounds]] = (0, [])  # (level, the rooms the explore steps go to stand in, in order)
        self.vanished: set[int] = set()  # remembered monsters that were not where they were seen
        self.tested: dict[int, tuple[int, int]] = {}  # unit -> (casts with the line through it, its life then)
        # boss unit -> until when the run gets back in reach of it (`untouched`)
        self.nearing: dict[int, float] = {}
        self.raisers: frozenset[int] = (
            frozenset()
        )  # the revivers raising their pack at the last look (hunting/revive.py)
        self.restock_said: set[int] = set()  # the potions a restock went for, said once each (`restock`)
        # unit -> (clock judged, Teleport brings it within LOOP_PICK_SECONDS): the loop's far valuables (`on_the_way`)
        self.far_judged: dict[int, tuple[float, bool]] = {}
        self.untouchable: dict[int, float] = {}  # unit -> clock time until which it is left alone
        self.unshot_since: dict[int, float] = {}  # a fight goal's unit -> since when no shot comes (`unshot`)
        # The loop's still watchdog asks for a recovery (running/watch.py `recover`): the clock time, None: none
        self.recover_asked: float | None = None
        self.swap_failed_at = -math.inf  # clock time a swap to the main weapons last did not come
        self.move: Move | None = None  # the move the player asked for and has not got yet: before any strike
        self.left_down = False  # the left mouse button at the last look
        self.drinker = Drinker(self.build.settings.drink)  # the belt keys beside the fight (drinking.py)
        # The clock bounding one look's pricing (`SafetySettings.look_seconds`); the arena's driver replaces it
        self.safety = Safety(timer=time.perf_counter)
        self.dropped = 0  # acts of slow looks dropped in a row (`stale`)
        self.expired_motion = False  # an expired macro click still moving: safety owns the next act
        self.reach_decision: dict | None = None  # the decision a BOUT_REACH yield was made under (`bout_reach`)
        self.struck_at = -math.inf  # clock time the fight last saw the character cast under the held strike
        # (clock, landing, focal) of the strike aimed during a Teleport's flight (PREAIM, `preaim`); the fight's first
        # aim takes it or drops it
        self.preaimed: tuple[float, Point, Point] | None = None
        self.life_seen: int | None = None  # the character's life at the last priced look (`safety_priced`)
        self.hurt_at = -math.inf  # clock time a priced look last saw the character's life go down
        # (the goal's key, since when, the dead seen then, the hostiles' life then) of the run's moves with no progress
        # (judging.py DANCE_BUDGET)
        self.dance: tuple[object, float, frozenset[int], dict[int, int]] | None = None
        # (since when, the dead seen then, the hostiles' life, (when, where, moved) of each look since) of the moves
        # with no progress whatever their goals (judging.py STILL_BUDGET)
        self.still: tuple[float, frozenset[int], dict[int, int], list[tuple[float, Point, bool]]] | None = None
        # NET_PROGRESS (hunting/judging.py): (area, the hostiles seen dead on it): what dies again was raised
        self.slain: tuple[int | None, frozenset[int]] = (None, frozenset())
        # 2026-10-23, judging.py: the hostiles a keep-range hop left (HELD_OFF); the last look's priced facts and the
        # strike reach's progress (clock, dead, lives: YIELD_KEEPS_KILLING)
        self.held_off: judging.HeldOff | None = None
        self.look_facts: Facts | None = None
        self.killing: tuple[float, frozenset[int] | None, dict[int, int]] = (-math.inf, None, {})
        # 2026-10-23, choice.py GUARD_STALL: (drop, since, last look, the dead and lives then); drops freed until when
        self.guard_watch: tuple[int, float, float, frozenset[int], dict[int, int]] | None = None
        self.guards_freed: dict[int, float] = {}
        # 2026-10-23, judging.py REFUSED_PASS: (the fight's place, retreats from it, the last's clock, the dead then)
        self.refusals: tuple[Point, int, float, frozenset[int]] | None = None
        self.refused_places: list[tuple[Point, float]] = []  # (where, until): no tour stop near (choice.py)
        # judging.py SLOW_FIGHT: (the fight's place, since when in reach, the hostiles' life then, the dead then)
        self.slow: tuple[Point, float, dict[int, int], frozenset[int]] | None = None
        self.own_read: tuple[bool, float] | None = None  # (Teleport the character's own, read at) (`own_teleport`)
        self.unmoved_since: float | None = None  # since when the loop's run made no move with a hostile in reach
        self.stands: Point | None = None  # where attack mode last saw the character
        # (where, since when, said) the character has been walking or running without getting anywhere
        self.ran: tuple[Point, float, bool] | None = None
        self.fresh_press = False  # a press seen since `nap` last began
        self.casting = False  # a cast runs or the strike input is held: a click now may be swallowed
        self.pressed_at = -math.inf  # the clock of the fight's last strike press (LANDING_UPKEEP_WAITS)
        self.landing_marked = -math.inf  # the jump (combat/pack.py HOP.at) LANDING_MARK last tried at
        # The pickup step during attack mode: the mode pauses itself once nothing is left in reach.
        self.after_fight = threading.Event()
        # The same request also asks for a step to a better stand.
        self.step_asked = threading.Event()
        self.unwait: Callable[[], None] | None = None  # tells the runner the press has nothing to pick up after all
        self.pick: Callable[[], None] | None = None  # the runner's: the pickup step runs once the mode has paused
        self.gather_looked = -math.inf  # clock time of the sweep's last look for something to pick up
        self.gather_waited = -math.inf  # clock time the sweep last said it leaves a drop for later
        self.drops = DropLedger()  # what the run tried and gave up on, drop by drop (macros/drop_ledger.py)
        self.round_said: set[int] = set()  # the drops said to be gone to first for want of a clear line (`judge`)
        self.bound_said: set[int] = set()  # the hostiles said to die with a summoner (`bound_lost`)
        self.away_said: set[int] = set()  # the same, said to be no fight to hold (`only_bound`)
        self.held: Drop | None = None  # the valuable in sight the sweep stays by (`gather`, `leaves`)
        self.held_said: set[int] = set()  # the drops that staying was said for
        self.held_logged = -math.inf
        self.cover_said: set[tuple[int, bool]] = set()  # the held leaders and outcomes `onto_held` said
        self.stepping: Step | None = None  # the step the fight stopped for
        self.guarding: Advance | None = None  # the safety step the fight stopped for with the pursuit off (`guard`)
        self.sweep = Sweep()
        self.step_asked_at: float | None = None  # clock time of a step taken, until the first cast after it
        # The pursuit's mailbox (macros/pursuit.py): the runner posts presses; a look reads it once and writes it
        # back only over what it read (`swap`): a press posted meanwhile is the next look's (run-0025-findings.md §2.1)
        self.pursuit: Pursuit | None = None
        self.mailbox = threading.Lock()  # the runner's posts and the loop's write-backs, one at a time
        self.bearings = Bearings()  # the runner's: what a goal is named from
        # the runner's: the key's routine (the route's own step) follows the mode's pause
        self.hand_over: Callable[[str], None] | None = None
        self.shack_tries: dict[int, int] = {}  # a shack's container (unit): the loop's tries to open it (`shack_goal`)
        self.shrines = ShrineWatch()  # the Experience Shrines of this game (hunting/shrines.py, 2026-10-20)
        self.use_tries: dict[int, int] = {}  # a route's object (unit): the tries to use it (ROUTE_USE_TRIES)
        self.dead_ends: list[tuple[Point, float]] = []  # spots a move did not reach, and until when they are passed
        self.progressed: tuple[Point, float] | None = None  # the pursuit's last own move's spot and clock (`bounced`)
        # the runner's: a level run ended by the hunt itself (the route's end, the character's death), with why
        self.run_over: Callable[[str], None] | None = None
        # The runner's (`_carry_one`): whether a unique Grand Charm refused for the carried Gheed's Fortune
        # (pickup.py `Refused`) starts the KP_6 loop's Gheed's swap (`carry_one_swap`); None or False: the run's rules
        self.carry_one: Callable[[Refused], bool] | None = None
        # The runner's: the terror zone agenda (macros/agenda.py) and each level's policy (tzroutine.py `policy_of`)
        self.agenda: Agenda | None = None
        self.agenda_policy: Callable[[int], str] | None = None
        self.agenda_said: tuple | None = None  # the last target said (`agenda_target`)
        # (game, level)s whose route goal the run found no way to: worked as COVER from then on (`agenda_target`)
        self.wayless: set[tuple[str, int]] = set()
        self.no_way_since: tuple[tuple[str, int], float] | None = None  # (game, level), since: `judge`
        self.ended_area: int | None = None  # the level of the level run that ended last (`end_run`)
        self.told = Told()  # the reason last said for a decision that moved nothing
        self.told_at = -math.inf  # clock time it was last said
        self.pursued: Goal | None = None  # the goal of the last decision, for the recorder and the viewer
        self.stopped_for: tuple[float, Drop | None] = (-math.inf, None)  # (the press, the drop it takes first)
        self.judged: tuple[float, float, bool] = (-math.inf, -math.inf, False)  # (the press, when, it asks a move)
        # The look a fight was let go for (`yielded_act`): (it, its clock, where the character stood, the level, the
        # press)
        self.yielded: tuple[Judged, float, Point, int, float] | None = None
        # (game, level, boss) -> clock a route's boss fight was first stood at with no boss; those given up
        # (`empty_mark`)
        self.mark_since: dict[tuple[str, int, str], float] = {}
        self.marks_empty: set[tuple[str, int, str]] = set()
        self.waves = Waves()  # the Throne's waves and portal this game (hunting/throne.py; the player, 2026-10-20)
        self.zone_left: tuple[str, int] | None = None  # (game, level) whose run ended as its zone moved on
        self.stop_kept: tuple[int, Bounds] | None = None  # (level, room) of the tour's stop gone to (`next_room`)
        # (the goal's label, the monsters the hands found in the way of its act, until when): `first_fight`
        self.blocking: tuple[str, frozenset[int], float] | None = None
        self.base: Goal | None = None  # the goal of the last look before the fight that bars it (`first_fight`)
        self.settled_at = -math.inf  # clock time an object used has brought what it calls (teleport.py `Use.brings`)
        self.missed: tuple[str, float] | None = None  # (a goal's label, until when) whose act did not take: `nearer`
        # The player's hand (`hand`): when last seen at work, and the pointer at the last look
        self.hand_at = -math.inf
        self.pointer_seen: tuple[int, int] | None = None
        # (the reason, how many times in a row) an act of the loop's was given up for: said every time (I1, I6)
        self.refused: tuple[str, int] | None = None
        self.struck_back_at = -math.inf  # when the strike was last selected on the right button (`strike_back`)
        self.waived: set[int] = set()  # valuables with no room a press went on from: not waited by again
        self.warned: int | None = None  # the valuable the card's "Inventory full" warning is of
        self.potions = Potions()  # the potions of the level, why one was left, the belt's healing (supply.py)
        self.guarded_since: dict[int, float] = {}  # potion -> clock time its guards were first the fight first
        self.fetching: tuple[float, Drop | None] = (-math.inf, None)  # (when judged, a scarce potion worth a detour)
        self.side_left: dict[int, str] = {}  # potion -> why a knot of moves gave it up (choice.py POTION_HELD)
        # QUIET_HOLD: (the drop, its label, clock) last the side drop; drop -> clocks the boss rule deferred it at;
        # drop -> (the bosses that deferred it, the hold's end, the level) while it is left alone
        self.quiet_seen: tuple[int, str, float] | None = None
        self.quiet_flips: dict[int, list[float]] = {}
        self.quiet_holds: dict[int, tuple[frozenset[int], float, int | None]] = {}
        self.area: int | None = None  # the level attack mode last saw the character on (not in town)
        # The run mode (macros/runmode.py): the pickup key's presses, the player's switch (level, full clear), the
        # level's mode (the HUD's) and the (level, line) last said
        self.taps = Taps()
        self.switched: tuple[int, bool] | None = None
        self.mode: Mode | None = None
        self.mode_said: tuple[int, str] | None = None
        self.far_said: str | None = None  # the boss attack mode alone last said it does not go to (`nearby`)
        # Clearing goals passed (key -> until), each one's judging (`Judging`), the key last gone for, goals left
        # for another (key -> (until, other key): TAKE_BACK), the full clear's last rest-of-level look
        self.passed: dict[object, float] = {}
        self.knots: dict[int, int] = {}  # times a unit was passed in a knot's place (judging.py KNOT_PASSES_PLACE)
        self.judging: dict[object, Judging] = {}
        self.went: object | None = None
        self.left_for: dict[object, tuple[float, object]] = {}
        self.rest: tuple[float, int, tuple[Point, str, int | None] | None] | None = None
        # A Herald's coming: its spot -> until when, on the level `omen_area`, and when the missiles were last read
        self.omens: dict[Point, float] = {}
        self.omen_area: int | None = None
        self.omen_looked = -math.inf
        self.omen_marked: set[Point] = set()  # the omens whose pack's mark was asked (OMEN_MARK_FIRST)
        self.omen_waited: str | None = None  # why an omen's mark waited, last said (`omen_waits`)
        self.toured: tuple[int, int, int] | None = None  # (level, rooms, explored) said to have no stop
        # Every level whose tour found no stop since the runner last read them (runner.py `_zone_seen`): a run carried
        # across a passage tours two levels, and `toured` names only the last. Barracks' 52 of 52 rooms, then the Outer
        # Cloister's: Barracks was never judged explored and entered again 6 times (16:02:14-16:03:03 on 2026-10-21)
        self.tours_done: set[int] = set()
        # The runner's: makes cube room for a valuable the inventory has none for (cube.py `stash`), how many went;
        # tried once a drop (`room_tried`)
        self.room_maker: Callable[[Run], int] | None = None
        self.room_tried: int | None = None
        # The runner's (running/room.py `_room_trip_due`): whether a trip to town for room is due for a valuable the
        # cube made no room for, an activity by hand's (the shared no-room routine, the player's ruling of 2026-10-19)
        self.room_trip: Callable[[Run, Drop, World, Loot], bool] | None = None
        # The runner's: whether such a trip could be made in this game now (none: the sites' own rules by hand)
        self.can_trip: Callable[[], bool] | None = None
        # Whether the KP_6 loop is on (the runner's): the sweep holds a plain valuable with no room too
        # (lootpolicy.py `NO_ROOM_PLAIN`, ruled 2026-10-18)
        self.looping: Callable[[], bool] = lambda: False
        # The runner's (loot/api.py `at_once`): the field routine for a big item picked for it, at a quiet look between
        # a level run's moves; whether it decided any (the player, 2026-10-20 ~14:28: "we must redesign our routins to
        # actually have space for mid-run identifying big items")
        self.field_now: Callable[[Run], bool] = lambda run: False
        self.field_area: int | None = None  # the level `field_quiet` last looked in, and the clock it was entered at
        self.field_entered = -math.inf

    def use(self, build: Build) -> None:
        """The build played from now on (runner.py `choosing`). Another build restarts what is kept per build
        (`buffs`, `travel`, the drinker); the level's and the fight's state stays."""
        if build is self.build:
            return
        self.build = build
        forget(build)
        self.buffs = Buffs(build)
        self.travel = Travel(build.movement)
        self.drinker = Drinker(build.settings.drink)

    @property
    def attack(self) -> Attack:
        """The build's attack; Abort for a build without one (attack mode stops)."""
        attack = self.build.attack
        if attack is None:
            raise Abort(f'attack mode off: the build ({self.build.name}) has no attack of its own')
        return attack

    @property
    def reach(self) -> float:
        """Units the build's attack reaches; 0.0 for a build that does not fight: nothing is in its reach."""
        attack = self.build.attack
        return 0.0 if attack is None else attack.reach

    @property
    def policy(self) -> Attack | Policy | None:
        """What is asked where to cast (`aim_choice`): the policy handed in or set, else the build's attack.
        The policy gives the aim alone; the reach and the rest stay the attack's."""
        return self.aimed_by if self.aimed_by is not None else self.build.attack

    @policy.setter
    def policy(self, policy: Policy | None) -> None:
        self.aimed_by = policy

    def boss(self, monster: Monster, *, pursued: bool = True) -> bool:
        """Whether `monster` is a boss: an act boss (BOSSES), a Herald, a class with a dearer life price
        (`SafetySettings.dear`), or the one the pursued goal fights (PURSUED_IS_BOSS; `pursued` False leaves that
        out, for a pickup's "fight first" monster that no shot reaches: hunting/judging.py `kept`)."""
        if monster.tier and monster.leader:
            return True  # a Terror Zone's Herald (stat 367, a unique): fought to its end (HERALD_OMEN)
        if monster.unit_id in self.raisers:
            return True  # a reviver raising its pack: never left alone (hunting/revive.py REVIVER_STAND)
        if monster.txt_id in BOSSES or any(monster.txt_id == txt for txt, _ in self.build.settings.safety.dear):
            return True
        goal = self.pursued
        return (
            pursued
            and PURSUED_IS_BOSS
            and goal is not None
            and goal.do == FIGHT
            and not goal.clearing
            and goal.unit == monster.unit_id
        )

    def side_drop(
        self,
        run: Run,
        here: Point,
        foes: Sequence[Monster] = (),
        world: World | None = None,
        *,
        restocking: bool = False,
    ) -> Drop | None:
        """What a level run takes on its way (hunting/choice.py `side_drop`), a drop the boss rule keeps deferring
        left alone while its boss lives (QUIET_HOLD)."""
        if not QUIET_HOLD or restocking:
            return choice.side_drop(self, run, here, foes, world, restocking=restocking)
        now = run.clock()
        area = world.player.area if world is not None and world.player is not None else None
        self.quiet_release(foes, area, now)
        found = choice.side_drop(self, run, here, foes, world)
        self.quiet_note(here, foes, found, area, now)
        return found

    def quiet_note(
        self, here: Point, foes: Sequence[Monster], found: Drop | None, area: int | None, now: float
    ) -> None:
        """QUIET_HOLD: `found`, the look's side drop, noted; a drop that was it QUIET_FLIP_GAP s ago and that the boss
        rule (buffs.py QUIET_BY_THE_BOSS) defers now is one flip more, and QUIET_FLIPS within QUIET_FLIP_WINDOW s hold
        it (`quiet_holds`, pickup.py SHUNNED)."""
        if found is not None and found.kind not in (HEALING, REJUVENATION):
            self.quiet_seen = (found.unit_id, found.label, now)
            return
        seen = self.quiet_seen
        if seen is None or now - seen[2] > QUIET_FLIP_GAP or not self.buffs.quiet_by_the_boss:
            return
        bosses = frozenset(m.unit_id for m in foes if self.boss(m) and math.dist(here, (m.x, m.y)) <= self.reach)
        if not bosses:
            return  # gone for another reason than the boss rule's
        unit, name, _ = seen
        self.quiet_seen = None
        if len(self.quiet_flips) > 200:
            self.quiet_flips.clear()
        flips = [at for at in self.quiet_flips.get(unit, ()) if now - at <= QUIET_FLIP_WINDOW] + [now]
        self.quiet_flips[unit] = flips
        if len(flips) < QUIET_FLIPS:
            return
        del self.quiet_flips[unit]
        until = now + QUIET_HOLD_SECONDS
        pickup_module.SHUNNED[unit] = until
        self.quiet_holds[unit] = (bosses, until, area)
        LOG.info(
            'Macro: pursuit: %s: deferred by the boss in reach %d times in %.1f s, each a moment after it was the '
            'goal: left alone while %s lives, %.0f s at most (QUIET_HOLD)',
            name, len(flips), now - flips[0], ', '.join(str(boss) for boss in sorted(bosses)), QUIET_HOLD_SECONDS,
        )  # fmt: skip

    def quiet_release(self, foes: Sequence[Monster], area: int | None, now: float) -> None:
        """QUIET_HOLD: the held drops whose bosses are dead or out of the read, on another level or past the hold's
        seconds taken up again."""
        for unit, (bosses, until, held_on) in list(self.quiet_holds.items()):
            alive = any(m.unit_id in bosses and m.mode not in (0, LYING_DEAD) for m in foes)
            if alive and area == held_on and now < until:
                continue
            del self.quiet_holds[unit]
            if pickup_module.SHUNNED.get(unit) == until:
                del pickup_module.SHUNNED[unit]
            why = (
                'its boss is dead or out of the read'
                if not alive
                else 'the level changed'
                if area != held_on
                else 'the hold ran out'
            )
            LOG.info('Macro: pursuit: the drop %d held by QUIET_HOLD is taken up again: %s', unit, why)

    def omens_now(self, run: Run, area: int, now: float) -> list[Point]:
        """The spots a Herald is coming to on level `area` (HERALD_OMEN), each kept OMEN_SECONDS from its first read."""
        if area != self.omen_area:
            self.omens, self.omen_area = {}, area
            self.omen_marked = set()
        flights = getattr(run, 'flights', None)
        if flights is not None and now - self.omen_looked >= OMEN_LOOK:
            self.omen_looked = now
            try:
                read = flights(frozenset((HERALD_OMEN,)))
            except OSError, ValueError:
                read = ()
            for _, _, x, y in read:
                if not any(math.dist((x, y), spot) < 1.0 for spot in self.omens):
                    self.omens[x, y] = now + OMEN_SECONDS
                    LOG.info('Macro: run: a Herald comes at (%.1f, %.1f) in 5 s: the run waits for it there', x, y)
                    run.say('A Herald is coming')
        self.omens = {spot: until for spot, until in self.omens.items() if until > now}
        herald_pack.saw_omens(self.omens.items())
        return list(self.omens)

    def coming(self, here: Point, now: float) -> tuple[Point, float] | None:
        """The pending omen within OMEN_OPEN_REACH whose pack shows first, and the clock it is expected at (its first
        read and OMEN_SPAWN); None with none."""
        found = [
            (spot, until - OMEN_SECONDS + OMEN_SPAWN)
            for spot, until in self.omens.items()
            if until > now and math.dist(here, spot) <= OMEN_OPEN_REACH
        ]
        return min(found, key=lambda one: one[1]) if found else None

    def omen_focal(self, here: Point, now: float, reachable: Sequence[Monster]) -> Point | None:
        """OMEN_STRIKE: the spot a fight's line goes through instead of its choice's focal, from OMEN_LEAD s before
        the expected spawn until the pack shows (a member of a tier 4-5 pack in reach) or OMEN_GRACE after it."""
        if not OMEN_STRIKE or any(herald_pack.in_pack(m.tier) for m in reachable):
            return None
        found = self.coming(here, now)
        if found is None or not found[1] - OMEN_LEAD <= now <= found[1] + OMEN_GRACE:
            return None
        return found[0]

    def omen_open(self, run: Run, world: World, foes: Sequence[Monster], ground: Ground, key_names) -> bool:
        """The quiet before a Herald's pack (OMEN_STRIKE's text): the build's first due 'opening' row is cast, else
        with OMEN_STRIKE in the last OMEN_LEAD s the strike is held on the spot (`omen_strike`). Whether it acted."""
        player = world.player
        if player is None:
            return False
        now = run.clock()
        if OMEN_READ_ALONE and not self.running:
            self.omens_now(run, player.area, now)  # a level run's agenda reads them (hunting/choice.py)
        here = (player.x, player.y)
        found = self.coming(here, now)
        if found is None:
            return False
        rect = run.actuator.keys.focused_window_rect()
        if rect is None:
            return False
        aspect = rect[2] / rect[3]
        facts = self.buffs.facts(run, world, foes)
        due = self.buffs.first(run, 'opening', facts)
        if due is not None:
            if due.row.caster is not None:
                self.step_aside()
            try:
                self.buffs.cast(run, due, key_names, aspect)
            except Abort as stop:
                if run.stops(stop):
                    raise
                LOG.info('Macro: no %s (%s)', skill_name(due.row.skill), stop)
                self.buffs.remember(due.row, now)
            return True
        spot, spawn = found
        if not OMEN_STRIKE or not spawn - OMEN_LEAD <= now <= spawn + OMEN_GRACE:
            return False
        return self.omen_strike(run, ground, aspect, key_names, spot, spawn)

    def omen_strike(self, run: Run, ground: Ground, aspect: float, key_names, spot: Point, spawn: float) -> bool:
        """The strike held on the line to a Herald's coming at `spot` until its pack is in reach, the player or the
        safety moves, or OMEN_GRACE past `spawn` (OMEN_STRIKE). Whether it was held."""
        if run.pad is not None:
            return False  # controller mode: the client strikes its own target, and there is none yet
        attack = self.attack
        try:
            held, how = strike_input(run, run.world(), key_names, attack.skill)
        except Abort as stop:
            if run.stops(stop):
                raise
            return False
        view = Viewport(aspect)
        began, ended = run.clock(), 'the pack did not show'
        with ExitStack() as stack:
            pressed = False
            while True:
                now = run.clock()
                world = run.world()
                player = world.player
                if player is None:
                    raise Abort('not in a game')
                if player.mode in DEAD:
                    raise Dead('the character is dead')
                self.sense(run)
                why = 'a move was asked for' if self.move is not None else self.moving(run, world, keys=not pressed)
                if why is not None:
                    ended = why
                    break
                here = (player.x, player.y)
                foes = self.foes(world, now)
                if any(in_reach(ground, here, (m.x, m.y), attack.reach, world.doors) for m in foes):
                    ended = 'the pack shows'
                    # Its mark under the strike held on, before the hold lets go (OMEN_MARK_FIRST)
                    self.omen_mark(run, world, foes, key_names)
                    break
                if now > spawn + OMEN_GRACE:
                    break
                if not pressed:
                    where = view.aim(here, spot)
                    if where is None:
                        ended = 'no point of its line on the screen'
                        break
                    run.actuator.aim(*where, scatter=(3, 3))
                    LOG.info(
                        'Macro: omen: %s (%s) held on the line to the Herald coming at (%.1f, %.1f), %.1f away, '
                        '%.2f s before its pack is due',
                        skill_name(attack.skill), how, *spot, math.dist(here, spot), spawn - now,
                    )  # fmt: skip
                    stack.enter_context(run.actuator.hold(*held))
                    pressed = True
                self.casting = True
                if self.nap(run, FRAME):
                    ended = 'a move was asked for'
                    break
        LOG.info('Macro: omen: the strike let go after %.2f s: %s', run.clock() - began, ended)
        return pressed

    def omen_shown(self, now: float, foes: Sequence[Monster]) -> tuple[Point, float, list[Monster]] | None:
        """OMEN_MARK_FIRST: a pending omen not yet marked whose pack shows now (its tier 4-5 members within
        OMEN_OPEN_REACH of its spot, OMEN_EARLY before its expected spawn to OMEN_MARK_WINDOW after it): its spot, the
        expected spawn and the members; None with none."""
        for spot, until in sorted(self.omens.items(), key=lambda one: one[1]):
            spawn = until - OMEN_SECONDS + OMEN_SPAWN
            if spot in self.omen_marked or not spawn - OMEN_EARLY <= now <= spawn + OMEN_MARK_WINDOW:
                continue
            members = [
                m for m in foes if herald_pack.in_pack(m.tier) and math.dist(spot, (m.x, m.y)) <= OMEN_OPEN_REACH
            ]
            if members:
                return spot, spawn, members
        return None

    def omen_due(self, now: float) -> bool:
        """OMEN_MARK_FIRST: whether an omen not yet marked has its pack due now (OMEN_EARLY before its expected spawn
        to OMEN_MARK_WINDOW after it)."""
        if not OMEN_MARK_FIRST:
            return False
        for spot, until in self.omens.items():
            spawn = until - OMEN_SECONDS + OMEN_SPAWN
            if spot not in self.omen_marked and spawn - OMEN_EARLY <= now <= spawn + OMEN_MARK_WINDOW:
                return True
        return False

    def omen_waits(self, why: str) -> None:
        """Said once a reason while an omen's mark waits (OMEN_MARK_FIRST)."""
        if why != self.omen_waited:
            self.omen_waited = why
            LOG.info("Macro: omen: the pack's mark waits: %s", why)

    def omen_mark(self, run: Run, world: World, foes: Sequence[Monster], key_names) -> bool:
        """OMEN_MARK_FIRST: a Herald's pack just shown (`omen_shown`) gets the build's first due FIRST row (Death Mark)
        before anything else, once an omen, on the member drawn nearest the pointer (the pack's order takes any: the
        player, 2026-10-21 Q1), with the quick aim (macros/buffs.py `quick_aim`: the strike held on, no hover wait when
        the pointer is on the pack). Not under the fight casts' hold (FIGHT_CAST_REACH) or past a real threat the
        safety saw (`Safety.hold_exempt`) other than OMEN_MARK_PAST's: then the next look asks again. Whether a key or
        the pointer was touched."""
        player = world.player
        if not OMEN_MARK_FIRST or player is None or player.mode in DEAD or run.pad is not None:
            return False
        now = run.clock()
        found = self.omen_shown(now, foes)
        if found is None:
            return False
        spot, spawn, members = found
        rect = run.actuator.keys.focused_window_rect()
        if rect is None or not rect[3]:
            return False
        aspect, here = rect[2] / rect[3], (player.x, player.y)
        view = Viewport(aspect)
        # Drawn where the mark may be aimed (macros/buffs.py `aimable`: MARK_SHAPE's outline, else AIM_LIMITS)
        drawn = [
            m
            for m in members
            if any(self.buffs.aimable(skill, view.body(here, m.x, m.y)) for skill in herald_pack.FIRST)
        ]
        if not drawn:
            return False
        threat = getattr(self.safety, 'hold_exempt', None)
        if threat is not None and not threat.startswith(OMEN_MARK_PAST):
            self.omen_waits(f'a real threat: {threat}')
            return False
        pointer = run.actuator.keys.pointer()
        at = (
            ((pointer[0] - rect[0]) / rect[2], (pointer[1] - rect[1]) / rect[3])
            if pointer is not None
            else view.body(here, *spot)
        )
        prey = min(drawn, key=lambda m: math.dist(at, view.body(here, m.x, m.y)))
        asked = self.fight_facts(run, world, foes, drawn, prey)
        if FIGHT_CAST_REACH and asked.cast_barred is not None:
            self.omen_waits(f'the fight casts are held: {asked.cast_barred}')
            return False
        self.omen_marked.add(spot)
        for row in self.buffs.rows('fight'):
            if row.skill not in herald_pack.FIRST or row.before_strike is None or not row.before_strike(asked):
                continue
            due = self.buffs.due(run, row, asked)
            if due is None:
                continue
            if due.target is not None and herald_pack.in_pack(due.target.tier):
                due = replace(due, target=prey)  # the pack's order: the member under the pointer, no pointer move
            with self.buffs.quick_aim():
                tried = self.buffs.cast(run, due, key_names, aspect)
            if tried.cast:
                LOG.info(
                    "Macro: mark: first at the Herald's pack, %.2fs after its spawn was due (OMEN_MARK_FIRST)",
                    run.clock() - spawn,
                )
            return tried.touched
        LOG.info('Macro: omen: the pack shows, no mark due on it (OMEN_MARK_FIRST)')
        return False

    def nearing_only(self, world: World, foes: Sequence[Monster], ground: Ground, here: Point, now: float) -> bool:
        """Whether everything in reach is a boss being neared (`untouched`) beyond the engage ring: the move first."""
        self.nearing = {unit: until for unit, until in self.nearing.items() if until > now}
        if not self.nearing:
            return False
        reachable = [m for m in foes if in_reach_of(ground, here, (m.x, m.y), self.reach, world.doors)]
        engage = self.attack.engage
        return bool(reachable) and all(
            m.unit_id in self.nearing and math.dist(here, (m.x, m.y)) > engage for m in reachable
        )

    def quiet(self, world: World, foes: Sequence[Monster]) -> bool:
        """Whether no hostile is within QUIET_UNITS of the character: the whole upkeep goes between a run's moves."""
        player = world.player
        if player is None:
            return False
        return all(math.dist((player.x, player.y), (m.x, m.y)) > QUIET_UNITS for m in foes)

    def field_quiet(self, run: Run, world: World) -> bool:
        """Whether the field routine may open the inventory now (loot/api.py `at_once`): not the first look of a level
        nor within AT_ONCE_SETTLE of the level's arrival (a waypoint, a portal, stairs), not within AT_ONCE_HURT of the
        character's life going down, and no hostile within AT_ONCE_CLEAR (every hostile read, the untouchable too).
        At 15:21:38 on 2026-10-20 it opened the inventory 1 s after a waypoint's arrival, hostiles near, and a fight
        back cancelled it half way (game 6 of 20261020T115501Z-4b07df55)."""
        player = world.player
        now = run.clock()
        if player is None or player.in_town:
            return False
        if player.area != self.field_area:
            self.field_area, self.field_entered = player.area, now  # the level's first look
            return False
        if now - self.field_entered < AT_ONCE_SETTLE or now - self.hurt_at < AT_ONCE_HURT:
            return False
        return all(math.dist((m.x, m.y), (player.x, player.y)) > AT_ONCE_CLEAR for m in hostiles(world))

    def foes(self, world: World, now: float) -> list[Monster]:
        """The hostiles the hunt goes for: `hostiles` without the ones left alone as untouchable."""
        self.untouchable = {unit: until for unit, until in self.untouchable.items() if until > now}
        return [m for m in hostiles(world) if m.unit_id not in self.untouchable]

    def untouched(self, run: Run, prey: Monster, casts: int) -> bool:
        """Count `casts` new casts with the line through `prey`; whether it is to be left alone now: its
        life reads and has not gone down in UNTOUCHED_CASTS of them."""
        if not prey.max_life:
            return False
        seen, life_then = self.tested.get(prey.unit_id, (0, prey.life))
        if prey.life < life_then:
            seen, life_then = 0, prey.life
            self.nearing.pop(prey.unit_id, None)  # struck from here: near enough
        seen += casts
        self.tested[prey.unit_id] = (seen, life_then)
        if seen < UNTOUCHED_CASTS:
            return False
        del self.tested[prey.unit_id]
        if self.boss(prey):
            # A boss is never left alone (the player, 2026-10-14; rca/2026-10-14/baal-sim.md): the run gets back
            # within the engage ring for NEARING_SECONDS instead (`goal`, `judge`).
            self.nearing[prey.unit_id] = run.clock() + NEARING_SECONDS
            LOG.info(
                'Macro: %s takes no damage (%s after %d casts through it): a boss is not left alone; getting back in '
                'reach, within %.0f of him',
                label(prey), life(prey), seen, self.attack.engage,
            )  # fmt: skip
            run.say(f'{label(prey)} takes no damage: getting nearer')
            return True
        self.untouchable[prey.unit_id] = run.clock() + UNTOUCHABLE_SECONDS
        LOG.info(
            'Macro: %s takes no damage (%s after %d casts through it): left alone for %.0fs',
            label(prey), life(prey), seen, UNTOUCHABLE_SECONDS,
        )  # fmt: skip
        run.say(f'{label(prey)} takes no damage: left alone')
        return True

    def unharmed(self, run: Run, prey: Monster, since: float, *, striking: bool) -> bool:
        """Whether `prey`, the line's monster, is left alone now as one that takes no damage: the strike is held and
        nothing in reach has lost life since `since` for NO_HARM_SECONDS. Never a boss (`boss`: an act boss, a
        Herald, a dear class, the pursued fight's boss) nor a monster whose life cannot be read."""
        if NO_HARM_SECONDS is None or not striking or not prey.max_life or self.boss(prey):
            return False
        quiet = run.clock() - since
        if quiet < NO_HARM_SECONDS:
            return False
        self.tested.pop(prey.unit_id, None)
        self.untouchable[prey.unit_id] = run.clock() + UNTOUCHABLE_SECONDS
        LOG.info(
            'Macro: %s takes no damage (%s; nothing in reach lost life in %.1fs of strikes): left alone for %.0fs',
            label(prey), life(prey), quiet, UNTOUCHABLE_SECONDS,
        )  # fmt: skip
        run.say(f'{label(prey)} takes no damage: left alone')
        return True

    @property
    def pursuing(self) -> bool:
        """Whether the build played has the pursuit loop on (`BuildSettings.pursuit`)."""
        return self.build.settings.pursuit

    def pressed(self, now: float) -> bool:
        """Whether a press of the key is in the mailbox and still asks for a move."""
        return self.pursuit is not None and self.pursuit.fresh(now)

    def advancing(self, now: float) -> bool:
        """Whether a fresh press asks for its goal now, before what is in reach (the teleport key's)."""
        return self.pursuit is not None and self.pursuit.advance and self.pursuit.fresh(now)

    @property
    def running(self) -> bool:
        """Whether a level run works now (the pickup key's leash: macros/pursuit.py), not paused by the hand."""
        return self.pursuit is not None and self.pursuit.runs

    @property
    def rushing(self) -> bool:
        """Whether the working level run is the KP_6 loop's (`Pursuit.rush`): no look for a better place in its
        fights (rca/2026-10-16/loop-chests-findings.md §1)."""
        return self.running and self.pursuit is not None and self.pursuit.rush

    @property
    def leashed(self) -> bool:
        """Whether a level run is held, working or paused by the player's hand."""
        return self.pursuit is not None and self.pursuit.leashed

    def post(self, pursuit: Pursuit) -> None:
        """A press posted by the runner. One that sets no leash keeps the run's (the teleport key asks for its
        goal now, the run goes on after); one that sets a leash on the same level keeps where it runs."""
        with self.mailbox:
            old = self.pursuit
            if pursuit.leashed and (old is None or not old.leashed):
                self.travel.tally = Tally()  # the run's pace counts from its own first leg (`Travel.paced`)
            if old is not None and old.leashed and not pursuit.looped:
                # The run's crossing noted (`heading`) and its carrying on (`carried`) stay with it
                kept = {
                    'area': old.area,
                    'onward': old.onward,
                    'entered': old.entered,
                    'rush': old.rush,
                    'agenda': old.agenda,
                }
                if not pursuit.leashed:
                    pursuit = replace(pursuit, leash=old.leash, paused=old.paused, **kept)
                elif pursuit.area is None:
                    pursuit = replace(pursuit, **kept)  # a fresh pickup press: the run goes on, unpaused
            waited = self.pursued
            if waited is not None and waited.do == WAIT and waited.unit is not None:
                # A press while the run stands by a valuable with no room for it: the player goes on without it
                if len(self.waived) > 200:
                    self.waived.clear()
                self.waived.add(waited.unit)
            if pursuit.leashed and not pursuit.advance and not pursuit.looped:
                self.taps = tapped(self.taps, pursuit.pressed_at)  # a double press switches the run mode (`run_mode`)
            self.pursuit = pursuit

    def swap(self, seen: Pursuit | None, new: Pursuit | None) -> bool:
        """The loop's write to the mailbox, made only while it still holds `seen`, what the loop read (by
        identity: every post is a new record); whether it was made. A press posted since stays as posted."""
        with self.mailbox:
            if self.pursuit is not seen:
                return False
            self.pursuit = new
            return True

    def end_run(self, run: Run | None, reason: str, seen: Pursuit | bool | None = True) -> None:
        """The level run is over (pursuit.py `Ended`): the leash goes back to none, said once; a fresh teleport
        press stays. `seen`: the mailbox as the ending look read it; a press posted since keeps the run (True:
        whatever the mailbox holds now)."""
        with self.mailbox:
            posted = self.pursuit if seen is True else seen
            if not isinstance(posted, Pursuit) or not posted.leashed:
                return
            if self.pursuit is not posted:
                LOG.info('Macro: pursuit: the level run goes on (%s): a press came during the look', reason)
                return
            ended = replace(posted, leash=NONE, area=None, paused=False, onward=None, entered=None)
            self.pursuit = ended if posted.advance else None
            self.ended_area = posted.area  # the level the run was of (runner.py `_run_over`: the agenda's area worked)
        LOG.info('Macro: pursuit: the level run ends: %s', reason)
        self.travel.paced(run.clock() if run is not None else None, reason)
        self.told.new(None)
        self.mode_said = None  # the next run says its mode again
        if run is not None:
            run.say(f'Level run over: {reason}')
            if self.run_over is not None:
                # Not for the runner's own ends (run None), made under its lock
                self.run_over(reason)

    def left_for_town(self, run: Run, world: World) -> bool:
        """A level run of a field level whose character stands in a town ends at once (pursuit.py LEVEL_LEFT); whether
        it did. A run asked in a town (KP_1 there) waits as before. At 17:14:53 on 2026-10-20 the Outer Steppes run's
        passage walk went back into the Pandemonium Fortress; attack mode waited there ("the character is on the move")
        until the loop's 45 s still watchdog left the game (rca/2026-10-20/fortress-gate-passage-findings.md)."""
        player, posted = world.player, self.pursuit
        if player is None or not player.in_town or posted is None or not posted.leashed:
            return False
        if posted.area is None or posted.area in TOWN_IDS:
            return False
        LOG.info(
            "Macro: run: in %s, off the run's level %s: the level run ends at once",
            display_name(player.area), display_name(posted.area),
        )  # fmt: skip
        self.end_run(run, LEVEL_LEFT, posted)
        return True

    def pause_run(self, run: Run, why: str) -> None:
        """The player's hand has the level run: paused, said once; it resumes once the hand rests (`hand`)."""
        posted = self.pursuit
        if posted is None or not posted.runs or not self.swap(posted, replace(posted, paused=True)):
            return
        LOG.info('Macro: pursuit: the level run is paused: %s', why)
        self.told.new(None)
        run.say(f"Level run paused: the player's hand ({why}); it goes on once the hand rests {SETTLE:g} s")

    def hand(self, run: Run, world: World) -> None:
        """One look at the player's hand: a panel open or the pointer moved by it (not where the loop put it) is
        the hand at work, as a click is; a panel pauses a working run (I7). A paused run resumes after SETTLE
        seconds of rest with no panel open."""
        now = run.clock()
        actuator = run.actuator
        pointer = actuator.keys.pointer()

        def apart(one: tuple[int, int] | None, other: tuple[int, int] | None) -> bool:
            # further apart than the steady guard allows (POINTER_DRIFT): a hand's tremor is no move
            if one is None:
                return False
            return other is None or max(abs(one[0] - other[0]), abs(one[1] - other[1])) > POINTER_DRIFT

        if world.open_panels:
            self.hand_at = now
            self.pause_run(run, f'{", ".join(world.open_panels)} open')
        elif self.pointer_seen is not None and apart(pointer, self.pointer_seen) and apart(pointer, actuator.left_at):
            self.hand_at = now
        elif actuator.button_held(3) or actuator.key_held():
            self.hand_at = now  # the player's own strike or key: the hand is at work
        self.pointer_seen = pointer
        posted = self.pursuit
        if posted is None or not posted.leashed or not posted.paused:
            return
        if (
            settled(self.hand_at, now, bool(world.open_panels))
            and not run.actuator.button_held(1)
            and self.swap(posted, replace(posted, paused=False))
        ):
            LOG.info('Macro: pursuit: the level run resumes: the hand has rested %.1f s', now - self.hand_at)
            self.told.new(None)
            run.say('Level run resumed')

    def attack_mode(self, run: Run, key_names) -> None:
        """Fight whatever comes into reach until cancelled. Every pause looks at the left button every SLICE
        (`Pace.watched`), so no click of the player's goes unseen."""
        with run.pace.watched(lambda: self.sense(run), SLICE, run.clock):
            self._attack_mode(run, key_names)

    def _attack_mode(self, run: Run, key_names) -> None:
        if PREAIM:
            run.flight = lambda landing: self.preaim(run, landing)  # teleport.py PREAIM_FLIGHT
        try:
            self._attack_looks(run, key_names)
        finally:
            run.flight = None

    def preaim(self, run: Run, landing: Point) -> None:
        """During a Teleport's flight onto `landing` (world units): the pointer onto the strike's aim from there, when
        something is in reach of it (PREAIM). The attack's held leader is left as it was; a stop the run does not honour
        leaves the pointer where it is."""
        self.preaimed = None
        if PREAIM_NOT_REBUFF and self.rebuff_flying(run.clock()):
            return  # Battle Orders at the landing, not the strike
        try:
            world = run.world()
            player, rect = world.player, run.actuator.keys.focused_window_rect()
            if player is None or rect is None or player.mode in DEAD or player.in_town:
                return
            attack = self.attack
            level = self.known_level(player)
            ground = Ground(level.ground if level is not None else ())
            there = replace(world, player=replace(player, x=landing[0], y=landing[1]))
            foes = self.foes(there, run.clock())
            reachable = [m for m in foes if in_reach(ground, landing, (m.x, m.y), attack.reach, world.doors)]
            if not reachable:
                return
            view = Viewport(rect[2] / rect[3])
            held = getattr(attack, 'held', None)
            unit = getattr(held, 'unit', None)
            try:
                found = self.choose(there, foes, reachable, ground, view)
            finally:
                if held is not None:
                    held.unit = unit  # the fight's own choice holds a leader, not this guess
            where = view.aim(landing, found.focal)
            if where is None:
                return
            run.actuator.aim(*where, scatter=(3, 3))
            self.preaimed = (run.clock(), landing, found.focal)
            LOG.info(
                'Macro: strike aimed during the flight: from the landing (%.1f, %.1f) at (%.1f, %.1f), %d in reach',
                *landing, *found.focal, len(reachable),
            )  # fmt: skip
        except Abort as stop:
            if run.stops(stop):
                raise

    def rebuff_flying(self, now: float) -> bool:
        """Whether a rebuff retreat the safety chose (`Safety.rebuff_chosen`) has not landed yet (PREAIM_NOT_REBUFF)."""
        safety = self.safety
        chosen = safety.rebuffed_at
        return safety.rebuff_landed < chosen <= now <= chosen + safety_module.REBUFF_LANDS

    def preaim_kept(self, run: Run, here: Point, focal: Point, view: Viewport) -> bool:
        """Whether the pointer the flight put (`preaim`) stands for the aim at `focal` from `here`: within PREAIM_PIXELS
        of it, the pre-aim PREAIM_SECONDS old at most, its focal within REAIM_UNITS. Used once: dropped either way."""
        pre, self.preaimed = self.preaimed, None
        if pre is None or run.clock() - pre[0] > PREAIM_SECONDS or math.dist(pre[2], focal) > REAIM_UNITS:
            return False
        where, rect = view.aim(here, focal), run.actuator.keys.focused_window_rect()
        pointer = run.actuator.keys.pointer()
        if where is None or rect is None or pointer is None or pointer != run.actuator.left_at:
            return False
        goal = (rect[0] + rect[2] * where[0], rect[1] + rect[3] * where[1])
        off = math.dist(goal, pointer)
        if off > PREAIM_PIXELS:
            return False
        LOG.info(
            'Macro: strike: the aim made during the flight is kept, %.0f px off, landed %.1f from (%.1f, %.1f)',
            off, math.dist(here, pre[1]), *pre[1],
        )  # fmt: skip
        return True

    def _attack_looks(self, run: Run, key_names) -> None:
        misses, logged_at, waited_at = 0, -math.inf, run.clock()
        self.after_fight.clear()  # a wait left over from a run that ended another way
        self.step_asked.clear()
        self.stepping = None  # a step the last run of the mode was stopped before taking
        entered = run.clock()  # the mode starts anew after every teleport and seek step
        unready_since: float | None = None  # since when Echoing Strike has been on no input (see below)
        run.say('Attack mode on')
        while True:
            world = run.world()  # Cancelled when the runner ends the mode
            self.score.note(run.clock(), world.player, hostiles(world), world.dead)
            if not world.in_game:
                # The lobby or the menu: the mode ends, so the macro request there starts the macro at once.
                raise Abort('attack mode off: the game was left')
            if world.open_panels and tidy(run, world):
                continue  # the loop's own panels a cancelled routine left open: closed, not the player's hand
            player = world.player
            self.stands = None if player is None else (player.x, player.y)
            # Only once the character is seen: the runner names the build by that look (`use`).
            attack = None if player is None else self.attack  # Abort: the build does not fight
            self.casting = player is not None and player.mode in ACTING
            self.sense(run)
            if player is not None:
                self.area = None if player.in_town else player.area  # the level whose potions are kept (`sense`)
                if player.in_town:
                    self.mode = None  # no run mode in town (the HUD's word for it: runner.py `run_badge`)
                if self.pursuing:
                    self.hand(run, world)  # a level run's pause and resume (pursuit off: no run, no look at the hand)
            if self.move is not None and player is not None:
                self.serve_move(run, world)  # the player's move first: no strike while it is pending
                self.nap(run, FRAME)
                continue
            if self.left_for_town(run, world):
                continue  # the run is over: the loop's next leg (the town exit again) or the player's mode as before
            why = None if player is None else self.moving(run, world)
            if player is None or world.open_panels or player.in_town or why:
                if why and run.clock() - waited_at >= WAIT_LOG_SECONDS:
                    waited_at = run.clock()
                    assert player is not None
                    LOG.info('Macro: waiting (%s), at (%.1f, %.1f), mode %d', why, player.x, player.y, player.mode)
                if player is not None and self.pursuing and self.pressed(run.clock()):
                    # The player's own move wins over the key's; a panel or the town is the route's own step's
                    if why:
                        self.tell(run, f'the key waits: {why}', aloud=False)
                    else:
                        self.defer(run, None, 'the town or an open panel')
                self.step_aside()
                self.nap(run, POLL)  # the player's move (a key, the left button, a run): waited through
                continue
            assert attack is not None  # the character is seen
            foes = self.foes(world, run.clock())
            self.keep_orders(run, world, foes)
            if OMEN_MARK_FIRST and self.omen_mark(run, world, foes, key_names):
                continue  # a Herald's pack just shown: its mark before anything else (OMEN_MARK_FIRST)
            if self.leashed and player.mode in DEAD:
                self.end_run(run, 'the character died')
            elif self.running and (not self.sweep.steps or run.clock() > self.sweep.until):
                # A level run keeps the sweep's look for a better place in its fights (combat/stance.py `camp`).
                self.sweep.start(run.clock())
            between = self.running and not self.advancing(run.clock())
            if between and self.field_quiet(run, world) and self.field_now(run):
                continue  # a big item identified at once: dropped at the feet or into the cube (loot/api.py)
            if between and self.upkeep(run, world, foes, key_names, renewing=not self.quiet(world, foes)):
                # Between the run's moves: in the quiet the whole upkeep (run-1932-findings.md issue 3), else only a
                # buff that would end inside the coming boss fight (buffs.py `lapsing`)
                continue
            if self.pursuing:
                # The key first, before a buff is kept up or a strike begun: its move goes out at once
                found = self.known_level(player)
                over = Ground(found.ground if found is not None else ())
                at = (player.x, player.y)
                near = any(in_reach(over, at, (m.x, m.y), attack.reach, world.doors) for m in foes)
                if self.pursue(run, world, foes, over, key_names, in_reach=near):
                    entered = run.clock()  # as after a teleport step: the main weapons wait MAIN_AFTER
                    self.unmoved_since = None
                    continue
                if near and self.rushing and run.clock() - self.hurt_at > HURT_SECONDS:
                    # The KP_6 loop's run: a look with no move is no strike's unless the character was just hurt or
                    # nothing moved for RUSH_UNMOVED (rca/2026-10-17/movement-findings.md §2)
                    if self.unmoved_since is None:
                        self.unmoved_since = run.clock()
                    if run.clock() - self.unmoved_since < RUSH_UNMOVED:
                        self.nap(run, FRAME)
                        continue
            if (LANDING_MARK or herald_pack.DM_AFTER_EVERY_MOVE) and self.landing_mark(run, world, foes, key_names):
                continue  # the mark first at a T5 Herald landing, the pack beyond the strike's reach
            if self.upkeep(run, world, foes, key_names):
                continue
            level = self.known_level(player)
            ground = Ground(level.ground if level is not None else ())
            here = (player.x, player.y)
            if not any(in_reach(ground, here, (m.x, m.y), attack.reach, world.doors) for m in foes):
                self.step_aside()
                if not self.running:  # a level run takes its drops as goals of its own (`side_drop`)
                    self.gather(run, here, foes)
                if self.pursuing and self.pursue(run, world, foes, ground, key_names, in_reach=False):
                    entered = run.clock()
                    continue
                if self.omen_open(run, world, foes, ground, key_names):
                    continue  # a Herald's pack coming: its opening (OMEN_STRIKE, the build's 'opening' rows)
                running = self.running  # a level run's moves are its own: not the sweep's toward the nearest
                if self.sweep.steps and foes and not running and self.follow_on(run, world, foes, ground, key_names):
                    continue
                if foes and run.clock() - logged_at >= IDLE_LOG_SECONDS:
                    logged_at = run.clock()
                    nearest = min(foes, key=lambda m: math.dist(here, (m.x, m.y)))
                    LOG.info(
                        'Macro: idle: %d hostiles, none in reach; nearest %s %.0f away, shot %s, from (%.0f, %.0f)',
                        len(foes), label(nearest), math.dist(here, (nearest.x, nearest.y)),
                        'clear' if clear_shot(ground, here, (nearest.x, nearest.y), world.doors) else 'blocked', *here,
                    )  # fmt: skip
                # A Herald's pack due: a look a frame, its first frame seen at once (OMEN_MARK_FIRST)
                self.nap(run, FRAME if self.omen_due(run.clock()) else POLL, key=self.pursuing)
                continue
            rect = run.actuator.keys.focused_window_rect()
            if rect is None:
                self.nap(run, POLL)
                continue
            try:
                strike_input(run, world, key_names, attack.skill)
                unready_since = None
            except Abort as stop:
                if run.cancelled.is_set():
                    # The runner's own cancel raced the check: "Attack mode off", not a false stop on "... is on no
                    # skill key" (rca/2026-10-20/crossing-teleport-back-findings.md F2)
                    raise Cancelled from stop
                if run.stops(stop):
                    raise
                # Right after a hop or a mark the right button holds that skill for a moment: wait. Only an input
                # that stays away is a stopped fight, unless `strike_back` puts it back.
                unready_since = run.clock() if unready_since is None else unready_since
                tail = self.cast_tail(run, world, key_names, attack.skill) if CAST_TAIL else None
                if tail is not None and CAST_TAIL_AGAIN:
                    unready_since = None
                    continue  # the cast's end seen: the loop's look (the pursuit's too) at once, with no FRAME nap
                if tail is not None:
                    # The cast's end seen with the strike back (CAST_TAIL): the fight from that look, not the next loop
                    world, player = tail
                    foes = self.foes(world, run.clock())
                    here = (player.x, player.y)
                    unready_since = None
                elif run.clock() - unready_since < INPUT_SECONDS:
                    self.nap(run, FRAME)
                    continue
                elif self.strike_back(run, world, attack.skill):
                    unready_since = None
                    continue
            try:
                # The main weapons for a tough pack, only MAIN_AFTER after the last step: a swap per hop of a
                # seek chain costs more than it gains. A fight begun earlier stops for the swap then.
                reachable = [m for m in foes if in_reach(ground, here, (m.x, m.y), attack.reach, world.doors)]
                boss = any(m.txt_id in BOSSES for m in reachable)  # the chain of hops ended at it
                tough = self.pursuing or boss or self.tough(world, reachable)
                settled = self.pursuing or boss or run.clock() - entered >= MAIN_AFTER
                held = self.main_weapons(run, world, key_names, swap=settled and tough)
                if self.pursuing and not held:
                    self.tell(run, 'waiting for the priced battle weapons')
                    self.nap(run, POLL)
                    continue
                pause = entered + MAIN_AFTER if tough and not held and not self.pursuing else None
                self.fight(run, ground, rect[2] / rect[3], key_names, until=pause)
                misses = 0
                self.take_guard(run, rect[2] / rect[3], key_names, ground)  # the safety step it stopped for
                self.take_step(run, rect[2] / rect[3], key_names, ground)  # the step the fight stopped for, if any
            except Cancelled:
                raise  # the mode's own pause for a valuable (`asked_step`), or the runner's cancel
            except Abort as stop:
                if run.cancelled.is_set():
                    raise Cancelled from stop  # the runner's cancel raced the fight's own check (F2)
                if run.stops(stop):
                    raise
                misses += 1
                LOG.info('Macro: the fight stopped (%s), %d in a row', stop, misses)
                if misses >= MISSES_IN_A_ROW:
                    raise Abort(f'attack mode off: {misses} fights stopped in a row, the last on "{stop}"') from stop
                self.nap(run, POLL)

    def burning(self, world: World, foes: Sequence[Monster]) -> bool:
        """Whether the fight is a mana-burn one for combat/pack.py HERALD_MARK_NO_BURN, by the safety's own tests
        (combat/threats/drain_escape.py `drains` and `drainers_near`, read only, on the read's Monsters): a draining
        hostile (Mana Burn, or with MANA_ESCAPE its type's own) within PACK_SEEN of the character, or the safety's burn
        leave standing (`Safety.burn_leaving`)."""
        from inventory_tracking.combat.threats import drain_escape, manaburn  # late: they build on combat/pack.py

        if self.safety.burn_leaving is not None:
            return True
        player = world.player
        if player is None:
            return False
        here = (player.x, player.y)
        return any(
            (manaburn.drains(m.modifiers) or (drain_escape.MANA_ESCAPE and drain_escape.threat(m.txt_id)))
            and math.dist(here, (m.x, m.y)) <= herald_pack.PACK_SEEN
            for m in foes
        )

    def first_facts(
        self,
        run: Run,
        world: World,
        foes: Sequence[Monster],
        reachable: Sequence[Monster],
        prey: Monster,
        aspect: float,
    ) -> BuffFacts:
        """The facts HERALD_MARK_FIRST's look asks the FIRST rows with: SETTLE_BEFORE_FIRST, their last casts settled
        first (`Buffs.settle`); HERALD_MARK_SHOWN, only the hostiles in reach drawn inside the aim's limits."""
        player = world.player
        if HERALD_MARK_SHOWN and player is not None:
            view, here = Viewport(aspect), (player.x, player.y)
            reachable = [m for m in reachable if view.on_screen(view.body(here, m.x, m.y))]
        asked = self.fight_facts(run, world, foes, reachable, prey)
        if not SETTLE_BEFORE_FIRST:
            return asked
        rows = [row for row in self.buffs.rows('fight') if row.skill in herald_pack.FIRST and row.shows is not None]
        for row in rows:
            self.buffs.settle(run, row, replace(asked, now=run.clock()))
        return self.fight_facts(run, world, foes, reachable, prey) if rows else asked

    def landing_members(self, run: Run, world: World, foes: Sequence[Monster]) -> list[Monster]:
        """The tier HERALD_MARK_TIER Herald pack's members drawn on the screen (game/view.py `on_screen`, the window's
        aspect) at a jump's landing where combat/pack.py `herald_mark_first` holds for them (LANDING_MARK); with
        combat/pack.py DM_AFTER_EVERY_MOVE in a hard fight (`hard_fight`), every hostile drawn there; none otherwise."""
        player = world.player
        if player is None or herald_pack.since_hop(run.clock()) > herald_pack.LANDING_AHEAD:
            return []
        rect = run.actuator.keys.focused_window_rect()
        view = Viewport(rect[2] / rect[3]) if rect is not None and rect[3] else Viewport()
        here = (player.x, player.y)
        if (
            herald_pack.DM_AFTER_EVERY_MOVE
            and herald_pack.hard_fight(here, foes) is not None
            and not (herald_pack.DM_MOVE_NO_BURN and herald_pack.burning(here, foes))
        ):
            # A hard fight's mark after every move (R1): any hostile drawn on the screen is in the mark's reach. Not
            # with a drainer near (DM_MOVE_NO_BURN), as the mark rules' R1 (mark.py `move_reason`): the landing's mark
            # among the Dark Shapes killed manaburn_death.py seeds 1 and 3 (2026-10-24 ~23:10)
            return [m for m in foes if view.on_screen(view.body(here, m.x, m.y))]
        if not LANDING_MARK:
            return []
        shown = [
            m for m in foes if m.tier >= herald_pack.HERALD_MARK_TIER and view.on_screen(view.body(here, m.x, m.y))
        ]
        burning = herald_pack.HERALD_MARK_NO_BURN and self.burning(world, foes)
        return shown if herald_pack.herald_mark_first(run.clock(), shown, foes, burning) else []

    def landing_mark(self, run: Run, world: World, foes: Sequence[Monster], key_names) -> bool:
        """LANDING_MARK: at a T5 Herald landing (`landing_members`), once a jump, the build's FIRST rows (combat/pack.py
        FIRST: Death Mark) asked with the members on the screen as those in reach, the first due one cast; whether a
        key or the pointer was touched. Not under the fight casts' hold (FIGHT_CAST_REACH)."""
        if herald_pack.HOP.at <= self.landing_marked:
            return False
        shown = self.landing_members(run, world, foes)
        if not shown or world.player is None:
            return False
        self.landing_marked = herald_pack.HOP.at
        said = (
            'a hard fight (DM_AFTER_EVERY_MOVE)'
            if herald_pack.DM_AFTER_EVERY_MOVE
            else 'the pack beyond the strike (LANDING_MARK)'
        )
        if not herald_pack.DM_AFTER_EVERY_MOVE:
            return self.first_rows(run, world, foes, shown, key_names, f'at the landing, %.2fs after it, {said}')
        with herald_pack.landing_ask():  # R1's own reasons alone, with every hostile on the screen in reach
            return self.first_rows(run, world, foes, shown, key_names, f'at the landing, %.2fs after it, {said}')

    def first_rows(
        self, run: Run, world: World, foes: Sequence[Monster], shown: Sequence[Monster], key_names, said: str
    ) -> bool:
        """The build's FIRST rows asked with `shown` as those in reach, the first due one cast before anything else
        (`said`: the log line's tail, its %.2f the seconds since the last landing); whether a key or the pointer was
        touched. Not under the fight casts' hold (FIGHT_CAST_REACH)."""
        player = world.player
        rect = run.actuator.keys.focused_window_rect()
        if not shown or player is None or rect is None or not rect[3]:
            return False
        here = (player.x, player.y)
        prey = min(shown, key=lambda m: math.dist(here, (m.x, m.y)))
        asked = self.fight_facts(run, world, foes, shown, prey)
        if FIGHT_CAST_REACH and asked.cast_barred is not None:
            return False
        for row in self.buffs.rows('fight'):
            if row.skill not in herald_pack.FIRST or row.before_strike is None or not row.before_strike(asked):
                continue
            due = self.buffs.due(run, row, asked)
            if due is None:
                continue
            tried = self.buffs.cast(run, due, key_names, rect[2] / rect[3])
            if tried.cast:
                LOG.info(f'Macro: mark: first {said}', herald_pack.since_hop(run.clock()))
            return tried.touched
        return False

    def mark_from_here(self, run: Run, world: World, foes: Sequence[Monster], key_names) -> bool:
        """MARK_THEN_WALK: the mark from where the character stands before the walk in (combat/pack.py `ask_mark`), the
        FIRST rows asked with the hostiles drawn on the screen; whether a key or the pointer was touched."""
        player = world.player
        if player is None:
            return False
        rect = run.actuator.keys.focused_window_rect()
        view = Viewport(rect[2] / rect[3]) if rect is not None and rect[3] else Viewport()
        here = (player.x, player.y)
        shown = [m for m in foes if view.on_screen(view.body(here, m.x, m.y))]
        herald_pack.ask_mark(run.clock())
        said = 'from here before the walk in (MARK_THEN_WALK), %.2fs after a landing'
        return self.first_rows(run, world, foes, shown, key_names, said)

    def mark_with_press(
        self,
        run: Run,
        world: World,
        foes: Sequence[Monster],
        reachable: Sequence[Monster],
        prey: Monster,
        key_names,
        aspect: float,
        again: Callable[[], None],
        cast: CastWatch,
    ) -> bool:
        """MARK_WITH_PRESS: right after the strike's press, the build's FIRST skills (combat/pack.py FIRST) whose rows
        are due before the strike, by this look's facts, cast once the strike's cast shows (PRESS_CAST_WAIT), the held
        strike pressed again under the cast (`Buffs.resume`). Whether the pointer or a key was touched."""
        asked = self.fight_facts(run, world, foes, reachable, prey)
        if FIGHT_CAST_REACH and asked.cast_barred is not None:
            return False  # the fight casts' hold: from the next look, as before
        rows = [
            row
            for row in self.buffs.rows('fight')
            if row.skill in herald_pack.FIRST and row.before_strike is not None and row.before_strike(asked)
        ]
        if not rows:
            return False
        if run.seen(lambda w: w.player is not None and w.player.mode in ACTING, PRESS_CAST_WAIT, SLICE) is None:
            return False  # the strike's cast not seen yet: the mark from the next look, as before
        for row in rows:
            due = self.buffs.due(run, row, asked)
            if due is None:
                continue
            self.casting = True
            tried = self.buffs.cast(run, due, key_names, aspect)
            if tried.touched:
                cast.excuse(run.clock())
                self.buffs.resume(run, again)
            return tried.touched
        return False

    def cast_tail(self, run: Run, world: World, key_names, skill: int) -> tuple[World, Player] | None:
        """CAST_TAIL: the character casting with the strike off its input (a Quick Cast keeps the cast's skill on the
        right button to its end): the game looked at every SLICE through the cast's tail; (the world, the character)
        of the look that sees the strike's input back, or None when it does not come in CAST_TAIL_MOST, the player's
        hand moves, a move is asked for, the character dies or the level changes."""
        player = world.player
        if player is None or player.mode not in ACTING:
            return None
        if CAST_TAIL_HOPS and player.right_skill != TELEPORT:
            return None  # a buff's or a mark's tail: the loop's naps and looks, as before
        until = run.clock() + CAST_TAIL_MOST
        while run.clock() < until:
            if self.nap(run, SLICE) or self.move is not None:
                return None
            seen = run.world()
            now = seen.player
            if now is None or now.mode in DEAD or now.area != player.area or not seen.in_game or seen.open_panels:
                return None
            if self.moving(run, seen) is not None:
                return None
            try:
                strike_input(run, seen, key_names, skill)
            except Abort as stop:
                if run.stops(stop):
                    raise
                continue
            return seen, now
        return None

    def strike_back(self, run: Run, world: World, skill: int) -> bool:
        """Keyboard mode, the strike on no input for INPUT_SECONDS (rca/2026-10-14/run-1904-findings.md §3.7):
        select it on the right button in the skill panel (skillpanel.py, `Build.skill_icons`), at most once per
        STRIKE_BACK_RETRY; whether the right button holds it now."""
        player = world.player
        icon = self.build.skill_icons.get(skill)
        if run.pad is not None or icon is None or player is None or player.right_skill is None:
            return False  # the right skill unread: the selection's outcome could not be seen
        now = run.clock()
        if now - self.struck_back_at < STRIKE_BACK_RETRY:
            return False
        self.struck_back_at = now
        LOG.info(
            'Macro: skill panel: %s is on no skill key and on neither mouse button (left %s, right %s): selecting it '
            'on the right button',
            skill_name(skill), skill_name(player.left_skill), skill_name(player.right_skill),
        )  # fmt: skip
        run.say(f'{skill_name(skill)} back on the right button')
        try:
            with run.actuator.held_act():
                select_right(run, skill, icon)
        except Abort as stop:
            if run.stops(stop):
                raise
            LOG.info('Macro: skill panel: %s', stop)
            return False
        return True

    def step_aside(self) -> None:
        """Nothing is fought: a step that waited for the fight (the pickup step) gets its turn (Cancelled)."""
        self.step_asked.clear()  # nothing in reach: the request is the pickup step's (its `step` moves)
        if self.after_fight.is_set():
            self.after_fight.clear()
            raise Cancelled

    def firing_target(self, level: Level, ground: Ground, here, mob, name: str, doors=()) -> Target:
        """The target of a hop toward `mob`: the nearest spot on a room with a shot at it, or the monster
        itself. A spot the character all but stands on leaves the hop nothing to gain, which the landing says."""
        spots = firing_spots(ground, mob, STRIKE_REACH, here, doors) or [mob]
        spot = next((s for s in spots if room_at(level.rooms, (s[0] / TILE_UNITS, s[1] / TILE_UNITS))), spots[0])
        tile = (spot[0] / TILE_UNITS, spot[1] / TILE_UNITS)
        LOG.info(
            'Macro: hunting %s at (%.1f, %.1f), %.0f away from (%.1f, %.1f), firing spot (%.1f, %.1f) of %d',
            name, mob[0], mob[1], math.dist(here, mob), here[0], here[1], spot[0], spot[1], len(spots),
        )  # fmt: skip
        return Target(level.area, level.rooms, tile, name, 'hunt', False, level.ground)

    def frontier(
        self,
        level: Level,
        player,
        rect,
        skip: Callable[[Point], bool] | None = None,
        keep: Bounds | None = None,
    ) -> tuple[float, Room, tuple[int, int]] | None:
        """(tiles by the way, room, tile) of the room to go and stand in next: the first stop of the
        tour that shows every unexplored room (macros/tour.py), by its tile nearest by the way past PLACE_NEAR from
        here. `skip(place)`: a stop passed for now (hunting/choice.py `next_room`). `keep`: the stop gone to, kept
        while the tour has it unless the first stop's way is under STOP_KEEP_SHARE of its (KEEP_STOP)."""
        seen = set(self.explored(level.area)) if self.explored is not None else set()
        # A loaded room of wall alone shows nothing: no stop stands by it (Frozen Tundra's edge columns, 44 of 150
        # rooms, held each run at the level's edge until its pass; rca/2026-10-19/tz-leveling-findings.md C2)
        seen |= walled(level)
        here = (player.x / TILE_UNITS, player.y / TILE_UNITS)
        # The far potential: the one the hop there is planned by (teleport.hop_toward).
        origin = Way(
            Target(level.area, level.rooms, here, 'here', 'explore', False, level.ground), Viewport.of(rect), True
        )
        # Where the character can stand in each room: its tile nearest by the way. Not its own room,
        # which showed what it shows when the character came into it.
        nearest: dict[Bounds, tuple[float, Room, tuple[int, int]]] = {}
        for room in level.rooms:
            if room_at((room,), here) is not None:
                continue
            costs = [
                (cost, (x, y))
                for x in range(room.x, room.x + room.width)
                for y in range(room.y, room.y + room.height)
                if (cost := origin.cost.get((x, y))) is not None
            ]
            # Not a tile within PLACE_NEAR of here: that is "arrived" from the room beside it, which was never
            # entered (21:05:19 on 2026-10-19: 15 s by 29 hostiles; rca/2026-10-19/tz-leveling-findings.md C1)
            beyond = [
                (cost, tile)
                for cost, tile in costs
                if math.dist(here, (tile[0] + 0.5, tile[1] + 0.5)) * TILE_UNITS > PLACE_NEAR
            ]
            if costs:
                cost, tile = min(beyond or costs)
                nearest[room.x, room.y, room.width, room.height] = (cost, room, tile)
        bounds = [(room.x, room.y, room.width, room.height) for room in level.rooms]
        before = self.route[1] if self.route[0] == level.area else []
        stops = tour(bounds, here, seen, nearest.keys(), before)
        self.route = (level.area, stops)
        if not stops and level.rooms and seen:
            self.tours_done.add(level.area)
        if not stops and self.toured != (level.area, len(level.rooms), len(seen)):
            # Said once a level and count: a full clear once ended with rooms unexplored, nothing saying why
            self.toured = (level.area, len(level.rooms), len(seen))
            LOG.info('Macro: run: the tour has no stop on level %d: %d rooms, %d explored, %d with a way from here',
                     level.area, len(level.rooms), len(seen), len(nearest))  # fmt: skip

        def unpassed(stop: Bounds) -> bool:
            _, _, (x, y) = nearest[stop]
            return skip is None or not skip(((x + 0.5) * TILE_UNITS, (y + 0.5) * TILE_UNITS))

        # A passed stop yields to the next: the first alone ended the run with half the level unseen
        # (21:05:43 on 2026-10-19; findings C3)
        first = next((stop for stop in stops if unpassed(stop)), None)
        if first is None:
            return None
        if (
            KEEP_STOP
            and keep is not None
            and keep != first
            and keep in stops
            and unpassed(keep)
            and nearest[first][0] >= STOP_KEEP_SHARE * nearest[keep][0]
        ):
            return nearest[keep]  # the stop gone to, while nothing much nearer came up (21:53:40-56; S3)
        return nearest[first]

    def explore(self, run: Run, level: Level, player, rect, key_names, frontier=None) -> None:
        """A hop toward the unexplored room `frontier` names (found here when not given)."""
        found = frontier or self.frontier(level, player, rect)
        if found is None:
            raise Abort('the level is explored and nothing is left to hunt')
        cost, room, (x, y) = found
        LOG.info(
            'Macro: exploring toward room %s at (%d, %d), %.0f tiles by the way, the first of %d stops, '
            '%d explored of %d',
            room.preset, x, y, cost, len(self.route[1]),
            len(self.explored(level.area)) if self.explored is not None else 0, len(level.rooms),
        )  # fmt: skip
        goal = ((x + 0.5) * TILE_UNITS, (y + 0.5) * TILE_UNITS)
        if self.afoot(run, Ground(level.ground), player, rect, goal, 'an unexplored room', key_names):
            return
        target = Target(
            level.area, level.rooms, (x + 0.5, y + 0.5), 'an unexplored room', 'explore', False, level.ground
        )
        hop_toward(run, target, player, rect, key_names)

    def main_weapons(self, run: Run, world: World, key_names, *, swap: bool = True) -> bool:
        """The main weapon set in hand for a fight; whether it is held, or nothing is known to want. With `swap`
        off it only looks; the next hop swaps the staff back (teleport.take_teleport). A build without
        `Build.weapons` or unreadable hands are left alone; a swap that did not come waits SWAP_RETRY_SECONDS."""
        loadout = self.build.weapons if world.player is not None else None
        if loadout is None:
            return True
        if run.hands is None:
            return not self.pursuing
        if run.clock() - self.swap_failed_at < SWAP_RETRY_SECONDS:
            return not self.pursuing or bool(loadout.battle & set(run.hands()))
        held = set(run.hands())
        if not held:
            return not self.pursuing
        if loadout.battle & held:
            return True
        if not swap:
            return False
        run.keys.update(key_names(world, (SWAP_WEAPONS,)))
        run.battle_hands = loadout.battle
        run.say('Main weapons for the fight')
        take_battle_weapons(run)
        if not loadout.battle & set(run.hands()):
            self.swap_failed_at = run.clock()
            return not self.pursuing
        return True

    def sense(self, run: Run) -> bool:
        """Look at the left mouse button; a press is a move asked for (`self.move`). True on a new press."""
        looked = self.drinker.looked_at
        self.drinker.look(run, self.stands)  # the life first: a potion is drunk beside whatever is in hand
        loot = self.drinker.last
        if self.drinker.looked_at != looked and loot is not None and self.area is not None and self.stands:
            pressed = self.drinker.pressed_at.get(PotionType.HEALING, -math.inf)
            empty = self.potions.see(loot, self.area, self.stands, run.clock(), pressed)
            if empty is not None:
                # "something is wrong if we're empty" (the player, 2026-10-13): logged, not carded, as the mercenary
                # may drink them all ("you can use all hp potions on merc")
                LOG.warning('Macro: potion stock: %s', empty)
        down = run.actuator.button_held(1)
        if down and run.pad is not None:
            # In controller mode a click is the player's and flips the game back: no move is made for it.
            raise Abort('a mouse button was pressed (the game leaves controller mode)')
        pressed = down and not self.left_down
        self.left_down = down
        if down:
            self.hand_at = run.clock()  # the hand at work: a paused level run waits for it to rest
        if pressed:
            self.expired_motion = False
            self.sweep.end()  # the player moves by hand: no step of the mode's own after it
            self.pause_run(run, 'a click')
            self.move = Move(run.clock(), run.actuator.keys.pointer(), swallowed=self.casting)
            self.fresh_press = True
        return pressed

    def nap(self, run: Run, seconds: float, *, key: bool = False) -> bool:
        """Sleep `seconds`, looking at the left button every SLICE (a click is down 60-120 ms); True when cut
        short by a press. With `key` a teleport press posted meanwhile also ends it, with False."""
        until = run.clock() + seconds
        self.fresh_press = False
        posted = self.pursuit
        while True:
            self.sense(run)
            if self.fresh_press:  # seen here or inside the sleep (attack mode's own `watchful`)
                return True
            if key and self.pursuit is not posted:
                return False
            left = until - run.clock()
            if left <= 0:
                return False
            run.pace.sleep(min(SLICE, left))

    def serve_move(self, run: Run, world: World) -> None:
        """The player's move before any strike (combat/controller.py `serve`): waited for, and a click a cast may
        have swallowed made again where they made it."""
        move, player = self.move, world.player
        if move is None or player is None:
            self.move = None
            return
        if world.open_panels:
            # A panel open: a click made again could drop the item on the cursor (run-2110-findings.md §2.4; I7)
            LOG.info('Macro: the click the cast swallowed is not made again: %s open', ', '.join(world.open_panels))
            self.move = None
            return
        todo = serve(
            move, run.clock(), (player.x, player.y),
            running=player.mode in RUN_MODES, acting=player.mode in ACTING, left_down=self.left_down,
        )  # fmt: skip
        if todo == PENDING:
            return
        if todo != CLICK:
            if todo == GAVE_UP:
                LOG.info(
                    'Macro: the move asked for %.1fs ago showed nothing after %d clicks',
                    run.clock() - move.at, move.clicks,
                )  # fmt: skip
            self.move = None
            return
        keys = run.actuator.keys
        back = keys.pointer()
        assert move.pixel is not None
        try:
            keys.move_pointer(*move.pixel)
            keys.sync()
            run.actuator.click()
            if back is not None:
                keys.move_pointer(*back)
                keys.sync()
        except Abort as stop:
            if run.stops(stop):
                raise
            LOG.info('Macro: the click for the player was not made (%s)', stop)
            self.move = None
            return
        move.clicked(run.clock())
        LOG.info(
            'Macro: the click the cast swallowed made again at %s, %.2fs after the press (%d of %d)',
            move.pixel, move.clicked_at - move.at, move.clicks, MOVE_CLICKS,
        )  # fmt: skip

    def upkeep(self, run: Run, world: World, foes: list[Monster], key_names, *, renewing: bool = False) -> bool:
        """Cast the first due row of the build's upkeep; whether one was. A key cast that fails is logged and
        counts as made; a row with a caster answers for itself (build.py `Tried`) and lets a waiting step go
        first. `renewing`: only a buff that would end inside the coming boss fight (`ahead`)."""
        player = world.player
        if LANDING_UPKEEP_WAITS and herald_pack.HOP.at > self.pressed_at and self.landing_members(run, world, foes):
            return False  # a T5 Herald landing: the mark and the strike before the upkeep
        facts = self.buffs.facts(run, world, foes, ahead=self.ahead(player.area if player is not None else None))
        facts = self.rebuff_facts(facts)  # a rebuff retreat's landing (cta.py REBUFF_GRACE)
        due = self.buffs.first(run, 'upkeep', facts, renewing=renewing)
        if due is None:
            return False
        own = due.row.caster is not None
        if own:
            self.step_aside()
        try:
            self.buffs.cast(run, due, key_names)
            if not own:
                run.pause('key')
        except Abort as stop:
            if run.stops(stop):
                raise
            LOG.info('Macro: no %s (%s)', skill_name(due.row.skill), stop)
            self.buffs.remember(due.row, run.clock())
        return True

    def keep_orders(self, run: Run, world: World, foes: Sequence[Monster]) -> cta.OrdersLook | None:
        """Battle Orders at this look for the safety (macros/cta.py `orders_look`: ORDERS_PREDICT, REBUFF_RETREAT), the
        rejuvenation alarm (BOUT_ALARM, DANGER_LOOK) and the aura reads (AURA_FORECAST); the look, or None."""
        safety = self.safety
        if safety.states_of is None and run.reads is not None:
            safety.states_of = run.reads.unit_states
        drunk = self.drinker.drunk_at.get(PotionType.REJUVENATION)
        safety.alarmed = BOUT_ALARM and drunk is not None and run.clock() - drunk <= ALARM_SECONDS
        track = cta.track_of(run)
        track.rebuffed_at = safety.rebuffed_at
        track.threat = self.cast_threat  # asked fresh at the cast (macros/safety.py CAST_REACH)
        safety.landed(herald_pack.HOP.at)  # the rebuff retreat's landing, when this hop is it
        loot = self.drinker.last
        looked = cta.orders_look(
            run, world, foes, hurt=self.buffs.hurt(run), max_life=loot.max_life if loot is not None else None,
            worn=worn_cta(run), barred=self.cast_threat(world),
        )  # fmt: skip
        safety.orders = looked
        return looked

    def fight_facts(
        self, run: Run, world: World, foes: Sequence[Monster], reachable: Sequence[Monster], prey: Monster
    ) -> BuffFacts:
        """The facts the bout's casts are asked with: the safety's last prices of the build's draw (build.py `Draw`)
        while fresh, and its last rebuff retreat (`rebuff_facts`)."""
        return self.rebuff_facts(self.buffs.facts(run, world, foes, reachable, prey, self.safety.priced(run.clock())))

    def rebuff_facts(self, facts: BuffFacts) -> BuffFacts:
        """`facts` with the safety's last rebuff retreat: chosen (cta.py REBUFF_GRACE) and landed (mark.py
        `rebuff_waits`)."""
        safety = self.safety
        return replace(
            facts, rebuffed=safety.rebuffed_at, rebuff_landed=safety.rebuff_landed,
            cast_barred=self.cast_threat(facts.world),
        )  # fmt: skip

    def bout_reach(self, run: Run, world: World) -> str | None:
        """Why the strike bout yields to the safety's look now (macros/safety.py BOUT_REACH), at the life last read: not
        within BOUT_REACH_EVERY s of the safety's last look (it chose this bout knowing the threat: no spin of looks and
        bouts on one clock)."""
        decision = self.safety.decision
        looked = decision.get('looked_at') if decision else None
        if looked is not None and run.clock() - looked < safety_module.BOUT_REACH_EVERY:
            return None
        if decision is self.reach_decision:
            # Yielded once and the safety has not looked since: a mode with no look of its own (attack mode alone,
            # the tests' players) went back into the bout at once, and yield and bout spun on one clock (the wide
            # suite, 2026-10-22: test_hunt's chained casts and test_pad's controller strike hung). The bout goes on.
            return None
        loot = self.drinker.last
        reach = self.safety.cast_threat(world, loot.life if loot is not None else None, bout=True)
        if reach is not None:
            self.reach_decision = decision
        return reach

    def paced(self, world: World) -> bool:
        """Whether the bout's casts go one a look (FIGHT_CAST_REACH): melee blows that together take the life can come
        within reach in FIGHT_PACE_SECONDS, at the life last read."""
        loot = self.drinker.last
        life = loot.life if loot is not None else None
        return self.safety.cast_threat(world, life, seconds=FIGHT_PACE_SECONDS) is not None

    def cast_threat(self, world: World) -> str | None:
        """Why the Call to Arms is not swapped to here now (macros/safety.py CAST_REACH), at the life last read."""
        loot = self.drinker.last
        return self.safety.cast_threat(world, loot.life if loot is not None else None)

    def orders_due(self, run: Run, world: World, foes: Sequence[Monster]) -> str | None:
        """Why the bout yields for Battle Orders now (BOUT_ORDERS): due (`OrdersLook.due`), safe to cast here, and
        its upkeep row due by the upkeep's own rules (macros/buffs.py `Buffs.due`); None: the bout goes on."""
        looked = self.safety.orders
        if not BOUT_ORDERS or looked is None or looked.due is None or not looked.safe:
            return None
        row = next((r for r in self.buffs.rows('upkeep') if r.caster == 'cta'), None)
        if row is None:
            return None
        facts = self.rebuff_facts(self.buffs.facts(run, world, foes))
        return looked.due if self.buffs.due(run, row, facts) is not None else None

    def ahead(self, area: int | None) -> float:
        """Seconds of a boss's fight the route brings next on level `area` (goals.py `boss_ahead`: the fight's
        stage, or the last seal of an arm): BOSS_AHEAD, else 0."""
        progress = self.bearings.progress
        step = progress.step(area) if progress is not None and area is not None else None
        script = getattr(step, 'script', None)
        if step is None or script is None:
            return 0.0
        return BOSS_AHEAD if boss_ahead(script.stages, step.stage) else 0.0

    def tough(self, world: World, reachable: list[Monster]) -> bool:
        """Whether what is in reach is worth the main weapons (damage, capped resistances; user, 2026-10-12: "we
        should swap to it against most of tough/hard-hitting enemies/bosses"): a pack leader or a Herald's own,
        TOUGH_POINTS of life (an elite's times ELITE_LIFE unless combat/mechanics/life.py TIER_LIFE has its rank in
        the points: `rank_share`), or a pack threat score (terror/danger.py) of HARD_SCORE.
        Examples: macros/history/hunt.md."""
        if world.player is None:
            return False
        if any(m.tier or m.leader for m in reachable):
            return True
        seen = observe(world.player, reachable, ())
        if sum(foe.left * rank_share(foe.elite) for foe in seen.foes.values()) >= TOUGH_POINTS:
            return True
        units = [Unit(m.unit_id, m.txt_id, m.x, m.y, m.modifiers, None, False, m.flags, m.tier) for m in reachable]
        return any(pack.score >= HARD_SCORE for pack in packs(units))

    def moving(self, run: Run, world: World, *, keys: bool = True) -> str | None:
        """Why the pointer is the player's now, or None: a held key, the left button down, or the character
        walking or running; attack mode yields to all three. With `keys` off a held key is no reason (the
        strike stays held through the player's key taps)."""
        if keys and run.actuator.key_held():
            self.expired_motion = False
            return 'a key is held'
        if run.actuator.button_held(1):
            self.expired_motion = False
            return 'the left button is down'
        if world.player is not None and world.player.mode in RUN_MODES:
            if self.pursuing and self.expired_motion:
                return None  # our old click is not the player's permission to keep walking
            here, now = (world.player.x, world.player.y), run.clock()
            if self.ran is None or math.dist(here, self.ran[0]) >= MOVED:
                self.ran = (here, now, False)
            elif now - self.ran[1] >= RUN_IN_PLACE:
                if not self.ran[2]:
                    self.ran = (*self.ran[:2], True)
                    LOG.info(
                        'Macro: the character runs in place at (%.1f, %.1f) for %.1fs (mode %d): not waited for',
                        *here, now - self.ran[1], world.player.mode,
                    )  # fmt: skip
                return None
            return 'the character is on the move'
        self.ran = None
        self.expired_motion = False
        return None

    def choose(
        self, world: World, foes: list[Monster], reachable: list[Monster], ground: Ground, view: Viewport
    ) -> Choice:
        """Where to cast now (`aim_choice`, scored as `live` by the simulator): the attack's cast over the
        hostiles in sight, else straight at what is in reach, at a focal point the pointer can reach; a boss in
        reach first."""
        player = world.player
        assert player is not None
        here = (player.x, player.y)
        near = [m for m in foes if math.dist(here, (m.x, m.y)) <= SIGHT]
        companions = [m for m in world.monsters if m.ally or m.owner != NO_OWNER]
        attack = self.attack
        seen = attack.sees(
            observe(
                player, near, companions, ground, world.doors, aimable=lambda focal: view.reachable_focal(here, focal)
            ),
            companions,
        )
        bosses = [m.unit_id for m in reachable if m.txt_id in BOSSES]
        # A hostile bound to a live summoner (threats.bound: Baal's clone) is no target while anything else is in
        # reach; the summoner in reach goes first (rca/2026-10-14/baal-sim.md fix 2)
        lost = self.bound_lost(foes, reachable)
        if lost:
            seen = replace(seen, foes={unit: foe for unit, foe in seen.foes.items() if unit not in lost})
        reached = {m.unit_id for m in reachable}
        masters = [unit for held in lost.values() for unit in held if unit in reached and unit not in bosses]
        # What bars the pursuit's goal (`blocking`: a pack on a seal) is struck through first, after a boss
        barring = self.blocking[1] if self.blocking is not None else frozenset()
        if self.pursuing:
            barring = barring | frozenset(self.safety.blocked_by)
        first = bosses + list(dict.fromkeys(masters))
        first += [m.unit_id for m in reachable if m.unit_id in barring and m.unit_id not in {*first, *lost}]
        aimer = self.aimed_by if self.aimed_by is not None else attack
        struck = [m.unit_id for m in reachable if m.unit_id not in lost]
        # Dolls running in before anything else: they die before they arrive, not on the character (DOLL_FIRST, F3 of
        # rca/2026-10-21/dolls-tz-findings.md); the best line through one of them, whatever else it holds
        first = dolls.first_struck(here, seen.foes, struck) or first
        found = aim_choice(aimer, seen, struck, first=first)
        assert found is not None  # the caller has something in reach
        return found

    def only_bound(self, world: World, foes: Sequence[Monster], ground: Ground, here: Point) -> bool:
        """Whether every hostile in reach dies with a summoner seen alive (threats.bound): no fight to hold."""
        lost = threats.bound({m.unit_id: m.txt_id for m in foes})
        reachable = [m for m in foes if in_reach_of(ground, here, (m.x, m.y), self.reach, world.doors)]
        only = bool(reachable) and all(m.unit_id in lost for m in reachable)
        if only:
            by_unit = {m.unit_id: m for m in foes}
            for m in reachable:
                if m.unit_id not in self.away_said:
                    if len(self.away_said) > 200:
                        self.away_said.clear()
                    self.away_said.add(m.unit_id)
                    LOG.info(
                        'Macro: pursuit: %s, the only one in reach, dies with %s: no fight to hold, the goal first',
                        label(m), label(by_unit[lost[m.unit_id][0]]),
                    )  # fmt: skip
        return only

    def bound_lost(self, foes: Sequence[Monster], reachable: Sequence[Monster]) -> dict[int, tuple[int, ...]]:
        """The hostiles in reach bound to a live summoner, with its units: no target while anything else is in
        reach (`choose`); empty when nothing else is."""
        by_unit = {m.unit_id: m for m in foes}
        bound = threats.bound({m.unit_id: m.txt_id for m in foes})
        lost = {m.unit_id: bound[m.unit_id] for m in reachable if m.unit_id in bound}
        if len(lost) == len(reachable):
            return {}
        for unit, held in lost.items():
            if unit not in self.bound_said:
                if len(self.bound_said) > 200:
                    self.bound_said.clear()
                self.bound_said.add(unit)
                LOG.info(
                    'Macro: target: %s dies with %s: not struck while anything else is in reach',
                    label(by_unit[unit]), label(by_unit[held[0]]),
                )  # fmt: skip
        return lost

    def off_labels(self, run: Run, view: Viewport, here: Point, focal: Point) -> None:
        """Move the pointer along the line to `focal` while an item's label is under it: the game casts at the unit
        under the pointer, so the blades would fly to the item; along the line they keep their length (view.py).
        User, 2026-10-12: "it aimed off and continued shooting there" (macros/history/hunt.md)."""
        if run.hovered is None:
            return
        away = math.dist(here, focal)
        tried = []
        for shift in LABEL_SHIFTS:
            if shift:
                if away + shift < MIN_FOCAL:
                    continue
                share = (away + shift) / away
                point = (here[0] + (focal[0] - here[0]) * share, here[1] + (focal[1] - here[1]) * share)
                where = view.aim(here, point)
                if where is None:
                    continue
                run.actuator.aim(*where, scatter=(2, 2))
                run.pace.sleep(HOVER_SECONDS)
            over = run.hovered()
            if over is None or over[0] != ITEM_UNIT:
                if tried:
                    LOG.info(
                        "Macro: an item's label under the aim at (%.1f, %.1f) (%s): the pointer %+.0f units along "
                        'the line instead',
                        *focal, ', '.join(tried), shift,
                    )  # fmt: skip
                return
            tried.append(f'{shift:+.0f}: item {over[1]}')
        LOG.info("Macro: an item's label under every aim along the line to (%.1f, %.1f): %s", *focal, ', '.join(tried))

    def onto_held(
        self, run: Run, view: Viewport, here: Point, prey: Monster, world: World, focal: Point, covering: int
    ) -> bool:
        """Move the pointer onto the held leader's body while the hover names the monster `covering` instead
        (HELD_ON_BODY): its body, then up it, then away from the neighbour, a look HOVER_SECONDS after each; back on
        the line to `focal` when none names it. Whether the hover names it at the end; said once a leader and way."""
        named = [covering]
        point = view.body(here, prey.x, prey.y)
        for nudge in range(HELD_NUDGES):
            other = next((m for m in world.monsters if m.unit_id == named[-1]), None)
            if nudge == 0:
                moved = point
            elif nudge == 1 or other is None:
                moved = (point[0], point[1] - HELD_UP)
            else:
                there = view.body(here, other.x, other.y)
                dx, dy = point[0] - there[0], point[1] - there[1]
                away = math.hypot(dx, dy) or 1.0
                moved = (point[0] + dx / away * HELD_AWAY, point[1] - HELD_UP + dy / away * HELD_AWAY)
            if not view.on_screen(moved):
                continue
            run.actuator.aim(*moved, scatter=(1, 1))
            run.pace.sleep(HOVER_SECONDS)
            over = run.hovered() if run.hovered is not None else None
            if over is not None and over[0] == MONSTER_UNIT and over[1] == prey.unit_id:
                self.say_held(prey, True, f'the pointer on its body after {nudge + 1} moves', named)
                return True
            if over is not None and over[0] == MONSTER_UNIT:
                named.append(over[1])
        where = view.aim(here, focal)
        if where is not None:
            run.actuator.aim(*where, scatter=(2, 2))
        self.say_held(prey, False, f'still covered after {HELD_NUDGES} moves: back on the line', named)
        return False

    def say_held(self, prey: Monster, on: bool, how: str, named: list[int]) -> None:
        """Log a held leader's cover once a leader and outcome (`onto_held`)."""
        if (prey.unit_id, on) in self.cover_said:
            return
        self.cover_said.add((prey.unit_id, on))
        LOG.info(
            'Macro: strike: %s held, the hover named %s over it (the blades go to the unit under the pointer): %s',
            label(prey), ', '.join(str(unit) for unit in dict.fromkeys(named)), how,
        )  # fmt: skip

    def fight(self, run: Run, ground: Ground, aspect: float, key_names, until: float | None = None) -> None:
        """Strike while anything is in reach and the player stands: one hold of the strike input, the pointer on
        the policy's line, asked again every DECIDE_SECONDS and when its monster is gone. Ends when nothing is in
        reach, the player moves, at `until` (a swap to the main weapons) or after FIGHT_SECONDS."""
        started = run.clock()
        attack = self.attack
        held, how = strike_input(run, run.world(), key_names, attack.skill)  # before any cast: no key, no fight
        down = 0
        cast = CastWatch(started)  # the casts seen since the press (combat/controller.py)
        choice: Choice | None = None
        decided_at = -math.inf
        aim = Aim((run.actuator.keys.pointer(), -math.inf))  # where the pointer was put, and the player's hand
        view = Viewport(aspect)
        again: Callable[[], None] | None = None
        watched: set[int] = set()  # the hostiles seen in reach while the input was held
        lined: int | None = None  # the monster the line last logged went through
        labels_due = math.inf  # clock time of the next look for an item's label under the standing pointer
        labels = LabelLook()  # the shifts tried off an item's label, one a look (LABEL_CLEAR_AIM)
        counted = 0  # the casts seen up to the last look
        harmed_at = started  # clock time something in reach last lost life or died (`unharmed`)
        lives: dict[int, int] = {}  # unit -> its life at the look before, what is in reach with a life read
        guarded_at = -math.inf  # clock time of the last safety look of the mode alone (`guard`)
        alarmed = self.safety.alarmed  # a rejuvenation was drunk just now at the last look (BOUT_ALARM)
        held_back: str | None = None  # why the bout's casts were last held (FIGHT_CAST_REACH), said once
        omen_said: Point | None = None  # the Herald's coming the line last went through (OMEN_STRIKE), said once
        ended = f'Fight stopped after {FIGHT_SECONDS:.0f}s'
        with ExitStack() as stack:
            stack.callback(setattr, self.buffs, 'let_go', None)
            while run.clock() - started < FIGHT_SECONDS:
                fight_looked = run.clock()  # the fight's look, for its decision event (takes/decisions.py)
                world = run.world()
                player = world.player
                if player is None:
                    raise Abort('not in a game')
                if player.mode in DEAD:
                    raise Dead('the character is dead')
                alive = {m.unit_id for m in world.monsters}
                down += len(watched - alive)
                watched &= alive
                held_input = cast.step(run.clock(), player.mode in ACTING) if again is not None else None
                if held_input == NO_CAST:
                    raise Abort(f'no cast seen after the {how} ({skill_name(attack.skill)} not on {how}?)')
                self.casting = again is not None or player.mode in ACTING
                if player.mode in ACTING and attack.skill in (player.left_skill, player.right_skill):
                    self.struck_at = run.clock()  # the strike-gap fact of the pursuit's arbiter (`Facts.quiet`)
                self.sense(run)
                why = 'a move was asked for' if self.move is not None else self.moving(run, world, keys=again is None)
                if why is not None:
                    ended = f'Yielded ({why})'
                    break
                if held_input == RETAP and again is not None:
                    # After the look at the player's move: a click just made is yielded to, not answered with a
                    # new press (review.md, finding 7).
                    again()
                here = (player.x, player.y)
                foes = self.foes(world, run.clock())
                self.score.note(run.clock(), player, foes, world.dead)
                reachable = [m for m in foes if in_reach(ground, here, (m.x, m.y), attack.reach, world.doors)]
                if not reachable:
                    ended = 'Nothing left in reach'
                    break
                read_lives = {m.unit_id: m.life for m in reachable if m.max_life}
                if any(points < lives.get(unit, points) for unit, points in read_lives.items()) or not (
                    lives.keys() <= alive
                ):
                    harmed_at = run.clock()  # something in reach lost life, or died
                lives = read_lives
                self.keep_orders(run, world, foes)
                due = self.orders_due(run, world, foes) if again is not None else None
                if due is not None:
                    ended = f'Yielded (Battle Orders: {due})'  # the upkeep casts it at the mode's next look
                    break
                reach = self.bout_reach(run, world)
                if reach is not None:
                    self.judged = (math.nan, -math.inf, False)  # the safety asked at the next look (BOUT_REACH)
                    ended = f'Yielded ({reach})'
                    break
                if self.safety.alarmed and not alarmed:
                    self.judged = (math.nan, -math.inf, False)  # a rejuvenation just drunk: the safety asked at once
                alarmed = self.safety.alarmed
                if self.pursuing and self.key_asks(run, world, foes, ground, unstruck=again is None):
                    ended = 'Yielded (the key asks for a move)'  # the mode makes it at its next look
                    break
                if until is not None and run.clock() >= until:
                    if self.tough(world, reachable) or any(m.txt_id in BOSSES for m in reachable):
                        ended = 'Stopping for the main weapons'  # attack mode takes them and fights on
                        break
                    until = None  # what is left is not worth the swap any more: fought on as it is
                if again is not None and run.actuator.key_held():
                    # A key of the player's: the strike stays held as their hand would; the macro's aims and keys wait.
                    if self.nap(run, FRAME):
                        ended = 'Yielded (a move was asked for)'
                        break
                    continue
                if self.step_asked.is_set():
                    self.step_asked.clear()
                    self.stepping = self.asked_step(run, world, foes, reachable, ground, aspect)
                    if self.stepping is not None:
                        ended = 'Stepping to a better place'
                        break
                if self.sweep.steps and not self.running:
                    self.gather(run, here, foes)
                if not self.pursuing and self.guarded(foes) and run.clock() - guarded_at >= DECIDE_SECONDS:
                    # The pursuit loop's safety step for the mode alone (`guard`): a dodge or a model's place only
                    guarded_at = run.clock()
                    self.guarding = self.guard(run, world, foes, ground)
                    if self.guarding is not None:
                        ended = 'Stepping out of harm'
                        break
                if (
                    self.pursuing
                    and self.running
                    and not self.rushing
                    and self.build.settings.fight_look
                    and again is not None  # after the strike's press: the look held it back (F2, `key_asks`)
                    and run.clock() - self.sweep.looked >= FOLLOW_CHECK
                ):
                    # A level run's fight keeps the look for a better place (rca/2026-10-13/kp1-level-run.md §2),
                    # priced by the safety against holding (`Safety.offer`): one mover (run-1932-findings.md §4).
                    self.sweep.looked = run.clock()
                    better = self.next_step(run, world, foes, ground, aspect, fighting=True, priced=True)
                    self.safety.offer(better, run.clock())
                    if better is not None:
                        LOG.info(
                            'Macro: run: a better place in the fight with %d of %d hostiles in reach, from '
                            '(%.1f, %.1f): %s; the safety prices it',
                            len(reachable), len(foes), *here, step_line(better, here),
                        )  # fmt: skip
                if not self.pursuing and self.sweep.due(run.clock()):
                    # The sweep: a better place is gone to without a press.
                    self.sweep.looked = run.clock()
                    better = self.next_step(run, world, foes, ground, aspect, fighting=True)
                    if better is not None:
                        LOG.info(
                            'Macro: sweeping in the fight with %d of %d hostiles in reach, from (%.1f, %.1f): %s',
                            len(reachable), len(foes), *here, step_line(better, here),
                        )  # fmt: skip
                        self.sweep_to(run, better)
                        ended = 'Stepping to a better place'
                        break
                if self.step_asked_at is not None and cast.casts:
                    LOG.info('Macro: first cast %.2fs after the step', run.clock() - self.step_asked_at)
                    self.step_asked_at = None
                # The aim only on a foe now: a bird that took off or one just left alone is alive but no foe.
                prey = next((m for m in foes if choice is not None and m.unit_id == choice.unit), None)
                if choice is None or prey is None or run.clock() - decided_at >= DECIDE_SECONDS:
                    choice, decided_at = self.choose(world, foes, reachable, ground, view), run.clock()
                    prey = next(m for m in foes if m.unit_id == choice.unit)
                    decisions.fight(fight_looked, decided_at, prey.unit_id, choice.focal)  # DECISION_EVENTS
                made = cast.chained if GUARD_COUNTS_HELD else cast.casts
                if self.untouched(run, prey, made - counted):
                    choice = None  # left alone: the next look chooses among the rest
                    counted = made
                    if self.pursuing and prey.unit_id in self.nearing:
                        ended = f'Getting back in reach of {label(prey)}'  # a boss: the run's move comes first
                        break
                    if self.nap(run, FRAME):  # a frame before the next look: never a spin on one clock (BOUT_NAP)
                        ended = 'Yielded (a move was asked for)'
                        break
                    continue
                counted = made
                if self.unharmed(run, prey, max(harmed_at, cast.began), striking=again is not None and made > 0):
                    choice, harmed_at = None, run.clock()  # left alone: the rest gets its own NO_HARM_SECONDS
                    if self.nap(run, FRAME):  # a frame before the next look (BOUT_NAP)
                        ended = 'Yielded (a move was asked for)'
                        break
                    continue
                # The strike first, the mark and sigil under it once a cast is out: before it they held the first
                # strike back on half the fight starts (2026-10-10). The first cast flies unmarked.
                struck = again is not None and (cast.casts > 0 or run.clock() - cast.began >= FIRST_STRIKE_SECONDS)
                asked, ahead = None, False
                # A tier 5 Herald fight's landing, no mana burn: the build's FIRST skills before the press
                # (combat/pack.py HERALD_MARK_FIRST, the player's ruling of 2026-10-24 ~17:39; HERALD_MARK_NO_BURN)
                first = again is None and herald_pack.herald_mark_first(
                    run.clock(), reachable, foes, herald_pack.HERALD_MARK_NO_BURN and self.burning(world, foes)
                )
                if first and not AHEAD_BEFORE_PRESS:
                    asked = self.first_facts(run, world, foes, reachable, prey, aspect)
                    struck = ahead = any(
                        row.skill in herald_pack.FIRST and row.before_strike is not None and row.before_strike(asked)
                        for row in self.buffs.rows('fight')
                    )
                    first = ahead
                elif (again is not None or AHEAD_BEFORE_PRESS) and not struck:
                    # The demons' aggro before the first strike (`Buff.before_strike`: the designated one's mark), the
                    # rows that say so alone
                    asked = self.fight_facts(run, world, foes, reachable, prey)
                    struck = ahead = self.buffs.before_strike(asked)
                    first = False
                marked_first = False  # a FIRST skill cast before the press (HERALD_MARK_FIRST): the press at once after
                if struck:
                    # The build's casts under the strike in plan order; one that moved the pointer has the aim put
                    # back. With the safety's last prices of the build's draw (build.py `Draw`), while fresh
                    if asked is None:
                        asked = self.fight_facts(run, world, foes, reachable, prey)
                    rows = self.buffs.rows('fight')
                    if FIGHT_CAST_REACH and asked.cast_barred is not None:
                        if held_back != asked.cast_barred:
                            through = ' (instant casts in place go on)' if INSTANT_THROUGH else ''
                            LOG.info('Macro: fight casts held%s: %s', through, asked.cast_barred)
                        held_back = asked.cast_barred
                        # The instant casts in place go on with the strike (INSTANT_THROUGH)
                        rows = tuple(row for row in rows if INSTANT_THROUGH and row.instant)
                    for row in rows:
                        if ahead and not (row.before_strike is not None and row.before_strike(asked)):
                            continue
                        if first and row.skill not in herald_pack.FIRST:
                            continue  # HERALD_MARK_FIRST: the FIRST skills alone before the press
                        due = self.buffs.due(run, row, asked)
                        if due is None:
                            continue
                        self.casting = True
                        tried = self.buffs.cast(run, due, key_names, aspect)
                        if tried.touched:
                            if row.on != 'self':
                                aim.forget()
                            cast.excuse(run.clock())
                            self.buffs.resume(run, again)
                        marked_first = first and tried.cast  # none made (off the screen, died): the press goes on
                        if (FIGHT_CAST_REACH and self.paced(world)) or marked_first:
                            break  # one cast a look: the bout looks again (BOUT_REACH) before the next
                if marked_first:
                    # The mark's cast under way (HERALD_MARK_FIRST): the next look (the bout's reach asked) presses the
                    # strike under it at once; the game starts the held strike at the cast's end. No nap: the cast's
                    # key and its confirmation took a frame and more.
                    LOG.info(
                        'Macro: mark: first at the landing, %.2fs after it, before the strike (HERALD_MARK_FIRST)',
                        herald_pack.since_hop(run.clock()),
                    )
                    continue
                # A Herald's pack due in OMEN_LEAD s: the line goes through its spot (OMEN_STRIKE, `omen_focal`)
                omen = self.omen_focal(here, run.clock(), reachable)
                focal = choice.focal if omen is None else omen
                if omen is not None and omen != omen_said:
                    omen_said = omen
                    LOG.info('Macro: omen: the line through the Herald coming at (%.1f, %.1f), %.1f away', *omen,
                             math.dist(here, omen))  # fmt: skip
                if again is None and self.preaimed is not None and self.preaim_kept(run, here, focal, view):
                    aim.put(focal, here, run.actuator.keys.pointer())  # aimed during the flight (PREAIM)
                pointer, left_at = run.actuator.keys.pointer(), run.actuator.left_at
                if run.pad is not None:
                    # Controller mode: the client strikes its own target, turned toward the prey (macros/pad.py).
                    run.pad.steer(MONSTER_UNIT, prey.unit_id, here, (prey.x, prey.y), label(prey))
                elif aim.due(run.clock(), pointer, left_at, focal, here):
                    where = view.aim(here, focal)
                    if where is None:
                        ended = f'Nothing in view to aim at ({label(prey)} is off the screen)'
                        break
                    # The strike's place in the window taken again at the input (actuator.py LATE_BIND, binding.py)
                    binding.aim(run, where, scatter=(3, 3), bind=partial(binding.newest_strike, run, prey, focal, view))
                    aim.put(focal, here, run.actuator.keys.pointer())
                    labels_due = run.clock() + HOVER_SECONDS  # once the game has noted what is under it
                elif pointer == left_at and run.hovered is not None and run.clock() >= labels_due:
                    # The pointer stands where the macro left it: an item's label may be under it now.
                    held_prey = HELD_ON_BODY and holding(attack) == prey.unit_id
                    labels_due = run.clock() + (HELD_LOOK_SECONDS if held_prey else LABEL_SECONDS)
                    over = run.hovered()
                    if LABEL_CLEAR_AIM and labels.look(run, view, here, focal, choice.unit, over):
                        # One shift a look (hunting/labels.py): the bout goes on between two
                        aim.put(focal, here, run.actuator.keys.pointer())
                        labels_due = run.clock() + HOVER_SECONDS
                    elif over is not None and over[0] == ITEM_UNIT:
                        if not LABEL_CLEAR_AIM:
                            self.off_labels(run, view, here, focal)
                            aim.put(focal, here, run.actuator.keys.pointer())
                    elif held_prey and over is not None and over[0] == MONSTER_UNIT and over[1] != prey.unit_id:
                        self.onto_held(run, view, here, prey, world, focal, over[1])
                        aim.put(focal, here, run.actuator.keys.pointer())
                pressed = again is None
                if again is None:
                    run.say(f'{skill_name(attack.skill)} ({how}) at {label(prey)}, {life(prey)}')
                    hold = run.pad.hold(attack.skill) if run.pad is not None else run.actuator.hold(*held)
                    again = stack.enter_context(hold)
                    self.buffs.let_go = getattr(again, 'release', None)  # for a key under the strike
                    cast.began = self.pressed_at = run.clock()
                    self.casting = True  # the strike is held from here to the end of the fight
                # The mark decided in the look that pressed the strike, cast once its cast shows (MARK_WITH_PRESS)
                if (
                    MARK_WITH_PRESS
                    and pressed
                    and run.pad is None
                    and self.mark_with_press(run, world, foes, reachable, prey, key_names, aspect, again, cast)
                ):
                    aim.forget()
                if prey.unit_id != lined:
                    lined = prey.unit_id
                    LOG.info(
                        'Macro: line through %s, %s, %.1f away, focal (%.1f, %.1f), worth %.0f, pointer %s',
                        label(prey), life(prey), math.dist(here, (prey.x, prey.y)), *choice.focal, choice.worth,
                        run.actuator.keys.pointer(),
                    )  # fmt: skip
                watched |= {m.unit_id for m in reachable}
                if self.nap(run, FRAME):
                    ended = 'Yielded (a move was asked for)'
                    break
        down += len(watched - {m.unit_id for m in run.world().monsters})
        seconds = run.clock() - started
        LOG.info('Macro: fight (%s): %d casts seen in %.1fs, %d down; %s', how, cast.casts, seconds, down, ended)
        run.say(f'{ended}: {down} down in {cast.casts} casts')
        if cast.casts:
            run.say(f'Last minute: {self.score.line()}')  # the HUD card's standing line between fights

    # choice.py (`side_drop` is the Hunter's own: QUIET_HOLD)
    restock = choice.restock
    given_up_charm = choice.given_up_charm
    carry_one_swap = choice.carry_one_swap
    forget_given_up = choice.forget_given_up
    again = choice.again
    left = choice.left
    refused_potion = choice.refused_potion
    scarce = choice.scarce
    stay_by = choice.stay_by
    no_room = choice.no_room
    trips_by_hand = choice.trips_by_hand
    shack_goal = choice.shack_goal
    super_chest_goal = choice.super_chest_goal
    at_hand = choice.at_hand
    blockers = choice.blockers
    goal = choice.goal
    cleared = choice.cleared
    _forget_passed = choice._forget_passed
    _on_the_way = choice._on_the_way
    _clear_through = choice._clear_through
    agenda_cleared = choice.agenda_cleared
    agenda_target = choice.agenda_target
    agenda_chests = choice.agenda_chests
    agenda_chest = choice.agenda_chest
    goal_key = choice.goal_key
    taken_back = choice.taken_back
    went_for = choice.went_for
    goes_on = choice.goes_on
    on_the_way = choice.on_the_way
    walked_near = choice.walked_near
    teleport_reach = choice.teleport_reach
    pass_by = choice.pass_by
    rest_of = choice.rest_of
    next_room = choice.next_room
    run_mode = choice.run_mode
    carry_on = choice.carry_on
    nearby = choice.nearby

    # judging.py
    judge = judging.judge
    safety_priced = judging.safety_priced
    escorted = judging.escorted
    guard = judging.guard
    guarded = judging.guarded
    take_guard = judging.take_guard
    key_asks = judging.key_asks
    yielded_act = judging.yielded_act
    empty_mark = judging.empty_mark
    tell = judging.tell
    defer = judging.defer
    blocked = judging.blocked

    # moves.py
    dead_end = moves.dead_end
    looped_now = moves.looped_now
    barred = moves.barred
    pursue = moves.pursue
    way_time = moves.way_time
    stale = moves.stale
    give_up = moves.give_up
    priced_for = moves.priced_for
    advance = moves.advance
    warp_ready = moves.warp_ready
    operate = moves.operate
    pursue_once = moves.pursue_once
    known_level = moves.known_level
    seek = moves.seek
    go = moves.go
    own_teleport = moves.own_teleport
    worn = staticmethod(moves.worn)
    afoot = moves.afoot
    boss_step = moves.boss_step
    warp_hop = moves.warp_hop
    class_step = moves.class_step
    foot_step = moves.foot_step
    step = moves.step
    better_stand = moves.better_stand
    next_step = moves.next_step

    # sweep.py
    leaves = sweep.leaves
    gather = sweep.gather
    follow_on = sweep.follow_on
    sweep_to = sweep.sweep_to
    toward = sweep.toward
    asked_step = sweep.asked_step
    take_step = sweep.take_step
    quarry = sweep.quarry
