"""Mana-draining packs and the mana floor: a pack that burns mana is fought from range, and a fight whose mana falls
is left while Teleport still has its mana (rca/2026-10-21/mana-burn-findings.md).

The player, 2026-10-21 ~15:50: "another super-sketchy battle against bird that burned all mana, we were tanking most
of T5 herald damage without being able to hit (=low mana)"; the standing rulings: "make sure that we don't stuck or
die", "we must not die or we lose exp and our gear".

The fight of 15:46:06-33 (take 20261021T124558Z-25, Tower Cellar Level 5): a tier 5 Ghost Herald with Cold Enchanted,
Extra Fast and Mana Burn (monumod 18, 6, 25; its 14 minions carry 18, 6, 25 too: monumod.txt `xfer` 1) came to the
omen stand. The Ghosts ran in at 17.4-19.3 units a second (6.2 for the plain Ghosts of the take; the simulator's walk
for wraith1 is 5.5) and stood on the character 1.1 s after they showed. Mana went 730 -> 660 -> 644 -> 0 in 0.66 s
(15:46:13.42-14.08) by their hits, life 2907 -> 1383 by 15:46:17. Three "pack: keeping range" hops of ~10 units were
chosen inside the pack (combat/pack.py PACK_BACK 10, the rings 14-18 from the pack's centre, which was the character's
place); none landed (the strike's cast, then hit recovery, then no mana). The Rejuvenation at 15:46:17.2 filled the
mana to 740 and the next frame's hits took it to 0 again.

- BURN_RANGE: a pack with a mana-draining modifier (DRAINING) is fought from its keep range (`keep_of`): the melee
  reach plus what its walk (Extra Fast included) covers in one of the safety's steps, never under KEEP_LEAST. A member
  on the character within it brings a hop back (`why_back`, macros/safety.py `Safety.pack_back`) to a place that far
  from every member (`hop_spots`), and no move goes deeper into its reach (`intrudes`, `Pricing.move_price`).
- MANA_FLOOR: mana falling FALL_SHARE of the pool within FALL_SECONDS, or under RESERVE, with a hostile whose reach
  covers the character (`threatened`): the look's life budget is 0 and the leave is priced first (MANA_SAID; pursuit.py
  `arbitrate`); a Teleport needs TELEPORT_MANA (skills.txt, `skill_mana`), and the strikes kill nothing under
  STRIKE_MANA (macros/safety.py `Pricing.starved`).
- The omen stand with a way out: macros/hunting/base.py STAND_WAY_OUT.
- MANA_POTIONS: a proposal only (the findings' design); no code reads it.
"""

import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from functools import lru_cache

from inventory_tracking.combat.mechanics.life import leader
from inventory_tracking.combat.pack import (
    DEMON_HOLDS,
    HOP_TURNS,
    PACK_BACK,
    PACK_SEEN,
    SURROUND_COUNT,
    SURROUND_RADIUS,
    holders,
    in_pack,
    left_holding,
    on_character,
)
from inventory_tracking.combat.sim.monsters import GAME_RATE, REACH, Traits
from inventory_tracking.config import MERC_HEALING
from inventory_tracking.game.layout import LEADER_FLAGS, LYING_DEAD, MINION_FLAG, NO_OWNER
from inventory_tracking.levels.geometry import Point
from inventory_tracking.terror import danger


