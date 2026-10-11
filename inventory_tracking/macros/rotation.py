"""The casts the hunt makes under its held strike (macros/hunt.py `fight`): Hex: Purge kept up, Death Mark
on a pack worth it, a sigil under an elite, Engorge on a corpse for the demons, and the strike taken
up again after each (`resume`).

`Rotation` keeps when each was last cast and answers whether one is due; the fight decides the order
and holds the strike. Each cast here is one aim and one key.
"""

import math
from collections.abc import Callable

from inventory_tracking.combat.policy import LinePolicy, Policy, observe
from inventory_tracking.combat.stance import BLADES_A_CAST
from inventory_tracking.common import LOG
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.routines import ACTING, on_screen, press_skill, screen_fraction
from inventory_tracking.macros.skills import DEATH_MARK, ENGORGE, HEX_PURGE, SIGIL_LETHARGY
from inventory_tracking.macros.teleport import HOVER_SECONDS, ground_fraction
from inventory_tracking.macros.travel import MONSTER_UNIT_TYPE, label, life
from inventory_tracking.macros.world import DEFILER_CLASS, Monster, World
from inventory_tracking.native.layout import HIRELING_CLASS_ID


# Engorge (skills.txt 379, cast on a corpse): heals the demons 30% of their life and more, and cuts the damage
# they take for 125 + 75 per level frames; cast under the held strike when a demon is hurt, and for the buff
ENGORGE_SECONDS = 15.0  # between two Engorges for the buff
ENGORGE_HURT_SECONDS = 4.0  # between two while a demon is under ENGORGE_BELOW of its life
ENGORGE_BELOW = 0.7
ENGORGE_REACH = 20.0  # world units: a corpse further off is not looked for
ENGORGE_RETRY = 2.0  # seconds before another look when no corpse lay in reach
ENGORGE_LOOKS = 2  # corpses the pointer is put on for one cast at most
ITEM_UNIT_TYPE = 4
# Hex: Purge (skills.txt 389, a buff of 3600 + 300 per level frames): the strikes do their damage through it,
# so attack mode casts it whenever the state does not show it; unseen casts retry after HEX_RETRY, then every
# HEX_DISTRUST seconds
HEX_RETRY = 3.0
HEX_DISTRUST = 60.0
HEX_TRIES = 2
# Death Mark: one monster takes more damage for 125 + 13 per level frames (skills.txt); the strike waits out its cast.
# Only a monster that outlives MARK_CASTS casts is marked; the strike is pressed again under the mark's cast.
MARK_CASTS = 4
RESUME_WAIT = 0.25  # seconds for the macro's own cast to show before the strike is pressed again
SIGIL_SECONDS = 10.0  # between two sigils under the same monster
ELITE_LIFE = 2.0  # a unique's or champion's life in Hell, in its type's points (the tables hold the plain monster's)


