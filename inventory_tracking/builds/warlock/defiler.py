"""A Defiler kept out (the player, 2026-10-14; rca/2026-10-14/run-1932-findings.md issue 3): the buff plan's row for
"no Defiler alive", in the quiet and under the held strike when it pays.

At 22:55:48 on 2026-10-14 the Defiler died in the Icy Cellar and nothing summoned it again: only Consume's casters
did (`defiler_dance`, `renew_consume`), at the next prebuff or Consume's renewal, up to 300 s later; the player
summoned it by hand 9.5 s after. What the row keeps:

- **the macro's own Defiler**: the one its prebuff or Consume's renewal left out (they cast Consume: `took`); a
  character the macro never buffed is the player's to summon for;
- **two demon slots**: an active Consume holds one, and a summon made with both taken ends the oldest, Consume
  included (the player, 2026-10-10). A summon is due only while no Defiler is alive (the world shows only live
  monsters), when the slots hold Consume alone: it ends nothing;
- **the player's hand**: never with a panel open (22:45:01-07: four presses into the inventory the player was
  using, no Defiler came), nor with the game in the background;
- **the price under the strike** (`price`): the summon is one key and one pointer move, the cast of a Death Mark
  (mark.py MARK_CAST_SECONDS); it pays by what its own blows take off the fight in reach over DEFILER_HORIZON, from
  its arrival on (data/damage.json `companions`, measured in reach of a hostile), in seconds of the strike's own
  work on the toughest of them, and with no demon of the character's out, by the Death Mark it makes possible
  again (mark.py `gain`, the skill needing a demon). What it draws off the character as a body is not priced
  (the safety's harm with and without it is not asked): a lower bound.
"""

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
from inventory_tracking.combat.policy import observe
from inventory_tracking.common import LOG
from inventory_tracking.game.layout import DEFILER_CLASS
from inventory_tracking.game.records import Monster, World
from inventory_tracking.macros.build import BuffFacts, DrawPrice
from inventory_tracking.macros.routines import DEAD
from inventory_tracking.takes.timeline import GAME_RATE


DEFILER_RETRY = 5.0  # seconds between two tries at a missing Defiler (one that came shows in under 1.5 s)
# Seconds of the fight its blows are counted over: the RCA's "over the next 10 s" (run-1932-findings.md issue 3);
# a fight longer than that is asked again at the next look anyway.
DEFILER_HORIZON = 10.0
# Seconds from the key until it strikes: it shows 0.3-0.6 s after the key (the summons of 2026-10-12, casters.py
# `renew_consume`) beside the character and walks to the nearest hostile; a stand-in, not measured.
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
        # The Defiler kept out is the one the macro's prebuff or Consume's renewal left out (both cast Consume and
        # summon one to stand): a character the macro never buffed is the player's to summon for
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


def worth_a_defiler(facts: BuffFacts, _target: Monster | None) -> bool:
    """The fight's row: the summon pays (`price`), said when it does (the cast follows at once: the row is due only
    with no Defiler alive and none tried for DEFILER_RETRY)."""
    found = price(facts)
    if found is None or found.worth <= 0:
        return False
    LOG.info(
        'Macro: Defiler: none out in the fight; its blows save %.2fs of the fight in reach over %.1fs, against the '
        "cast's %.2fs: %+.2fs",
        found.gain, found.span, found.cost, found.worth,
    )  # fmt: skip
    return True