# Item 1 (2026-10-21, the player ~15:50: "a battle against bird that burned all mana, we were tanking most of T5
# herald damage without being able to hit"): a mana-draining pack is fought from range. False: a Mana Burn pack is
# any other (a Herald's by combat/pack.py alone), as before.
BURN_RANGE = True
# Item 3 (2026-10-21, the same words, "without being able to hit (=low mana)"; "we must not die"): the mana floor in a
# fight, the mana reserve in the safety's budget. False: mana is not looked at, as before.
MANA_FLOOR = True
# Item 4, a proposal (2026-10-21): mana potions in the belt (rca/2026-10-21/mana-burn-findings.md "Mana potions").
# The belt's layout is the player's call: off, and nothing reads it.
MANA_POTIONS = False
# The player's rulings of 2026-10-21 ~16:30, on the findings' questions:
# - "Yes, 18 for Extra Fast": an Extra Fast melee pack with no Mana Burn is kept at range as a draining one, FAST_KEEP.
#   False: such a pack is any other (a tier 4-5 Herald's by combat/pack.py alone), as before.
FAST_RANGE = True
# - "we can restore mana with rejuv potions, in a very scary moments, but make sure that we don't overuse it": a
#   Rejuvenation for the mana under the floor with a dangerous pack in reach and no Teleport out
#   (`rejuvenation_for_mana`; macros/hunting/moves.py `pursue`). False: a Rejuvenation for the life alone, as before.
MANA_REJUVENATION = True
# The player, 2026-10-21 18:59: "also, we're stopping attacking => no mana/hp leech => teleporting a lot and wasting
# time" (the T5 Herald pack of 11 Vile Witches, 18:53:50-18:58:59, take 20261021T155355Z-128: 39 leaves under the
# reserve at mana 1-39 of 740; the strike's hits leech the mana back, a Teleport leave spends TELEPORT_MANA, so the
# leave fed itself). True: the mana floor's leave only with a mana burner in reach (`drains`) or a burn seen (FALL_SHARE
# within FALL_SECONDS); under the reserve otherwise the fight goes on and the strike's leech refills the mana; a
# Rejuvenation for the mana only under one strike's cost (STRIKE_MANA), on MANA_REJUVENATION's terms (`short_of`).
# False: under the reserve with anything in reach, the leave, as from 16:15 to 19:10.
LEAVE_BURNERS_ONLY = True
# The player, 2026-10-21 ~18:45, on the tier 5 Herald of Gloams of 18:35 (Chain Lightning fliers, the Herald immune to
# the strike's physical): "do RCA for battle, model everything and find out the best way to act in such situation".
# A tier 4-5 Herald's pack of ranged elemental casters (terror/data/threats.json `ranged`, elemental over physical:
# Gloams, Vile Witches' kin) is kept at FAST_KEEP with BURN_HOPS hops, as an Extra Fast pack. The model calibrated on
# the take (rca/2026-10-21/herald-gloam-findings.md §5): 20 s within 6 of a Gloam and 4270 life lost as played,
# 0.8 s and 719 kept at 18 with the Herald marked; the take lost 189 a second within 6, 43 at 6-25. False: such a pack
# by combat/pack.py alone (PACK_BACK 10, PACK_HOPS 3), as before.
CASTER_RANGE = True
# The same fight: from 18:35:39 a far super healing potion was "worth its detour: 7.8 s against 12 s (belt healing 0)"
# with 7 rejuvenations on the belt; at 18:36:01-08 the run went 228-274 units off on it with the Herald at 66/128 and
# never came back (rca/2026-10-21/herald-gloam-findings.md §3-4). True: no far healing potion is fetched while a
# member of a live tier 4-5 Herald's pack is within PACK_SEEN of the character and the belt holds more rejuvenations
# than KEPT_REJUVENATIONS (`herald_fight`; macros/hunting/choice.py `scarce`): the drinker's rejuvenations are the life
# for that fight. False: the detour is priced alone, as before.
STAY_IN_HERALD_FIGHT = True
# The second tier 5 Herald of the Arachnid Lair (2026-10-21 20:31:17.14, take 20261021T172936Z-84): "Teleport toward
# full clear: the hostile by the Herald coming", 15 away, landed 7.6 from the Herald with 9 of its pack within 10 and 3
# within 5; 20:31:17.7-24.5 cost 3509 life (the player, ~20:34: "we had a quite bad positioning and suffered alot of
# damage"). The player's range ruling for these packs is 14-18, a hop back within PACK_BACK (combat/pack.py Q2). True:
# no move that is not a retreat or a dodge ends within PACK_BACK of a live member of a tier 4-5 Herald's pack and
# nearer it than it began (`pack_landing`, macros/safety.py `Pricing.move_price`, PACK_LANDED). False: as before.
PACK_LANDING = False
PACK_LANDED = "kept at range: a move into a Herald pack's PACK_BACK"
OMEN_LANDED = -1  # `pack_landing`: the move nears a pending Herald omen's spot, not a member

