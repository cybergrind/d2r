"""A Defiler kept out (the player, 2026-10-14; rca/2026-10-14/run-1932-findings.md issue 3): the buff plan's row for
"no Defiler alive", in the quiet and under the held strike when it pays.

Only the macro's own Defiler (one its prebuff or Consume's renewal left out); only while none is alive, so with two
demon slots and Consume holding one the summon ends nothing (the player, 2026-10-10); never with a panel open or the
game in the background. Under the strike (`price`) it costs a Death Mark's cast and pays by its blows over
DEFILER_HORIZON in seconds of the strike's work on the toughest in reach, and by the Death Mark it makes possible.
What it draws off the character is not priced: a lower bound.
"""

from collections.abc import Sequence

from inventory_tracking.builds.warlock.echoing_strike.damage import companion_table
from inventory_tracking.builds.warlock.mark import (
    MARK_CAST_SECONDS,
    demons,
    gain,
    life_to_come,
    strike_rate,
    strongest,
)
from inventory_tracking.builds.warlock.skills import CONSUME, DEATH_MARK, SUMMON_DEFILER
from inventory_tracking.combat import pack as herald_pack
from inventory_tracking.combat.policy import observe
from inventory_tracking.common import LOG
from inventory_tracking.game.layout import DEFILER_CLASS, NO_OWNER
from inventory_tracking.game.records import Monster, World
from inventory_tracking.levels.geometry import Point
from inventory_tracking.macros.build import BuffFacts, DrawPrice
from inventory_tracking.macros.routines import DEAD
from inventory_tracking.takes.timeline import GAME_RATE


DEFILER_RETRY = 5.0  # seconds between two tries at a missing Defiler (one that came shows in under 1.5 s)
# Seconds of the fight its blows are counted over (run-1932-findings.md issue 3); a longer fight asks again.
DEFILER_HORIZON = 10.0
# Seconds from the key until it strikes (it shows 0.3-0.6 s after, then walks): a stand-in, not measured.
DEFILER_ARRIVES = 1.0
DEFILER_CAST_SECONDS = MARK_CAST_SECONDS  # one key and one pointer move under the strike, as a mark


def defilers(world: World) -> list[Monster]:
    """The Defilers alive (the world leaves out the dead: game/, modes 0 and 12)."""
    return [m for m in world.monsters if m.txt_id == DEFILER_CLASS]


def defiler_missing(facts: BuffFacts) -> bool:
    """Whether a Defiler is to be summoned now: its skill on a key, the character alive out of town, no panel open,
    no Defiler alive (then a summon ends nothing: the module text), the macro's Consume cast (`BuffFacts.took`), the
    last try DEFILER_RETRY old and the game's window in front."""
    world = facts.world
    player = world.player
    if player is None or player.mode in DEAD or player.in_town:
        return False
    if SUMMON_DEFILER not in world.slots or world.open_panels or defilers(world):
        return False
    if CONSUME not in facts.took:
        # A character the macro never buffed is the player's to summon for
        return False
    if facts.since(SUMMON_DEFILER) <= DEFILER_RETRY:
        return False
    return facts.focused()


def price(facts: BuffFacts) -> DrawPrice | None:
    """What a summon under the strike is worth (the module text) as a `DrawPrice` on the toughest hostile in reach
    (mark.py `strongest`); None with nothing in reach."""
    world = facts.world
    target = strongest(facts)
    if target is None or world.player is None:
        return None
    seen = observe(world.player, list(facts.reachable), ())
    if target.unit_id not in seen.foes:
        return None
    strike = strike_rate(target.txt_id)
    if strike <= 0:
        return None
    left = sum(life_to_come(seen, unit) for unit in seen.foes)
    fight = left / strike  # seconds the strike alone needs for what is in reach
    rate = companion_table().get(DEFILER_CLASS, (0.0, 0.0))[1] * GAME_RATE
    struck = min(left, rate * max(0.0, min(DEFILER_HORIZON, fight) - DEFILER_ARRIVES))
    saved = struck / strike
    if DEATH_MARK in world.slots and not demons(world):
        # No demon out: no Death Mark can be cast; the Defiler makes the next one possible
        one = observe(world.player, [target], ())
        saved += gain(one, target.unit_id, [DEFILER_CLASS])
    span = min(DEFILER_HORIZON, fight)
    return DrawPrice(target.unit_id, 0.0, 0.0, saved, DEFILER_CAST_SECONDS, span)


def pack_gate(facts: BuffFacts) -> bool:
    """Whether a Defiler is summoned whatever its price: a tier 4-5 Herald's pack among the foes and none of it on the
    character within PACK_BACK (the player, 2026-10-21 ~10:00, Q6: "a missing Defiler is summoned even under attack,
    from range"; combat/pack.py DEMON_GATE). With the pack on the character the hop back comes first."""
    player = facts.world.player
    if not herald_pack.DEMON_GATE or player is None:
        return False
    pack = herald_pack.members(facts.foes)
    if not pack:
        return False
    sent = [(d.x, d.y) for d in demons(facts.world)]
    return not herald_pack.pressing((player.x, player.y), pack, sent)


def spot_between(here: Point, hostiles: Sequence[Monster]) -> Point | None:
    """Where the fight's Defiler is summoned with a tier 4-5 Herald pack among `hostiles`: between the character and
    the pack (combat/pack.py PETS_BETWEEN, `between_spot`); None with no pack."""
    found = herald_pack.members(hostiles)
    return herald_pack.between_spot(here, herald_pack.nearby(here, found)) if found else None


def pack_spot(facts: BuffFacts) -> Point | None:
    """`spot_between` for the fight's foes."""
    player = facts.world.player
    return spot_between((player.x, player.y), facts.foes) if player is not None else None


def world_spot(world: World) -> Point | None:
    """`spot_between` for the hostiles of a look (the caster's, which has no foes of its own)."""
    player = world.player
    if player is None:
        return None
    hostiles = [m for m in world.monsters if not m.ally and m.owner == NO_OWNER]
    return spot_between((player.x, player.y), hostiles)


def worth_a_defiler(facts: BuffFacts, _target: Monster | None) -> bool:
    """The fight's row: the summon pays (`price`), said when it does (the cast follows at once: the row is due only
    with no Defiler alive and none tried for DEFILER_RETRY); with a Herald pack at range whatever the price
    (`pack_gate`)."""
    if pack_gate(facts):
        LOG.info('Macro: Defiler: none out with a tier 4-5 Herald pack about, none of it on the character: summoned')
        return True
    found = price(facts)
    if found is None or found.worth <= 0:
        return False
    LOG.info(
        'Macro: Defiler: none out in the fight; its blows save %.2fs of the fight in reach over %.1fs, against the '
        "cast's %.2fs: %+.2fs",
        found.gain, found.span, found.cost, found.worth,
    )  # fmt: skip
    return True
