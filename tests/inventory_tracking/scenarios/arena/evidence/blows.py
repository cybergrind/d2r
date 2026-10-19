"""Every drop of the character's life in a take, put on whoever dealt it as far as the take can say.

takes/hurts.py lists a drop's suspects; this goes one step on and names a class for each drop, so
that the monster model can be fitted on the drops one monster dealt alone and the rest is counted,
not guessed. What a take holds that makes this possible, each checked over the 670 schema 2 takes
under runs/combat on 2026-10-12:

- **who owns a missile.** The unit record written at a missile's first sight (missiles.jsonl
  `record`) holds its owner at OWNER: the unit type (0 a player, 1 a monster) and the unit id. Of
  242,904 first sights 130,622 name a player and the rest a monster; of the 30,433 hostile missiles
  the frames then show, 30,307 belong to a monster the take's frames held and 126 to none
  (`UNKNOWN`). It agrees with the game's tables where they name a type's missile
  (pricing/raw/game-excel monstats `MissA1`: all 1,380 `cr_arrow3` are owned by type 162, 936
  `skbowarrow7` by 578, 544 `blowgun` by 659) and also covers what no table ties to a type: the nova
  of a Cold Enchanted monster's death (`coldunique` 194) and the sparks of a Lightning Enchanted one
  (`lightunique` 195) are owned by that monster. So a missile is tied to its shooter by this id,
  not by the type's row and not by co-occurrence;
- **whom a monster is after.** Its path record names a target: the unit type at TARGET_KIND and the
  id at hurts.TARGET_UNIT (0 of type 0: nobody). 577 of the 670 takes hold path records;
- **when a monster strikes.** Its mode in a frame (hurts.ATTACK_MODES), at 25 frames a second.

The classes (CLASSES), decided from the frame before the drop and the frame of it (and every frame
between, when the vitals were not read in some):

- `sole melee`: one hostile in an attack mode, beside the character (hurts.BESIDE) or within
  hurts.SUSPECT_REACH with the character as its target, no hostile missile near, and it is the only
  suspect. A monster of a ranged type striking with no missile of its own in sight falls here too;
  `ranged_type` marks it (its arrow may have landed between two frames);
- `sole ranged`: the hostile missiles near the character (`near_missiles`) all have one live owner,
  and nobody else is striking. The owner striking itself is the same suspect, not a second one;
- `nova/explosion`: the missiles near all belong to one monster that is dead (its death's missiles),
  nobody striking; or, with no suspect at all, a hostile that can burst (`can_burst`: an elemental
  enchantment, or a corpse the threat table has exploding) died within NOVA_RADIUS in the
  NOVA_FRAMES before (`via` 'death nearby': the weaker rule, for an explosion that is no missile);
- `several`: more than one suspect. Left unattributed here (`by` lists them all); rates.py counts
  such a drop both ways, as nobody's and split evenly;
- `unknown`: no suspect: poison and burning, a curse that makes casting cost life, a blow from a
  monster the client does not hold, a drop over a pause of the recorder (`gap`).

Rows are plain dicts (ROW says what they hold), small enough to cache per take as JSON.
"""

import math
import struct
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

from inventory_tracking.combat.mechanics.tables import area_level, tables
from inventory_tracking.combat.sim.monsters import CHAMPION_FLAG, SUPER_FLAG, UNIQUE_FLAG
from inventory_tracking.game.layout import HERALD_TIER_STAT, MINION_FLAG, NO_OWNER
from inventory_tracking.levels.geometry import Point
from inventory_tracking.takes.hurts import (
    ATTACK_MODES,
    BESIDE,
    COLD,
    FIRE,
    HURT_LEAST,
    LIGHTNING,
    MISSILE_REACH,
    SUSPECT_REACH,
    TARGET_UNIT,
    harmless,
    lost,
    missile_point,
)
from inventory_tracking.takes.record import RESIST_STATS
from inventory_tracking.takes.takes import MonsterRow, PlayerRow, Take, player_of
from inventory_tracking.terror.danger import DATA as THREATS
from inventory_tracking.terror.monsters import LEVEL_STAT


