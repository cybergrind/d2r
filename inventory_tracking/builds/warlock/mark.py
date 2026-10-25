"""Death Mark (skills.txt 375): what it buys and when the fight casts it (rca/2026-10-14/death-mark.md).

The player, 2026-10-14: "death mark is skill that forces daemons to attack and lowers enemy defence"; "a very
effective mechanism that allow to distract/re-aggro enemies". The character's demons (none: it cannot be cast)
teleport to the marked monster (MARK_JUMP, MARK_BESIDE), the monsters round it turn to them (MARK_TURNS of the
pack within MARK_PACK), and the mark takes flat points off each element of a hit and cuts its defence.

A mark is worth what it draws off the character (the safety's harm, macros/safety.py `Safety.weigh`) and what it
adds to the strike (`gain`), against one volley of blades (MARK_CAST_SECONDS). A Herald first; then a monster immune to
magic (IMMUNE_TO, the player 2026-10-20: the demons kill what the magic cannot); a leader or boss before a plain
monster ("on the leader / most dangerous monster"), whatever the price unless it costs life under pressure
(MARK_LEADERS, 2026-10-20); never with no demon, never on trash (TRASH_CASTS), never again while a mark lasts; a
leader passed over is named once with why (SAY_PASSED); a mark that did not take is cast again (MARK_RECASTS). The
measures behind each number:
builds/history/warlock-mark.md; rca/2026-10-20/leader-not-marked-findings.md.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace

from inventory_tracking.builds.warlock.echoing_strike.attack import BLADES_A_CAST, ECHOING_STRIKE_ATTACK
from inventory_tracking.builds.warlock.echoing_strike.damage import companion_table, damage_data
from inventory_tracking.builds.warlock.skills import DEATH_MARK
from inventory_tracking.combat import pack as herald_pack, revivers
from inventory_tracking.combat.harm import SafetySettings
from inventory_tracking.combat.mechanics.life import rank_share
from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.policy import Observation, observe
from inventory_tracking.combat.sim import casters as rules
from inventory_tracking.combat.sim.casters import hit_chance
from inventory_tracking.combat.stance import CAST_SECONDS
from inventory_tracking.combat.threats import dolls
from inventory_tracking.common import LOG
from inventory_tracking.game.layout import DEFILER_CLASS, MAGIC_RESIST, MONSTER_RESISTS
from inventory_tracking.game.records import Monster, World
from inventory_tracking.macros.build import BuffFacts, Draw, DrawPrice
from inventory_tracking.macros.goals import is_boss
from inventory_tracking.macros.skills import skill_name
from inventory_tracking.macros.travel import label, life
from inventory_tracking.native.layout import BATTLE_ORDERS_SKILL, HIRELING_CLASS_ID
from inventory_tracking.takes.timeline import GAME_RATE


_MARK = damage_data()['death_mark']
# The mark at the character's level (data/damage.json `death_mark`, read off marked monsters' stats in the takes).
MARK_POINTS = float(_MARK['points'])  # points more an element of a hit takes
MARK_ELEMENTS = 1  # elements of a blade's hit: the weapon's physical damage (Echoing Strike has no EType)
MARK_SECONDS = int(_MARK['frames']) / GAME_RATE  # 125 + 13 x (level - 1) frames: 12.28 s at 15 (11.76 s at 14)
MARK_DELAY = 20 / GAME_RATE  # skills.txt localdelay: the skill cannot be cast again sooner
MARK_DEFENCE = float(_MARK['defence'])  # the marked monster's defence falls by this (stat 31, -540 at level 15)
# What a cast costs the strike: one volley of its blades (rca/2026-10-14/death-mark-engage.md §3).
MARK_CAST_SECONDS = 0.37
MARK_JUMP = 0.28  # seconds from the key until the demons land (the median of 409 jumps; quartiles 0.24, 0.29)
MARK_BESIDE = 2.8  # units from the marked monster a demon lands (the median of 910 landings; quartiles 2.0, 5.2)
MARK_REACH = math.inf  # units: no cap showed (Param9 "teleport distance" 38; 11 of 11 demons farther jumped)
# Never on a monster this many casts kill, whatever the price says (the player, 2026-10-14: "never on trash").
TRASH_CASTS = 2
# Seconds before a mark moves to another live monster, so near-equal prices do not trade the demons back and forth.
MARK_AGAIN = 2.0
HELD = 3.0  # units beyond MARK_BESIDE within which a demon is taken to strike a monster already: no gain of its own
PACE = SafetySettings().strike_spread[len(SafetySettings().strike_spread) // 2]  # the strikes' kill time over forecast
# What a mark turns: the monsters within MARK_PACK of it (rca/2026-10-14/death-mark.md §2: 8% at the character after
# a mark against 66% round an unmarked elite).
MARK_PACK = 8.0
MARK_TURNS = 0.66 - 0.08
# The player, 2026-10-20 ~14:31: "right now we're not using mark death for magic immune mobs. but our damage is mostly
# magic, so we need to engage our daemon even for regular mobs when they do have magic immunity (for WarlockAA
# build!)". A monster in reach immune to an element of IMMUNE_TO (its resistance as read live, game/records.py
# `Monster.resists`) is a reason of the one designation (DESIGNATED_MARK): after a Herald and before any other, the
# trash rule aside; while its mark lasts the mark moves off it only to a Herald or under pressure (`DrawPrice.pressed`).
# MARK_IMMUNE (on since 2026-10-20) retired into it 2026-10-22.
# The elements whose immunity sends the demons. Magic: the Hex: Purge explosions the blades set off (skills.txt 389,
# EType mag), with the character's magic mastery and pierce (stats 357/358: 23% and 15% in the take of 2026-10-20
# 10:32). The blade itself is weapon damage, physical (skills.txt 388: SrcDam 116, MinDam/MaxDam, no EType), with the
# gear's cold (stats 54/55). Not physical: the demons strike physical too (monstats A1MinD/A1MaxD).
IMMUNE_TO = (MAGIC_RESIST,)
# The player, 2026-10-20 ~15:03: "we were fighting against pack with uniq leader, but we focused rest of the pack, not
# leader and never death marked the leader so our daemon was still all the time" (rca/2026-10-20/
# leader-not-marked-findings.md). That game's bound demon was an Urdar (189), a class data/damage.json `companions`
# has no measure of (the Pit Lord 361, the mercenary and the Defiler only): `gain` counted the Defiler's 375 points a
# second alone, and a mark on a Thorned Hulk leader came to 0.14 s of the fight against the 0.37 s cast (refused at
# 15:01:23 and 15:02:00). True: a demon of an unmeasured class strikes at the measured bound demon's rate (BOUND_DEMON)
# times its monstats A1 mean damage over that one's (`demon_rate`). False: it adds nothing, as before.
PRICE_ANY_DEMON = True
BOUND_DEMON = 361  # the bound demon data/damage.json measures (a Pit Lord, 72 points a frame)
# The same words: a pack's leader or a boss in reach (`ranked`: the trash rule aside) is marked whenever a demon is out
# and one is to be sent (not every one within MARK_BESIDE + HELD of it already), after an unmarked Herald and a monster
# immune to the magic; the safety's price stops it only where the cast costs life while holding is over the life
# budget, as for an immune one. A mark lasting on plain monsters only moves to such a leader (MARK_AGAIN after).
# False: the safety's price decides for a leader too (the rule of 2026-10-14). On since 2026-10-20 ~19:00, the
# player's answer: "ok, recast. pack leader/herald first" (the goldens recorded again: the leaders the price refused
# are marked; rca/2026-10-20/mark-recast-leaders-findings.md).
MARK_LEADERS = True
# The player, 2026-10-20 ~18:45 (asked whether to cast again when the mark did not take): "ok, recast". The mark as
# the client holds it is state 212 (states.txt `death_mark`) in the monster's state words (game/layout.py STATE_RUN,
# states 0-255 from the first word): over the stats events of 2026-10-20's takes it is on in 1,822 of the 1,831 with
# stat 34 < 0 (the mark's flat points) and off in 73,021 of the 73,025 without. After the key it shows on the target in
# a median 0.43 s (p95 0.60 s, the latest of 283 at 0.80 s): not shown MARK_SHOWS s after the key, it did not take, and
# the mark is cast again, MARK_RECASTS times a monster at most (macros/buffs.py `Buffs.settle`). 0: said, not cast
# again (rca/2026-10-20/mark-recast-leaders-findings.md).
MARK_STATE = 212
MARK_SHOWS = 0.8
MARK_RECASTS = 2
# A leader or boss in reach the mark passes over is named once, with why (`mark_passed`): the silent "never marked" of
# elite 397 at 15:01:12 (trash by the strike's table, no line said). False: bosses struck down to trash only.
SAY_PASSED = True
# One designation (the player, 2026-10-22 ~19:58: "we must read mobs immunities and must correctly use our minions to
# handle immune mobs"; ~20:10: "we know who must be death marked / we apply DM when designated mob doesn't have it / we
# clear DM when we're teleporting with mobs / we re-apply DM because we have designated mob active"; "if designated
# minion has died -> DM disappears from it"). One owner, `designate` (`DESIGNATION`), holds the monster the demons must
# hold and why: a Herald (a doll Herald too: its blast kills, the demons take its aggro), then a monster immune to the
# magic (IMMUNE_TO), then the leader the strike holds (echoing_strike/attack.py HOLD_LEADER), then a leader or boss the
# mark fits (`ranked`, `leader_first`); in a tier 4-5 Herald pack the pack's member (`pack_designated`). It changes
# only when the one held dies or leaves reach, loses its reason, a higher reason comes in reach, or MARK_RECASTS keys
# took nowhere on it; each change is said with its reason. Its mark is due while the demons do not hold it
# (`aggro_held`): no mark of the character's lasts on it, or a Teleport or Blade Warp of REMARK_HOP units or more landed
# after the mark's key with a demon taken along (within TAKEN_ALONG of the character, combat/pack.py `HOP`, fed by
# every jump: macros/travel.py `Travel.jump`, macros/teleport.py), and the demons are not back on it: the state word
# outlives the hop, so it is not asked then (the takes of 2026-10-21/22, 137 hops under a lasting mark: the demons
# stood a median 2.8 units off the marked monster before the hop and 21 units one second after; state 212 still on in
# 18 of the 24 reads after a hop; a mark again within 3 s after 1 of the 137:
# rca/2026-10-22/immune-mark-findings.md). The mark is cast once at the landing, when the casts are allowed
# (macros/hunt.py FIGHT_CAST_REACH, CAST_REACH, one a look), ahead of the bout's first strike (`mark_ahead`), after the
# rebuff's Battle Orders at a rebuff landing (REBUFF_CAST_WAIT). It replaces REMARK_AFTER_HOP (off), MARK_HELD_LEADER
# (off), HELD_KEEPS_MARK (off), REMARK_AFTER_REBUFF (on: a rebuff landing is a hop), MARK_IMMUNE (on: a reason) and
# macros/hunt.py DOLL_HERALD_MARK (on: `mark_ahead`), retired 2026-10-22. False: the mark as before the model
# (`target_before`, the retired switches at their last values), kept for the arena's off-and-on measure only.
DESIGNATED_MARK = True
REMARK_HOP = 4.0  # units: a shorter jump takes no demon off its monster
TAKEN_ALONG = herald_pack.TAKEN_ALONG  # units: the allies within it come along on a Teleport (95-100% of 312 hops)
# The pack's re-aggro with nobody designated (2026-10-24, rca/2026-10-24/aggro-findings.md; the player, ~11:30:
# "heralds/packs loose their aggro on minions and daemon/merc are staying not active for some time after teleport ... if
# we handle aggro correctly, we would be agle to handle most of situations"; 2026-10-21: "if you reposition - re-aggro
# again"). The takes of 2026-10-24 09:53-11:32: of 872 fight hops never marked again before the next hop or 5 s, 774 had
# no monster designated (a plain pack: no Herald, no immune, no leader in reach), so no mark was due after the jump and
# the demons stood 9-11 units off the pack for seconds; where a mark went at the landing the demons struck at 1.1 s
# (p50), where none did at 3.3 s, 27 of 60 not within 5 s. True: with nobody designated, after a jump of REMARK_HOP or
# more that took a demon along (under REAGGRO_AFTER s ago, no mark keyed since), or with REAGGRO_PRESS hostiles on the
# character (combat/pack.py `on_character`, within PACK_BACK) while no demon strikes, the member in reach that outlives
# TRASH_CASTS casts with the most of the pack within MARK_PACK is designated (REAGGRO_RANK, the lowest), its mark due at
# once and again after each jump, as any designated one's. False: nobody, as before. On 2026-10-24 ~12:20, gated
# (480 plays, 0 deaths, T5 Herald unchanged, fane-20 kills 15.4 -> 16.4, marks up).
REAGGRO_PACK = True
REAGGRO_AFTER = 4.0  # seconds after a jump landed within which the pack's re-aggro is designated
REAGGRO_PRESS = 2  # hostiles on the character that designate it without a jump
REAGGRO_SAID = "the pack's re-aggro: the demons are off it"
# A jump frees the pack's order (2026-10-24 ~20:10, rca/2026-10-24/dm-latency-findings.md §8; the player's ruling
# ~17:39: "when we're repositioning for re-aggro against T5 heralds, the first things we need to do - drop off aggro
# from us == DM"). The 10 Herald marks after a landing that went after the strike, 18:49-19:31: at 18:52:58.418,
# 19:19:16.169 and 19:30:41.458 a mark still counted as lasting on a member out of the strike's reach (25.0, 29.6, 24.0
# off; two of them had gone onto a neighbour, "did not take", settled only at the second look), and `pack_target`
# gives none while a member's mark lasts unless the pack presses the character, so no member in reach was designated
# and the strike went first. True: after a jump that took the demons along (`dragged`: REMARK_HOP or more, under
# REAGGRO_AFTER s ago, after the last key), a mark lasting on a member does not hold the pack's order back: the free
# members in reach are chosen as with none. False: as before.
PACK_HOP_FREES = False
# No mark again on a cursed monster (2026-10-24 ~20:15, dm-latency-findings.md §10; rca/2026-10-24/dm-truth-findings.md
# §3): of 73 first keys at T5 Herald landings 18:49-20:00, 26 hit a monster the curse was still on (state 212: the
# cast changed nothing in the game's state), 22 of them `aggro_lost`'s "its mark again" after a jump, judged from the
# demons' places alone. Whether such a cast sends the demons again is not known from the takes (I). True: no mark
# again while the monster's state words show the curse (`mark_shows`; BuffFacts.states). False: as before.
REMARK_UNSHOWN = False
# The doll Herald first in its pack (2026-10-24; the player's ruling of 2026-10-22: a doll Herald, Death Mark aggro on
# it, then kill it very fast). Take 20261024T084322Z-86, 11:44:20-30: the tier 5 Undead Stygian Doll Herald (unit
# 3904379104) stood 11-20 units off with 2-7 members within 4 of it; `pack_target` puts a member no body covers
# (`covered`) before the Herald, so the first mark (11:44:23.7) went on a member and the Herald's only at 11:44:39.
# True: a tier 4-5 pack's doll Herald in reach is designated before the pack's order and before a member whose mark
# lasts (`doll_herald_designated`): marked at once, again after a jump took the demons off it, MARK_AGAIN after the last
# key while another member's mark lasts; a key that took nowhere on it MARK_RECASTS times hands it back to the pack's
# order. False: the pack's order, as before. On 2026-10-24 ~13:25, gated: doll cut kills +13%, leaders 2.45 -> 3.55,
# same low; the 8 standard scenes identical to REAGGRO_PACK alone (20 seeds).
DOLL_HERALD_FIRST = True
# Any tier 4-5 Herald first in its pack (2026-10-24; the player, ~13:30: "we're jumping too close, and not DM our daemon
# into T5 herald. several times in a row"). Take 20261024T102258Z-116, 13:23:31-13:24:04: the tier 5 Herald (unit
# 809272624, class 634) stood 19 units off with 10 members within 4 of it; `pack_target` ranks a member no body covers
# before the Herald, so the Herald's first mark went out at 13:24:02.8, 1.7 s before it died. The 2026-10-21 Q1 ruling
# ("the nearest pack member that can be clicked, the Herald when it can be, no lock-out") names no cover rank: the
# Herald first whenever it can be clicked fits it and the 13:30 words. True: `doll_herald_designated` takes any tier 4-5
# Herald in reach, not only a doll. False: the doll Herald only (DOLL_HERALD_FIRST), as before.
HERALD_FIRST = False
# R1's triggers (combat/pack.py DM_AFTER_EVERY_MOVE, `hard_fight`; 2026-10-24 ~20:30; the stopwatch's "pet stand",
# .agents/skills/d2-loop-watch/tools/stopwatch.py: a demon within 4.5 of the character with a live hostile within 30,
# today's T5 fights 271 stands, p50 1.20 s, p90 4.45 s, in 119 a hostile with the mark lived within 30 all along: a
# jump takes the demons off the marked one and only a fresh cast sends them, 20:18:00.712 the same unit's recast moved
# them 0.28 s after it). `move_reason`: a jump of REMARK_HOP or more landed under MOVE_AFTER s ago with no key since,
# or a demon idles (no hostile within PET_CONTACT) within PETS_WITH_US of the character PETS_AGAIN s or more after
# the last key.
PETS_WITH_US = 4.5  # units (the stopwatch's pet stand; the player's ~4)
# units: a demon with no hostile this near strikes none (MARK_BESIDE and a margin). Not its mode: take -71 at
# 20:18:42.417 the bound demon (189) stood 0.1 off the character in mode 1 and the War Defiler (744) in mode 8, both
# 11.6 or more off the nearest live hostile
PET_CONTACT = 3.0
PETS_AGAIN = 1.2  # seconds: the mark's delay (0.8), the demons' jump (MARK_JUMP 0.28) and a look
MOVE_AFTER = REAGGRO_AFTER  # seconds after a landing its mark is still owed
MOVE_RANK = -2  # above everything: the mark after a move in a hard fight
MOVE_SAID = 'the mark after the move (DM_AFTER_EVERY_MOVE)'
PETS_SAID = 'the demons idle by the character (DM_AFTER_EVERY_MOVE)'
REBUFF_REMARK_WITHIN = 6.0  # seconds after a rebuff landing the mark before the model went again (`target_before`)
REBUFF_CAST_WAIT = 2.0  # seconds after a rebuff landing with no Battle Orders keyed: marked without it


def state_on(words: bytes, state: int) -> bool:
    """Whether `state` is set in a unit's state words read raw from the first (game/layout.py STATE_RUN: 32 states to
    a little-endian word)."""
    word, bit = divmod(state, 32)
    if len(words) < (word + 1) * 4:
        return False
    return bool(int.from_bytes(words[word * 4 : word * 4 + 4], 'little') >> bit & 1)


def mark_shows(words: bytes) -> bool:
    """Whether a monster's state words show Death Mark on it (MARK_STATE): the cast took."""
    return state_on(words, MARK_STATE)


