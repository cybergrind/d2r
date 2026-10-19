"""Death Mark (skills.txt 375): what it buys and when the fight casts it (rca/2026-10-14/death-mark.md).

The player, 2026-10-14: "death mark is skill that forces daemons to attack and lowers enemy defence"; "a very
effective mechanism that allow to distract/re-aggro enemies". The character's demons (none: it cannot be cast)
teleport to the marked monster (MARK_JUMP, MARK_BESIDE), the monsters round it turn to them (MARK_TURNS of the
pack within MARK_PACK), and the mark takes flat points off each element of a hit and cuts its defence.

A mark is worth what it draws off the character (the safety's harm, macros/safety.py `Safety.weigh`) and what it
adds to the strike (`gain`), against one volley of blades (MARK_CAST_SECONDS). A leader or boss before a plain
monster ("on the leader / most dangerous monster"); never with no demon, never on trash (TRASH_CASTS), never again
while a mark lasts. The measures behind each number: builds/history/warlock-mark.md.
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
from inventory_tracking.game.layout import DEFILER_CLASS
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


def first_blow(sent: Sequence[int]) -> float:
    """Seconds from the key until the demons first strike: MARK_JUMP, then one think and one swing of the strongest
    (`aidel(H)` and its A1 frames, combat/sim/casters.py); MARK_JUMP alone where no row says."""
    rates = companion_table()
    strongest = max(sent, key=lambda txt: rates.get(txt, (0.0, 0.0))[1], default=None)
    row = rules.row_of(strongest) if strongest is not None else None
    mind = rules.mind_of(strongest) if strongest is not None else None
    if row is None or mind is None:
        return MARK_JUMP
    return MARK_JUMP + (rules.MODE_FRAMES.get((mind, 'A1'), 0) + rules.number(row, 'aidel(H)')) / GAME_RATE


def gain(seen: Observation, unit: int, sent: Sequence[int]) -> float:
    """Seconds of the fight a mark on `unit` saves besides the harm: its time to die by the strike alone less that
    with the demons `sent` striking at their rates (data/damage.json `companions`) from `first_blow`, by
    `struck_more`, while the mark lasts, and MARK_POINTS more an element on each blade."""
    foe = seen.foes.get(unit)
    if foe is None:
        return 0.0
    rates = companion_table()
    strike = strike_rate(foe.txt)
    if strike <= 0:
        return 0.0
    focus = sum(rates.get(txt, (0.0, 0.0))[1] * struck_more(txt, foe.txt) for txt in sent) * GAME_RATE
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
    """Whom Death Mark is for now: the leaders and bosses in reach (`ranked`) first. With the safety's prices fresh,
    the best priced (while a mark lasts, only another priced above nothing, MARK_AGAIN after); else `strongest`,
    and none while a mark lasts on a live one."""
    first_of_all = unmarked_herald(facts)
    if first_of_all is not None:
        return first_of_all
    held = marked(facts)
    if facts.draws is None:
        return None if held else strongest(facts)
    first = ranked(facts)
    priced = [m for m in (first or facts.reachable) if m.unit_id in facts.draws]
    if held:
        if facts.since(DEATH_MARK) < MARK_AGAIN:
            return None
        priced = [m for m in priced if m not in held and worth_of(facts, m.unit_id) > 0]
    if not priced:
        return None
    return max(priced, key=lambda m: (worth_of(facts, m.unit_id), -m.unit_id))


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
    """Why no mark goes on `monster`, or None when it pays. A leader or boss when the price pays; a plain monster only
    as a re-aggro under pressure (`DrawPrice.pressed`): marks on plain packs that did not press cost time and kept
    no life (death-mark-engage.md §5, death-mark.md §2)."""
    if not demons(facts.world):
        return "no demon of the character's is out (the skill needs one)"
    if herald(monster):
        return None  # a Herald is marked whatever the price (`unmarked_herald`)
    seen = seen_of(facts, monster)
    if seen is None:
        return 'no character'
    if not fits(seen, monster.unit_id):
        casts = casts_to_kill(seen, monster.unit_id)
        return f'trash: {casts:.1f} casts of the strike kill it (a mark needs more than {TRASH_CASTS})'
    leads = monster.leader or is_boss(monster)
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
    "I'm not sure if death mark is used"). None for a plain monster or one TRASH_CASTS kills."""
    if not (monster.leader or is_boss(monster)):
        return None
    seen = seen_of(facts, monster)
    if seen is not None and not fits(seen, monster.unit_id):
        return None
    why = why_not(facts, monster)
    if why is None:
        return None
    return f'Macro: mark: no {skill_name(DEATH_MARK)} on {label(monster)}, {life(monster)}: {why}'


def mark_passed(facts: BuffFacts) -> list[tuple[Monster, str]]:
    """The bosses in reach `ranked` leaves out (struck down to a cast or two), each with the line that says why
    (`Buff.passed`: once a boss; rca/2026-10-14/run-0305-findings.md §2)."""
    player = facts.world.player
    if player is None or DEATH_MARK not in facts.world.slots:
        return []
    found = []
    for m in facts.reachable:
        if not is_boss(m):
            continue
        seen = observe(player, [m], ())
        if fits(seen, m.unit_id):
            continue
        casts = casts_to_kill(seen, m.unit_id)
        why = (
            f'dropped from the mark: trash now, {casts:.1f} casts of the strike kill it '
            f'(a mark needs more than {TRASH_CASTS})'
        )
        found.append((m, f'Macro: mark: no {skill_name(DEATH_MARK)} on {label(m)}, {life(m)}: {why}'))
    return found


def mark_said(facts: BuffFacts, monster: Monster) -> str:
    """The line of a cast, in the service's log under `Macro: mark:`, with what it was found worth."""
    if facts.draws is None:
        worth = own_line(own_price(facts, monster))
    else:
        price = facts.draws.get(monster.unit_id)
        worth = f'the safety prices it: {price.line()}' if price is not None else 'the safety prices it'
    return f'Macro: mark: {skill_name(DEATH_MARK)} on {label(monster)}, {life(monster)}: {worth}'