MANA_BURN = 25  # monumod.txt `manahit` (terror/tracker.py MODIFIER_NAMES 'Mana Burn')
EXTRA_FAST = 6  # monumod.txt `fast`
# The monster modifiers whose hits drain the character's mana. Mana Burn alone: the other TZ modifiers (strong, fast,
# curse, the enchantments, spectral hit, stone skin: terror/tracker.py TERROR_MODIFIERS) take life, not mana.
DRAINING = frozenset((MANA_BURN,))
# Extra Fast's walk against the simulator's (sim/monsters.py `Traits.speed`, which does not know the modifier): the
# take's Extra Fast Ghosts ran 17.4-19.3 units a second (the 9 fastest tracks over 0.3-0.6 s, 15:46:11.5-14.0) against
# 5.5 for wraith1's row; 18.7 / 5.5 = 3.4. (Dolls under Extra Fast: 21.9 against 15.5, combat/threats/dolls.py.)
EXTRA_FAST_PACE = 3.4
# Seconds from a look to the landing of the hop it chooses: the safety's own price of a Teleport (macros/safety.py
# `Pricing.move_price`: 0.31 transit + `SafetySettings.move_overhead` 0.5). The take: the hop chosen at 13.64, its key
# at 13.85, the cast refused until 14.27 (the strike's cast before it).
STEP_SECONDS = 0.81
# The least keep range of a draining pack: the Herald pack's "a Teleport back when anything is within 10" (the player,
# 2026-10-21 ~10:00; combat/pack.py PACK_BACK). H-B of 09:32:20 (rca/2026-10-21/herald-fight-findings.md §1.3), a Mana
# Burn pack of Bramble Hulks (no Extra Fast) held on the demons 8+ units off, lost nothing: it stays a fight.
KEEP_LEAST = PACK_BACK
# The hop's lengths from the character, best first, and the clearance beyond the keep range a hop is first looked for
# at: what the pack runs in a look and a half (18.7 x 0.2), so the landing is not inside the range by the next look.
# The take's Teleports flew 9-29 units (probe.log 15:46:00-37).
HOP_LENGTHS = (16.0, 20.0, 24.0, 12.0)
HOP_CLEAR = 4.0
# The keep range of an Extra Fast pack, draining or not: the player's 18 (2026-10-21 ~16:30), the take's Ghosts' 18.3
# rounded. One number for every type: the walk times EXTRA_FAST_PACE gives 12.3 (Bramble Hulk) to 41.8 (Devilkin,
# its walk 14 a second) over a step, and past the strike's reach (22) a pack is never struck.
FAST_KEEP = 18.0
# Hops out of one draining pack at most, a hop counted once however many looks choose it before it lands; then the
# plain safety (with the mana floor) decides. Ten, against the Herald pack's 3 (combat/pack.py PACK_HOPS): a pack
# that runs at 18.7 units a second catches a hop of ~20 in about a second, so the fight from range is hop, strike.
BURN_HOPS = 10
BURN_SAID = 'mana burn'  # the hop's reason after combat/pack.py BACK_SAID, for a draining pack
FAST_SAID = 'extra fast'  # the same for an Extra Fast pack that does not drain (FAST_RANGE)
CASTER_SAID = 'casters'  # the same for a tier 4-5 pack of ranged elemental casters (CASTER_RANGE)
# A plain drainer by type in a drain fight (combat/threats/drain_escape.py `typed_burners`, 2026-10-23): the hops'
# and the leave's landings keep clear of it; it makes no hop, bars no approach and names no pack (`triggers`)
LANDING_ONLY = 'kept clear'
LANDED = "kept at range: a move into the pack's reach"  # the bar on a move that goes deeper into a keep range
INTRUDE_SLACK = 1.0  # units nearer a burner inside its keep range a move may end before it is barred
# The keep range only against a pack whose threat warrants it (the coordinator, 2026-10-21 ~21:20, from the herald-left
# findings: 1623 of today's "no progress act fits the life budget" vetoes were LANDED, at full life against easy
# Heralds; at 21:07:23 a leftover minion at 11/128 kept the only progress move out; the player: "there were EASY
# heralds", "we were FULL health and full potions"). With THREAT_GATE: a member under LEFTOVER of its life is no
# burner; an Extra Fast or caster pack's members (not a draining one's: their threat is the mana, `drains`) are kept at
# range only under a threat (`threatening`): the life measured lost over the safety's pressure window
# (combat/survival.py `Pressure.lost`, of the most life) is FELT_SHARE or more, or the life is under UNHURT of the most,
# or the safety's own
# forecast of what they do in THREAT_SECONDS to the character standing at the nearest one's keep range (or here, if
# nearer) is THREAT_SHARE of its life or more. The forecast alone prices the Gloam's Chain Lightning pack low (21 of
# 1943 life arriving, 86 of 1585 pressed): the Gloam case is kept by the measured life (67% and 55% of the most;
# rca/2026-10-21/herald-gloam-findings.md). False: every such member is kept at range.
THREAT_GATE = True
LEFTOVER = 0.25  # of a member's life
THREAT_SECONDS = 2.0
THREAT_SHARE = 0.10  # of the character's life
FELT_SHARE = 0.10  # of the most life, lost over the pressure window (4 s)
UNHURT = 0.75  # of the most life
# A draining member is kept at range only under a threat to the mana too (DRAIN_GATE, with THREAT_GATE): in a tier
# 4-5 Herald's pack (`in_pack`), Extra Fast, the mana under MANA_SAFE of the pool, or a burn seen (`burnt`). The
# coordinator's JUMP_CLUSTER of 2026-10-21 23:10:48-23:11:09 (take 20261021T201038Z-35): a plain Dark Shaman unique
# (61) and its Dark Ones (22) with Spectral Hit, Mana Burn and Teleportation, standing 15-23 off, the mana 730-745 of
# 745 throughout: 31 hops, "safe approach" in, "every progress act is vetoed (kept at range)" out, 0 strikes in 21 s.
# False: every draining member is kept at range, as before.
DRAIN_GATE = True
MANA_SAFE = 0.6  # of the mana pool
# The player, 2026-10-22 ~18:12: "our treat assesments are totally wrong, I have seen game where we jumped around
# non-damaging, non-scary mobs for several minutes ... we weren't nearly any danger" (game cyberg64, Lower Kurast,
# 18:09:26-18:10:35, take 20261022T150918Z-79; rca/2026-10-22/lk-dance-findings.md): a champion pack of Hell Buzzards
# (monstats 112, vulture3) with Extra Fast, Mana Burn and Spectral Hit held the loop 18 off the chests for 69 s, 77
# Teleports, 37 vetoed retreats; life 2930 of 2930 throughout (5 points lost once), mana 723-745 of 745, the pack's hits
# priced 0 by the safety. `drain_threat` kept every Extra Fast drainer at FAST_KEEP whatever it could do. True: with
# the mana safe (DRAIN_GATE) an Extra Fast draining member outside a tier 4-5 Herald's pack is kept at range only under
# a threat, priced as an Extra Fast pack's (THREAT_GATE: the life felt, the life left, the forecast over THREAT_SECONDS
# at its keep range), or when that forecast, taken as mana burnt (a Mana Burn hit burns about what it hits for), passes
# the mana's spare over RESERVE (`spare`). Rejuvenations are not counted: they stay the scary moment's backstop
# (MANA_REJUVENATION, "don't overuse it"). A Herald's pack and a burn seen (`mana_safe` False) are kept as before.
# False: every Extra Fast drainer is kept at range, as from 2026-10-21 23:30.
MANA_BUDGET = True
# BURN_STALL_COMMIT (2026-10-24, rca/2026-10-24/manaburn-cycle-findings.md §1; the player: "exp/hour, never die"): take
# 20261024T132953Z-63, Maggot Lair Level 2, 16:31:13-33: a tier 5 Herald pack of 6 Sand Warriors (monstats 92, scarab2:
# Extra Fast, Mana Burn) in a walled side cave. The keep range (FAST_KEEP 18) against the strike's 22 left a band
# that walls shut: of 30 looks after the first hop 27 had no member with a clear shot within 22, every move with one
# ended inside 18 (LANDED), the arbiter retreated (pursuit.py: every progress act vetoed) 4 looks in a row out to
# 34-55 off, the safe approach came back and a member ran in at 17-25 units a second (the take) within one look: 24
# Teleports, 0 kills, life 2943 of 2943 and mana 725-745 throughout (no burn), until the run gave the pack up for 600 s
# (STILL_BUDGET). True: a pack whose triggers all drain by Mana Burn alone (no drainer by type within PACK_SEEN:
# their blows take 200-300 each, combat/threats/drain_escape.py MANA_ELEMENT) that has held the fight's progress off
# by LANDED for COMMIT_SECONDS (the bar again within STALL_GAP, no member DENTED or killed meanwhile: the arena's
# cut stood between the retreats, "waiting here: every way out costs more"), with the mana safe (DRAIN_GATE's
# `mana_safe`), no burn remembered and the life unhurt (UNHURT, nothing felt), is no longer kept at range
# (macros/safety.py `Safety.burn_stalls`, `kept_at_range`): it is fought as any tier 4-5 Herald pack (combat/pack.py
# PACK_BACK). The first burn seen, life felt or the mana under MANA_SAFE ends it for that pack for good. False: as
# before.
BURN_STALL_COMMIT = False
COMMIT_SECONDS = 5.0  # hunting/judging.py DANCE_SECONDS, macros/safety.py RANGE_STALL_SECONDS
STALL_GAP = 2.0  # seconds a stall lasts past the last look whose progress LANDED barred (the stands between them)
DENTED = 0.15  # of a member's life lost since the stall began: the fight goes on, no stall (a kill likewise)
COMMIT_SAID = 'kept at range with no progress: the mana burn keep range let go (BURN_STALL_COMMIT)'