def demons(world: World) -> list[Monster]:
    """The character's own units Death Mark sends (`pettype demon`): its summons and bound demon, not the
    mercenary."""
    player = world.player
    return [m for m in world.monsters if sends(world, m)] if player is not None else []


def sends(world: World, monster: Monster) -> bool:
    """Whether Death Mark sends `monster`: a unit of the character's that is no mercenary."""
    player = world.player
    if player is None or monster.txt_id == HIRELING_CLASS_ID or monster.unit_id == player.unit_id:
        return False
    return monster.ally or monster.owner == player.unit_id or monster.txt_id == DEFILER_CLASS


def own_demons(world: World) -> list[Monster]:
    """R1's demons (DM_AFTER_EVERY_MOVE): of `demons`, the Warlock's summons and those monstats calls a demon
    (pets.py `heals`). Not the ally-flagged units no one owns: the Bloody Foothills' barbarians (monstats 522/523,
    "bound Act 5 Combatant" in the log; rca/2026-10-24/engorge-findings.md), which no mark sends."""
    from inventory_tracking.builds.warlock.pets import heals  # late: pets.py builds on this module

    return [d for d in demons(world) if heals(d)]


def pets_with_us(world: World, hostiles: Sequence[Monster]) -> list[Monster]:
    """R1's demons (`own_demons`) within PETS_WITH_US of the character with none of `hostiles` within PET_CONTACT of
    them: idle by it, no mark holding them on a hostile."""
    player = world.player
    if player is None:
        return []
    here, foes = (player.x, player.y), [(m.x, m.y) for m in hostiles]
    near = [d for d in own_demons(world) if math.dist(here, (d.x, d.y)) <= PETS_WITH_US]
    return [d for d in near if not any(math.dist((d.x, d.y), at) <= PET_CONTACT for at in foes)]


