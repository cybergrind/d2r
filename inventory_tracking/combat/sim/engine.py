"""The simulator (combat/plan.md stage 4): casts at given frames and focal points, the blades
emulated (mechanics/echoing_strike.py), contacts with the monsters' recorded positions
(mechanics/hits.py radius), damage per contact from data/damage.json with the duplicate rule
(skills.txt calc6: blades after the first of a cast on a monster deal DUPLICATE of it), deaths
when the points run out. Monsters move open loop along their recorded paths; a monster the
simulation kills takes no more contacts, one it has not killed yet keeps its recorded path to its
recorded end. The companions (the mercenary, the bound demon, the Defiler) deal a rate of points
per frame to the nearest live hostile within their reach while they stand there (data/damage.json
`companions`, from the recorded drops no blade explains, 2026-10-10). The Defiler's Health Link
(skills.txt 405) links up to LINKS live hostiles nearest it within its aura range; damage to a
linked monster is dealt again at SHARE to every other linked one (data/damage.json `health_link`;
user, 2026-10-10: "our companion casts an aura that makes mobs share a portion of damage"). Hex
Purge (skills.txt 389, a buff on the character) hexes every monster a blade hits; when a hexed
monster dies it explodes for `points` of magic damage on every live hostile within `radius`
(data/damage.json `hex_purge`; the trigger taken as death from the takes, user 2026-10-10: "doing
AoE damage"). Death Mark (skills.txt 375) at the situation's recorded presses makes the marked monster
take `more_damage` more from every source for `frames` (data/damage.json `death_mark`). Sigil:
Lethargy lowers what monsters deal, not what they take: nothing here.

The calibration gate (`replay`): the recorded casts replayed with their focal points, compared
with the recorded kills and life drops.
"""

import math
import statistics
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from inventory_tracking.combat.mechanics.damage import (
    DEFILER,
    companion_table,
    damage_table,
    explosion_table,
    link_table,
    mana_table,
    mark_table,
)
from inventory_tracking.combat.mechanics.echoing_strike import OUT_FRAMES, cast
from inventory_tracking.combat.mechanics.hits import CONTACT_RADIUS, HIT_LAG
from inventory_tracking.combat.policy import DUPLICATE, RUN_MODES, Foe, Observation, Policy, linked_set
from inventory_tracking.combat.sim.situation import Situation


Point = tuple[float, float]
KILL_TOLERANCE = 0.2  # a simulated kill within this share of the recorded time from first sight counts as matched
KILL_FLOOR_FRAMES = 12  # and never tighter than this
COMPANION_NEAR = 8.0  # units: a monster a companion came this near carries the companion model too
LIFE_EXPLAINED = 0.8  # the gate: mean share of a recorded kill's life the simulation had taken by its death
DAMAGE_BAND = 0.15  # the gate: simulated over recorded damage within this of 1
CURVE_GAP = 0.1  # the gate: the bias of the blades' side of the life curves within this share of a life
CURVE_MONSTERS = 5  # fewer monsters away from the companions than this say nothing


def fitted_mana(situation: Situation, pool: float, cost: float) -> tuple[float, float, float]:
    """(pool, regeneration per frame, cost) with the smallest regeneration that keeps the recorded
    casts above zero from a full pool: the mana economy the player actually had (potions, mana after
    kill and gear regeneration included), until a take records the mana itself."""
    from inventory_tracking.combat.sim.input import BIRTH_LAG

    starts = sorted(c.frame - BIRTH_LAG for c in situation.casts)
    if not starts:
        return (pool, 0.0, cost)
    first = starts[0]
    needed = 0.0
    for count, frame in enumerate(starts, start=1):
        spent = count * cost - pool
        elapsed = frame - first
        if spent > 0 and elapsed > 0:
            needed = max(needed, spent / elapsed)
        elif spent > 0:
            needed = math.inf
    return (pool, needed if needed != math.inf else 0.0, cost)


BLADES, COMPANIONS, LINK, EXPLOSIONS = 'blades', 'companions', 'link', 'explosions'