# BURN_ENGAGE (2026-10-25, rca/2026-10-25/tactics/apply-burn.md; the coordinator's JUMP_CLUSTER of take
# 20261025T110846Z-131, the Throne 14:10:40-51: 7 jumps round (15087, 5018) within 22, 0 kills, "toward Lister the
# Tormentor" x5 against "keeping range: mana burn" x4, MARK_HOLDS_JUMPS live; door-pack-findings.md: the door opened,
# the keep range still held the fight off). The keep range's hop and the pursuit's jump in undo each other, and every
# drainer seen waived the mark's hold (macros/safety.py `real_threat`: "a drainer"). True: (a) a drainer waives the
# hold only within its keep range of the character or with the mana leaving; (b) while the demons hold a burner
# (`burn_held`: one within combat/pack.py DEMON_HOLDS of it) no progress jump lands inside a burner's keep range
# (ENGAGE_HELD; a walk, a retreat and a dodge are not barred); (c) while the demons hold a burner the keep range
# hops out once per Death Mark (combat/pack.py MARK): a second hop waits for a new mark, unless a drainer closes in
# (`closing_in`); with no mark keyed, or the burners unheld, the hops as before.
BURN_ENGAGE = True  # on 2026-10-25 ~17:15: gburn3 gate passed (apply-burn.md)
ENGAGE_HELD = 'the demons hold the burners: no jump into their keep range (BURN_ENGAGE)'


def burn_held(demons: Iterable[Point], burning: Sequence[Burner]) -> bool:
    """Whether a demon holds a burner (BURN_ENGAGE): one within combat/pack.py DEMON_HOLDS of a draining burner."""
    found = [b.at for b in burning if b.drains]
    return any(math.dist(d, at) <= DEMON_HOLDS for d in demons for at in found)


def drainer_close(here: Point, burning: Sequence[Burner]) -> bool:
    """A draining burner within its keep range of `here` (BURN_ENGAGE's real threat)."""
    return any(b.drains and math.dist(here, b.at) < b.keep for b in burning)


# skills.txt row 54 Teleport (the installed game's, pricing/raw/game-excel/skills.txt, read 2026-10-21): mana 24,
# lvlmana -1, minmana 1, manashift 8. Cost at skill level L: max(mana + lvlmana * (L - 1), minmana) * 2^manashift / 256.
# The character's Teleport level is not read: level 1's, the dearest (tests/.../combat/threats/test_manaburn.py checks
# the row against the installed game's when it is there).
TELEPORT_ROW = {'mana': 24, 'lvlmana': -1, 'minmana': 1, 'manashift': 8}
# The build's strike as the take shows it: the first cast at 15:46:12.1 took 740 -> 724.
STRIKE_MANA = 16.0
RESERVE_TELEPORTS = 2  # Teleports the reserve keeps: one out, one more if the pack follows
FALL_SHARE = 0.30  # of the pool lost within FALL_SECONDS: the mana is being burnt
FALL_SECONDS = 1.0
# A fall is counted over the looks read under the same most mana only (take 20261021T172936Z-84, 20:30:32: "mana:
# leaving: mana 511 of 526, 43% gone within 1 s", the pool's most gone 740 -> 526, no burn;
# rca/2026-10-21/arachnid-herald-2-findings.md §1). False: every look of the window counts, as before.
SAME_MOST = True
MOST_SLACK = 1.0  # points of most mana two reads may differ by and stay the same pool
MANA_SAID = 'mana: leaving'  # the leave's reason (pursuit.py `arbitrate` takes it first, as the pack's hop)
NO_TELEPORT = 'no mana for Teleport'  # the bar on a Teleport the mana does not pay for


def skill_mana(row: dict[str, int], level: int = 1) -> float:
    """A skill's mana cost at `level` from its skills.txt columns (`TELEPORT_ROW`'s)."""
    points = max(row['mana'] + row['lvlmana'] * (level - 1), row['minmana'])
    return points * 2 ** row['manashift'] / 256