def move_reason(facts: BuffFacts) -> str | None:
    """Why the mark goes out now whatever the mark rules say (combat/pack.py DM_AFTER_EVERY_MOVE): a hard fight
    (`hard_fight`), a hostile in reach, a demon out, and a jump of REMARK_HOP or more landed under MOVE_AFTER s ago with
    no key since (MOVE_SAID), or a demon idle by the character PETS_AGAIN s after the last key (PETS_SAID); or the mark
    from where the character stands asked by the walk in (combat/pack.py MARK_THEN_WALK, `ask_mark`: WALK_SAID). None
    else."""
    if not (herald_pack.DM_AFTER_EVERY_MOVE or herald_pack.MARK_THEN_WALK) or not facts.reachable:
        return None
    player = facts.world.player
    if player is None or not own_demons(facts.world):
        return None
    here = (player.x, player.y)
    pressed = facts.draws is not None and any(price.pressed for price in facts.draws.values())
    if herald_pack.hard_fight(here, facts.foes, pressed) is None:
        return None
    if herald_pack.mark_asked(facts.now) and facts.since(DEATH_MARK) > MARK_DELAY:
        return herald_pack.WALK_SAID  # R2: the mark from here before the walk in (macros/hunting/moves.py)
    if not herald_pack.DM_AFTER_EVERY_MOVE:
        return None
    if herald_pack.DM_MOVE_NO_BURN and herald_pack.burning(here, facts.foes):
        return None  # a mana-burn fight: the mana leave first (combat/pack.py DM_MOVE_NO_BURN)
    hop = herald_pack.since_hop(facts.now)
    if (
        herald_pack.HOP.units >= REMARK_HOP
        and hop <= MOVE_AFTER
        and hop < facts.since(DEATH_MARK)
        and pets_with_us(facts.world, facts.foes)
    ):
        # The jump pulled a demon back to the character, off what it fought (the stopwatch: a Teleport or Blade Warp
        # takes them along and the old curse does not send them again); a demon the jump left on its monster is
        # still at it (the arena's Baal chamber, seed 5: 7 marks after moves with the Defiler 2.8 off Baal)
        return MOVE_SAID
    if facts.since(DEATH_MARK) >= PETS_AGAIN and pets_with_us(facts.world, facts.foes):
        return PETS_SAID
    return None


def move_target(facts: BuffFacts) -> Monster | None:
    """The mark's target after a move (`move_reason`): the one the mark's own rules (`rules_target`) pick (the held one
    again after a jump), else the one they pick as if no mark of the character's were on anything (the casts' clocks of
    Death Mark left out; the keys that took nowhere kept), so a mark lasting on the old one holds nothing back, the doll
    Herald and the pack's order still first. When those rules pick none (a hard fight of trash the rules leave alone):
    of those in reach the keys did take on, one no body covers (`covered`), a Herald, a boss, a tier 4-5 Herald pack's
    member, a leader, one the strike does not kill in TRASH_CASTS (`fits`), the nearest."""
    player = facts.world.player
    if player is None:
        return None
    pool = [m for m in facts.reachable if facts.missed.get((DEATH_MARK, m.unit_id), 0) < MARK_RECASTS]
    if not pool:
        return None
    fresh = replace(facts, cast_at={key: at for key, at in facts.cast_at.items() if key[0] != DEATH_MARK})
    for asked in (facts, fresh):
        chosen = rules_target(asked)
        if chosen is not None and any(m.unit_id == chosen.unit_id for m in pool):
            return chosen
    here = (player.x, player.y)
    bodies = [(m.x, m.y) for m in facts.foes]

    def rank(m: Monster) -> tuple:
        seen = observe(player, [m], ())
        return (
            facts.missed.get((DEATH_MARK, m.unit_id), 0),
            herald_pack.covered((m.x, m.y), bodies),  # one that can be clicked first (the 2026-10-21 Q1 ruling)
            not herald(m),
            not is_boss(m),
            not herald_pack.in_pack(m.tier),
            not m.leader,
            not fits(seen, m.unit_id),
            math.dist(here, (m.x, m.y)),
            m.unit_id,
        )

    return min(pool, key=rank)


def moved_mark(facts: BuffFacts) -> Monster | None:
    """The monster designated for the mark after a move (`move_reason`, `move_target`), or None."""
    why = move_reason(facts)
    if why is None:
        return None
    chosen = move_target(facts)
    return note(chosen, MOVE_RANK, why) if chosen is not None else None


def strike_rate(txt: int) -> float:
    """Points a second the strike takes off a monster of `txt` in reach, at the strikes' measured pace (`PACE`)."""
    return BLADES_A_CAST * ECHOING_STRIKE_ATTACK.damage_of(txt) / CAST_SECONDS / PACE


def life_to_come(seen: Observation, unit: int) -> float:
    """Its life left in points: the observation's (with combat/mechanics/life.py TIER_LIFE its rank and Herald tier are
    in them), else an elite's in its type's points times ELITE_LIFE (`rank_share`)."""
    foe = seen.foes[unit]
    return foe.left * rank_share(foe.elite)


def casts_to_kill(seen: Observation, unit: int) -> float:
    """The strike's casts its life to come takes, at the strikes' measured pace (PACE: a cast takes less than its
    forecast, by misses and moves)."""
    foe = seen.foes[unit]
    return life_to_come(seen, unit) / (BLADES_A_CAST * ECHOING_STRIKE_ATTACK.damage_of(foe.txt) / PACE)


def fits(seen: Observation, unit: int) -> bool:
    """Whether a monster is one to mark at all: it outlives TRASH_CASTS casts of the strike."""
    return unit in seen.foes and casts_to_kill(seen, unit) > TRASH_CASTS