THREAT_TABLE = Path(__file__).parents[2] / 'threat' / 'threat_table.json'
# The missile's unit record (missiles.jsonl `record`): its owner's unit type, then its unit id.
# Found by looking for the take's unit ids in the records of 20261012T065226Z-130: 1,771 of 1,866
# records hold one at this offset and nowhere else.
OWNER = 0xE8
PLAYER_KIND, MONSTER_KIND = 0, 1  # unit types as the records hold them
TARGET_KIND = TARGET_UNIT - 4  # path record: the unit type of the target named at hurts.TARGET_UNIT
HERO, FOE, FRIEND, UNKNOWN = 'hero', 'foe', 'friend', 'unknown'  # whose a missile is
NOBODY, OTHER = 'nobody', 'other'  # whom a path record names, beside HERO and FRIEND
# A missile that was in flight in the frame before the drop and is gone in the frame of it ended in
# between: it counts as near from this far, twice hurts.MISSILE_REACH (an arrow covers more than
# three units between two frames).
ENDED_REACH = 2 * MISSILE_REACH
NOVA_RADIUS = 8.0  # units from the character: a hostile's death this near can be what hurt
NOVA_FRAMES = 15  # frames before a drop such a death is looked for in (0.6 s)
BURSTING = frozenset((FIRE, LIGHTNING, COLD))  # the enchantments whose bearer's death is looked at
GAP = 0.5  # seconds between the two read frames of a drop beyond which nobody is blamed
SOLE_MELEE, SOLE_RANGED, NOVA, SEVERAL, NONE = 'sole melee', 'sole ranged', 'nova/explosion', 'several', 'unknown'
CLASSES = (SOLE_MELEE, SOLE_RANGED, NOVA, SEVERAL, NONE)
SWING, MISSILE, DEATH_MISSILE, DEATH = 'swing', 'missile', 'death missile', 'death nearby'  # a suspect's `via`
PLAIN, MINION, CHAMPION, UNIQUE, SUPER = 'plain', 'minion', 'champion', 'unique', 'super unique'
RANKS = (PLAIN, MINION, CHAMPION, UNIQUE, SUPER)
ROW = {
    'take': "the take's directory name",
    'frame': 'index into the frames of the frame the drop shows in',
    't': "seconds from the take's first frame",
    'area': 'the level id',
    'lost': 'points (hurts.lost: a fall of the most life with it is not a blow)',
    'life': 'points left',
    'max_life': 'of how many',
    'share': 'lost / most life before the drop',
    'dead': 'the drop killed',
    'gap': 'seconds between the two read frames',
    'resists': "the character's RESIST_STATS at the last reading before (None: the take holds none)",
    'class': 'one of CLASSES',
    'by': 'the suspects: unit, txt, name, rank, flags, mods, tier, level, away, aimed, mode, via, missile',
    'missiles': 'the hostile missiles near: [txt, distance, owner unit or None, ended]',
    'hero_mode': "the character's mode in the frame before",
    'death_near': 'no suspect, and a hostile that cannot burst died within NOVA_RADIUS in the NOVA_FRAMES before',
    'death_control': 'no suspect, and a hostile died there two to three times NOVA_FRAMES before',
    'foes_near': 'live hostiles within NOVA_RADIUS in the frame before',
    'nearest_striking': 'units to the nearest hostile in an attack mode in the frame before, whoever it is after',
}


def rank_of(flags: int) -> str:
    """A monster's rank by its type flags (sim/monsters.py names the bits): a unique's minion first,
    then a super unique, a champion, a unique."""
    if flags & MINION_FLAG:
        return MINION
    if flags & SUPER_FLAG:
        return SUPER
    if flags & CHAMPION_FLAG:
        return CHAMPION
    return UNIQUE if flags & UNIQUE_FLAG else PLAIN


@cache
def threats() -> dict[str, Any]:
    """terror/data/threats.json: per type its name and whether it fights from range."""
    import json

    return json.loads(THREATS.read_text())['monsters']


def name_of(txt: int) -> str:
    """The type's name: the threat table's, else its monstats `NameStr`, else its number."""
    found = threats().get(str(txt), {}).get('name') or tables()['monsters'].get(str(txt), {}).get('NameStr')
    return found or f'type {txt}'