TELEPORT_MANA = skill_mana(TELEPORT_ROW)
RESERVE = RESERVE_TELEPORTS * TELEPORT_MANA + STRIKE_MANA
PACK_FLAGS = LEADER_FLAGS | MINION_FLAG  # type flags of a pack's leader or minion (game/layout.py)
# MANA_REJUVENATION, not overused:
# - REJUVENATION_GAP: seconds since any Rejuvenation (the life drinker's, the healer's, this one): the safety's price
#   of a Rejuvenation (combat/harm.py `SafetySettings.rejuvenation_seconds`, 20) and about the take's regeneration
#   after the burn (15:46:17-33, 20-170 mana);
# - one a pack (its leader's unit, `ManaLook.key`), however long the fight;
# - never the last KEPT_REJUVENATIONS on the belt: the player's "keep at least 2 rev potions for user" (2026-10-13,
#   config.py MERC_HEALING `rejuvenation_reserve`, which the healer and the belt's restock keep too). The inventory's
#   are not counted: the belt is what a key drinks.
REJUVENATION_GAP = 20.0
KEPT_REJUVENATIONS = MERC_HEALING.rejuvenation_reserve
FRESH_LOOK = 0.5  # seconds a safety's look stands for the mana's state (hunting/judging.py looks every ~0.12 s)


def drains(mods: Iterable[int]) -> bool:
    """Whether a hostile with these modifiers drains mana by its hits (DRAINING)."""
    return any(mod in DRAINING for mod in mods)


def typed(txt: int) -> bool:
    """Whether a type drains mana by its own row (combat/threats/drain_escape.py MANA_ESCAPE, 2026-10-23)."""
    from inventory_tracking.combat.threats import drain_escape  # late: it builds on this module

    return drain_escape.MANA_ESCAPE and drain_escape.threat(txt)


@lru_cache(maxsize=1024)
def pace(txt: int, mods: tuple[int, ...]) -> float:
    """Units a second a hostile of type `txt` with `mods` closes in: its row's walk, EXTRA_FAST_PACE times under Extra
    Fast."""
    walk = Traits.of(txt).speed * GAME_RATE
    return walk * (EXTRA_FAST_PACE if EXTRA_FAST in mods else 1.0)


def reach_of(txt: int, mods: tuple[int, ...]) -> float:
    """Units within which a hostile strikes the character before the safety's next step lands: its melee reach plus
    its run over STEP_SECONDS."""
    return REACH + pace(txt, mods) * STEP_SECONDS


def keep_of(txt: int, mods: tuple[int, ...]) -> float:
    """The units a hostile kept at range is kept at: FAST_KEEP under Extra Fast, else its reach (`reach_of`), never
    under KEEP_LEAST."""
    if EXTRA_FAST in mods:
        return FAST_KEEP
    return max(KEEP_LEAST, reach_of(txt, mods))


@lru_cache(maxsize=1024)
def melee(txt: int) -> bool:
    """Whether a type strikes in melee (monstats `isMelee`, sim/monsters.py `Traits.melee`)."""
    return Traits.of(txt).melee


def fast_pack(txt: int, mods: Iterable[int], flags: int) -> bool:
    """Whether a hostile is of an Extra Fast melee pack (FAST_RANGE): Extra Fast, melee, and a pack's leader or minion
    (type flags: a Terror Zone gives every plain monster of a 'fast' zone Extra Fast, terror/tracker.py)."""
    return FAST_RANGE and EXTRA_FAST in mods and bool(flags & PACK_FLAGS) and melee(txt)


@lru_cache(maxsize=1024)
def caster(txt: int) -> bool:
    """Whether a type fights from range with elemental damage over physical (terror/data/threats.json, built from
    monstats by terror/build_threats.py: the Gloam's 1.9 elemental, 0 physical)."""
    row = danger.table().monsters.get(txt)
    return row is not None and row.ranged and row.elemental > row.physical


def caster_pack(txt: int, flags: int, tier: int) -> bool:
    """Whether a hostile is of a tier 4-5 Herald's pack of ranged elemental casters (CASTER_RANGE): the pack's leader or
    minion (type flags), its Herald's tier (combat/pack.py `in_pack`), a caster type (`caster`)."""
    return CASTER_RANGE and in_pack(tier) and bool(flags & PACK_FLAGS) and caster(txt)


@dataclass(frozen=True)
class Burner:
    """A hostile kept at range: its unit, place, keep range, whether it leads the pack, whether it drains mana (an
    Extra Fast pack's member does not: FAST_RANGE), and the kind of pack for the hop's reason (`said`)."""

    unit: int
    at: Point
    keep: float
    herald: bool = False
    drains: bool = True
    kind: str = BURN_SAID


def burners(hostiles: Iterable) -> list[Burner]:
    """The hostiles kept at range among those with `unit`, `at`, `txt`, `modifiers` and `flags` (combat/harm.py
    `Hostile`): the draining ones (BURN_RANGE), those of an Extra Fast melee pack (FAST_RANGE) and those of a tier 4-5
    pack of ranged elemental casters (CASTER_RANGE, kept at FAST_KEEP at least)."""
    found = []
    for m in hostiles:
        mods = tuple(m.modifiers)
        draining = BURN_RANGE and drains(mods)
        fast = fast_pack(m.txt, mods, m.flags)
        casting = caster_pack(m.txt, m.flags, getattr(m, 'tier', 0))
        if draining or fast or casting:
            keep = max(keep_of(m.txt, mods), FAST_KEEP) if casting else keep_of(m.txt, mods)
            kind = BURN_SAID if draining else FAST_SAID if fast else CASTER_SAID
            found.append(Burner(m.unit, m.at, keep, leader(m.flags), draining, kind))
    return found


def said(burning: Sequence[Burner]) -> str:
    """The kind of pack a hop is out of, for its reason: BURN_SAID when one of `burning` drains, else FAST_SAID when
    one is of an Extra Fast pack, else CASTER_SAID."""
    if any(b.drains for b in burning):
        return BURN_SAID
    return FAST_SAID if any(b.kind == FAST_SAID for b in burning) else CASTER_SAID