def struck_more(companion: int, txt: int) -> float:
    """How much more often a companion's blow lands on a marked monster of `txt`: its to-hit with MARK_DEFENCE over
    without (combat/sim/casters.py `hit_chance`). 1 where a row is missing (the Defiler)."""
    rows, levels = tables()['monsters'], tables()['monlvl']
    striker, struck = rows.get(str(companion)), rows.get(str(txt))
    if striker is None or struck is None or not striker.get('A1TH(H)') or not struck.get('AC(H)'):
        return 1.0
    level, against = int(striker['Level(H)']), int(struck['Level(H)'])
    defence = float(struck['AC(H)']) * float(levels[str(against)]['AC(H)']) / 100
    before = hit_chance(striker, level, defence, against)
    return hit_chance(striker, level, max(0.0, defence - MARK_DEFENCE), against) / before if before > 0 else 1.0


def swing(txt: int) -> float:
    """A monster class's mean A1 damage in Hell (monstats A1MinD(H)/A1MaxD(H)); 0 where no row says."""
    row = tables()['monsters'].get(str(txt))
    if row is None or not row.get('A1MinD(H)') or not row.get('A1MaxD(H)'):
        return 0.0
    return (float(row['A1MinD(H)']) + float(row['A1MaxD(H)'])) / 2


def demon_rate(txt: int) -> float:
    """Points a frame a sent companion of `txt` takes off the monster it strikes: data/damage.json `companions`; for a
    demon of a class it does not measure, the measured bound demon's by their `swing` (PRICE_ANY_DEMON); else 0."""
    rates = companion_table()
    if txt in rates:
        return rates[txt][1]
    measured = rates.get(BOUND_DEMON)
    if not PRICE_ANY_DEMON or measured is None or txt in {HIRELING_CLASS_ID, DEFILER_CLASS} or not swing(BOUND_DEMON):
        return 0.0
    return measured[1] * swing(txt) / swing(BOUND_DEMON)


def first_blow(sent: Sequence[int]) -> float:
    """Seconds from the key until the demons first strike: MARK_JUMP, then one think and one swing of the strongest
    (`aidel(H)` and its A1 frames, combat/sim/casters.py); MARK_JUMP alone where no row says."""
    strongest = max(sent, key=demon_rate, default=None)
    row = rules.row_of(strongest) if strongest is not None else None
    mind = rules.mind_of(strongest) if strongest is not None else None
    if row is None or mind is None:
        return MARK_JUMP
    return MARK_JUMP + (rules.MODE_FRAMES.get((mind, 'A1'), 0) + rules.number(row, 'aidel(H)')) / GAME_RATE


def gain(seen: Observation, unit: int, sent: Sequence[int]) -> float:
    """Seconds of the fight a mark on `unit` saves besides the harm: its time to die by the strike alone less that
    with the demons `sent` striking at their rates (`demon_rate`) from `first_blow`, by `struck_more`, while the mark
    lasts, and MARK_POINTS more an element on each blade."""
    foe = seen.foes.get(unit)
    if foe is None:
        return 0.0
    strike = strike_rate(foe.txt)
    if strike <= 0:
        return 0.0
    focus = sum(demon_rate(txt) * struck_more(txt, foe.txt) for txt in sent) * GAME_RATE
    flat = MARK_POINTS * MARK_ELEMENTS * BLADES_A_CAST / CAST_SECONDS / PACE
    left = life_to_come(seen, unit)
    start = min(first_blow(sent), MARK_SECONDS)
    before = (strike + flat) * start  # the strike and the mark's points, the demons not striking yet
    within = before + (strike + flat + focus) * (MARK_SECONDS - start)
    if left <= before:
        marked = left / (strike + flat)
    elif left <= within:
        marked = start + (left - before) / (strike + flat + focus)
    else:
        marked = MARK_SECONDS + (left - within) / strike
    return max(0.0, left / strike - marked)


herald_pack.THROUGH.add(DEATH_MARK)  # the mark through the fight casts' hold (combat/pack.py MARK_THROUGH_HOLD)
herald_pack.FIRST.add(DEATH_MARK)  # the mark first at a T5 Herald fight's landing (combat/pack.py HERALD_MARK_FIRST)

DEATH_MARK_DRAW = Draw(
    DEATH_MARK,
    sends,
    MARK_REACH,
    MARK_BESIDE,
    MARK_CAST_SECONDS,
    MARK_SECONDS,
    gain,
    fits,
    MARK_JUMP,
    MARK_PACK,
    MARK_TURNS,
)


def mark_due(facts: BuffFacts) -> bool:
    """Whether a Death Mark is looked for now: the skill on a key and out of its delay (MARK_DELAY)."""
    return DEATH_MARK in facts.world.slots and facts.since(DEATH_MARK) > MARK_DELAY


def marked(facts: BuffFacts) -> list[Monster]:
    """The hostiles of the fight whose mark lasts still."""
    return [m for m in facts.foes if facts.since(DEATH_MARK, m.unit_id) < MARK_SECONDS]


def strongest(facts: BuffFacts) -> Monster | None:
    """The monster the demons should hold by the build's own rule: a boss first, then a pack's leader, then the most
    life; the nearer of two alike."""
    player = facts.world.player
    if player is None or not facts.reachable:
        return None
    here = (player.x, player.y)
    return max(facts.reachable, key=lambda m: (is_boss(m), m.leader, m.max_life, -math.dist(here, (m.x, m.y))))


def worth_of(facts: BuffFacts, unit: int) -> float:
    """The safety's price of a mark on `unit` (`DrawPrice.worth`), -inf where it has none."""
    found = facts.draws.get(unit) if facts.draws is not None else None
    return found.worth if found is not None else -math.inf


def immune_to(monster: Monster) -> tuple[int, ...]:
    """The elements of IMMUNE_TO `monster` takes nothing of (`Monster.immune`)."""
    return tuple(stat for stat in IMMUNE_TO if monster.immune(stat))


def resists_line(monster: Monster) -> str:
    """Its immunities and resistances in words: 'magic, cold (resists physical 33, magic 100, ...)'."""
    found = dict(monster.resists)
    immune = ', '.join(name for stat, name in MONSTER_RESISTS.items() if monster.immune(stat))
    resists = ', '.join(f'{name} {found[stat]}' for stat, name in MONSTER_RESISTS.items() if stat in found)
    return f'{immune or "nothing"} (resists {resists or "unread"})'


def unmarked_immune(facts: BuffFacts) -> Monster | None:
    """The nearest monster in reach immune to the character's magic (`immune_to`) whose mark has run out or was never
    laid: the mark's target after a Herald (`target_before`)."""
    player = facts.world.player
    if player is None:
        return None
    here = (player.x, player.y)
    found = [m for m in facts.reachable if immune_to(m) and facts.since(DEATH_MARK, m.unit_id) >= MARK_SECONDS]
    return min(found, key=lambda m: math.dist(here, (m.x, m.y))) if found else None


def herald(monster: Monster) -> bool:
    """A Terror Zone's Herald: stat 367 with the unique flag (terror/tracker.py); its minions carry the stat too and
    are no leaders."""
    return bool(monster.tier) and monster.leader


def unmarked_herald(facts: BuffFacts) -> Monster | None:
    """The nearest Herald in reach whose mark has run out or was never laid: the mark's first target (the player,
    2026-10-18: "prioritizing keeping herald on sigil lethargy + death mark")."""
    player = facts.world.player
    if player is None:
        return None
    here = (player.x, player.y)
    found = [m for m in facts.reachable if herald(m) and facts.since(DEATH_MARK, m.unit_id) >= MARK_SECONDS]
    return min(found, key=lambda m: math.dist(here, (m.x, m.y))) if found else None


def ranked(facts: BuffFacts) -> list[Monster]:
    """The leaders and bosses in reach a mark may go on (`fits`). While one is in reach no plain monster is marked
    (the player, 2026-10-14: "on the leader / most dangerous monster")."""
    player = facts.world.player
    if player is None:
        return []
    found = []
    for m in facts.reachable:
        if m.leader or is_boss(m):
            seen = observe(player, [m], ())
            if fits(seen, m.unit_id):
                found.append(m)
    return found


def pack_lasts(facts: BuffFacts, monster: Monster) -> bool:
    """Whether a mark of the character's may still be on `monster`: cast on it within MARK_SECONDS, and not settled as
    one that did not take (`BuffFacts.missed`) unless a later cast is still being looked for (MARK_SHOWS)."""
    since = facts.since(DEATH_MARK, monster.unit_id)
    if since >= MARK_SECONDS:
        return False
    return facts.missed.get((DEATH_MARK, monster.unit_id), 0) == 0 or since < MARK_SHOWS


def pack_marked(facts: BuffFacts) -> bool:
    """Whether the mark is the tier 4-5 Herald pack's to choose (combat/pack.py MARK_ANY_MEMBER): one of the pack is in
    reach with a clear shot."""
    return herald_pack.MARK_ANY_MEMBER and any(herald_pack.in_pack(m.tier) for m in facts.reachable)


