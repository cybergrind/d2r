"""The death in Flayer Dungeon Level 1, 2026-10-23 18:57:45 (take 20261023T155650Z-88, area 88, the KP_6 terror zone
loop; rca/2026-10-23/death-manaburn-findings.md) as a situation: danger_fights.py `cut` from 18:57:29.0, as the tier 5
Herald pack of Dark Shapes (monstats 42, wraith5: Extra Fast, Mana Burn, Fire Enchanted, the Herald's aura) came, with
nine plain Dark Shapes and the Flayers (398, fetishblow3) about, and the mana the arena does not count (game.py: "mana
is not counted") played as the take shows it:

- the pool: the take's 745, back at REGEN a second (the take's median over 47 rises with no blow and no potion);
- the costs, the take's falls at each key with no hurt near: Teleport 11, the strike 16, Blade Warp 15, Psychic Ward
  54 (COSTS); a cast its mana does not pay for is not cast (the key does nothing, as the game takes no cast);
- a Rejuvenation fills the mana (the take: 0 -> 745 at 49.67, 51.27, 52.28, 53.43 s);
- the burn: every melee blow of a type whose monstats attack carries the mana element (wraith5's A1: El1Type mana,
  El1Pct(H) 70, 200-300) that lands burns, with its row's chance, an even roll over that times BURN_RAISE, the take's
  one blow of one attacker (46.72 s: 745 -> 277, 468) and the falls of 524-660 by several in a frame. Wraith5 drains by
  its type: the nine plain Dark Shapes (no Mana Burn modifier) made the first burn and the burn to 0 (the take's hurts);
- the Dark Shapes' blows: fitted on the take (`Swarm`): each within CONTACT of the character lands CONTACT_RATE
  blows a second of BLOW points (the take's 6828 life over 70.9 Dark-Shape-seconds within 3), each burning as above;
  the strike and the pets take PACK_DAMAGE of the arena's points off the Herald pack (physical immune: `dented`);
  in the character's Sigil: Lethargy (SIGIL_SLOWS) a Dark Shape's blows come at its factor and its pace stays the
  take's under the slow (2026-10-23, the sigil agent's find, rca/2026-10-23/sigil-opener-findings.md §4);
- the pace: the take's Herald pack members ran 15.6 units a second (median over 0.5 s windows, 2830), the plain ones
  8.2 (679);
- the companions: the mercenary and the bound demon lived past the character, the Defiler fell at 52.74 s of the
  take (FALLS).

The recording: mana 745 -> 277 at 46.72 s (8.4 s into the play), 0 at 49.07 (10.8), life 2943 -> 0 at 54.36 (16.1).

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.manaburn_death --cut
    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.manaburn_death --seeds 20
"""

import argparse
import functools
import json
import math
import random
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from inventory_tracking.combat.sim.monsters import GAME_RATE, MELEE
from inventory_tracking.game.layout import FULL_REJUVENATION
from inventory_tracking.game.records import NO_OWNER
from tests.inventory_tracking.scenarios.arena.game import MANA_SHOWN, RECOVERY_SHARE, SIGIL_SLOWS
from tests.inventory_tracking.scenarios.arena.situations import danger_fights as fights
from tests.inventory_tracking.scenarios.arena.situations.canyon_death import Dips
from tests.inventory_tracking.scenarios.arena.situations.fane_death import ALL_ON
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Outcome, Situation, dump, load, once
from tests.inventory_tracking.scenarios.arena.situations.stage import Hurt, Stage