def triggers(burning: Sequence[Burner]) -> list[Burner]:
    """The burners that make a hop and bar an approach: all but the LANDING_ONLY ones."""
    return [b for b in burning if b.kind != LANDING_ONLY]


def key_of(burning: Sequence[Burner]) -> int | None:
    """The draining pack's name for the hop count: its leader's unit, else its lowest unit."""
    burning = triggers(burning)
    if not burning:
        return None
    leaders = [b.unit for b in burning if b.herald]
    return leaders[0] if leaders else min(b.unit for b in burning)


def pressing(here: Point, burning: Sequence[Burner], demons: Iterable[Point]) -> list[Burner]:
    """The burners within their keep range of the character that are on it, not on a demon that holds them (the
    Herald tactic's `on_character`: the player, 2026-10-21 ~09:40, "keep group on our daemon")."""
    held_by = holders(here, demons)
    return [b for b in burning if math.dist(here, b.at) < b.keep and on_character(here, b.at, held_by)]


def why_back(here: Point, burning: Sequence[Burner], demons: Iterable[Point]) -> str | None:
    """Why the character hops back from a draining pack now, or None: surrounded (combat/pack.py SURROUND_COUNT within
    SURROUND_RADIUS, on a demon or not), else a burner on it within its keep range."""
    burning = triggers(burning)
    close = [b for b in burning if math.dist(here, b.at) <= SURROUND_RADIUS]
    if len(close) >= SURROUND_COUNT:
        return f'{said(close)}: surrounded: {len(close)} of the pack within {SURROUND_RADIUS:.0f}'
    near = pressing(here, burning, demons)
    if not near:
        return None
    nearest = min(near, key=lambda b: math.dist(here, b.at))
    return (
        f'{said(near)}: {len(near)} of the pack on the character within {nearest.keep:.0f} '
        f'(the nearest at {math.dist(here, nearest.at):.1f})'
    )


def clear_of(spot: Point, burning: Sequence[Burner], beyond: float = 0.0) -> bool:
    """Whether `spot` is out of every burner's keep range (and `beyond` more)."""
    return all(math.dist(spot, b.at) >= b.keep + beyond for b in burning)


def hop_spots(here: Point, burning: Sequence[Burner], demons: Sequence[Point]) -> list[Point]:
    """Where to hop to, best first: HOP_LENGTHS from the character along the way from the pack's centre (of the burners
    within PACK_SEEN) through the demons that hold apart (the character where none does: combat/pack.py `hop_spots`),
    turned by HOP_TURNS; those HOP_CLEAR beyond every burner's keep range first, then those just clear of it
    (`clear_of`). A running pack closes a ring round its centre at once: the hop's length is the character's."""
    if not burning:
        return []
    near = [b.at for b in burning if math.dist(here, b.at) <= PACK_SEEN] or [b.at for b in burning]
    middle = (sum(p[0] for p in near) / len(near), sum(p[1] for p in near) / len(near))
    through = holders(here, left_holding(demons, jumped=True)) or [here]  # ALONG_ALL: the hop brings them along
    via = (sum(p[0] for p in through) / len(through), sum(p[1] for p in through) / len(through))
    if math.dist(via, middle) < 1e-6:
        via = here
    heading = math.atan2(via[1] - middle[1], via[0] - middle[0]) if math.dist(via, middle) > 1e-6 else 0.0
    wide, clear = [], []
    for turn in HOP_TURNS:
        angle = heading + math.radians(turn)
        for length in HOP_LENGTHS:
            spot = (here[0] + length * math.cos(angle), here[1] + length * math.sin(angle))
            if clear_of(spot, burning, HOP_CLEAR):
                wide.append(spot)
            elif clear_of(spot, burning):
                clear.append(spot)
    return wide + clear


def threatening(
    here: Point,
    hostiles: Iterable,
    burning: Sequence[Burner],
    priced: Callable[[list, Point], float],
    life: float,
    whole: float = 1.0,
    felt: float = 0.0,
    mana_safe: bool = False,
    spare: float = math.inf,
) -> list[Burner]:
    """The burners kept at range (THREAT_GATE): none under LEFTOVER of its life (`life`, a share, of the `hostiles` of
    the same unit); the draining ones; the others under a threat: `felt` (the life lost over the pressure window, a
    share of the most) FELT_SHARE or more, `whole` (the life, a share of the most) under UNHURT, or
    `priced(those hostiles, place)` (the life they take in THREAT_SECONDS from the character at `place`) THREAT_SHARE
    of `life` (the character's, in points) or more, `place` the point at the nearest one's keep range on the way to
    `here` (here, if nearer). With MANA_BUDGET and the mana safe, an Extra Fast drainer outside a Herald's pack is
    one of the others, and kept too when its forecast, as mana burnt, reaches `spare` (the mana over RESERVE).
    Off: `burning` as it is."""
    if not THREAT_GATE or not burning:
        return list(burning)
    by_unit = {m.unit: m for m in hostiles}
    live = [b for b in burning if getattr(by_unit.get(b.unit), 'life', 1.0) >= LEFTOVER]
    eased: set[int] = set()
    if DRAIN_GATE and mana_safe:  # `mana_safe`: the mana over MANA_SAFE and no burn seen (macros/safety.py)
        live = [b for b in live if not b.drains or drain_threat(by_unit.get(b.unit))]
        if MANA_BUDGET:
            eased = {b.unit for b in live if b.drains and b.unit in by_unit and fast_drainer(by_unit[b.unit])}
    rest = [b for b in live if (not b.drains or b.unit in eased) and b.unit in by_unit]
    if not rest or felt >= FELT_SHARE or whole < UNHURT:
        return live
    nearest = min(rest, key=lambda b: math.dist(here, b.at))
    gap = math.dist(here, nearest.at)
    if gap <= nearest.keep or gap < 1e-6:
        place = here
    else:
        share = nearest.keep / gap
        place = (nearest.at[0] + (here[0] - nearest.at[0]) * share, nearest.at[1] + (here[1] - nearest.at[1]) * share)
    if priced([by_unit[b.unit] for b in rest], place) < THREAT_SHARE * life:
        kept = [b for b in live if b.drains and b.unit not in eased]
        burning_too = [b for b in live if b.unit in eased]
        if burning_too and priced([by_unit[b.unit] for b in burning_too], place) >= spare:
            kept = [b for b in live if b.drains]  # their hits would burn the mana past its spare (MANA_BUDGET)
        return kept
    return live