def pack_target(facts: BuffFacts) -> Monster | None:
    """A tier 4-5 Herald pack's mark (the player, 2026-10-21 ~10:00, Q1: "the nearest pack member that can be clicked,
    the Herald when it can be, no lock-out"). While a mark may last on a member (`pack_lasts`) none, unless the pack
    still comes at the character (combat/pack.py `pressing`) MARK_AGAIN after the last key. Else, of the members in
    reach whose mark does not last: those with the fewest keys that did not take on them (a key that took nowhere
    goes next on another member, never locked out), then one no body in front covers (`covered`), the Herald before
    the rest, the nearest."""
    player = facts.world.player
    if player is None:
        return None
    here = (player.x, player.y)
    near = [m for m in facts.reachable if herald_pack.in_pack(m.tier)]
    if not near:
        return None
    pack = [m for m in facts.foes if herald_pack.in_pack(m.tier)] or near
    if any(pack_lasts(facts, m) for m in pack) and not (PACK_HOP_FREES and dragged(facts)):
        if facts.since(DEATH_MARK) < MARK_AGAIN:
            return None
        sent = [(d.x, d.y) for d in demons(facts.world)]
        if not herald_pack.pressing(here, herald_pack.members(pack), sent):
            return None
    free = [m for m in near if not pack_lasts(facts, m)]
    if not free:
        return None
    bodies = [(m.x, m.y) for m in facts.foes]

    def rank(m: Monster) -> tuple[int, bool, bool, float]:
        tries = facts.missed.get((DEATH_MARK, m.unit_id), 0)
        return (tries, herald_pack.covered((m.x, m.y), bodies), not herald(m), math.dist(here, (m.x, m.y)))

    return min(free, key=rank)


def rebuff_hopped(facts: BuffFacts) -> float | None:
    """Seconds since the Battle Orders rebuff retreat landed (`BuffFacts.rebuff_landed`) for the mark before the model
    (`target_before`): under REBUFF_REMARK_WITHIN s ago, no Death Mark keyed since, and the Battle Orders keyed since or
    REBUFF_CAST_WAIT s gone. None else."""
    hop = facts.now - facts.rebuff_landed
    if not 0.0 <= hop <= REBUFF_REMARK_WITHIN or facts.since(DEATH_MARK) <= hop:
        return None
    return hop if facts.since(BATTLE_ORDERS_SKILL) <= hop or hop >= REBUFF_CAST_WAIT else None


def rebuff_target(facts: BuffFacts) -> Monster | None:
    """The mark after a Battle Orders rebuff retreat before the model (`target_before`, `rebuff_hopped`): on the leader
    the strike holds while in reach, else the nearest leader or boss in reach; None with no rebuff hop to answer, no
    demon out, nobody of those in reach, or the mark still shown on the one chosen (`mark_shows`)."""
    player = facts.world.player
    if player is None or rebuff_hopped(facts) is None or not demons(facts.world):
        return None
    unit = ECHOING_STRIKE_ATTACK.holding()
    chosen = next((m for m in facts.reachable if m.unit_id == unit), None) if unit is not None else None
    if chosen is None:
        here = (player.x, player.y)
        leaders = [m for m in facts.reachable if m.leader or is_boss(m)]
        chosen = min(leaders, key=lambda m: (math.dist(here, (m.x, m.y)), m.unit_id)) if leaders else None
    if chosen is None:
        return None
    words = facts.states(chosen) if facts.states is not None else None
    if words is not None and mark_shows(words):
        return None
    return chosen


# -- the one designation (DESIGNATED_MARK) --

HERALD_RANK, IMMUNE_RANK, HELD_RANK, LEADER_RANK, PACK_RANK, REAGGRO_RANK = 0, 1, 2, 3, 4, 5
REVIVER_RANK = -1  # a reviver raising its pack (combat/revivers.py REVIVERS_FIRST): before a Herald


@dataclass
class Designation:
    """The monster the demons were last found to have to hold (DESIGNATED_MARK, `designate`, which reads it from the
    look and the marks' clocks): its unit, why, and the reason's rank (lower first), for the log lines and the cast's
    checks; None: nobody. `said` is the hop whose re-aggro was said (`aggro_lost`)."""

    unit: int | None = None
    reason: str = ''
    rank: int = PACK_RANK
    said: float = -math.inf


DESIGNATION = Designation()


def reason_of(monster: Monster, leaders: Sequence[Monster], holding: int | None) -> tuple[int, str] | None:
    """Why `monster` is one the demons must hold, with its rank (lower first): a Herald, a monster immune to the magic,
    the leader the strike holds, a leader or boss the mark fits (`leaders`); None: none of those."""
    if herald(monster):
        if dolls.herald_doll(monster):
            return HERALD_RANK, 'a doll Herald: the demons take its aggro, then it is struck down'
        return HERALD_RANK, 'a Herald'
    if immune_to(monster):
        return IMMUNE_RANK, f'immune to {resists_line(monster)}: the demons are its answer'
    if monster in leaders:
        if monster.unit_id == holding:
            return HELD_RANK, 'the leader the strike holds'
        return LEADER_RANK, 'a boss' if is_boss(monster) else 'a pack leader'
    return None


def note(monster: Monster | None, rank: int = PACK_RANK, reason: str = '') -> Monster | None:
    """`monster` is the one designated from here, for `reason`: said when it changes."""
    unit = monster.unit_id if monster is not None else None
    if unit != DESIGNATION.unit or (unit is not None and reason != DESIGNATION.reason):
        if monster is not None:
            LOG.info('Macro: mark: designated %s, %s: %s', label(monster), life(monster), reason)
        elif DESIGNATION.unit is not None:
            LOG.info('Macro: mark: none designated now (unit %d dead, out of reach or no reason)', DESIGNATION.unit)
        DESIGNATION.unit, DESIGNATION.reason, DESIGNATION.rank = unit, reason, rank
    return monster


def designate(facts: BuffFacts) -> Monster | None:
    """The monster the demons must hold now, outside a tier 4-5 Herald pack (`pack_designated`), said when it changes
    (`DESIGNATION`): the last one marked while it is in reach, keeps its reason (`reason_of`) and no higher reason is in
    reach; else the best of those in reach by rank, the nearest (leaders: `leader_first`, one the demons do not stand by
    first). Read from the look and the marks' clocks alone, so it changes only when that one dies or leaves reach,
    loses its reason or a higher one comes. Never one on which MARK_RECASTS keys took nowhere, none with no demon out.
    A dead one is gone from the hostiles: the next is designated in the same look, its mark due at once."""
    player = facts.world.player
    if player is None or not demons(facts.world):
        return note(None)
    leaders = ranked(facts) if MARK_LEADERS else []
    holding = ECHOING_STRIKE_ATTACK.holding()
    found = []
    for m in facts.reachable:
        why = reason_of(m, leaders, holding)
        if why is not None and facts.missed.get((DEATH_MARK, m.unit_id), 0) < MARK_RECASTS:
            found.append((why, m))
    if not found:
        picked = reaggro_pick(facts)
        return note(picked, REAGGRO_RANK, REAGGRO_SAID) if picked is not None else note(None)
    best = min(why[0] for why, _ in found)
    marked_ones = [(why, m) for why, m in found if facts.since(DEATH_MARK, m.unit_id) < math.inf]
    if marked_ones:
        why, kept = min(marked_ones, key=lambda x: (facts.since(DEATH_MARK, x[1].unit_id), x[1].unit_id))
        if why[0] <= best:
            return note(kept, *why)
    pool = [m for why, m in found if why[0] == best]
    if best == LEADER_RANK:
        chosen = leader_first(facts, [m for m in pool if not held_by_demons(facts, m)] or pool)
    else:
        here = (player.x, player.y)
        chosen = min(pool, key=lambda m: (math.dist(here, (m.x, m.y)), m.unit_id))
    why = next(why for why, m in found if m is chosen)
    return note(chosen, *why)


def dragged(facts: BuffFacts) -> bool:
    """Whether a jump of REMARK_HOP units or more landed under REAGGRO_AFTER s ago, after the last Death Mark key, with
    a demon of the character's within TAKEN_ALONG of it (taken along: REAGGRO_PACK)."""
    hop = herald_pack.since_hop(facts.now)
    if hop > REAGGRO_AFTER or herald_pack.HOP.units < REMARK_HOP or not hop < facts.since(DEATH_MARK):
        return False
    player = facts.world.player
    return player is not None and any(
        math.dist((player.x, player.y), (d.x, d.y)) <= TAKEN_ALONG for d in demons(facts.world)
    )