NAME = 'manaburn-death-1857'
TAKE = '20261023T155650Z-88'
START = 38.277  # seconds of the take the cut begins at (18:57:29.0)
FIGHT = (TAKE, '2026-10-23T18:57:29.0')
SECONDS = 17.0
PLAYED = 32.0  # the take's 17 s and as long again, so a fight the belt only puts off is played to its end
DIED_AT = 54.36 - START
BURNT_AT = 46.72 - START
# Monster types whose melee attack carries the mana element (monstats El1-3Type 'mana', Hell): type -> (chance, least,
# most). wraith5 (42) is this take's; the rest of the family is combat/threats/drain_escape.py MANA_ELEMENT.
MANA_BLOW = {42: (0.70, 200.0, 300.0)}
BURN_RAISE = 1.9  # the take's 468 of one blow over the row's 250 mean
MANA_BURN = 25  # monumod manahit: a blow of a member with it burns as its type's (the arena plays no more for it)
REGEN = 36.0  # mana a second
COSTS = {'teleport': 11.0, 'strike': 16.0, 'warp': 15.0, 'ward': 54.0}
PACK_PACE, PLAIN_PACE = 15.6, 8.2  # units a second of type 42: the Herald pack's (Extra Fast) and the plain ones
WRAITH = 42
PACK_FLAGS = 8 | 16  # a unique (the Herald) or a minion
DEFILER = 744
# The strike's and the pets' points on a member of the Herald pack, as a share of the arena's: Dark Shapes are immune
# to physical (monstats ResDm(H) 100) and the arena's blades do not know it. The take's 15 members lost 0-37 of 128
# (mean 14 %) and the Herald 5 in the 16 s; the arena's at 1.0 lost 40-68 % in 17 s (3 seeds), 0.25 sits on the take
PACK_DAMAGE = 0.25
# The Dark Shapes' blows, fitted on the take instead of the arena's pooled melee fit (0.3 of the swings on the
# character take life, the Psychic Ward's stun on the striker): every one within CONTACT of the character lands
# CONTACT_RATE blows a second on it, each an even roll over BLOW (after the resistances, the ward and the blocks: the
# fit is on the life lost), so the take's 6828 life lost over its 70.9 Dark-Shape-seconds within 3 (96 a second each,
# 46.7-54.4 s) is played; each blow burns the mana as MANA_BLOW says. The arena's own blows of the type are 0 (`paced`)
CONTACT = 3.0
CONTACT_RATE = 0.96
BLOW = (50.0, 150.0)
AWARE = 60.0  # units within which a Dark Shape follows the character (the take: each of its hops of 8-24 followed)
FALLS = {DEFILER: 52.74 - START}


def cut() -> Situation:
    found = fights.cut(
        NAME, fight=FIGHT, seconds=SECONDS,
        about='2026-10-23 18:57:29.0: the tier 5 Dark Shape Herald pack in Flayer Dungeon Level 1 (manaburn_death.py)',
    )  # fmt: skip
    if found.orders is not None:  # Battle Orders went off with the death only
        found.orders = replace(found.orders, ends=SECONDS + 120.0)
    found.curses = tuple(row for row in found.curses if row[0] < DIED_AT - 0.5)
    found.scene.mobs = [
        replace(mob, life=mob.full) if mob.owner is not None and mob.txt == fights_mercenary() else mob
        for mob in found.scene.mobs
    ]
    hero = found.scene.hero
    found.scene.hero = replace(hero, mana=hero.max_mana or 745.0, max_mana=hero.max_mana or 745.0)
    found.rules = tuple(sorted({*found.rules, MANA_SHOWN}))
    found.aware = AWARE
    # Ghosts stand in each other and on the character (the take: 20 within 3 of it): no body bars them
    found.rules = tuple(rule for rule in found.rules if rule != 'bodies block')
    found.assumed.update({
        'orders': 'Battle Orders up through the play (its state went off with the death)',
        'scene.mercenary': 'the mercenary at its full life (the take: 128/128 to the end)',
        'mana': f'regenerated at {REGEN}/s, spent {COSTS}, burnt by each landed melee blow of a mana-element type '
        f'({MANA_BLOW}, x{BURN_RAISE}), filled by a Rejuvenation (manaburn_death.py `Mana`)',
        'pack damage': f'the strike and the pets take {PACK_DAMAGE} of the arena\'s points off the Herald pack\'s '
        'Dark Shapes (physical immune; the take\'s members lost 14 % in 16 s)',
        'pace': f'type {WRAITH}: the Herald pack {PACK_PACE}, the plain {PLAIN_PACE} units a second (the take)',
    })  # fmt: skip
    return found


def fights_mercenary() -> int:
    from tests.inventory_tracking.scenarios.arena.situations.canyon_death import MERCENARY

    return MERCENARY


@functools.cache
def stored() -> Situation:
    return load(FIXTURES / f'{NAME}.json')