def drain_threat(m) -> bool:
    """Whether a draining hostile (with `tier`, `modifiers`; None: unknown) is a threat to the mana while the mana is
    safe (DRAIN_GATE): one of a tier 4-5 Herald's pack, or Extra Fast."""
    if m is None:
        return True
    return in_pack(getattr(m, 'tier', 0)) or EXTRA_FAST in tuple(getattr(m, 'modifiers', ()))


def fast_drainer(m) -> bool:
    """Whether a draining hostile (with `tier`, `modifiers`) is kept at range by Extra Fast alone (MANA_BUDGET): Extra
    Fast and not of a tier 4-5 Herald's pack."""
    return EXTRA_FAST in tuple(getattr(m, 'modifiers', ())) and not in_pack(getattr(m, 'tier', 0))


def committable(here: Point, burning: Sequence[Burner], hostiles: Iterable) -> bool:
    """BURN_STALL_COMMIT: whether the pack kept at range may be fought in: its triggers (`triggers`) all drain by the
    Mana Burn modifier (BURN_SAID) and no drainer by type (combat/threats/drain_escape.py `threat`) is within PACK_SEEN
    of the character."""
    found = triggers(burning)
    if not found or any(b.kind != BURN_SAID for b in found):
        return False
    from inventory_tracking.combat.threats import drain_escape  # late: it builds on this module

    return not any(drain_escape.threat(m.txt) and math.dist(here, m.at) <= PACK_SEEN for m in hostiles)


def committed(burning: Sequence[Burner], key: int | None) -> list[Burner]:
    """The burners kept at range once the pack `key` is fought in (BURN_STALL_COMMIT): all but its Mana Burn triggers
    (the landings still keep clear of the LANDING_ONLY ones); `burning` as it is when `key` names no pack of it."""
    if key is None or key_of(burning) != key:
        return list(burning)
    return [b for b in burning if b.kind != BURN_SAID]


def intrudes(here: Point, spot: Point, burning: Sequence[Burner]) -> Burner | None:
    """The burner a move from `here` to `spot` goes deeper into the keep range of (ends inside it, over INTRUDE_SLACK
    nearer than here), or None."""
    return next(
        (
            b
            for b in triggers(burning)
            if math.dist(spot, b.at) < b.keep and math.dist(spot, b.at) < math.dist(here, b.at) - INTRUDE_SLACK
        ),
        None,
    )


def mana_of(stats: Iterable[tuple[int, int]]) -> tuple[float, float] | None:
    """The character's (mana, most mana) in whole points from its stats (itemstatcost 8 and 9, 8 fraction bits:
    takes/record.py VITAL_STATS); None when unread or with no pool."""
    found = dict(stats)
    if 9 not in found or found[9] <= 0:
        return None
    return found.get(8, 0) / 256, found[9] / 256


def fell(history: Iterable[tuple[float, ...]], now: float, mana: float, most: float | None = None) -> float:
    """Points the mana fell within FALL_SECONDS before `now`: the most it held then, less `mana`. History entries are
    (clock, mana) or (clock, mana, most mana); with SAME_MOST and `most` given, only those read under the same most
    mana count (a pool that shrank is no burn)."""
    held = [
        entry[1]
        for entry in history
        if 0.0 <= now - entry[0] <= FALL_SECONDS
        and not (SAME_MOST and most is not None and len(entry) > 2 and abs(entry[2] - most) > MOST_SLACK)
    ]
    return max(0.0, max(held, default=mana) - mana)


def threatened(here: Point, hostiles: Iterable) -> list:
    """The hostiles (with `at`, `txt`, `modifiers`) whose reach covers the character: a burner's keep range, another's
    `reach_of`."""
    found = []
    for m in hostiles:
        mods = tuple(m.modifiers)
        reach = keep_of(m.txt, mods) if drains(mods) or typed(m.txt) or EXTRA_FAST in mods else reach_of(m.txt, mods)
        if math.dist(here, m.at) < reach:
            found.append(m)
    return found


def mana_low(history: Iterable[tuple[float, ...]], now: float, mana: float, most: float, near: int) -> str | None:
    """Why the mana floor is crossed, in words, or None (MANA_FLOOR off, nothing within reach, the mana well): fallen
    FALL_SHARE of the pool within FALL_SECONDS, or under RESERVE, with `near` hostiles in reach."""
    if not MANA_FLOOR or near <= 0 or most <= 0:
        return None
    lost = fell(history, now, mana, most)
    if lost >= FALL_SHARE * most:
        return f'mana {mana:.0f} of {most:.0f}, {lost / most:.0%} gone within {FALL_SECONDS:g} s, {near} in reach'
    if mana < RESERVE:
        return f'mana {mana:.0f} of {most:.0f}, under the reserve {RESERVE:.0f}, {near} in reach'
    return None