@cache
def exploding() -> frozenset[int]:
    """The types whose corpse hurts what stands by it: scenarios/threat/threat_table.json `death_damage`."""
    import json

    table = json.loads(THREAT_TABLE.read_text())['monsters']
    return frozenset(int(txt) for txt, row in table.items() if row.get('death_damage'))


def explodes(txt: int) -> bool:
    return txt in exploding()


def ranged_type(txt: int) -> bool:
    return bool(threats().get(str(txt), {}).get('ranged'))


def owner_of(record: str) -> tuple[int, int] | None:
    """(unit type, unit id) of a missile's owner from its unit record (hex); None when the record is
    cut short (a trimmed take keeps no records)."""
    start = 2 * OWNER
    if len(record) < start + 16:
        return None
    return struct.unpack('<II', bytes.fromhex(record[start : start + 16]))


def target_of(record: str) -> tuple[int, int] | None:
    """(unit type, unit id) of a monster's target from its path record (hex); None when too short."""
    start = 2 * TARGET_KIND
    if len(record) < start + 16:
        return None
    return struct.unpack('<II', bytes.fromhex(record[start : start + 16]))


@dataclass
class Flight:
    """One missile in one frame."""

    unit: int
    txt: int
    at: Point
    kind: str  # HERO, FOE, FRIEND or UNKNOWN: whose it is
    owner: int | None  # the owner's unit id; None when not known
    born: float  # the clock of its first sight: with `unit` it names the missile (unit ids come back)

    @property
    def key(self) -> tuple[int, float]:
        return (self.unit, self.born)

    @property
    def hostile(self) -> bool:
        """Can hurt the character: not its own or a companion's, and not one of the harmless ones."""
        return self.kind in (FOE, UNKNOWN) and self.txt not in harmless()


@dataclass
class Moment:
    """One frame, sorted out: the character, the hostiles alive, the dead, the companions, whom each
    monster's path record names (`aims`: HERO, FRIEND, OTHER, NOBODY; absent without a record) and
    the missiles in flight."""

    index: int
    t: float
    hero: PlayerRow | None
    foes: list[MonsterRow] = field(default_factory=list)
    fallen: list[MonsterRow] = field(default_factory=list)
    friends: list[MonsterRow] = field(default_factory=list)
    aims: dict[int, str] = field(default_factory=dict)
    flying: list[Flight] = field(default_factory=list)

    @property
    def read(self) -> bool:
        """The character's vitals were read: a failed read shows life 0 of 0, schema 1 has none."""
        return self.hero is not None and bool(self.hero.max_life)


def whose_of(first: Mapping[str, Any], own: set[int], seen: set[int]) -> tuple[str, int | None]:
    """Whose a missile is by its first sight (a row of missiles.jsonl), and the owner's unit id: the
    character's (any player's), a companion's (`own`), a hostile's the take saw (`seen`), or UNKNOWN:
    no record, or a monster the take's frames never held."""
    owner = owner_of(first.get('record') or '')
    if owner is None:
        return UNKNOWN, None
    if owner[0] == PLAYER_KIND:
        return HERO, owner[1]
    if owner[1] in own:
        return FRIEND, owner[1]
    return (FOE if owner[1] in seen else UNKNOWN), owner[1]


def companions(take: Take) -> set[int]:
    """The unit ids ever seen as the character's own in the take (owned or allied in a frame's row).
    units.jsonl does not hold them at all (20261012T065226Z-130: 7 companions, none in it)."""
    return {m[0] for frame in take.frames for m in frame['m'] if m[9] or m[8] != NO_OWNER}