class Mana:
    """The character's mana as the module text plays it, on the arena's `Stage`: the keys it does not pay for are not
    cast, the blows of a mana-element type burn it, a Rejuvenation fills it, and the macro reads it each tick (game.py
    MANA_SHOWN shows the hero's). Hooked on the stage at the first tick (`hook`)."""

    def __init__(self, seed: int) -> None:
        self.rolls = random.Random(seed * 7_727 + 88)
        self.hooked = False
        self.blows: list[int] = []  # the types of this tick's blows on the character (`Swarm`)
        self.series: list[tuple[float, float]] = []  # (clock, mana) each tick
        self.burns: list[tuple[float, float]] = []  # (clock, points) each burning blow
        self.refused: list[tuple[float, str]] = []  # (clock, what) a cast the mana did not pay for

    def get(self, stage: Stage) -> float:
        return stage.scene.hero.mana

    def put(self, stage: Stage, mana: float) -> None:
        hero = stage.scene.hero
        stage.scene.hero = replace(hero, mana=max(0.0, min(mana, hero.max_mana)))

    def pays(self, stage: Stage, what: str) -> bool:
        cost = COSTS[what]
        if self.get(stage) < cost:
            self.refused.append((stage.clock.now, what))
            return False
        self.put(stage, self.get(stage) - cost)
        return True

    def hook(self, stage: Stage) -> None:
        hop, warp, strike, drink, quick = stage.hop, stage.warp, stage.strike, stage.drink, stage.quick_cast
        mana = self

        def paid_hop() -> None:
            if stage.instant_moves or mana.pays(stage, 'teleport'):
                hop()

        def paid_warp() -> None:
            if mana.pays(stage, 'warp'):
                warp()

        def paid_strike() -> None:
            if mana.pays(stage, 'strike'):
                strike()

        def paid_quick(name: str) -> None:
            from inventory_tracking.builds.warlock.skills import PSYCHIC_WARD
            from tests.inventory_tracking.macros.fakes import KEYS

            if name == KEYS.get(PSYCHIC_WARD) and not mana.pays(stage, 'ward'):
                return
            quick(name)

        def filling_drink(column: int, who: str) -> bool:
            class_id = stage.loot.belt[column - 1]
            done = drink(column, who)
            if done and class_id == FULL_REJUVENATION:
                mana.put(stage, stage.scene.hero.max_mana)
                stage.show()
            return done

        stage.hop, stage.warp, stage.strike = paid_hop, paid_warp, paid_strike  # type: ignore[method-assign]
        stage.drink, stage.quick_cast = filling_drink, paid_quick  # type: ignore[method-assign]
        self.hooked = True

    def __call__(self, stage: Stage, _routed: Any) -> None:
        if not self.hooked:
            self.hook(stage)
            dented(stage)
        if stage.over is not None:
            return
        now = stage.clock.now
        mana = self.get(stage) + REGEN / GAME_RATE
        for txt in self.blows:
            blow = MANA_BLOW.get(txt)
            if blow is None:
                continue
            chance, least, most = blow
            if self.rolls.random() < chance:
                points = self.rolls.uniform(least, most) * BURN_RAISE
                mana -= points
                self.burns.append((now, points))
        self.blows = []
        self.put(stage, mana)
        self.series.append((now, self.get(stage)))
        stage.show()


class Swarm:
    """The Dark Shapes' blows on the character as the take shows them (CONTACT, CONTACT_RATE, BLOW): each tick each
    live one within CONTACT lands with CONTACT_RATE / GAME_RATE, its points off the life (a stagger when the tick's
    take RECOVERY_SHARE of the most, the death at 0), its type handed to `Mana` for the burn."""

    def __init__(self, seed: int, mana: Mana) -> None:
        self.rolls = random.Random(seed * 3_571 + 42)
        self.mana = mana
        self.contact = 0.0  # Dark-Shape-seconds within CONTACT (the take: 70.9 over its 16 s)

    def __call__(self, stage: Stage, _routed: Any) -> None:
        if stage.over is not None:
            return
        now, here = stage.clock.now, stage.here
        mobs, taken = stage.cast.mobs, 0.0
        slows = SIGIL_SLOWS in stage.rules
        for unit in stage.cast.live():
            mob = mobs[unit]
            if mob.txt != WRAITH or math.dist(mob.at, here) > CONTACT:
                continue
            self.contact += 1 / GAME_RATE
            # In the character's sigil a swing takes twice as long (game.py SIGIL_SLOWS; 2026-10-23, found by the
            # sigil agent: rca/2026-10-23/sigil-opener-findings.md §4)
            factor = stage.slow_at(mob.at) if slows else 1.0
            if self.rolls.random() < CONTACT_RATE * factor / GAME_RATE:
                points = self.rolls.uniform(*BLOW)
                taken += points
                stage.cast.hurts.append(Hurt(now, unit, WRAITH, MELEE, points))
                self.mana.blows.append(WRAITH)
        if not taken:
            return
        stage.taken += taken
        stage.life -= taken
        if stage.life <= 0.0:
            stage.die(now)
            return
        if taken >= stage.max_life * RECOVERY_SHARE:
            stage.stagger(now)
        stage.show()