def pack_landing(here: Point, spot: Point, hostiles: Iterable, omens: Iterable[Point] = ()) -> int | None:
    """The unit of the live tier 4-5 Herald pack member (`in_pack`; with `unit`, `at`, `tier`) a move from `here` to
    `spot` ends within PACK_BACK of and over INTRUDE_SLACK nearer than here; OMEN_LANDED for a pending Herald omen's
    spot (`omens`, combat/pack.py: its pack shows there within 5 s) so neared; None else (PACK_LANDING off: None).
    Take 20261021T172936Z-84, 20:31:17.14: the Teleport "toward full clear: the hostile by the Herald coming" landed
    7.6 from the omen's spot 0.4 s before the pack showed round it, 9 within 10 (rca/2026-10-21/arachnid-herald-2)."""
    if not PACK_LANDING:
        return None
    for m in hostiles:
        if not in_pack(m.tier):
            continue
        gap = math.dist(spot, m.at)
        if gap < PACK_BACK and gap < math.dist(here, m.at) - INTRUDE_SLACK:
            return m.unit
    for omen in omens:
        gap = math.dist(spot, omen)
        if gap < PACK_BACK and gap < math.dist(here, omen) - INTRUDE_SLACK:
            return OMEN_LANDED
    return None


def burnt(history: Iterable[tuple[float, ...]], now: float, mana: float, most: float) -> bool:
    """Whether a burn is seen: the mana fell FALL_SHARE of the pool within FALL_SECONDS (`fell`)."""
    return most > 0 and fell(history, now, mana, most) >= FALL_SHARE * most


def leave_for(low: str | None, burn: bool, drainers: int) -> str | None:
    """The mana floor's leave (`mana_low`'s why), or None: with LEAVE_BURNERS_ONLY only while a burn is seen (`burnt`)
    or `drainers` mana burners are in reach; else under the reserve the strike goes on, its leech the way back."""
    if low is None or not LEAVE_BURNERS_ONLY:
        return low
    return low if burn or drainers > 0 else None


def short_of(leave: str | None, low: str | None, mana: float) -> str | None:
    """The mana's want a Rejuvenation may answer (`rejuvenation_for_mana`): the leave's why; with LEAVE_BURNERS_ONLY and
    no leave, the floor's why only under one strike's cost (STRIKE_MANA: the strike, and so its leech, cannot go on)."""
    if leave is not None or not LEAVE_BURNERS_ONLY:
        return low
    return low if mana < STRIKE_MANA else None


@dataclass(frozen=True)
class ManaLook:
    """The mana's state at one safety look (macros/safety.py `Safety.mana_look`): the mana and its pool, why the floor
    is crossed (None: it is not), the dangerous hostiles in reach and their pack, and whether the act chosen is a
    Teleport out (a leave that can be made)."""

    at: float
    mana: float
    most: float
    why: str | None
    danger: int
    key: int | None
    teleport_out: bool


def dangerous(here: Point, hostiles: Iterable) -> tuple[int, int | None]:
    """The dangerous hostiles whose reach covers the character (`threatened`): draining ones and a tier 4-5 Herald's
    pack (combat/pack.py `in_pack`); how many, and their pack's name (a leader's unit, else the lowest unit)."""
    found = [m for m in threatened(here, hostiles) if drains(m.modifiers) or typed(m.txt) or in_pack(m.tier)]
    if not found:
        return 0, None
    leaders = [m.unit for m in found if leader(m.flags)]
    return len(found), leaders[0] if leaders else min(m.unit for m in found)


def herald_fight(here: Point, monsters: Iterable, rejuvenations: int) -> int:
    """The members of a live tier 4-5 Herald's pack within PACK_SEEN of the character (`monsters`: game/records.py
    `Monster`s) while the belt holds more than KEPT_REJUVENATIONS rejuvenations; 0 with STAY_IN_HERALD_FIGHT off."""
    if not STAY_IN_HERALD_FIGHT or rejuvenations <= KEPT_REJUVENATIONS:
        return 0
    return sum(
        1
        for m in monsters
        if in_pack(m.tier)
        and not m.ally
        and m.owner == NO_OWNER
        and m.mode not in (0, LYING_DEAD)
        and math.dist(here, (m.x, m.y)) <= PACK_SEEN
    )


def rejuvenation_for_mana(
    look: ManaLook | None, now: float, rejuvenations: int, since: float, drunk: Iterable[int]
) -> str | None:
    """Why a Rejuvenation is drunk for the mana now, in words, or None (MANA_REJUVENATION). A scary moment: the mana
    floor crossed (`mana_low`) with a dangerous pack in reach (`dangerous`) and no Teleport out chosen (the leave is
    not possible, or a walk is not enough). Not overused: REJUVENATION_GAP seconds since any (`since`), one a pack
    (`drunk`: the packs one went to), never the last KEPT_REJUVENATIONS (`rejuvenations` on the belt). `look`: the
    safety's, no older than FRESH_LOOK."""
    if not MANA_REJUVENATION or look is None or not 0.0 <= now - look.at <= FRESH_LOOK:
        return None
    if look.why is None or look.danger <= 0 or look.teleport_out:
        return None
    if rejuvenations <= KEPT_REJUVENATIONS or since < REJUVENATION_GAP or look.key in set(drunk):
        return None
    out = 'no Teleport out' if look.mana < TELEPORT_MANA else 'the leave is a walk'
    return (
        f'{look.why}; {look.danger} of a dangerous pack in reach, {out}; {rejuvenations} rejuvenations on the belt, '
        f'{KEPT_REJUVENATIONS} kept'
    )