@dataclass
class Outcome:
    deaths: dict[int, int] = field(default_factory=dict)  # monster unit -> frame it died in the simulation
    dealt_by: dict[int, list[tuple[int, float]]] = field(default_factory=dict)  # monster unit -> [(frame, points)]
    damage: dict[int, float] = field(default_factory=dict)  # monster unit -> points dealt by the blades
    companion_damage: dict[int, float] = field(default_factory=dict)  # monster unit -> points dealt by companions
    linked_damage: dict[int, float] = field(default_factory=dict)  # monster unit -> points shared through Health Link
    explosion_damage: dict[int, float] = field(default_factory=dict)  # monster unit -> points from Hex Purge explosions
    mark_damage: dict[int, float] = field(default_factory=dict)  # monster unit -> the extra points Death Mark added
    # Source (BLADES, COMPANIONS, LINK, EXPLOSIONS) -> the life it took off the monsters. The bags above hold
    # the blows as struck (a 1,000-point blow on a monster with 100 left is 1,000 there, 100 here): the
    # blows are what Health Link shares and what the life curves follow; the life taken is the score.
    removed: dict[str, float] = field(default_factory=dict)
    contacts: int = 0
    casts: int = 0
    cast_frames: list[tuple[int, Point]] = field(default_factory=list)  # (birth frame, focal) of every cast made
    mana_low: float = math.inf  # the lowest the mana pool went (negative: the casts outran the model's pool)
    casts_refused: int = 0  # policy casts the mana pool refused
    blades_walled: int = 0  # blades a wall or closed door stopped on the way out (no return leg)

    @property
    def blade_damage(self) -> float:
        return sum(self.damage.values())

    @property
    def effective_damage(self) -> float:
        """The life the simulation took off the monsters, from every source."""
        return sum(self.removed.values())

    @property
    def placement(self) -> float:
        """The life the blades took, directly and through the link: what the aim decides."""
        return self.removed.get(BLADES, 0.0) + self.removed.get(LINK, 0.0)

    @property
    def total_damage(self) -> float:
        """The blows as struck, overkill included (a diagnostic; the score is `effective_damage`)."""
        extra = sum(self.companion_damage.values()) + sum(self.linked_damage.values())
        return self.blade_damage + extra + sum(self.explosion_damage.values()) + sum(self.mark_damage.values())