def reaggro_pick(facts: BuffFacts) -> Monster | None:
    """The pack's member the demons are sent to with nobody designated (REAGGRO_PACK): the one designated so last while
    its mark lasts and it is in reach; else, after a jump that took the demons along (`dragged`) or with REAGGRO_PRESS
    hostiles on the character (combat/pack.py `pressing`), while no demon stands within DEMON_HOLDS of a hostile, the
    member in reach that outlives TRASH_CASTS casts (`fits`) with the most hostiles within MARK_PACK of it, then the
    most life, the nearest. None: off, no demon out, or none of those."""
    player = facts.world.player
    sent = demons(facts.world)
    if not REAGGRO_PACK or player is None or not sent:
        return None
    if DESIGNATION.rank == REAGGRO_RANK and DESIGNATION.unit is not None:
        kept = next((m for m in facts.reachable if m.unit_id == DESIGNATION.unit), None)
        tries = facts.missed.get((DEATH_MARK, kept.unit_id), 0) if kept is not None else MARK_RECASTS
        if kept is not None and pack_lasts(facts, kept) and tries < MARK_RECASTS:
            return kept
    here = (player.x, player.y)
    foes = [(m.x, m.y) for m in facts.foes]
    spots = [(d.x, d.y) for d in sent]
    if any(math.dist(d, at) <= herald_pack.DEMON_HOLDS for d in spots for at in foes):
        return None  # a demon strikes already
    near = [herald_pack.Member(m.unit_id, (m.x, m.y)) for m in facts.foes]
    if not dragged(facts) and len(herald_pack.pressing(here, near, spots)) < REAGGRO_PRESS:
        return None
    pool = []
    for m in facts.reachable:
        if facts.missed.get((DEATH_MARK, m.unit_id), 0) >= MARK_RECASTS:
            continue
        seen = observe(player, [m], ())
        if fits(seen, m.unit_id):
            pool.append(m)
    if not pool:
        return None

    def rank(m: Monster) -> tuple[int, int, float]:
        around = sum(math.dist((m.x, m.y), at) <= MARK_PACK for at in foes)
        return (around, m.max_life, -math.dist(here, (m.x, m.y)))

    return max(pool, key=rank)


def raisers(facts: BuffFacts) -> list[Monster]:
    """The revivers in the mark's reach raising their pack (combat/revivers.py `raising`, REVIVERS_FIRST) past the
    blades' reach (the strike's weighted lines take one within it: combat/revivers.py REVIVER_WEIGHT; in the arena's
    Fallen Herald pack the mark and a strike held on the shamans both cleared it in 22 s, either alone in 13.6), the
    mark still allowed on (fewer than MARK_RECASTS keys took nowhere), with a demon of the character's out to send."""
    player = facts.world.player
    if not revivers.REVIVERS_FIRST or player is None or not demons(facts.world):
        return []
    found = revivers.raising((m.unit_id, m.txt_id, (m.x, m.y), m.flags) for m in facts.foes)
    here, reach = (player.x, player.y), ECHOING_STRIKE_ATTACK.reach
    return [
        m
        for m in facts.reachable
        if m.unit_id in found
        and math.dist(here, (m.x, m.y)) > reach
        and facts.missed.get((DEATH_MARK, m.unit_id), 0) < MARK_RECASTS
    ]


def reviver_designated(facts: BuffFacts) -> tuple[bool, Monster | None]:
    """Whether a reviver raising its pack decides the mark now (`raisers`), and the one to mark now: the one whose mark
    lasts is designated, its mark again only when a jump took the demons off it (`aggro_lost`), else none; with none
    lasting, the one with the fewest keys that took nowhere, the nearest. (False, None): no such reviver in reach."""
    near = raisers(facts)
    if not near:
        return False, None
    lasting = [m for m in near if pack_lasts(facts, m)]
    if lasting:
        held = min(lasting, key=lambda m: (facts.since(DEATH_MARK, m.unit_id), m.unit_id))
        note(held, REVIVER_RANK, 'a reviver raising its pack: the demons hold it first')
        return True, held if aggro_lost(facts, held) else None
    player = facts.world.player
    here = (player.x, player.y) if player is not None else (0.0, 0.0)
    chosen = min(
        near, key=lambda m: (facts.missed.get((DEATH_MARK, m.unit_id), 0), math.dist(here, (m.x, m.y)), m.unit_id)
    )
    return True, note(chosen, REVIVER_RANK, 'a reviver raising its pack: the demons hold it first')


def doll_herald_designated(facts: BuffFacts) -> tuple[bool, Monster | None]:
    """Whether a tier 4-5 pack's doll Herald (DOLL_HERALD_FIRST) or any Herald (HERALD_FIRST) in reach decides the mark,
    and the one to mark now: it, while its mark does not last or a jump took the demons off it (`aggro_lost`),
    MARK_AGAIN after the last key when another member's mark lasts; else none. (False, None): off, or no such Herald in
    reach the keys did take on."""
    if not (DOLL_HERALD_FIRST or HERALD_FIRST):
        return False, None
    player = facts.world.player
    found = [
        m
        for m in facts.reachable
        if herald_pack.in_pack(m.tier)
        and ((DOLL_HERALD_FIRST and dolls.herald_doll(m)) or (HERALD_FIRST and herald(m)))
        and facts.missed.get((DEATH_MARK, m.unit_id), 0) < MARK_RECASTS
    ]
    if player is None or not found:
        return False, None
    here = (player.x, player.y)
    chosen = min(found, key=lambda m: (math.dist(here, (m.x, m.y)), m.unit_id))
    kind = 'doll Herald' if dolls.herald_doll(chosen) else 'Herald'
    note(chosen, HERALD_RANK, f'the tier {chosen.tier} {kind}: the demons take its aggro, then it is struck down')
    if pack_lasts(facts, chosen):
        return True, chosen if aggro_lost(facts, chosen) else None
    others = [m for m in facts.foes if m is not chosen and herald_pack.in_pack(m.tier) and pack_lasts(facts, m)]
    if others and facts.since(DEATH_MARK) < MARK_AGAIN:
        return True, None
    return True, chosen


def pack_designated(facts: BuffFacts) -> Monster | None:
    """A tier 4-5 Herald pack's mark (combat/pack.py MARK_ANY_MEMBER): its doll Herald first (DOLL_HERALD_FIRST,
    `doll_herald_designated`); the member whose mark lasts is the one designated (a Herald first, the last marked), its
    mark again when the demons lost it (`aggro_lost`); else the pack's own rule (`pack_target`: the first member, or
    another while the pack presses the character)."""
    decided, doll = doll_herald_designated(facts)
    if decided:
        return doll
    lasting = [m for m in facts.reachable if herald_pack.in_pack(m.tier) and pack_lasts(facts, m)]
    if lasting:
        held = min(lasting, key=lambda m: (not herald(m), facts.since(DEATH_MARK, m.unit_id), m.unit_id))
        note(held, PACK_RANK, f"the tier {held.tier} Herald pack's marked member")
        if aggro_lost(facts, held):
            return held
    chosen = pack_target(facts)
    if chosen is not None:
        note(chosen, PACK_RANK, f"the tier {chosen.tier} Herald pack's member (the pack's order)")
    return chosen


def aggro_lost(facts: BuffFacts, monster: Monster) -> bool:
    """Whether a jump took the demons off `monster` since its mark's key: a Teleport or Blade Warp of REMARK_HOP units
    or more landed after it (combat/pack.py `HOP`), a demon within TAKEN_ALONG of the character (it came along), and
    the demons not back on it (`held_by_demons`). The state word outlives the hop: it is not asked."""
    hop = herald_pack.since_hop(facts.now)
    if not hop < facts.since(DEATH_MARK, monster.unit_id) or herald_pack.HOP.units < REMARK_HOP:
        return False
    if REMARK_UNSHOWN and facts.states is not None:
        words = facts.states(monster)
        if words is not None and mark_shows(words):
            return False  # the curse still on it (REMARK_UNSHOWN)
    player, sent = facts.world.player, demons(facts.world)
    if player is None or not any(math.dist((player.x, player.y), (d.x, d.y)) <= TAKEN_ALONG for d in sent):
        return False
    if held_by_demons(facts, monster):
        return False
    if DESIGNATION.said != herald_pack.HOP.at:
        DESIGNATION.said = herald_pack.HOP.at
        LOG.info(
            'Macro: mark: the jump of %.1f units %.2fs ago took the demons off %s: its mark again',
            herald_pack.HOP.units, hop, label(monster),
        )  # fmt: skip
    return True


def aggro_held(facts: BuffFacts, monster: Monster) -> bool:
    """Whether the demons hold `monster`: a mark of the character's may last on it (`pack_lasts`), its state words show
    it once MARK_SHOWS s are gone (when read), and no jump took the demons off it since (`aggro_lost`)."""
    if not pack_lasts(facts, monster) or aggro_lost(facts, monster):
        return False
    if facts.states is None or facts.since(DEATH_MARK, monster.unit_id) < MARK_SHOWS:
        return True
    words = facts.states(monster)
    return not words or mark_shows(words)


def rebuff_waits(facts: BuffFacts) -> bool:
    """Whether the mark waits for the rebuff's Battle Orders at a rebuff retreat's landing (macros/cta.py REBUFF_GRACE):
    landed under REBUFF_CAST_WAIT s ago with no Battle Orders keyed since."""
    hop = facts.now - facts.rebuff_landed
    return 0.0 <= hop < REBUFF_CAST_WAIT and facts.since(BATTLE_ORDERS_SKILL) > hop