class Rotation:
    """When each cast under the strike was last made, and the casts."""

    def __init__(self, policy: Callable[[], Policy]) -> None:
        self.policy = policy  # the hunt's policy now: what a pack is worth to a cast
        self.sigiled: dict[int, float] = {}  # unit id -> clock time of the last sigil under it
        self.marked_at = -math.inf  # clock time of the last Death Mark
        self.engorged_at = -math.inf  # clock time of the last Engorge (or of the last look for a corpse)
        self.purged_at = -math.inf  # clock time of the last Hex: Purge cast
        self.purges_unseen = 0  # casts of it in a row that the character's state did not show after

    def sigil_due(self, run: Run, prey: Monster) -> bool:
        return prey.leader and run.clock() - self.sigiled.get(prey.unit_id, -math.inf) > SIGIL_SECONDS

    def sigil(self, run: Run, world: World, prey: Monster, aspect: float, key_names) -> None:
        """Sigil: Lethargy on the ground under an elite (slows it, lowers its defence)."""
        assert world.player is not None
        run.keys.update(key_names(world, (SIGIL_LETHARGY,)))
        where = ground_fraction(world.player, prey.x, prey.y, aspect)
        if not on_screen(where):
            # Off the screen (the blades reach further than it shows): no sigil now, asked again in a second.
            self.sigiled[prey.unit_id] = run.clock() - SIGIL_SECONDS + 1.0
            return
        run.actuator.aim(*where, scatter=(4, 3))
        press_skill(run, SIGIL_LETHARGY)
        self.sigiled[prey.unit_id] = run.clock()

    def engorge_due(self, run: Run, world: World) -> bool:
        """Whether Engorge is worth a cast now: a demon of the character's is out, and it is hurt or
        the last cast is ENGORGE_SECONDS old."""
        player = world.player
        if run.corpses is None or player is None:
            return False
        demons = [
            m
            for m in world.monsters
            if (m.ally or m.owner == player.unit_id or m.txt_id == DEFILER_CLASS) and m.txt_id != HIRELING_CLASS_ID
        ]
        if not demons:
            return False
        hurt = any(m.max_life and m.life < ENGORGE_BELOW * m.max_life for m in demons)
        return run.clock() - self.engorged_at > (ENGORGE_HURT_SECONDS if hurt else ENGORGE_SECONDS)

    def engorge(self, run: Run, world: World, aspect: float, key_names) -> bool:
        """Engorge on the nearest corpse in view within ENGORGE_REACH; whether it was cast."""
        player = world.player
        assert player is not None
        assert run.corpses is not None
        here = (player.x, player.y)
        near = [
            corpse
            for corpse in run.corpses()
            if math.dist(here, corpse[1:]) <= ENGORGE_REACH and on_screen(ground_fraction(player, *corpse[1:], aspect))
        ]
        if not near:
            self.engorged_at = run.clock() - ENGORGE_HURT_SECONDS + ENGORGE_RETRY
            return False
        run.keys.update(key_names(world, (ENGORGE,)))
        alive = {m.unit_id for m in world.monsters}
        # The nearest corpse the pointer really has under it: of 12 casts on 2026-10-10 the record
        # named a monster under the pointer 11 times and an item's label once, and whether that monster
        # was the corpse was not known (a live one stands on a corpse often: the fight is there).
        for unit, x, y in sorted(near, key=lambda corpse: math.dist(here, corpse[1:]))[:ENGORGE_LOOKS]:
            run.actuator.aim(*ground_fraction(player, x, y, aspect), scatter=(3, 3))
            over = None
            if run.hovered is not None:
                run.pace.sleep(HOVER_SECONDS)
                over = run.hovered()
                # Not cast with a live monster or an item's label under the pointer; with nothing
                # there it is (whether the record shows a corpse at all is not known yet).
                if over is not None and (
                    over[0] == ITEM_UNIT_TYPE or (over[0] == MONSTER_UNIT_TYPE and over[1] in alive)
                ):
                    LOG.info(
                        'Macro: no Engorge at (%.1f, %.1f): under the pointer %s, not the corpse %d', x, y, over, unit
                    )
                    continue
            press_skill(run, ENGORGE)
            self.engorged_at = run.clock()
            LOG.info(
                'Macro: Engorge on the corpse %d at (%.1f, %.1f), %.1f away; under the pointer %s',
                unit, x, y, math.dist(here, (x, y)), over,
            )  # fmt: skip
            return True
        self.engorged_at = run.clock() - ENGORGE_HURT_SECONDS + ENGORGE_RETRY
        return True  # the pointer was moved: the strike's aim is put back

    def resume(self, run: Run, again: Callable[[], None] | None) -> None:
        """The held strike pressed again under a cast of the macro's own (a mark, a sigil, Engorge,
        Hex: Purge), so the game has it waiting when that cast ends: left alone it stood idle 0.37 s
        at the median after a Death Mark before the hold's own press-again came."""
        if again is None:
            return
        run.seen(lambda w: w.player is not None and w.player.mode in ACTING, RESUME_WAIT)
        again()

    def worth_a_mark(self, world: World, target: Monster) -> bool:
        """Whether `target` outlives MARK_CASTS casts on its line: else the mark costs more casting
        than the damage it adds."""
        if world.player is None:
            return False
        current = self.policy()
        policy = current if isinstance(current, LinePolicy) else LinePolicy()
        foe = observe(world.player, [target], ()).foes[target.unit_id]
        full = foe.left * (ELITE_LIFE if foe.elite else 1.0)
        return full > MARK_CASTS * BLADES_A_CAST * policy.damage_of(foe.txt)

    def purge_due(self, run: Run, world: World) -> bool:
        """Whether Hex: Purge is to be cast now: the character's state reads without it."""
        player = world.player
        if player is None or HEX_PURGE not in world.slots:
            return False
        if player.hex_purge is not False:
            self.purges_unseen = 0 if player.hex_purge else self.purges_unseen
            return False
        wait = HEX_RETRY if self.purges_unseen < HEX_TRIES else HEX_DISTRUST
        return run.clock() - self.purged_at > wait

    def purge(self, run: Run, world: World, key_names) -> None:
        """Hex: Purge, a cast on the character itself."""
        if self.purges_unseen == HEX_TRIES:
            LOG.warning('Macro: Hex: Purge cast %d times and the state does not show it', HEX_TRIES)
        run.keys.update(key_names(world, (HEX_PURGE,)))
        press_skill(run, HEX_PURGE)
        self.purged_at = run.clock()
        self.purges_unseen += 1

    def death_mark(self, run: Run, target: Monster, aspect: float, key_names) -> None:
        """Death Mark on `target`: the pointer on its body, then the key (Quick Cast)."""
        world = run.world()
        if world.player is None:
            raise Abort('not in a game')
        run.keys.update(key_names(world, (DEATH_MARK,)))
        point = screen_fraction(world.player, target.x, target.y, aspect)
        if not on_screen(point):
            return
        run.actuator.aim(*point, scatter=(3, 3))
        if all(m.unit_id != target.unit_id for m in run.world().monsters):
            return  # it died under the strike while the pointer went over: no mark on a corpse
        press_skill(run, DEATH_MARK)
        self.marked_at = run.clock()
        run.say(f'Death Mark on {label(target)}, {life(target)}')