def simulate(
    situation: Situation,
    casts: list[tuple[int, Point]] | None = None,
    damage_of: Callable[[int], float] | None = None,
    radius: float = CONTACT_RADIUS,
    companions: dict[int, tuple[float, float]] | None = None,
    link: tuple[float, int, float] | None = None,
    explosion: tuple[float, float] | None = None,
    mark: tuple[float, int] | None = None,
    policy: Policy | None = None,
    mana: tuple[float, float, float] | None = None,
    mortal: bool = True,
) -> Outcome:
    """Run the situation frame by frame: the given `casts` ((blade birth frame, focal point)) and,
    with a `policy`, the casts it asks for when the character is free and the mana allows (the
    cadence of sim/input.py). The companions (`companions`: txt id -> (reach, points per frame), the
    data file's by default), the Defiler's Health Link (`link`: (range, links, share)), Hex Purge's
    explosion (`explosion`: (radius, points)), Death Mark (`mark`: (more damage, frames)) and the
    mana model (`mana`: (pool, regeneration per frame, cost)) run alongside. With `mortal` off the
    monsters live exactly as long as the record shows them, whatever the simulation deals (the
    two-sided gate: what the model deals over the recorded exposure); a hexed monster then explodes
    at its recorded death."""
    from inventory_tracking.combat.sim.input import (
        BIRTH_LAG,
        CAST_FRAMES,
    )

    damage_of = damage_of or damage_table()
    companions = companion_table() if companions is None else companions
    link_range, links, share = link_table() if link is None else link
    blast_radius, blast_points = explosion_table() if explosion is None else explosion
    more_damage, mark_frames = mark_table() if mark is None else mark
    pool, regen, cost = mana_table() if mana is None else mana
    marked_until: dict[int, int] = {}
    marks_at: dict[int, list[int]] = {}
    for mark_frame, unit in situation.marks:
        marks_at.setdefault(mark_frame, []).append(unit)
    outcome = Outcome()
    life = {unit: track.life_at_start * track.points for unit, track in situation.monsters.items()}
    first_of: set[tuple[int, int, str]] = set()  # (cast, monster, leg) already hit by a blade of that cast
    by_frame: dict[int, list[tuple[int, int, int, str]]] = {}

    def schedule(index: int, birth: int, focal: Point) -> None:
        """The contacts of one cast, by frame, against the monsters' recorded paths."""
        origin = situation.player_at(birth)
        outcome.casts += 1
        outcome.cast_frames.append((birth, focal))
        walls = situation.blocked_at(birth)
        for blade, path in enumerate(cast(origin, focal, lambda k, f=birth: situation.player_at(f + k), walls)):
            touched: set[tuple[int, str]] = set()
            outcome.blades_walled += len(path) <= OUT_FRAMES  # the out leg broke at a wall
            for k, position in enumerate(path):
                leg = 'out' if k <= OUT_FRAMES else 'back'
                for unit, track in situation.monsters.items():
                    where = track.path.get(birth + k)
                    if where is None or (unit, leg) in touched or math.dist(position, where) > radius:
                        continue
                    touched.add((unit, leg))
                    by_frame.setdefault(birth + k, []).append((index, blade, unit, leg))

    for index, (birth, focal) in enumerate(sorted(casts or [])):
        schedule(index, birth, focal)
    next_index = len(casts or [])

    def alive(unit: int) -> bool:
        return not mortal or (unit not in outcome.deaths and life.get(unit, 0.0) > 0.0)

    recorded_deaths: dict[int, list[int]] = {}
    if not mortal:
        for unit, track in situation.monsters.items():
            if track.recorded_death is not None:
                recorded_deaths.setdefault(track.recorded_death, []).append(unit)

    def explode(unit: int, frame: int) -> None:
        corpse = situation.monsters[unit].path.get(frame) or situation.monsters[unit].path.get(frame - 1)
        for other, track in situation.monsters.items():
            where = track.path.get(frame)
            if other != unit and corpse and where and alive(other) and math.dist(corpse, where) <= blast_radius:
                hurt(other, blast_points, frame, outcome.explosion_damage)

    linked: set[int] = set()
    hexed: set[int] = set()  # monsters a blade has hit: Hex Purge's debuff on them

    sources = {
        id(outcome.damage): BLADES,
        id(outcome.companion_damage): COMPANIONS,
        id(outcome.linked_damage): LINK,
        id(outcome.explosion_damage): EXPLOSIONS,
    }

    def hurt(unit: int, dealt: float, frame: int, bag: dict[int, float]) -> None:
        bag[unit] = bag.get(unit, 0.0) + dealt
        taken = dealt
        if frame <= marked_until.get(unit, -1):
            taken = dealt * (1 + more_damage)
            outcome.mark_damage[unit] = outcome.mark_damage.get(unit, 0.0) + taken - dealt
        outcome.dealt_by.setdefault(unit, []).append((frame, taken))
        source = sources[id(bag)]
        outcome.removed[source] = outcome.removed.get(source, 0.0) + min(taken, max(life[unit], 0.0))
        life[unit] -= taken
        if mortal and life[unit] <= 0.0 and situation.monsters[unit].points > 0:
            outcome.deaths[unit] = frame
            if unit in hexed and blast_points:
                explode(unit, frame)
        if unit in linked and bag is not outcome.linked_damage:
            for other in linked:
                if other != unit and alive(other):
                    hurt(other, dealt * share, frame, outcome.linked_damage)

    current = pool
    busy_until = -1
    for frame in range(situation.start, situation.end + 1):
        current = min(pool, current + regen) if pool else current
        for unit in recorded_deaths.get(frame, ()):
            if unit in hexed and blast_points:
                explode(unit, frame)
        for unit in marks_at.get(frame, ()):
            if alive(unit):
                marked_until[unit] = frame + mark_frames
        live = {
            unit: track.path[frame] for unit, track in situation.monsters.items() if frame in track.path and alive(unit)
        }
        defilers = [c.path[frame] for c in situation.companions.values() if c.txt == DEFILER and frame in c.path]
        linked = set(linked_set(defilers, live, link_range, links))
        if policy is not None and frame >= busy_until:
            seen = Observation(
                situation.player_at(frame),
                {
                    unit: Foe(
                        situation.monsters[unit].txt,
                        where,
                        life[unit],
                        situation.monsters[unit].elite,
                        situation.routes.get(unit, {}).get(frame),
                    )
                    for unit, where in live.items()
                },
                frozenset(linked),
                share,
                situation.blocked_at(frame),  # the doors as they stand at the decision, not at the blades' birth
                situation.modes.get(frame) in RUN_MODES,
                current,
                frozenset(unit for unit, until in marked_until.items() if frame <= until),
                frame,
            )
            choice = policy(seen)
            focal = choice.focal if choice is not None else None
            if focal is not None:
                if pool and current < cost:
                    outcome.casts_refused += 1
                else:
                    current -= cost if pool else 0.0
                    busy_until = frame + CAST_FRAMES
                    schedule(next_index, frame + BIRTH_LAG, focal)
                    next_index += 1
        for birth, _ in casts or ():
            if birth - BIRTH_LAG == frame and pool:
                current -= cost  # the recorded casts spend mana too: the model's pool is tested against them
        outcome.mana_low = min(outcome.mana_low, current)
        for index, _blade, unit, leg in by_frame.get(frame, ()):
            if not alive(unit):
                continue
            key = (index, unit, leg)
            blade_share = DUPLICATE if key in first_of else 1.0
            first_of.add(key)
            outcome.contacts += 1
            hexed.add(unit)
            hurt(unit, damage_of(situation.monsters[unit].txt) * blade_share, frame, outcome.damage)
        for companion in situation.companions.values():
            where = companion.path.get(frame)
            model = companions.get(companion.txt)
            if where is None or model is None:
                continue
            reach, rate = model
            targets = [
                (math.dist(where, track.path[frame]), unit)
                for unit, track in situation.monsters.items()
                if frame in track.path and alive(unit)
            ]
            if targets and min(targets)[0] <= reach:
                hurt(min(targets)[1], rate, frame, outcome.companion_damage)
    return outcome