def walk(take: Take) -> Iterator[Moment]:
    """The take's frames as moments, in order, with the path records and the missiles' first sights
    laid on the frames' clock."""
    own = companions(take)
    seen = {m[0] for frame in take.frames for m in frame['m']} - own
    hero_ids = {frame['p'][0] for frame in take.frames if frame.get('p')}
    aims: dict[int, str] = {}
    firsts = [(first, *whose_of(first, own, seen)) for first in take.missiles]
    # A missile the recorder wrote no first sight of (the character's blades, in some takes) is taken
    # for the character's when every first sight of its type in the take is.
    kinds: dict[int, set[str]] = {}
    for first, whose, _who in firsts:
        kinds.setdefault(first['txt_id'], set()).add(whose)
    born: dict[int, tuple[int, str, int | None, float]] = {}  # missile unit -> txt, whose, owner, first sight
    loose: dict[int, tuple[int, float, int]] = {}  # the same for one without a first sight: txt, clock, frame
    paths, taken, shown = take.paths, 0, 0
    for index, frame in enumerate(take.frames):
        while taken < len(paths) and paths[taken]['t'] <= frame['t']:
            for unit, record in paths[taken]['m']:
                found = target_of(record)
                if found is None:
                    continue
                kind, target = found
                if kind == PLAYER_KIND and target in hero_ids:
                    aims[unit] = HERO
                elif kind == PLAYER_KIND and not target:
                    aims[unit] = NOBODY
                else:
                    aims[unit] = FRIEND if kind == MONSTER_KIND and target in own else OTHER
            taken += 1
        while shown < len(firsts) and firsts[shown][0]['t'] <= frame['t']:
            first, whose, who = firsts[shown]
            born[first['unit_id']] = (first['txt_id'], whose, who, first['t'])
            shown += 1
        moment = Moment(index, frame['t'], player_of(frame))
        for raw in frame['m']:
            monster = MonsterRow(*raw)
            if monster.unit in own or monster.ally or monster.owner != NO_OWNER:
                if monster.alive:
                    moment.friends.append(monster)
            elif monster.alive:
                moment.foes.append(monster)
            else:
                moment.fallen.append(monster)
        moment.aims = {m.unit: aims[m.unit] for m in moment.foes if m.unit in aims}
        for unit, txt, _mode, _x, _y, path in frame['x']:
            if len(path) < 16:
                continue  # a missile whose path record was not read: nowhere to put it
            known = born.get(unit)
            if known is None or known[0] != txt:
                before = loose.get(unit)
                since = before[1] if before is not None and before[0] == txt and before[2] == index - 1 else frame['t']
                loose[unit] = (txt, since, index)
                known = (txt, HERO if kinds.get(txt) == {HERO} else UNKNOWN, None, since)
            moment.flying.append(Flight(unit, txt, missile_point(path), known[1], known[2], known[3]))
        yield moment


def deaths(moments: Sequence[Moment]) -> list[tuple[int, MonsterRow]]:
    """(frame index, the row of its last live frame) of each hostile that the next frame shows dead."""
    found = []
    alive: dict[int, MonsterRow] = {}
    for moment in moments:
        for monster in moment.fallen:
            before = alive.pop(monster.unit, None)
            if before is not None:
                found.append((moment.index, before))
        alive.update((monster.unit, monster) for monster in moment.foes)
    return found


class Readings:
    """The character's resistances over a take: the manifest's at its start, then each `hurt` event's
    (cut.py `resists_at`, without reading the events again for every drop)."""

    def __init__(self, take: Take) -> None:
        stats = take.manifest.get('character_stats')
        self.first = [int(stats.get(str(stat), 0)) for stat in RESIST_STATS] if stats else None
        self.later = [
            (event['t'], [int(value) for value in event['resists']])
            for event in take.events
            if event['event'] == 'hurt' and event.get('resists')
        ]

    def at(self, t: float) -> list[int] | None:
        found = self.first
        for clock, resists in self.later:
            if clock > t:
                break
            found = resists
        return found


def near_missiles(before: Sequence[Moment], after: Moment) -> list[list[Any]]:
    """The hostile missiles near the character in the frames `before` a drop: within
    hurts.MISSILE_REACH, or within ENDED_REACH and gone by the frame of the drop. Each
    `[txt, distance, owner, ended]`, of each missile its nearest sight, nearest first."""
    still = {flight.key for flight in after.flying}
    found: dict[tuple[int, float], list[Any]] = {}
    for moment in before:
        if moment.hero is None:
            continue
        for flight in moment.flying:
            if not flight.hostile:
                continue
            away = math.dist(flight.at, moment.hero.at)
            ended = flight.key not in still
            if away <= MISSILE_REACH or (ended and away <= ENDED_REACH):
                kept = found.get(flight.key)
                if kept is None or away < kept[1]:
                    found[flight.key] = [flight.txt, round(away, 1), flight.owner, ended and away > MISSILE_REACH]
    return sorted(found.values(), key=lambda row: row[1])


