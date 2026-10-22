"""Bind Demon again in a tier 4-5 Herald pack fight (combat/pack.py REBIND_DEMON;
rca/2026-10-21/herald-fight-findings.md §7): the buff plan's row for "the bound demon is gone".

The player, 2026-10-21 ~09:40: "keep them busy with a daemon, while killing in the most efficient way ... keep group
on our daemon, not ourselves or merc"; ~10:00 (Q6): "the bound demon holds the pack as the Defiler does", a missing
Defiler "summoned even under attack, from range". The Defiler's own row is defiler.py `pack_gate`; this is the same
for the bound demon.

Bind Demon (skills.txt 382, read 2026-10-21 from pricing/raw/game-excel): cast on a monster (TargetableOnly,
LineOfSight 4), pettype `binddemon` with petmax 1 (one bound demon, besides the Defilers' slots), and only on a
monster monstats calls a demon (column `demon` 1, bundled in combat/data/tables.json). Its capture is a chance
(Param3/Param4 "% capture referenced in monpet.txt", Param8 "Chance to Bind w/ Death Mark"): monpet.txt is not in the
dump, so a bind that brought no demon is tried again after BIND_RETRY. Not verified: whether a unique, champion or a
Herald's minion can be bound (leaders are left out here) and the cast's length (a sequence, seqnum 6).
"""

import math

from inventory_tracking.builds.warlock.mark import demons
from inventory_tracking.builds.warlock.skills import BIND_DEMON
from inventory_tracking.combat import pack as herald_pack
from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.game.records import Monster, World
from inventory_tracking.macros.build import BuffFacts
from inventory_tracking.macros.goals import is_boss
from inventory_tracking.macros.routines import DEAD
from inventory_tracking.macros.skills import skill_name
from inventory_tracking.macros.travel import label
from inventory_tracking.native.layout import DEAD_MODES


# The Warlock's summons (skills.txt `summon` of Summon Goatman 373, Summon Tainted 376, Summon Defiler 377: wargoatman,
# warbighead, warputriddefiler, monstats *hcIdx 742-744): the character's demons that are no bound demon.
SUMMONED = frozenset((742, 743, 744))
# The macros never cast Bind Demon (the player, 2026-10-21 ~16:30: "I will do bind daemon myself. you don't use bind
# daemon anywhere for now and keep it so"): its one caller, the fight row (buffs.py, `bind_due`, casters.py `bind`), is
# never due. Engorge for a demon the player bound stays (buffs.py `engorge_first`). True: the rebind in a tier 4-5
# Herald pack fight (combat/pack.py REBIND_DEMON) as built that morning.
BIND_DEMON_CASTS = False
BIND_RETRY = 3.0  # seconds between two binds while none came (a capture is a chance: the module text)
BIND_NO_KEY = 60.0  # seconds before the row is asked again when Bind Demon has no key the macro can press


def bound(world: World) -> list[Monster]:
    """The character's bound demon (none or one: petmax 1): a demon Death Mark sends that is none of its summons."""
    return [m for m in demons(world) if m.txt_id not in SUMMONED]


def bindable(monster: Monster) -> bool:
    """Whether Bind Demon may take `monster`: a hostile alive that monstats calls a demon, no leader and no boss."""
    if monster.ally or monster.owner != NO_OWNER or monster.mode in DEAD_MODES:
        return False
    row = tables()['monsters'].get(str(monster.txt_id))
    return row is not None and row.get('demon') == '1' and not monster.leader and not is_boss(monster)


def bind_due(facts: BuffFacts) -> bool:
    """Whether the bound demon is bound again now: REBIND_DEMON, the skill on a key, the character alive out of town,
    a tier 4-5 Herald's pack among the foes and none of it on the character within PACK_BACK ("from range"), no bound
    demon out, the last try BIND_RETRY old."""
    world = facts.world
    player = world.player
    if not (BIND_DEMON_CASTS and herald_pack.REBIND_DEMON) or player is None or player.mode in DEAD or player.in_town:
        return False
    if BIND_DEMON not in world.slots or world.open_panels or bound(world):
        return False
    pack = herald_pack.members(facts.foes)
    if not pack or facts.since(BIND_DEMON) <= BIND_RETRY:
        return False
    sent = [(d.x, d.y) for d in demons(world)]
    return not herald_pack.pressing((player.x, player.y), pack, sent)


def bind_target(facts: BuffFacts) -> Monster | None:
    """The demon bound: the nearest bindable monster in reach (`bindable`); None with none."""
    player = facts.world.player
    if player is None:
        return None
    here = (player.x, player.y)
    found = [m for m in facts.reachable if bindable(m)]
    return min(found, key=lambda m: math.dist(here, (m.x, m.y))) if found else None


def bind_said(facts: BuffFacts, monster: Monster) -> str | None:
    """The cast's line in the service's log."""
    return (
        f'Macro: bind: {skill_name(BIND_DEMON)} on {label(monster)}: no bound demon out in a tier 4-5 Herald pack '
        'fight (the pack kept on a demon)'
    )
