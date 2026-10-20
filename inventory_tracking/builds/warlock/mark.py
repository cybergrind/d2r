"""Death Mark (skills.txt 375): what it buys and when the fight casts it (rca/2026-10-14/death-mark.md).

The player, 2026-10-14: "death mark is skill that forces daemons to attack and lowers enemy defence"; "a very
effective mechanism that allow to distract/re-aggro enemies". The character's demons (none: it cannot be cast)
teleport to the marked monster (MARK_JUMP, MARK_BESIDE), the monsters round it turn to them (MARK_TURNS of the
pack within MARK_PACK), and the mark takes flat points off each element of a hit and cuts its defence.

A mark is worth what it draws off the character (the safety's harm, macros/safety.py `Safety.weigh`) and what it
adds to the strike (`gain`), against one volley of blades (MARK_CAST_SECONDS). A Herald first; then a monster immune to
magic (MARK_IMMUNE, the player 2026-10-20: the demons kill what the magic cannot); a leader or boss before a plain
monster ("on the leader / most dangerous monster"), whatever the price unless it costs life under pressure
(MARK_LEADERS, 2026-10-20); never with no demon, never on trash (TRASH_CASTS), never again while a mark lasts; a
leader passed over is named once with why (SAY_PASSED). The measures behind each number:
builds/history/warlock-mark.md; rca/2026-10-20/leader-not-marked-findings.md.
"""

import math
from collections.abc import Sequence

from inventory_tracking.builds.warlock.echoing_strike.attack import BLADES_A_CAST, ECHOING_STRIKE_ATTACK
from inventory_tracking.builds.warlock.echoing_strike.damage import companion_table, damage_data
from inventory_tracking.builds.warlock.skills import DEATH_MARK
from inventory_tracking.combat.harm import SafetySettings
from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.policy import Observation, observe
from inventory_tracking.combat.sim import casters as rules
from inventory_tracking.combat.sim.casters import hit_chance
from inventory_tracking.combat.stance import CAST_SECONDS
from inventory_tracking.game.layout import DEFILER_CLASS, MAGIC_RESIST, MONSTER_RESISTS
from inventory_tracking.game.records import Monster, World
from inventory_tracking.macros.build import BuffFacts, Draw, DrawPrice
from inventory_tracking.macros.goals import is_boss
from inventory_tracking.macros.rotation import ELITE_LIFE
from inventory_tracking.macros.skills import skill_name
from inventory_tracking.macros.travel import label, life
from inventory_tracking.native.layout import HIRELING_CLASS_ID
from inventory_tracking.takes.timeline import GAME_RATE


_MARK = damage_data()['death_mark']
# The mark at the character's level (data/damage.json `death_mark`, read off marked monsters' stats in the takes).
MARK_POINTS = float(_MARK['points'])  # points more an element of a hit takes
MARK_ELEMENTS = 1  # elements of a blade's hit: the weapon's physical damage (Echoing Strike has no EType)
MARK_SECONDS = int(_MARK['frames']) / GAME_RATE  # 125 + 13 x (level - 1) frames: 11.76 s at 14
MARK_DELAY = 20 / GAME_RATE  # skills.txt localdelay: the skill cannot be cast again sooner
MARK_DEFENCE = float(_MARK['defence'])  # the marked monster's defence falls by this (stat 31, -505 at level 14)
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
# `Monster.resists`) is marked whenever a demon is out: after an unmarked Herald and before any other, the trash rule
# aside, again when its mark runs out while it lives; while its mark lasts the mark moves off it only to a Herald or
# under pressure (`DrawPrice.pressed`). False: the mark as before.
MARK_IMMUNE = True
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
# False: the safety's price decides for a leader too (the rule of 2026-10-14).
MARK_LEADERS = True
# A leader or boss in reach the mark passes over is named once, with why (`mark_passed`): the silent "never marked" of
# elite 397 at 15:01:12 (trash by the strike's table, no line said). False: bosses struck down to trash only.
SAY_PASSED = True


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


def strike_rate(txt: int) -> float:
    """Points a second the strike takes off a monster of `txt` in reach, at the strikes' measured pace (`PACE`)."""
    return BLADES_A_CAST * ECHOING_STRIKE_ATTACK.damage_of(txt) / CAST_SECONDS / PACE


def life_to_come(seen: Observation, unit: int) -> float:
    """Its life left in points, an elite's in its type's points times ELITE_LIFE (the tables hold the plain one)."""
    foe = seen.foes[unit]
    return foe.left * (ELITE_LIFE if foe.elite else 1.0)


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
    """The elements of IMMUNE_TO `monster` takes nothing of (`Monster.immune`); () with MARK_IMMUNE off."""
    return tuple(stat for stat in IMMUNE_TO if monster.immune(stat)) if MARK_IMMUNE else ()


def resists_line(monster: Monster) -> str:
    """Its immunities and resistances in words: 'magic, cold (resists physical 33, magic 100, ...)'."""
    found = dict(monster.resists)
    immune = ', '.join(name for stat, name in MONSTER_RESISTS.items() if monster.immune(stat))
    resists = ', '.join(f'{name} {found[stat]}' for stat, name in MONSTER_RESISTS.items() if stat in found)
    return f'{immune or "nothing"} (resists {resists or "unread"})'


def unmarked_immune(facts: BuffFacts) -> Monster | None:
    """The nearest monster in reach immune to the character's magic (`immune_to`) whose mark has run out or was never
    laid: the mark's target after a Herald (MARK_IMMUNE)."""
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


def target(facts: BuffFacts) -> Monster | None:
    """Whom Death Mark is for now: an unmarked Herald, then an unmarked monster immune to the magic
    (`unmarked_immune`) while no immune one's mark lasts, then the leaders and bosses in reach (`ranked`): with
    MARK_LEADERS one of those (`leader_first`) while no mark lasts or one lasts on plain monsters only (MARK_AGAIN
    after). With the safety's prices fresh, the best priced (while a mark lasts, only another priced above nothing,
    MARK_AGAIN after; while an immune one's lasts, only one under pressure); else `strongest`, and none while a mark
    lasts on a live one."""
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
            if free:
                return leader_first(facts, free)
    if facts.draws is None:
        return None if held else strongest(facts)
    priced = [m for m in (first or facts.reachable) if m.unit_id in facts.draws]
    if held:
        if facts.since(DEATH_MARK) < MARK_AGAIN:
            return None
        priced = [m for m in priced if m not in held and worth_of(facts, m.unit_id) > 0]
        if holds_immune:  # the demons kill what the strike cannot: taken off it only for the character's life
            priced = [m for m in priced if facts.draws[m.unit_id].pressed]
    if not priced:
        return None
    return max(priced, key=lambda m: (worth_of(facts, m.unit_id), -m.unit_id))


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
    if herald(monster):
        return None  # a Herald is marked whatever the price (`unmarked_herald`)
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
    return f'Macro: mark: {skill_name(DEATH_MARK)} on {label(monster)}, {life(monster)}: {worth}'


def mark_told(facts: BuffFacts, monster: Monster) -> str | None:
    """The line of the first cast on a monster immune to the magic (`Buff.told`, once a monster): what it is immune to
    and its resistances as read. None for any other."""
    if not immune_to(monster) or herald(monster):
        return None
    return f'Macro: mark: {skill_name(DEATH_MARK)} on {label(monster)}: immune to {resists_line(monster)}'