class Roster:
    """What a take knows of each unit beyond a frame's row: its level, its Herald's tier and its
    enchantments (units.jsonl; `mods` for a take from before they were written, hurts.enchantments)."""

    def __init__(self, take: Take, mods: Mapping[int, Sequence[int]] | None = None) -> None:
        self.units = {unit['unit']: unit for unit in take.units}
        self.given = mods or {}

    def mods(self, unit: int) -> list[int] | None:
        row = self.units.get(unit)
        if row is not None and 'mods' in row:
            return [*row['mods']]
        return [*self.given[unit]] if unit in self.given else None

    def stat(self, unit: int, stat: int) -> int:
        return int((self.units.get(unit) or {}).get('stats', {}).get(str(stat), 0))

    def suspect(self, monster: MonsterRow, away: float, aim: str | None, via: str, area: int) -> dict[str, Any]:
        return {
            'unit': monster.unit,
            'txt': monster.txt,
            'name': name_of(monster.txt),
            'rank': rank_of(monster.flags),
            'flags': monster.flags,
            'mods': self.mods(monster.unit),
            'tier': self.stat(monster.unit, HERALD_TIER_STAT),
            'level': self.stat(monster.unit, LEVEL_STAT) or area_level(area) or 0,
            'away': round(away, 1),
            'aimed': None if aim is None else int(aim == HERO),
            'mode': monster.mode,
            'via': via,
            'missile': None,
        }


def strikers(before: Sequence[Moment], after: Moment) -> dict[int, tuple[MonsterRow, float, str | None]]:
    """The hostiles striking at a drop, as hurts.sole has them: in an attack mode in one of the frames,
    beside the character or within hurts.SUSPECT_REACH with the character as their target. Of each
    the nearest striking sight (the row, the distance, whom its path record names)."""
    found: dict[int, tuple[MonsterRow, float, str | None]] = {}
    at = before[0].hero.at if before and before[0].hero else None
    for moment in (*before, after):
        if at is None:
            break
        for monster in moment.foes:
            if monster.mode not in ATTACK_MODES:
                continue
            away = math.dist(monster.at, at)
            aim = moment.aims.get(monster.unit)
            if away > SUSPECT_REACH or not (away <= BESIDE or aim == HERO):
                continue
            if monster.unit not in found or away < found[monster.unit][1]:
                found[monster.unit] = (monster, away, aim)
    return found


def can_burst(txt: int, mods: Sequence[int] | None) -> bool:
    """Whether a death of such a monster can hurt by itself, as far as the tables say: it carries an
    elemental enchantment (monumod 9 fire, 17 lightning, 18 cold: hurts.py's names) or its corpse
    explodes (the threat table's `death_damage`, monstats `deathDmg`). Over all takes a death of a
    monster with neither was followed by a drop no more often than it was preceded by one."""
    return bool(mods and BURSTING.intersection(mods)) or explodes(txt)


def classify(by: Sequence[Mapping[str, Any]], unowned: int) -> str:
    """The class of a drop from its suspects (`by`, one per unit) and the count of hostile missiles
    near whose owner is not known (each a suspect nobody can name)."""
    if len(by) + (1 if unowned else 0) > 1:
        return SEVERAL
    if unowned:
        return NONE  # something flew by, and whose it was the take does not say
    if not by:
        return NONE
    return {SWING: SOLE_MELEE, MISSILE: SOLE_RANGED}.get(by[0]['via'], NOVA)