def paced(stage: Stage, _routed: Any) -> None:
    """Type 42's walkers at the take's pace, a Herald pack member's (Extra Fast) else the plain one's, each going for
    the character (the take: up to 20 within 3 of it, the mercenary and the bound demon at full life)."""
    pack, mobs = stage.cast.pack, stage.cast.mobs
    for unit, walker in pack.walkers.items():
        mob = mobs.get(unit)
        if walker.txt != WRAITH or mob is None or getattr(walker, '_paced', False):
            continue
        fast = bool(getattr(mob, 'flags', 0) & PACK_FLAGS) or 6 in tuple(getattr(mob, 'mods', ()))
        walker.traits = replace(walker.traits, speed=(PACK_PACE if fast else PLAIN_PACE) / GAME_RATE)
        walker.traits = replace(walker.traits, damage=(0.0, 0.0))  # its blows are the take's (`Swarm`)
        walker.charging = True  # it closes in, never held off (the take: none stood off a reachable character)
        walker.favour = -1.0  # every one went for the character (the take: 20 within 3 of it, the companions unhurt)
        walker._paced = True  # type: ignore[attr-defined]
        # The pace is the walker's own under the sigil's slow too: mobs.py `Horde._slow` puts each walker back on its
        # `base` every frame (2026-10-23, sigil-opener-findings.md §4: it walked at the row's 8.5 and struck besides)
        base = getattr(pack, 'base', None)
        if base is not None:
            base[unit] = walker.traits


def dented(stage: Stage) -> None:
    """A blow on a member of the Herald pack of type 42 (a leader or a minion) takes PACK_DAMAGE of its points."""
    hit, mobs = stage.cast.hit, stage.cast.mobs

    def immune_hit(unit: int, points: float, *, by_pet: bool = False) -> bool:
        mob = mobs.get(unit)
        if mob is not None and mob.txt == WRAITH and mob.flags & PACK_FLAGS:
            points *= PACK_DAMAGE
        return hit(unit, points, by_pet=by_pet)

    stage.cast.hit = immune_hit  # type: ignore[method-assign]


def falls(stage: Stage, _routed: Any) -> None:
    """A companion of a type FALLS names is gone from its time on, as in the take."""
    now = stage.clock.now
    kept, gone = [], []
    for monster in stage.world.monsters:
        due = FALLS.get(monster.txt_id) if monster.ally or monster.owner != NO_OWNER else None
        (gone if due is not None and now >= due else kept).append(monster)
    if gone:
        stage.pet_deaths.extend((now, m.unit_id, m.txt_id) for m in gone)
        stage.world = replace(stage.world, monsters=tuple(kept))


def pursued(situation: Situation | None = None, seconds: float = PLAYED) -> Situation:
    """The fight as the live loop played it: the TZ run's pursuit, one KP_1 press, `seconds` long."""
    return (situation or stored()).logic('new').variant(presses=(once('pickup'),), seconds=seconds)


def play(
    values: Mapping[str, bool], seed: int, situation: Situation | None = None, lap: float | None = 0.02
) -> tuple[fights.Measures, float, Outcome, Mana]:
    """One play of the pursuit with the fixes `values`: its measures, the lowest share of life before potions, the
    outcome and the mana's record."""
    from tests.inventory_tracking.scenarios.arena.situations.fane_death import play as fane_play

    dips, mana = Dips(), Mana(seed)
    swarm = Swarm(seed, mana)

    def extra(stage: Stage, routed: Any) -> None:
        routed.progress.wanted = lambda area: True  # the level is a terror zone (terror/tracker.py)
        paced(stage, routed)
        falls(stage, routed)
        swarm(stage, routed)
        mana(stage, routed)
        dips(stage, routed)

    outcome = fane_play(pursued(situation), values, seed, lap=lap, extra=extra)
    mana.contact = swarm.contact  # type: ignore[attr-defined]
    return fights.measures(outcome), round(max(dips.low, 0.0), 3), outcome, mana


def summary(seed: int, values: Mapping[str, bool] = ALL_ON) -> dict[str, Any]:
    measured, dip, outcome, mana = play(values, seed)
    stage: Stage = outcome.stage_  # type: ignore[attr-defined]
    zero = next((t for t, m in mana.series if m < COSTS['teleport']), None)
    return {
        'seed': seed, 'dead': measured.dead_at, 'low': dip, 'kills': measured.kills, 'rejuv': measured.rejuvenations,
        'hops': measured.hops, 'burns': len(mana.burns), 'first_burn': mana.burns[0][0] if mana.burns else None,
        'mana_out': zero, 'contact': round(getattr(mana, 'contact', 0.0), 1), 'refused': len(mana.refused),
        'herald': stage.fell.get(HERALD),
    }  # fmt: skip


HERALD = 4252704539


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cut', action='store_true', help='cut the situation from its take into the fixtures')
    parser.add_argument('--seeds', type=int, default=0)
    parser.add_argument('--out', type=Path, default=None)
    args = parser.parse_args(argv)
    if args.cut:
        dump(cut(), FIXTURES / f'{NAME}.json')
        stored.cache_clear()
    for seed in range(1, args.seeds + 1):
        row = summary(seed)
        print(json.dumps(row), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