def score(situation: Situation, outcome: Outcome) -> dict[str, Any]:
    """Effective damage per second over the situation and kills per minute. The damage is the life
    taken off the monsters (`Outcome.removed`), per source with Death Mark's share inside each; the
    blows as struck, overkill and all, are `raw_damage_points`."""
    seconds = situation.seconds or 1.0
    return {
        'kills': len(outcome.deaths),
        'kills_per_minute': round(len(outcome.deaths) / seconds * 60, 1),
        'damage_points': round(outcome.effective_damage),
        'raw_damage_points': round(outcome.total_damage),
        'blade_damage_points': round(outcome.removed.get(BLADES, 0.0)),
        'companion_damage_points': round(outcome.removed.get(COMPANIONS, 0.0)),
        'linked_damage_points': round(outcome.removed.get(LINK, 0.0)),
        'explosion_damage_points': round(outcome.removed.get(EXPLOSIONS, 0.0)),
        'death_mark_points': round(sum(outcome.mark_damage.values())),
        'mana_low': round(outcome.mana_low) if outcome.mana_low != math.inf else None,
        'casts_refused_for_mana': outcome.casts_refused,
        'blades_walled': outcome.blades_walled,
        'damage_per_second': round(outcome.effective_damage / seconds),
        'contacts': outcome.contacts,
        'casts': outcome.casts,
    }


def curves(situation: Situation, outcome: Outcome, lag: int = HIT_LAG, near: float = COMPANION_NEAR) -> dict[str, Any]:
    """How far the simulated life curves run ahead of and behind the recorded ones, as a share of a
    life averaged over each monster's engaged frames (from the first drop, simulated or recorded, to
    its recorded death or last sight), then over the monsters. `ahead` is the simulated loss above
    the recorded loss `lag` frames later (the server's batches make the record late, never early);
    `behind` is the recorded loss above the simulated one at the same frame; `bias` is ahead less
    behind. A simulator that deals too much has a bias above zero, one that deals too little below:
    the gate fails either way. Ahead and behind together without a bias are scatter: contacts put on
    the wrong monster or frame, and the mean damage per contact standing in for a roll (a monster
    with about one blade's worth of life dies of every first contact here and of most in the game).
    Monsters
    no companion came within `near` units of are the blades' own side of the model (`away`); the rest
    carry the companion model too (`near`)."""
    sums = {'away': [0, 0.0, 0.0], 'near': [0, 0.0, 0.0]}
    for unit, track in situation.monsters.items():
        full = track.points * track.life_at_start
        recorded, simulated = sorted(situation.drops.get(unit, ())), sorted(outcome.dealt_by.get(unit, ()))
        if not full or not (recorded or simulated):
            continue
        first = min(found[0][0] for found in (recorded, simulated) if found)
        last = track.recorded_death if track.recorded_death is not None else track.last
        if last < first:
            continue
        beside = any(
            frame in companion.path and math.dist(companion.path[frame], where) <= near
            for frame, where in track.path.items()
            for companion in situation.companions.values()
        )
        r = s = late = 0
        lost = dealt = lost_later = ahead = behind = 0.0
        for frame in range(first, last + 1):
            while s < len(simulated) and simulated[s][0] <= frame:
                dealt += simulated[s][1]
                s += 1
            while r < len(recorded) and recorded[r][0] <= frame:
                lost += recorded[r][1]
                r += 1
            while late < len(recorded) and recorded[late][0] <= frame + lag:
                lost_later += recorded[late][1]
                late += 1
            ahead += max(0.0, min(dealt, full) - min(lost_later, full))
            behind += max(0.0, min(lost, full) - min(dealt, full))
        frames = (last - first + 1) * full
        found = sums['near' if beside else 'away']
        found[0] += 1
        found[1] += ahead / frames
        found[2] += behind / frames
    return {
        side: {
            'monsters': count,
            'ahead': round(ahead / count, 3) if count else None,
            'behind': round(behind / count, 3) if count else None,
            'bias': round((ahead - behind) / count, 3) if count else None,
        }
        for side, (count, ahead, behind) in sums.items()
    }


