"""Death Mark (skills.txt 375): what it buys and when the fight casts it (rca/2026-10-14/death-mark.md).

The player, 2026-10-14: "death mark is skill that forces daemons to attack and lowers enemy defence"; "also,
death mark is a very effective mechanism that allow to distract/re-aggro enemies". What the skill does, by the
client and the takes (death-mark.md §1-2):

- the character's demons (`pettype demon`, `requirespettype 1`: with none it cannot be cast) teleport to the
  marked monster about 0.28 s after the cast and land 2.8 units from it at the median (the Pit Lord and the
  Defiler, both in about 90% of 454 marks; the mercenary is no demon and walks); no reach cap showed in the takes
  (11 of 11 demons farther than Param9's 38 units jumped too);
- the monsters round it then go for the demons, the nearest body by the client's rule (the pack's path targets:
  44% at the character before, 8% three seconds after, against 66% steady at unmarked elites);
- the marked monster takes stats 34 and 35 at -(5 + 2 x (level - 1)) and stat 31 at -(50 + 35 x (level - 1)):
  flat, not percent (the client subtracts stats 34/35 from each element of each hit as read, with no floor:
  ai_d2_dmg_element 0x14038FB70): -31 at the character's level 14 is 31 more points an element a hit, about 2% of a
  blade's; the defence cut (-505) helps only what rolls to hit (the mercenary, the demons), which no model here
  prices;
- the cast costs the strike about MARK_CAST_SECONDS (the macro's marks of 2026-10-13: the next strike 1.76 s after
  the key at the median against 0.73 s between two strikes).

So a mark is worth what it draws off the character (priced by the safety pricing's harm, macros/safety.py
`Safety.weigh`, at the look's price of life, so the arbiter weighs it against the retreat) and what the demons
and the mark add to the strike on the marked monster (`gain`), against the cast. The fight's buff row casts it on
the hostile that price names (the safety's last look, `BuffFacts.draws`); with no price fresh (the pursuit off)
by `gain` alone. Never with no demon, never on a monster a cast or two kills (TRASH_CASTS), never again on one
marked while its mark lasts: a new one when the marked monster dies or its mark runs out and the fight goes on.
"""

import math
from collections.abc import Sequence

from inventory_tracking.builds.warlock.echoing_strike.attack import BLADES_A_CAST, ECHOING_STRIKE_ATTACK
from inventory_tracking.builds.warlock.echoing_strike.damage import companion_table, damage_data
from inventory_tracking.builds.warlock.skills import DEATH_MARK
from inventory_tracking.combat.harm import SafetySettings
from inventory_tracking.combat.policy import Observation, observe
from inventory_tracking.combat.stance import CAST_SECONDS
from inventory_tracking.combat.timeline import GAME_RATE
from inventory_tracking.macros.build import BuffFacts, Draw, DrawPrice
from inventory_tracking.macros.goals import is_boss
from inventory_tracking.macros.rotation import ELITE_LIFE
from inventory_tracking.macros.skills import skill_name
from inventory_tracking.macros.travel import label, life
from inventory_tracking.macros.world import DEFILER_CLASS, Monster, World
from inventory_tracking.native.layout import HIRELING_CLASS_ID