def blows(
    take: Take,
    mods: Mapping[int, Sequence[int]] | None = None,
    moments: Sequence[Moment] | None = None,
) -> list[dict[str, Any]]:
    """The rows of a take (ROW), one per drop of the character's life of hurts.HURT_LEAST points or
    more. A frame whose vitals were not read is passed over and the drop counted across it, as
    calibrate.py `life_lost` does. `mods` (unit id -> monumod ids) are the enchantments of a take
    recorded before it held them; `moments` the take's frames already walked."""
    moments = list(walk(take)) if moments is None else moments
    if take.schema < 2 or not moments:
        return []
    roster, readings = Roster(take, mods), Readings(take)
    start = moments[0].t
    last_seen: dict[int, MonsterRow] = {}
    died: dict[int, tuple[int, MonsterRow]] = {}
    found: list[dict[str, Any]] = []
    before: Moment | None = None
    for moment in moments:
        for monster in moment.fallen:
            if monster.unit in last_seen:
                died[monster.unit] = (moment.index, last_seen.pop(monster.unit))
        for monster in moment.foes:
            last_seen[monster.unit] = monster
            died.pop(monster.unit, None)  # raised again (a shaman's Fallen): alive, whatever it was
        if not moment.read:
            continue
        hero = moment.hero
        assert hero is not None
        assert hero.life is not None
        assert hero.max_life is not None
        if before is not None and before.hero is not None and before.hero.unit == hero.unit:
            past = before.hero
            assert past.life is not None
            assert past.max_life is not None
            fell = lost(past.life, past.max_life, hero.life, hero.max_life)
            if fell >= HURT_LEAST:
                span = moments[before.index : moment.index]
                gap = moment.t - before.t
                by: list[dict[str, Any]] = []
                near = near_missiles(span, moment) if gap <= GAP else []
                if gap <= GAP:
                    for monster, away, aim in strikers(span, moment).values():
                        by.append(roster.suspect(monster, away, aim, SWING, hero.area))
                unowned = 0
                for txt, _away, owner, _ended in near:
                    if owner is None or (owner not in last_seen and owner not in died):
                        unowned += 1
                        continue
                    gone = owner in died
                    monster = died[owner][1] if gone else last_seen[owner]
                    kept = next((s for s in by if s['unit'] == owner), None)
                    if kept is None:
                        away = math.dist(monster.at, past.at)
                        kept = roster.suspect(monster, away, before.aims.get(owner), MISSILE, hero.area)
                        by.append(kept)
                    kept['via'] = DEATH_MISSILE if gone else MISSILE
                    kept['missile'] = kept['missile'] or txt
                death_near = death_control = False
                if not by and not unowned and gap <= GAP:
                    close = sorted(
                        (
                            (math.dist(monster.at, past.at), moment.index - index, monster)
                            for index, monster in died.values()
                            if moment.index - 3 * NOVA_FRAMES < index <= moment.index
                        ),
                        key=lambda found: found[0],
                    )
                    close = [found for found in close if found[0] <= NOVA_RADIUS]
                    fresh = [found for found in close if found[1] < NOVA_FRAMES]
                    by = [
                        roster.suspect(monster, away, None, DEATH, hero.area)
                        for away, _ago, monster in fresh
                        if can_burst(monster.txt, roster.mods(monster.unit))
                    ]
                    # What a death nearby is worth as a clue: how often a drop nobody can be blamed
                    # for has one just before it, against one a second earlier.
                    death_near = bool(fresh) and not by
                    death_control = any(ago >= 2 * NOVA_FRAMES for _away, ago, _monster in close)
                by.sort(key=lambda suspect: suspect['away'])
                around = [(math.dist(m.at, past.at), m) for m in before.foes]
                swinging = [away for away, m in around if m.mode in ATTACK_MODES]
                found.append(
                    {
                        'take': take.directory.name,
                        'frame': moment.index,
                        't': round(moment.t - start, 3),
                        'area': hero.area,
                        'lost': fell,
                        'life': hero.life,
                        'max_life': hero.max_life,
                        'share': round(fell / past.max_life, 3) if past.max_life else None,
                        'dead': hero.life <= 0,
                        'gap': round(gap, 3),
                        'resists': readings.at(moment.t),
                        'class': classify(by, unowned),
                        'by': by,
                        'missiles': near,
                        'hero_mode': past.mode,
                        'death_near': death_near,
                        'death_control': death_control,
                        'foes_near': sum(away <= NOVA_RADIUS for away, _m in around),
                        'nearest_striking': round(min(swinging), 1) if swinging else None,
                    }
                )
        before = moment
    return found