def verdict(report: dict[str, Any]) -> list[str]:
    """Why a gate report fails; empty when the take passes. The life the simulation explains by each
    recorded kill (median 1.0, mean at least LIFE_EXPLAINED), the damage ratio within DAMAGE_BAND,
    and the bias of the blades' side of the life curves within CURVE_GAP of a life either way."""
    reasons = []
    explained = report['life_explained_at_recorded_kill']
    if explained['median'] is None:
        return ['no recorded kills']
    if explained['median'] < 1.0 or explained['mean'] < LIFE_EXPLAINED:
        reasons.append(f'life explained {explained["median"]} / {explained["mean"]}')
    ratio = report['damage_ratio']
    if ratio is None or abs(ratio - 1) > DAMAGE_BAND:
        reasons.append(f'damage ratio {ratio}')
    away = report['life_curves']['away']
    if away['monsters'] >= CURVE_MONSTERS and abs(away['bias']) > CURVE_GAP:
        reasons.append(f'blades run {"ahead" if away["bias"] > 0 else "behind"} by {abs(away["bias"])}')
    return reasons


def gate(situation: Situation, outcome: Outcome) -> dict[str, Any]:
    """The calibration gate: simulated kills and damage against the recorded ones."""
    recorded = {unit: t.recorded_death for unit, t in situation.monsters.items() if t.recorded_death is not None}
    both = sorted(set(recorded) & set(outcome.deaths))
    # Per recorded kill: the share of the monster's life the simulation had taken by the recorded death.
    explained = []
    for unit, death in recorded.items():
        track = situation.monsters[unit]
        if track.points:
            dealt = sum(points for frame, points in outcome.dealt_by.get(unit, ()) if frame <= death)
            explained.append(min(dealt / (track.points * track.life_at_start), 1.0))
    differences = [outcome.deaths[unit] - recorded[unit] for unit in both]
    within = 0
    for unit in both:
        allowed = max(KILL_FLOOR_FRAMES, KILL_TOLERANCE * (recorded[unit] - situation.monsters[unit].first))
        within += abs(outcome.deaths[unit] - recorded[unit]) <= allowed
    order_pairs = concordant = 0
    for i, a in enumerate(both):
        for b in both[i + 1 :]:
            if recorded[a] != recorded[b] and outcome.deaths[a] != outcome.deaths[b]:  # ties say nothing
                order_pairs += 1
                concordant += (recorded[a] < recorded[b]) == (outcome.deaths[a] < outcome.deaths[b])
    report: dict[str, Any] = {
        'recorded_kills': len(recorded),
        'simulated_kills': len(outcome.deaths),
        'matched_kills': len(both),
        'kills_only_simulated': len(set(outcome.deaths) - set(recorded)),
        'kills_only_recorded': len(set(recorded) - set(outcome.deaths)),
        'kill_time_difference_frames': {
            'median': statistics.median(differences) if differences else None,
            'median_abs': statistics.median(abs(d) for d in differences) if differences else None,
        },
        'kills_within_tolerance': round(within / len(both), 2) if both else None,
        'life_explained_at_recorded_kill': {
            'median': round(statistics.median(explained), 2) if explained else None,
            'mean': round(statistics.fmean(explained), 2) if explained else None,
        },
        'kill_order_agreement': round(concordant / order_pairs, 2) if order_pairs else None,
        'damage_ratio': round(outcome.effective_damage / situation.recorded_damage, 2)
        if situation.recorded_damage
        else None,
        'life_curves': curves(situation, outcome),
    }
    report['fails'] = verdict(report)
    return report


def replay(
    situation: Situation, focal: str = 'fitted', damage_of: Callable[[int], float] | None = None, **options: Any
) -> dict[str, Any]:
    """The recorded casts through the simulator, with the fitted or the pointer focal points;
    `options` go to `simulate` (radius, companions, link, explosion)."""
    casts = [(c.frame, c.fitted if focal == 'fitted' or c.pointer is None else c.pointer) for c in situation.casts]
    outcome = simulate(situation, casts, damage_of, **options)
    return {'focal': focal, 'score': score(situation, outcome), 'gate': gate(situation, outcome)}