def due_on(facts: BuffFacts) -> Monster | None:
    """The designated monster whose mark is due now outside a tier 4-5 Herald pack (DESIGNATED_MARK, `designate`; the
    pack's is `pack_designated`): not held by the demons (`aggro_held`); a leader's not while a leader's or an immune
    one's mark lasts on another, nor within MARK_AGAIN of a key while one lasts on a plain monster. None else."""
    if pack_marked(facts):
        return None
    chosen = designate(facts)
    if chosen is None or aggro_held(facts, chosen):
        return None
    if DESIGNATION.rank >= HELD_RANK:
        held = [m for m in marked(facts) if m is not chosen and not aggro_lost(facts, m)]
        if held and not any(m.leader or is_boss(m) or immune_to(m) for m in held):
            if facts.since(DEATH_MARK) < MARK_AGAIN:
                return None
        elif held:
            return None  # a leader's, an immune one's mark lasts: the demons hold it
    return chosen


def target(facts: BuffFacts) -> Monster | None:
    """Whom Death Mark is for now. With DESIGNATED_MARK: a tier 4-5 Herald pack's member (`pack_designated`), else the
    dolls' bait (DOLL_BAIT, off), else the designated monster while its mark is due (`due_on`); else, with the
    safety's prices fresh, the best priced (while a mark lasts, only another priced above nothing, MARK_AGAIN after;
    while an immune one's lasts, only one under pressure); else `strongest`, and none while a mark lasts on a live one.
    Without: `target_before`."""
    if not DESIGNATED_MARK:
        return target_before(facts)
    if rebuff_waits(facts):
        return None  # the rebuff's Battle Orders at its landing first
    moved = moved_mark(facts)
    if moved is not None:
        return moved  # a hard fight's mark after a move (combat/pack.py DM_AFTER_EVERY_MOVE)
    if herald_pack.LANDING_ASK.on:
        return None  # R1's landing ask: its own reasons alone (combat/pack.py `landing_ask`)
    return rules_target(facts)


def rules_target(facts: BuffFacts) -> Monster | None:
    """`target`'s own rules past the rebuff's wait and the mark after a move."""
    decided, reviver = reviver_designated(facts)
    if decided:
        return reviver  # a reviver raising its pack first (combat/revivers.py REVIVERS_FIRST)
    if pack_marked(facts):
        return pack_designated(facts)
    bait = doll_bait(facts)  # the dolls drawn onto the demons (combat/threats/dolls.py DOLL_BAIT, off)
    if bait is not None:
        return bait
    chosen = due_on(facts)
    if chosen is not None:
        return chosen
    return priced_target(facts, marked(facts), ranked(facts))


def priced_target(facts: BuffFacts, held: Sequence[Monster], first: Sequence[Monster]) -> Monster | None:
    """The mark by the safety's prices when no designated mark is due: the best priced of `first` (else of those in
    reach); while a mark lasts (`held`), only another priced above nothing, MARK_AGAIN after, and while an immune
    one's lasts only one under pressure; with no fresh price `strongest`, none while a mark lasts."""
    if facts.draws is None:
        return None if held else strongest(facts)
    priced = [m for m in (first or facts.reachable) if m.unit_id in facts.draws]
    if held:
        if facts.since(DEATH_MARK) < MARK_AGAIN:
            return None
        priced = [m for m in priced if m not in held and worth_of(facts, m.unit_id) > 0]
        if any(immune_to(m) for m in held):  # the demons kill what the strike cannot: off it only for the life
            priced = [m for m in priced if facts.draws[m.unit_id].pressed]
    if not priced:
        return None
    return max(priced, key=lambda m: (worth_of(facts, m.unit_id), -m.unit_id))


def target_before(facts: BuffFacts) -> Monster | None:
    """The mark before the one designation (DESIGNATED_MARK off; the retired switches at their last values): after a
    rebuff landing (`rebuff_target`), a tier 4-5 Herald pack's member (`pack_target`), the dolls' bait, an unmarked
    Herald, an unmarked monster immune to the magic while no immune one's mark lasts, a leader or boss (MARK_LEADERS:
    while no mark lasts or one lasts on plain monsters only, MARK_AGAIN after), else `priced_target`."""
    again = rebuff_target(facts)
    if again is not None:
        return again
    if pack_marked(facts):
        return pack_target(facts)
    bait = doll_bait(facts)
    if bait is not None:
        return bait
    first_of_all = unmarked_herald(facts)
    if first_of_all is not None:
        return first_of_all
    held = marked(facts)
    holds_immune = any(immune_to(m) for m in held)
    if not holds_immune:
        immune = unmarked_immune(facts)
        if immune is not None:
            return immune
    first = ranked(facts)
    if MARK_LEADERS and first and not holds_immune:
        leads_held = any(m.leader or is_boss(m) for m in held)
        if not held or (not leads_held and facts.since(DEATH_MARK) >= MARK_AGAIN):
            free = [m for m in first if m not in held]
            free = [m for m in free if not held_by_demons(facts, m)] or free  # one the demons strike already last
            if free:
                return leader_first(facts, free)
    return priced_target(facts, held, first)


def mark_ahead(facts: BuffFacts) -> bool:
    """Whether the build's fight casts go before the bout's first strike (`Buff.ahead`): the designated monster's mark
    is due (`due_on`, a Herald pack's member's with `pack_designated`), for the demons' aggro first. Before the model
    (DESIGNATED_MARK off): a doll Herald in reach (macros/hunt.py DOLL_HERALD_MARK, 2026-10-22)."""
    if not DESIGNATED_MARK:
        return any(dolls.herald_doll(m) for m in facts.reachable)
    if not mark_due(facts) or rebuff_waits(facts):
        return False
    if moved_mark(facts) is not None:
        return True  # a hard fight's mark after a move, before the strike (combat/pack.py DM_AFTER_EVERY_MOVE)
    if herald_pack.LANDING_ASK.on:
        return False  # R1's landing ask: its own reasons alone (combat/pack.py `landing_ask`)
    decided, reviver = reviver_designated(facts)
    if decided:
        return reviver is not None and worth_a_mark(facts, reviver)
    chosen = pack_designated(facts) if pack_marked(facts) else due_on(facts)
    return chosen is not None and worth_a_mark(facts, chosen)


def doll_bait(facts: BuffFacts) -> Monster | None:
    """The doll a mark draws the dolls with (combat/threats/dolls.py `bait_target`, DOLL_BAIT); None: off, no demon
    out, or no such doll."""
    player = facts.world.player
    if not dolls.DOLL_BAIT or player is None or not demons(facts.world):
        return None
    return dolls.bait_target(
        (player.x, player.y), facts.foes, MARK_PACK, lambda m: pack_lasts(facts, m),
        lambda m: facts.missed.get((DEATH_MARK, m.unit_id), 0),
    )  # fmt: skip


def leader_first(facts: BuffFacts, leaders: Sequence[Monster]) -> Monster:
    """Which of the leaders and bosses in reach the mark goes on (MARK_LEADERS): a boss first, then the safety's best
    price, then the nearest."""
    player = facts.world.player
    here = (player.x, player.y) if player is not None else (0.0, 0.0)
    return max(
        leaders, key=lambda m: (is_boss(m), worth_of(facts, m.unit_id), -math.dist(here, (m.x, m.y)), -m.unit_id)
    )


def held_by_demons(facts: BuffFacts, monster: Monster) -> bool:
    """Every demon of the character's stands within MARK_BESIDE + HELD of `monster`: striking it already."""
    found = demons(facts.world)
    return bool(found) and all(math.dist((d.x, d.y), (monster.x, monster.y)) <= MARK_BESIDE + HELD for d in found)


def seen_of(facts: BuffFacts, monster: Monster) -> Observation | None:
    world = facts.world
    if world.player is None:
        return None
    return observe(world.player, [monster], ())


def own_price(facts: BuffFacts, monster: Monster) -> DrawPrice | None:
    """The mark's price with no safety price fresh: `gain` by the idle demons (none within MARK_BESIDE + HELD of a
    hostile) against the cast; no life is counted."""
    seen = seen_of(facts, monster)
    if seen is None:
        return None
    foes = [(m.x, m.y) for m in (*facts.foes, monster)]
    sent = [m.txt_id for m in demons(facts.world) if all(math.dist((m.x, m.y), at) > MARK_BESIDE + HELD for at in foes)]
    return DrawPrice(monster.unit_id, 0.0, 0.0, gain(seen, monster.unit_id, sent), MARK_CAST_SECONDS, MARK_SECONDS)


def own_line(price: DrawPrice | None) -> str:
    """The build's own price in words (no life is counted by it)."""
    if price is None:
        return "by the build's rule (no safety price): no price"
    return (
        f"by the build's rule (no safety price): the demons sent and the mark's points save {price.gain:.2f}s of the "
        f"fight, against the cast's {price.cost:.2f}s: {price.worth:+.2f}s"
    )