_MARK = damage_data()['death_mark']
# The mark at the character's level (data/damage.json `death_mark`: the marked monsters' stats in the takes of
# 2026-10-13, 34 and 35 at -31, 31 at -505: level 14 by skills.txt ln12 = Param1 + Param2 x (level - 1)).
MARK_POINTS = float(_MARK['points'])  # points more an element of a hit takes
MARK_ELEMENTS = 1  # elements of a blade's hit: the weapon's physical damage (Echoing Strike has no EType)
MARK_SECONDS = int(_MARK['frames']) / GAME_RATE  # 125 + 13 x (level - 1) frames: 11.76 s at 14
MARK_DELAY = 20 / GAME_RATE  # skills.txt localdelay: the skill cannot be cast again sooner
# What a cast costs the strike: the macro's 18 marks of 2026-10-13 (rca/2026-10-14/scripts/mark_measure.py): the
# next strike came 1.76 s after the key at the median, against 0.73 s between two strikes (the player's own: 0.92)
MARK_CAST_SECONDS = 1.0
MARK_JUMP = 0.28  # seconds from the key until the demons land (the median of 409 jumps; quartiles 0.24, 0.29)
MARK_BESIDE = 2.8  # units from the marked monster a demon lands (the median of 910 landings; quartiles 2.0, 5.2)
MARK_REACH = math.inf  # units: no cap showed (Param9 "teleport distance" 38; 11 of 11 demons farther jumped)
# The player's intent (2026-10-14): "never on trash a cast or two kills": a monster whose life to come is no more than
# this many of the strike's casts on it is not marked, whatever the price says.
TRASH_CASTS = 2
# Seconds between two marks on two monsters both alive: a mark is moved to another monster (the safety's price says
# it pays more there) no sooner, so two near-equal prices do not trade the demons back and forth.
MARK_AGAIN = 2.0
HELD = 3.0  # units beyond MARK_BESIDE within which a demon is taken to hold a monster already: no gain of its own
PACE = SafetySettings().strike_spread[len(SafetySettings().strike_spread) // 2]  # the strikes' kill time over forecast


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


def gain(seen: Observation, unit: int, sent: Sequence[int]) -> float:
    """Seconds of the fight a mark on `unit` saves besides the harm: the demons sent (`sent`, their classes) strike
    it at their rates (data/damage.json `companions`, measured while a hostile was in their reach) for as long as the
    mark lasts, and each blade on it deals MARK_POINTS more an element. Its time to die by the strike alone, less
    that with them. The demons' own hits taking the flat points and the defence cut are not counted (no hit rate
    and no to-hit in the model)."""
    foe = seen.foes.get(unit)
    if foe is None:
        return 0.0
    rates = companion_table()
    strike = strike_rate(foe.txt)
    if strike <= 0:
        return 0.0
    focus = sum(rates.get(txt, (0.0, 0.0))[1] for txt in sent) * GAME_RATE
    flat = MARK_POINTS * MARK_ELEMENTS * BLADES_A_CAST / CAST_SECONDS / PACE
    left = life_to_come(seen, unit)
    both = strike + focus + flat
    within = both * MARK_SECONDS
    marked = left / both if left <= within else MARK_SECONDS + (left - within) / strike
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


def target(facts: BuffFacts) -> Monster | None:
    """Whom Death Mark is for now. With the safety's prices fresh: the monster in reach it priced best; while a
    mark lasts on a live one, only another it prices above nothing, and MARK_AGAIN after the last mark. With none:
    by `strongest`, and none while a mark lasts on a live one (it is renewed when that dies or runs out)."""
    held = marked(facts)
    if facts.draws is None:
        return None if held else strongest(facts)
    priced = [m for m in facts.reachable if m.unit_id in facts.draws]
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
    """The mark's price by the build's own rule, with no safety price fresh: what it gains on the monster (`gain`) by
    the demons alive that do not hold it already, against the cast; no life is counted."""
    seen = seen_of(facts, monster)
    if seen is None:
        return None
    at = (monster.x, monster.y)
    sent = [m.txt_id for m in demons(facts.world) if math.dist((m.x, m.y), at) > MARK_BESIDE + HELD]
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
    """Why no mark goes on `monster`, or None when it pays."""
    if not demons(facts.world):
        return "no demon of the character's is out (the skill needs one)"
    seen = seen_of(facts, monster)
    if seen is None:
        return 'no character'
    if not fits(seen, monster.unit_id):
        casts = casts_to_kill(seen, monster.unit_id)
        return f'trash: {casts:.1f} casts of the strike kill it (a mark needs more than {TRASH_CASTS})'
    if facts.draws is not None:
        price = facts.draws.get(monster.unit_id)
        if price is None:
            return 'not priced by the safety at its last look'
        return None if price.worth > 0 else f'the safety prices it: {price.line()}'
    price = own_price(facts, monster)
    if price is None or price.worth <= 0:
        return own_line(price)
    return None


def worth_a_mark(facts: BuffFacts, monster: Monster | None) -> bool:
    """Whether the mark on `monster` pays (`why_not` says nothing against it)."""
    return monster is not None and why_not(facts, monster) is None


def mark_refusal(facts: BuffFacts, monster: Monster) -> str | None:
    """What is said when a mark on an elite or a boss is refused (`Buff.refused`: once a target), in the service's
    log under `Macro: mark:` (the player, 2026-10-14: "I'm not sure if death mark is used"). None for a plain
    monster, and for an elite a cast or two kills (TRASH_CASTS): no mark was ever in question there."""
    if not (monster.leader or is_boss(monster)):
        return None
    seen = seen_of(facts, monster)
    if seen is not None and not fits(seen, monster.unit_id):
        return None
    why = why_not(facts, monster)
    if why is None:
        return None
    return f'Macro: mark: no {skill_name(DEATH_MARK)} on {label(monster)}, {life(monster)}: {why}'


def mark_said(facts: BuffFacts, monster: Monster) -> str:
    """The line of a cast, in the service's log under `Macro: mark:`, with what it was found worth."""
    if facts.draws is None:
        worth = own_line(own_price(facts, monster))
    else:
        price = facts.draws.get(monster.unit_id)
        worth = f'the safety prices it: {price.line()}' if price is not None else 'the safety prices it'
    return f'Macro: mark: {skill_name(DEATH_MARK)} on {label(monster)}, {life(monster)}: {worth}'