def why_not(facts: BuffFacts, monster: Monster) -> str | None:
    """Why no mark goes on `monster`, or None when it pays. A monster immune to the magic (`immune_to`) whatever its
    life or kind, unless the safety prices the cast as costing life while holding is over the life budget; a leader or
    boss the trash rule leaves alone, with MARK_LEADERS on the same terms (and a demon to send, `held_by_demons`),
    else when the price pays; a plain monster only as a re-aggro under pressure (`DrawPrice.pressed`): marks on plain
    packs that did not press cost time and kept no life (death-mark-engage.md §5, death-mark.md §2)."""
    if not demons(facts.world):
        return "no demon of the character's is out (the skill needs one)"
    if DESIGNATION.rank == MOVE_RANK and monster.unit_id == DESIGNATION.unit and move_reason(facts) is not None:
        return None  # a hard fight's mark after a move (combat/pack.py DM_AFTER_EVERY_MOVE)
    if DESIGNATED_MARK and monster.unit_id == DESIGNATION.unit and aggro_lost(facts, monster):
        return None  # the designated one's mark again after a jump took the demons off it (`aggro_lost`)
    if DESIGNATED_MARK and REAGGRO_PACK and monster.unit_id == DESIGNATION.unit and DESIGNATION.rank == REAGGRO_RANK:
        return None  # the pack's re-aggro (`reaggro_pick`): the demons are off the pack
    if not DESIGNATED_MARK:
        again = rebuff_target(facts)
        if again is not None and again.unit_id == monster.unit_id:
            return None  # the re-aggro after a Battle Orders rebuff retreat (before the model)
    if herald(monster):
        return None  # a Herald is marked whatever the price (`unmarked_herald`)
    if any(m.unit_id == monster.unit_id for m in raisers(facts)):
        return None  # a reviver raising its pack: what it raises comes back while it lives (REVIVERS_FIRST)
    if dolls.DOLL_BAIT and dolls.runner(monster.txt_id):
        return None  # a doll the demons draw the dolls with: trash, but its blast goes off on them (`doll_bait`)
    if herald_pack.MARK_ANY_MEMBER and herald_pack.in_pack(monster.tier):
        return None  # a tier 4-5 Herald pack's member too: the demons hold the pack (combat/pack.py, Q1)
    if immune_to(monster):
        # No gain is priced for it (the strike's table knows no resistance): only the life the cast costs can stop it,
        # and only while that pressure lasts
        price = facts.draws.get(monster.unit_id) if facts.draws is not None else None
        if price is not None and price.pressed and price.life < 0:
            return (
                f'immune to {resists_line(monster)}, but the cast costs life while holding is over the life budget: '
                f'{price.line()}'
            )
        return None
    seen = seen_of(facts, monster)
    if seen is None:
        return 'no character'
    if not fits(seen, monster.unit_id):
        casts = casts_to_kill(seen, monster.unit_id)
        return f'trash: {casts:.1f} casts of the strike kill it (a mark needs more than {TRASH_CASTS})'
    leads = monster.leader or is_boss(monster)
    if leads and MARK_LEADERS:
        price = facts.draws.get(monster.unit_id) if facts.draws is not None else None
        if price is not None and price.pressed and price.life < 0:
            return f'the cast costs life while holding is over the life budget: {price.line()}'
        if held_by_demons(facts, monster):
            return f'the demons stand by it already (within {MARK_BESIDE + HELD:.1f} units): none to send'
        return None
    if facts.draws is not None:
        price = facts.draws.get(monster.unit_id)
        if price is None:
            return 'not priced by the safety at its last look'
        if price.worth <= 0:
            return f'the safety prices it: {price.line()}'
        if not leads and not price.pressed:
            return f'a plain monster, and holding fits the life budget without it: {price.line()}'
        return None
    if not leads:
        return 'a plain monster: with no safety price, no pack is priced'
    price = own_price(facts, monster)
    if price is None or price.worth <= 0:
        return own_line(price)
    return None


def worth_a_mark(facts: BuffFacts, monster: Monster | None) -> bool:
    """Whether the mark on `monster` pays (`why_not` says nothing against it)."""
    return monster is not None and why_not(facts, monster) is None


def mark_refusal(facts: BuffFacts, monster: Monster) -> str | None:
    """The `Macro: mark:` line when a mark on an elite or boss is refused (`Buff.refused`; the player, 2026-10-14:
    "I'm not sure if death mark is used"), or on a monster immune to the magic. None for a plain monster or one
    TRASH_CASTS kills."""
    immune = bool(immune_to(monster))
    if not (monster.leader or is_boss(monster) or immune):
        return None
    seen = seen_of(facts, monster)
    if not immune and seen is not None and not fits(seen, monster.unit_id):
        return None
    why = why_not(facts, monster)
    if why is None:
        return None
    return f'Macro: mark: no {skill_name(DEATH_MARK)} on {label(monster)}, {life(monster)}: {why}'


def mark_passed(facts: BuffFacts) -> list[tuple[Monster, str]]:
    """The bosses in reach `ranked` leaves out (struck down to a cast or two), each with the line that says why
    (`Buff.passed`: once a boss; rca/2026-10-14/run-0305-findings.md §2); with SAY_PASSED every leader in reach the
    mark passes over too (`passed_why`)."""
    player = facts.world.player
    if player is None or DEATH_MARK not in facts.world.slots:
        return []
    found = []
    chosen = target(facts) if SAY_PASSED else None
    held = marked(facts) if SAY_PASSED else []
    for m in facts.reachable:
        if immune_to(m) or not (is_boss(m) or (SAY_PASSED and m.leader)):
            continue
        seen = observe(player, [m], ())
        if fits(seen, m.unit_id):
            why = passed_why(facts, m, chosen, held) if SAY_PASSED else None
            if why is None:
                continue
        elif is_boss(m):
            casts = casts_to_kill(seen, m.unit_id)
            why = (
                f'dropped from the mark: trash now, {casts:.1f} casts of the strike kill it '
                f'(a mark needs more than {TRASH_CASTS})'
            )
        else:
            casts = casts_to_kill(seen, m.unit_id)
            why = f'trash: {casts:.1f} casts of the strike kill it (a mark needs more than {TRASH_CASTS})'
        found.append((m, f'Macro: mark: no {skill_name(DEATH_MARK)} on {label(m)}, {life(m)}: {why}'))
    return found


def passed_why(facts: BuffFacts, monster: Monster, chosen: Monster | None, held: Sequence[Monster]) -> str | None:
    """Why the mark passes over a leader or boss in reach it fits (`mark_passed`), or None: it is the one chosen (its
    refusal, if any, is `mark_refusal`'s), a Herald (always first), or its mark lasts."""
    if monster is chosen or herald(monster) or monster in held:
        return None
    if not demons(facts.world):
        return "no demon of the character's is out (the skill needs one)"
    if chosen is not None:
        return f'the mark goes on {label(chosen)} first'
    if held:
        lasting = max(held, key=lambda m: MARK_SECONDS - facts.since(DEATH_MARK, m.unit_id))
        left = MARK_SECONDS - facts.since(DEATH_MARK, lasting.unit_id)
        if facts.draws is None:
            return f'the mark lasts on {label(lasting)} ({left:.1f}s left) and no safety price is fresh'
        price = facts.draws.get(monster.unit_id)
        priced = f'the safety prices it: {price.line()}' if price is not None else 'not priced by the safety'
        return f'the mark lasts on {label(lasting)} ({left:.1f}s left); {priced}'
    if facts.draws is not None and monster.unit_id not in facts.draws:
        return 'not priced by the safety at its last look'
    return None


def mark_said(facts: BuffFacts, monster: Monster) -> str | None:
    """The line of a cast, in the service's log under `Macro: mark:`, with what it was found worth. None on a monster
    immune to the magic: `mark_told` says why, once."""
    if immune_to(monster) and not herald(monster):
        return None
    if facts.draws is None:
        worth = own_line(own_price(facts, monster))
    else:
        price = facts.draws.get(monster.unit_id)
        worth = f'the safety prices it: {price.line()}' if price is not None else 'the safety prices it'
    if DESIGNATED_MARK and monster.unit_id == DESIGNATION.unit and DESIGNATION.reason:
        worth = f'designated: {DESIGNATION.reason}; {worth}'
    return f'Macro: mark: {skill_name(DEATH_MARK)} on {label(monster)}, {life(monster)}: {worth}'


def mark_told(facts: BuffFacts, monster: Monster) -> str | None:
    """The line of the first cast on a monster immune to the magic (`Buff.told`, once a monster): what it is immune to
    and its resistances as read. None for any other."""
    if not immune_to(monster) or herald(monster):
        return None
    return f'Macro: mark: {skill_name(DEATH_MARK)} on {label(monster)}: immune to {resists_line(monster)}'
