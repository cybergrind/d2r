"""The death in the Disused Fane, 23:35:33.97 on 2026-10-21, as a situation (rca/2026-10-21/death-findings.md,
battle-orders-findings.md; this file's findings: rca/2026-10-21/fane-death-sim-findings.md).

The take is 20261021T203514Z-95 (area 95, schema 4, game cyberr16, the KP_6 terror zone loop's game 8). It starts at
23:35:14.07, three seconds after the door into the Fane, and the character died 19.9 s in; it went on recording the
corpse for eight hours (758,659 frames), so `cut` reads only its first HEAD seconds (`head`). Two cuts:

- `fane-death-24`: 23:35:24.0, before the burst: Amplify Damage on (from 23:35:23.35), Conviction 0.18 s later, the
  Herald's pack there, life 2600 of 2943 (88%);
- `fane-death-20`: 23:35:20.0: Amplify Damage and Conviction come 3.35 and 4.18 s in, the tier 2 Herald's pack
  appears at 2.6 s (record.py's spawns, as the take first saw it), life 2247 (76%).

Both play to 23:35:44 (20 and 24 s). Where each part of the scene comes from:

- ground, rooms, doors: the take's level.json (cut.py, REACH round the character). The arena's walls: no hop, walk or
  warp ends off footing (game.py `footing`, a hop aimed there is refused), monsters walk round walls (mobs.py
  `Horde`), walls stop the blades;
- hostiles (place, share of life, type, rank, mods, Herald tier): the frames and units.jsonl (cut.py), at the Terror
  Zone's level (`terrorized`, below);
- the character's life, mana, belt and buffs: the frame's `p`, `b` and `f` (record.py);
- resistances: the frames' `r` readings of the main set and of the Call to Arms set (MAIN, CTA), capped at 75;
- Amplify Damage and Conviction: the states 9 and 28 and the `r` readings at their times, played as scripted curses
  (stage.py); no curse cast is played;
- Battle Orders: state 32 off at 23:35:32.67, the most life 2943 -> 1896 (stage.py `Orders`); the macro's Call to Arms
  key casts it again;
- Teleport: Enigma's (no staff in the take: `w` never written; Teleport on a key; stage.py `own_teleport`);
- the skill keys: macros/fakes.py HUNT_SLOTS (the build's skills, Teleport, Battle Orders; Battle Command is on no key);
- the blows (2026-10-22, the coordinator's ruling: a test-side cap, sim/monsters.py untouched): each melee blow cut at
  the game's most for its monster, computed from the tables: monstats A1MaxD(H) x monlvl DM(H) at level 96 x its
  rank's (difficultylevels UniqueDamageBonus), Extra Strong's and its Herald tier's boost, each element at its top
  share (`Traits.damage`, `Traits.elements`); then, on the physical points alone, the unit's own damage percent as
  the take read it (stat 25, the auras on it summed: Might L16 +190, Concentration L16 +285; `damage_percents`, its
  latest reading at each moment; mobs.py `Mobs._raised`), Amplify Damage and Conviction (the curses) after (mobs.py
  `Mobs.bounded`, `Mobs.landed`; `capped`). The unique Night Lord's most is 452 physical and 452 fire;
- the chance to take life: the fit's (sim/monsters.py `swing_of`, 0.296 pooled), not the D2 hit chance (2026-10-22,
  population calibration, findings §8: over the takes' 1658 fight windows the fit with the cap and stat 25 lands
  within 10% of the game's life per swing, the D2 chance against defence 1530 overshoots by 45% since the fit
  already holds misses, blocks and the Psychic Ward). `Mobs.to_hit` (AR = A1TH(H) x monlvl TH(H) x the rank's
  monumod bonus against defence at level 96, 0.70-0.87 here) is played only when a cut sets `defence`;
- the awareness: 35 (AWARE): the second unique stood idle 37-44 away for 17 s and ran in when a hop took the character
  to 26 of it;
- the looks: late (`late_timer`, the take's decisions were `late: true` at 81-99 ms); the tests play LAP 0.02.

The calibration against the take (`intake.py`, findings §3, §7; with the D2 hit chance, before §8): the arena took 1429
life in the game's last 10 s against its 2369, and with every fix off no seed of 20 died. On the take's own track the
§8 calibration takes 5035 in the Fane's window against the game's 2453 (findings §8).

`drawing` puts the second unique's pack where the take had it from the character at 7.17 s (it came because the
character's hops went east, which the arena's seldom do).

The cut.py gap this file fills: a monster's stat 12 is its type's monstats Level(H) (84 for a Flesh Hunter, 82 for a
Night Lord), not its level in a Terror Zone (combat/mechanics/life.py's module text). The Fane was terrorized at
character level 96 (the manifest's stat 12): monster level 96 (`zone_level`, its cap), which the findings' blow sizes
fit (death-findings.md Q1). `terrorized` puts every hostile at that level with its points there.

What the scene does not carry (the arena's own lists aside, game.py and mobs.py): the Herald's Concentration and Holy
Freeze (states 42 and 44 on it; its Conviction is the scripted curse, `AURAS`), the Cursed Night Lord's cast (Amplify
Damage is scripted at its time instead), the chill on the character (state 11, 28.25-30.68), Battle Command, Spectral
Hit (monumod 27) and Extra Fast (6) beyond what sim/monsters.py plays of them, the Night Lords' Meteors, the
mercenary's blows (the arena's companions deal nothing; with the rule PETS_FIGHT the Defiler and the bound Pit Lord
fight, `RULES`).

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.fane_death --cut
    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.fane_death --seeds 20
"""

import argparse
import datetime
import functools
import gzip
import json
import math
import statistics
import tempfile
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from inventory_tracking.builds.warlock import mark
from inventory_tracking.combat import harm, survival
from inventory_tracking.combat.mechanics.life import zone_level
from inventory_tracking.combat.mechanics.tables import points_of, tables
from inventory_tracking.game.layout import FULL_REJUVENATION
from inventory_tracking.game.memory import CTA_CODE
from inventory_tracking.macros import cta, hunt, pursuit, safety
from inventory_tracking.takes.takes import Take, monsters_of
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS
from tests.inventory_tracking.scenarios.arena import cut as cutting
from tests.inventory_tracking.scenarios.arena.cut import DEFAULT_HERO, HELL_PENALTY, KINDS, through
from tests.inventory_tracking.scenarios.arena.game import BODIES_BLOCK, PET_POINTS, PETS_FIGHT, SIGIL_SLOWS
from tests.inventory_tracking.scenarios.arena.mobs import AURA_FACTOR
from tests.inventory_tracking.scenarios.arena.scene import Mob, WeaponSet
from tests.inventory_tracking.scenarios.arena.situations.record import TAKES, from_take
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Outcome, Situation, dump, load
from tests.inventory_tracking.scenarios.arena.situations.stage import Orders, Spawn, Stage


TAKE = '20261021T203514Z-95'
ZONE = '+03:00'  # the session's local time
DAY = '2026-10-21'
HEAD = 40.0  # seconds of the take read: the fight and the death are in its first 20
END = '23:35:44.0'  # both cuts play to here: ten seconds past the death
ARRIVES = '-arrives'  # a cut whose second unique's pack comes as the take saw it come (`arriving`)
# Units within which a hostile goes for the character (sim/monsters.py AWARE, 20, widened: stage.py `awareness`). The
# take: the second unique stood idle 37-44 from the character for 17 s and ran in when a hop took the character to 26
# of it (23:35:30.74), so the game's lies between 26 and 37; 35 is the client's sight round the character
AWARE = 35.0
# Units a second each type walks and runs in the takes of 2026-10-20 to 22: the displacement over 0.5 s windows
# (0.45-0.5 s between the ends) within a stretch in modes 2 and 15, the median per type (WINDOWED) and the 90th
# percentile (BRISK; `brisk`). Before 2026-10-22 the figure was frame to frame (FRAME, kept as `fast`): 0.5-unit
# positions over 40 ms frames read a Flesh Hunter at 18.6, nearly twice its 10.6 (one unique's own median 7.6, p90 9.4),
# so the arena's ran in twice as fast as the game's (fane-death-sim-findings.md §11, f24 drawn seed 4). Kept as `fast`
# for the Extra Fast uniques the game has. Speeds of the danger fights' types too (danger_fights.py `speeds_of`).
WINDOWED = {
    4: 4.31,
    8: 2.34,
    27: 3.2,
    47: 10.56,
    71: 4.34,
    99: 3.19,
    100: 3.39,
    104: 4.56,
    118: 12.76,
    120: 13.22,
    124: 6.36,
    125: 6.26,
    128: 3.41,
    132: 6.99,
    133: 7.51,
    183: 3.73,
    188: 5.9,
    214: 11.96,
    215: 10.36,
    216: 11.16,
    247: 6.77,
    304: 10.77,
    310: 5.86,
    362: 9.01,
    398: 11.0,
    453: 9.16,
    492: 7.26,
    529: 9.45,
    598: 8.78,
    610: 11.96,
    687: 9.37,
    691: 14.66,
}
BRISK = {
    4: 6.33,
    8: 3.96,
    27: 7.43,
    47: 18.11,
    71: 8.43,
    99: 7.12,
    100: 6.63,
    104: 5.64,
    118: 22.72,
    120: 17.8,
    124: 13.72,
    125: 14.1,
    128: 7.24,
    132: 8.25,
    133: 12.72,
    183: 7.29,
    188: 7.35,
    214: 20.04,
    215: 17.57,
    216: 19.11,
    247: 17.79,
    304: 12.22,
    310: 7.22,
    362: 12.58,
    398: 17.1,
    453: 17.89,
    492: 13.77,
    529: 10.91,
    598: 15.56,
    610: 14.26,
    687: 17.28,
    691: 19.84,
}
FRAME = {
    4: 4.95,
    8: 2.24,
    27: 4.0,
    47: 18.63,
    71: 4.0,
    99: 3.55,
    100: 3.29,
    104: 4.3,
    118: 15.99,
    120: 15.85,
    124: 7.75,
    125: 7.77,
    128: 3.97,
    132: 6.86,
    133: 8.14,
    183: 4.95,
    188: 6.0,
    214: 16.325,
    215: 14.5,
    216: 16.07,
    247: 11.22,
    304: 10.26,
    310: 6.01,
    362: 9.92,
    398: 13.44,
    453: 15.2,
    492: 10.0,
    529: 9.35,
    598: 9.25,
    610: 12.25,
    687: 13.49,
    691: 16.735,
}
SPEEDS = {txt: WINDOWED[txt] for txt in (47, 132, 27)}
LIFE_READ = 0.4  # seconds: the client's life changes on this beat (stage.py `Stage.client_life`)
PACK = 12.0  # units: the second unique's pack, round it at the start
DRAW_STEPS = 40  # `drawing`: the steps back toward the character a spot off footing is moved by
CUTS = {
    'fane-death-24': '23:35:24.0',
    'fane-death-20': '23:35:20.0',
    f'fane-death-24{ARRIVES}': '23:35:24.0',
    f'fane-death-20{ARRIVES}': '23:35:20.0',
}
HERALD, SECOND = 4193434304, 120235824  # the tier 2 Herald; the second unique Flesh Hunter (Fire Ench., Aura, Fast)
NIGHT_LORD = 2783642058  # the Cursed, Extra Strong, Fire Enchanted Night Lord minion whose blows came first
# The Night Lord's type (monstats 132 `vampire2`): the threat table calls it ranged, so the arena plays it as a shooter;
# its blows in the take were melee at 2.9 units (death-findings.md Q1), so it is played hand to hand (stage.py `melee`)
NIGHT_LORD_TYPE = 132
# Units of ground and hostiles kept round the character (cut.py's reach and, for the cut, its MOB_RANGE). 80, not 60:
# the second unique's pack stood 61-70 east at 23:35:24 (`cut`)
REACH = 80.0
PLAYER_LEVEL = 96  # the character's level (the manifest's `character_stats` 12)
DEFENCE = 1530.0  # the character's defence (the manifest's `character_stats` 31)
DEXTERITY = 134  # its dexterity (stat 2)
BLOCK = 22 * (DEXTERITY - 15) / (2 * PLAYER_LEVEL) / 100  # the game's block chance: the shield's 22 (stat 20)
TZ_LEVEL = zone_level(95, PLAYER_LEVEL) or 96  # the Fane's monster level, terrorized (96)
# The resistances as the frames' `r` read them (physical, fire, lightning, cold, poison; before the Hell penalty):
# the main set's at the take's start, the Call to Arms set's at the swap of 23:35:18.38
MAIN_READ = (18, 194, 183, 203, 181)
CTA_READ = (0, 154, 143, 163, 141)
# The curses as the readings show them (states 9 and 28 on the character): Amplify Damage -100 physical at 23:35:23.35,
# Conviction -85 fire, lightning and cold at 23:35:24.18 (`r` [-82, 109, 98, 118, 181])
AMPLIFY_AT, CONVICTION_AT = '23:35:23.35', '23:35:24.18'
AMPLIFIED = (-82, 194, 183, 203, 181)
CONVICTED = (-82, 109, 98, 118, 181)
# Battle Orders: state 32 off at 23:35:32.67, the most life 2943 -> 1896 (the share kept); cast at 23:32:32.08 by the
# service before the restart of 23:35:08, which the new service did not know (battle-orders-findings.md Q1)
ORDERS_END, ORDERS_CAST = '23:35:32.67', '23:32:32.08'
MOST_WITH, MOST_WITHOUT = 2943.0, 1896.0
# The arena's three rules of a pack fight (game.py RULES; situations/herald.py): the sigil slows, the Defiler and the
# bound Pit Lord out in the take fight and take blows, bodies block (the walk of 23:35:32.35 went into running bodies)
RULES = (SIGIL_SLOWS, PETS_FIGHT, BODIES_BLOCK)
PET_TYPES = (744, 361)  # the Defiler and the bound Pit Lord (megademon2)
# The auras by unit (stage.py `auras`). The take's states: Might (33) on unique 120235824, so Might's factor
# (mobs.py AURA_FACTOR) on the blows round it; on the Herald Conviction (28: scripted as the curse it is), Concentration
# (42) and Holy Freeze (44), which the arena does not play: the Night Lord's blows beside the Herald (234, 207, 436)
# fit its blow with Amplify Damage and no aura (death-findings.md Q1), so none for the Herald
AURAS = {SECOND: AURA_FACTOR}


def clock(at: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(f'{DAY}T{at}{ZONE}')


def seconds_between(start: str, at: str) -> float:
    return round((clock(at) - clock(start)).total_seconds(), 3)


def shares(read: Sequence[int]) -> dict[str, float]:
    """A reading's shares let through, by kind (cut.py KINDS: physical as read, the elements less Hell's penalty)."""
    return {kind: through(read[index] - (HELL_PENALTY if index else 0)) for index, kind in enumerate(KINDS)}


# The two sets: the main (Heart of the Oak's flail, as builds/characters.py names it; mobs.py RAW_RESISTS does not
# hold the set of 2026-10-21, so the shares are the readings' own) and the Call to Arms. No staff: Teleport is Enigma's.
MAIN = WeaponSet(('fla',), shares(MAIN_READ))
CTA = WeaponSet((CTA_CODE,), shares(CTA_READ))


def head(directory: Path, seconds: float, into: Path) -> Path:
    """The take's first `seconds` as a small take under `into` (the frames, events, units, missiles and path records
    in that time, the manifest and the level), read line by line: `Take.load` of the whole recording holds its eight
    hours of the corpse."""
    target = into / directory.name
    target.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((directory / 'manifest.json').read_text())
    end = manifest['clock']['monotonic'] + seconds
    for name in ('frames', 'events', 'units', 'missiles', 'paths'):
        plain, packed = directory / f'{name}.jsonl', directory / f'{name}.jsonl.gz'
        if not plain.exists() and not packed.exists():
            continue
        with (
            plain.open(encoding='utf-8') if plain.exists() else gzip.open(packed, 'rt', encoding='utf-8') as source,
            (target / f'{name}.jsonl').open('w', encoding='utf-8') as out,
        ):
            past = 0
            for line in source:
                if not line.strip():
                    continue
                if json.loads(line).get('t', 0.0) > end:
                    past += 1
                    if name in ('frames', 'paths') and past > 100:
                        break  # in time order: the rest is later
                    continue
                out.write(line if line.endswith('\n') else line + '\n')
    kept = {key: value for key, value in manifest.items() if key != 'census'}
    kept['trimmed'] = {'take': directory.name, 'seconds': seconds, 'recording': directory.name}
    (target / 'manifest.json').write_text(json.dumps(kept))
    for level in ('level.json', 'level.json.gz'):
        if (directory / level).exists():
            (target / level).write_bytes((directory / level).read_bytes())
    return target


def terrorized(mob: Mob, area: int) -> Mob:
    """A hostile at the Terror Zone's level (the module text): its points there, its share of life kept."""
    if mob.owner is not None or mob.ally:
        return mob
    factor = points_of(mob.txt, area, TZ_LEVEL) / points_of(mob.txt, area)
    return replace(mob, level=TZ_LEVEL, full=round(mob.full * factor, 1), life=round(mob.life * factor, 1))


def pet(mob: Mob) -> Mob:
    """A demon of the character's at PET_POINTS (game.py), its share of life kept: the take's row holds the share alone
    (cut.py gives a companion the row's numbers, 128ths)."""
    if not (mob.ally or mob.owner is not None) or mob.txt not in PET_TYPES:
        return mob
    return replace(mob, life=round(PET_POINTS * mob.life / 128, 1), full=PET_POINTS)


def out_of_sight(take: Take, found: Situation) -> list[Mob]:
    """The hostiles the take saw before the start that the start's frame does not hold (out of the client's sight) and
    the play has nowhere else (record.py's spawns hold only hostiles first seen after the start), each where and as it
    was last seen if that is within REACH of the character: at 23:35:24 the second unique's pack, which stood idle at
    (15097.5, 5654.5) out of sight from 23:35:21.7 until the character came east at 23:35:29.4."""
    first = int((found.source or {})['frame'])
    present = {mob.unit for mob in found.scene.mobs} | {mob.unit for spawn in found.spawns for mob in spawn.mobs}
    last: dict[int, int] = {}
    for index in range(first):
        for monster in monsters_of(take.frames[index]):
            if monster.hostile and monster.at != (0.0, 0.0):
                last[monster.unit] = index
    missing = {unit: index for unit, index in last.items() if unit not in present}
    here, kept = found.scene.hero.at, []
    for index in sorted(set(missing.values())):
        try:
            seen = cutting.cut(take, index, defaults=DEFAULT_HERO, reach=REACH)
        except cutting.Refused:
            continue  # a frame cut.py refuses (its vitals not read): its hostiles are not put back
        kept += [
            mob for mob in seen.mobs
            if missing.get(mob.unit) == index and mob.life > 0 and math.dist(mob.at, here) <= REACH
        ]  # fmt: skip
    if kept:
        found.assumed['scene.mobs.out_of_sight'] = (
            f"{len(kept)} hostiles out of the client's sight at the start, put where last seen (`out_of_sight`)"
        )
    return kept


def damage_percents(directory: Path, at: float) -> dict[int, list[tuple[float, float]]]:
    """Each hostile's damagepercent readings (stat 25: the sum of the damage auras on it, its own among them) as
    (seconds from `at`, percent) in order, from units.jsonl and the `stats` events; a unit that never reads above 0
    is left out."""
    readings: dict[int, list[tuple[float, float]]] = {}
    for name in ('units.jsonl', 'events.jsonl'):
        plain, packed = directory / name, directory / f'{name}.gz'
        if not plain.exists() and not packed.exists():
            continue
        with plain.open(encoding='utf-8') if plain.exists() else gzip.open(packed, 'rt', encoding='utf-8') as source:
            for line in source:
                row = json.loads(line) if line.strip() else {}
                if name == 'events.jsonl' and row.get('event') != 'stats':
                    continue
                if 'unit' in row and isinstance(row.get('stats'), dict):
                    value = float(row['stats'].get('25', 0))
                    readings.setdefault(row['unit'], []).append((round(row['t'] - at, 2), value))
    return {unit: sorted(rows) for unit, rows in readings.items() if any(value for _, value in rows)}


def arriving(take: Take, found: Situation) -> None:
    """The second unique's pack (the hostiles within PACK of it at the start) comes as the take saw it come: a spawn
    at the first frame after the start that shows the unique moved (23:35:31.52, running, 13.9 from the character),
    each of the pack where that frame has it, else where it stood (rca/2026-10-21/fane-death-sim-findings.md §2: the
    arena's pack stands where last seen until the character comes within the awareness, and the arena's character
    seldom went east as the game's did). `found` is changed."""
    stale = next(mob.at for mob in found.scene.mobs if mob.unit == SECOND)
    pack = [mob for mob in found.scene.mobs if not mob.ally and mob.owner is None and math.dist(mob.at, stale) <= PACK]
    first = int((found.source or {})['frame'])
    index = next(
        index for index in range(first + 1, len(take.frames))
        if any(m.unit == SECOND and m.at != stale for m in monsters_of(take.frames[index]))
    )  # fmt: skip
    seen = {mob.unit: mob for mob in cutting.cut(take, index, defaults=DEFAULT_HERO, reach=REACH).mobs}
    come = [seen.get(mob.unit, mob) for mob in pack]
    at = round(take.frames[index]['t'] - take.frames[first]['t'], 2)
    units = {mob.unit for mob in pack}
    found.scene.mobs = [mob for mob in found.scene.mobs if mob.unit not in units]
    found.spawns = [*found.spawns, Spawn(come, at=at, label="the second unique's pack, as the take saw it run in")]
    found.assumed['spawns.arrives'] = (
        f"the second unique's pack ({len(come)} within {PACK:.0f} of it) at {at} s, where the take first shows the "
        f'unique moved ({sum(mob.unit in seen for mob in pack)} of them in that frame; `arriving`)'
    )


def cut(name: str, directory: Path | None = None) -> Situation:
    """The situation `name` (CUTS) from the take (the module text)."""
    start = CUTS[name]
    kept = cutting.MOB_RANGE
    # cut.py keeps hostiles within MOB_RANGE (60) whatever the reach, and record.py's spawns hold only hostiles first
    # seen after the start: at 23:35:24 the second unique's pack stood 61-70 east and would never be in the play
    cutting.MOB_RANGE = REACH
    try:
        with tempfile.TemporaryDirectory() as scratch:
            small = head(directory or TAKES / TAKE, HEAD, Path(scratch))
            found = from_take(
                small, f'{DAY}T{start}{ZONE}', seconds_between(start, END), name=name, reach=REACH,
                about=(
                    f'Disused Fane, {DAY} {start}: the tier 2 Flesh Hunter Herald (Aura Enchanted, Spectral Hit, '
                    'Teleportation), a second unique Flesh Hunter (Fire Enchanted, Aura Enchanted, Extra Fast), Cursed '
                    'Extra Strong Fire Enchanted Night Lords; Amplify Damage and Conviction on the character, Battle '
                    'Orders out at 23:35:32.67. The character died at 23:35:33.97.'
                ),
            )  # fmt: skip
            loaded = Take.load(small)
            found.scene.mobs += out_of_sight(loaded, found)
            percent = damage_percents(small, loaded.frames[int((found.source or {})['frame'])]['t'])
            if name.endswith(ARRIVES):
                arriving(loaded, found)
    finally:
        cutting.MOB_RANGE = kept
    area = found.scene.hero.area
    found.scene.mobs = [pet(terrorized(mob, area)) for mob in found.scene.mobs]
    found.spawns = [replace(spawn, mobs=[terrorized(mob, area) for mob in spawn.mobs]) for spawn in found.spawns]
    found.scene.hero = replace(found.scene.hero, sets=(MAIN, CTA), hand=0, slots=HUNT_SLOTS)
    curses = []
    for at, read in ((AMPLIFY_AT, AMPLIFIED), (CONVICTION_AT, CONVICTED)):
        when = max(seconds_between(start, at), 0.0)
        before = shares(MAIN_READ)
        curses += [(when, kind, share) for kind, share in shares(read).items() if share != before[kind]]
    found.curses = tuple(sorted(curses))
    found.orders = Orders(
        ends=seconds_between(start, ORDERS_END),
        factor=round(MOST_WITH / MOST_WITHOUT, 4),
        cast_at=None,  # the restart of 23:35:08 lost the cast's age (battle-orders-findings.md Q1)
    )
    found.own_teleport = True
    found.rules = RULES
    found.melee = (NIGHT_LORD_TYPE,)
    found.auras = dict(AURAS)
    found.capped = True  # each melee blow at most the game's most (mobs.py `Mobs.bounded`)
    # The population calibration (findings §8): the fit's chance to take life per swing matches the takes' (64 points
    # a swing against 64-69); the game's chance to hit (`defence`) overshot it by 45%, so it is not played here
    units = {mob.unit for mob in found.scene.mobs} | {mob.unit for spawn in found.spawns for mob in spawn.mobs}
    found.damage_percent = {unit: rows for unit, rows in percent.items() if unit in units}
    found.aware = AWARE
    found.speeds = dict(SPEEDS)
    found.life_read = LIFE_READ
    found.assumed.update({
        'scene.mobs.level': f'monster level {TZ_LEVEL}: the Terror Zone at character level {PLAYER_LEVEL} (stat 12 is '
        "the type's monstats level: combat/mechanics/life.py)",
        'scene.hero.sets': "the main set's and the Call to Arms set's resistances as the frames' `r` read them; no "
        'staff (Teleport is Enigma\'s); the codes are builds/characters.py\'s main and the Call to Arms',
        'scene.hero.slots': 'macros/fakes.py HUNT_SLOTS: the build, Teleport, Battle Orders (Battle Command on no key)',
        'curses': 'Amplify Damage and Conviction at the times the `r` readings and states 9 and 28 show them, on '
        'both sets alike',
        'orders': f'Battle Orders up, out at {ORDERS_END} (state 32), most life {MOST_WITH:.0f} -> {MOST_WITHOUT:.0f}; '
        'its cast not known to the macro (the restart)',
        'auras': "Might's factor round 120235824 (state 33); none round the Herald (Conviction scripted, "
        'Concentration and Holy Freeze not played; its pack\'s blows fit no boost)',
        'melee': 'the Night Lords (132) hand to hand, as the take shows them; their Meteors not played',
        'damage_percent': 'each hostile\'s stat 25 (the sum of the damage auras on it) as the take read it at the '
        'start, else when first seen, on its physical points (mobs.py `damage_percent`); it replaces `auras`',
        'hit': 'the fit\'s chance to take life per swing (the population: findings §8), not the game\'s chance to '
        'hit against defence 1530, which overshot the takes by 45% a swing',
        'speeds': 'the types\' walk as the takes measure it over 0.5 s windows (SPEEDS), not monstats Velocity x PACE',
        'life_read': f'the life the macro and the healer read refreshed every {LIFE_READ} s and at a stagger',
        'aware': f'{AWARE:.0f} units (AWARE: between the 26 the second unique woke at and the 37 it slept at)',
        'pets': 'the Defiler and the bound Pit Lord at PET_POINTS each (game.py; the take shows only their share)',
        'not played': "the Cursed cast, Holy Freeze on the character, Battle Command, the mercenary's blows",
    })  # fmt: skip
    return found


@functools.cache
def stored(name: str) -> Situation:
    return load(FIXTURES / f'{name}.json')


# -- the fixes under test ----------------------------------------------------------------------------------------

# The switches of the death's fixes: name -> (module, attribute). Rounds 1-2's six (death-findings.md,
# battle-orders-findings.md), then round 3's (death-findings.md "Round 3": the rebuff, the bout's yield and alarm, the
# aura forecast, the reach bar, the clear footing, the danger look, the read lag)
SWITCHES: dict[str, tuple[Any, str]] = {
    'EMERGENCY_REJUVENATION': (survival, 'EMERGENCY_REJUVENATION'),
    'RETREAT_AWAY': (pursuit, 'RETREAT_AWAY'),
    'VETOED_ESCAPE': (pursuit, 'VETOED_ESCAPE'),
    'CLEAR_ESCAPES': (safety, 'CLEAR_ESCAPES'),
    'FLOOR_NO_CREDIT': (safety, 'FLOOR_NO_CREDIT'),
    'RENEW_ORDERS': (cta, 'RENEW_ORDERS'),
    'REBUFF': (cta, 'REBUFF'),
    'BOUT_ORDERS': (hunt, 'BOUT_ORDERS'),
    'BOUT_ALARM': (hunt, 'BOUT_ALARM'),
    'REBUFF_RETREAT': (safety, 'REBUFF_RETREAT'),
    'REBUFF_FIRST': (pursuit, 'REBUFF_FIRST'),
    'ORDERS_PREDICT': (safety, 'ORDERS_PREDICT'),
    'AURA_FORECAST': (safety, 'AURA_FORECAST'),
    'REACH_BAR': (safety, 'REACH_BAR'),
    'CLEAR_FOOTING': (safety, 'CLEAR_FOOTING'),
    'DANGER_LOOK': (safety, 'DANGER_LOOK'),
    'READ_LAG': (survival, 'READ_LAG'),
    # rounds 3b-3c (REMARK_AFTER_REBUFF, DOLL_HERALD_MARK): the one designation since 2026-10-22, its mark again after a
    # rebuff hop and a doll Herald's before the first strike (builds/warlock/mark.py DESIGNATED_MARK)
    'DESIGNATED_MARK': (mark, 'DESIGNATED_MARK'),
    'DOLL_HERALD_FIRST': (cta, 'DOLL_HERALD_FIRST'),
    # round 3d (2026-10-22, the t5 Hulk and the pursuit-mode Fane deaths; REJUV_REACTS and AURA_SWINGERS stay off and
    # out of the list):
    # - RAISED_KEEP: a raised fight's retreat keeps the hostile of the most harm in reach;
    # - MOVED_ACTIVE: a hostile seen to move a unit or more counts as active for 1 s;
    # - KILL_FIRST: no rebuff retreat while a one-shotter in reach dies before it reaches the character, or a doll
    #   Herald is in reach;
    # - CAST_REACH: no Battle Orders cast in place while melee hostiles whose top blows together take the life can come
    #   in reach;
    # - NEAR_WAKES: a neutral hostile with no line still prices when it can walk into reach within 1 s.
    'RAISED_KEEP': (safety, 'RAISED_KEEP'),
    'MOVED_ACTIVE': (safety, 'MOVED_ACTIVE'),
    'KILL_FIRST': (safety, 'KILL_FIRST'),
    'CAST_REACH': (safety, 'CAST_REACH'),
    'NEAR_WAKES': (harm, 'NEAR_WAKES'),
    # round 3e (2026-10-22): a look's hostiles priced at the terror zone's or the area's monster level, not the type's
    # base (the unique Night Lord at x5.75: 1727 -> 2003)
    'ZONE_LEVEL': (safety, 'ZONE_LEVEL'),
    # round 5-6 (2026-10-22): the strike bout yields where holding is barred (BOUT_REACH); the most stat 25 over 5 s
    # (RAISE_KEEP); a walk priced at the speed it was seen to move (OBSERVED_SPEED); no doll killed within its blast
    # (DOLL_ESCAPES); the bout's casts held while a one-shotter can come in reach, one cast a look
    # (FIGHT_CAST_REACH); a walk's end barred by what reaches it in the walk's blind 1.1 s (WALK_REACH)
    'BOUT_REACH': (safety, 'BOUT_REACH'),
    'RAISE_KEEP': (safety, 'RAISE_KEEP'),
    'OBSERVED_SPEED': (safety, 'OBSERVED_SPEED'),
    'DOLL_ESCAPES': (safety, 'DOLL_ESCAPES'),
    'FIGHT_CAST_REACH': (hunt, 'FIGHT_CAST_REACH'),
    'WALK_REACH': (safety, 'WALK_REACH'),
}
ALL_ON = dict.fromkeys(SWITCHES, True)
ALL_OFF = dict.fromkeys(SWITCHES, False)


@contextmanager
def switched(values: Mapping[str, bool]) -> Iterator[None]:
    """The switches as `values` say while the block runs (the others as they are), put back after."""
    saved = {name: getattr(*SWITCHES[name]) for name in values}
    for name, value in values.items():
        setattr(*SWITCHES[name], value)
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(*SWITCHES[name], value)


def only(name: str) -> dict[str, bool]:
    return {**ALL_OFF, name: True}


def but(name: str) -> dict[str, bool]:
    return {**ALL_ON, name: False}


# -- the variants -------------------------------------------------------------------------------------------------


def paced(situation: Situation, pace: Mapping[int, float], name: str) -> Situation:
    """`situation` with its types' speeds from `pace` (those it holds; the rest as they are)."""
    speeds = situation.speeds or {}
    return situation.variant(
        f'{situation.name}, {name}', speeds={txt: pace.get(txt, now) for txt, now in speeds.items()}
    )


def fast(situation: Situation) -> Situation:
    """The types at the frame-to-frame pace (FRAME): fast closers, as an Extra Fast unique is."""
    return paced(situation, FRAME, 'fast')


def brisk(situation: Situation) -> Situation:
    """The types at their 90th percentile pace (BRISK)."""
    return paced(situation, BRISK, 'brisk')


def renewed(situation: Situation) -> Situation:
    """Battle Orders not running out in the play: what RENEW_ORDERS's quiet rule would have left (the Bazaar's quiet
    looks from 23:34:36 had under 60 s left, so it would have been cast again before the door; battle-orders-findings.md
    Q1, Q3)."""
    orders = situation.orders
    assert orders is not None
    return situation.variant(f'{situation.name}, orders renewed', orders=replace(orders, ends=orders.ends + 180.0))


def known(situation: Situation) -> Situation:
    """The cast's age known to the macro (no restart): cast 180.6 s before it ran out, so the fight renewal under
    FIGHT_LEFT may come."""
    orders = situation.orders
    assert orders is not None
    return situation.variant(
        f'{situation.name}, orders known', orders=replace(orders, cast_at=orders.ends - cta.ORDERS_LASTS)
    )


def client_levels(situation: Situation) -> Situation:
    """Every hostile at the level the client's stat 12 shows (84 for the Flesh Hunters and Wailing Beasts, 82 for the
    Night Lords: each type's monstats Level(H), the same for every unit of a type in the take) in place of the Terror
    Zone's 96, its points there and its share of life kept: what the look prices at (rca/2026-10-21/death-findings.md
    Round 3, "the monsters' level"), against what the arena plays (`terrorized`)."""

    def lowered(mob: Mob) -> Mob:
        if mob.owner is not None or mob.ally:
            return mob
        level = int(tables()['monsters'][str(mob.txt)]['Level(H)'])
        area = situation.scene.hero.area
        factor = points_of(mob.txt, area, level) / points_of(mob.txt, area, mob.level or TZ_LEVEL)
        return replace(mob, level=level, full=round(mob.full * factor, 1), life=round(mob.life * factor, 1))

    scene = replace(situation.scene, mobs=[lowered(mob) for mob in situation.scene.mobs])
    spawns = tuple(replace(spawn, mobs=[lowered(mob) for mob in spawn.mobs]) for spawn in situation.spawns)
    return situation.variant(f'{situation.name}, client levels', scene=scene, spawns=list(spawns))


def drawing(name: str) -> Callable[[Stage, Any], None]:
    """An `each_tick` for `play` (`extra`) that draws the second unique's pack in as the take had it come to the
    character, wherever the arena's character stands: at the moment of the `-arrives` cut's spawn (`arriving`, 7.17 s
    into fane-death-24), each of the pack is put where the take had it from the character then (14-27 east, 4-10
    south), stepped back toward the character onto footing if that is a wall. The take's pack woke because the
    character's own hops took it east (death-findings.md Q3); the arena's character seldom goes there, so this plays
    the pack the game sent at the time it came (rca/2026-10-21/fane-death-sim-findings.md §2, the drawn variant)."""
    arrived = stored(f'{name}{ARRIVES}')
    spawn = arrived.spawns[-1]
    at = spawn.at
    assert at is not None
    track = (arrived.recorded or {})['track']
    _, hx, hy = min(track, key=lambda row: abs(row[0] - at))
    offsets = {mob.unit: (mob.at[0] - hx, mob.at[1] - hy) for mob in spawn.mobs}
    done: list[bool] = []

    def each_tick(stage: Stage, _: Any) -> None:
        if done or stage.clock.now < at:
            return
        done.append(True)
        x, y = stage.here
        for unit, (dx, dy) in offsets.items():
            mob, walker = stage.mobs.mobs.get(unit), stage.mobs.pack.walkers.get(unit)
            if mob is None or walker is None or mob.life <= 0:
                continue
            spots = [(x + dx * (1 - step / DRAW_STEPS), y + dy * (1 - step / DRAW_STEPS)) for step in range(DRAW_STEPS)]
            spot = next((spot for spot in spots if stage.barred is None or not stage.barred(spot)), spots[-1])
            mob.at = spot
            walker.x, walker.y = spot

    return each_tick


def late_timer(lap: float) -> Callable[[], float]:
    """A look's timer that runs `lap` seconds a call (macros/safety.py `LookClock`): with the look's 0.08 s, a lap of
    0.02 is late at the fifth reading, 1.0 at the first (tests/.../macros/test_death_pricing.py `late`)."""
    calls = [0]

    def timer() -> float:
        calls[0] += 1
        return calls[0] * lap

    return timer


# -- a play and its measures --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Measures:
    """What one play came to, in the findings' words."""

    seed: int
    dead_at: float | None
    low: float  # the least life, points
    low_share: float  # the least life over the most at that moment
    rejuvenations: int
    healing: int
    hops: int
    refused: int  # aims of a hop, a warp or a walk where nobody stands (walls, the void)
    off_footing: int  # hops that landed where the level has no footing (must be 0)
    retreats: int  # the macro's retreating moves
    herald_dead: float | None
    second_dead: float | None
    orders: tuple[tuple[float, str], ...]
    kills: int

    @property
    def dead(self) -> bool:
        return self.dead_at is not None


def play(
    situation: Situation,
    values: Mapping[str, bool],
    seed: int,
    *,
    lap: float | None = None,
    extra: Callable[[Stage, Any], None] | None = None,
) -> Outcome:
    """One play with the switches `values`; `lap` a late look's timer (`late_timer`), None no timer (the driver's);
    `extra` another `each_tick` (intake.py `Sampler`)."""
    hooked: list[bool] = []

    def each_tick(stage: Stage, routed: Any) -> None:
        if lap is not None and not hooked:
            routed.hunter.safety.timer = late_timer(lap)
            hooked.append(True)
        lows = getattr(stage, 'low_shares', None)
        if lows is None:
            lows = stage.low_shares = []  # type: ignore[attr-defined]
        if stage.over is None and stage.max_life:
            lows.append(stage.life / stage.max_life)
        if extra is not None:
            extra(stage, routed)

    with switched(values):
        return situation.play(seed=seed, keep=True, each_tick=each_tick)


def measures(outcome: Outcome) -> Measures:
    stage: Stage = outcome.stage_  # type: ignore[attr-defined]
    rejuvenations = sum(1 for _, item, _ in outcome.potions if item == FULL_REJUVENATION)
    off = sum(1 for _, _, spot in stage.hops if stage.barred is not None and stage.barred(spot))
    lows = getattr(stage, 'low_shares', [])
    return Measures(
        seed=outcome.seed,
        dead_at=outcome.dead_at,
        low=outcome.low,
        low_share=round(min(lows, default=1.0), 3),
        rejuvenations=rejuvenations,
        healing=len(outcome.potions) - rejuvenations,
        hops=len(stage.hops),
        refused=len(stage.refused),
        off_footing=off,
        retreats=outcome.said_count('retreat'),
        herald_dead=stage.fell.get(HERALD),
        second_dead=stage.fell.get(SECOND),
        orders=tuple(stage.orders_log),
        kills=len(outcome.kills),
    )


@dataclass(frozen=True)
class Row:
    """A variant over its seeds."""

    label: str
    plays: tuple[Measures, ...]

    @property
    def deaths(self) -> int:
        return sum(play.dead for play in self.plays)

    def text(self) -> str:
        plays = self.plays
        died = [play.dead_at for play in plays if play.dead_at is not None]
        lows = [play.low_share for play in plays]
        alive = [play.low_share for play in plays if not play.dead]
        herald = sum(play.herald_dead is not None for play in plays)
        second = sum(play.second_dead is not None for play in plays)

        def mean(values: Sequence[float]) -> float:
            return statistics.fmean(values) if values else 0.0

        return (
            f'| {self.label} | {self.deaths}/{len(plays)} | '
            f'{"-" if not died else f"{min(died):.1f} / {statistics.median(died):.1f} / {max(died):.1f}"} | '
            f'{min(lows):.0%} / {statistics.median(lows):.0%} | {"-" if not alive else f"{min(alive):.0%}"} | '
            f'{mean([p.rejuvenations for p in plays]):.1f} | {mean([p.healing for p in plays]):.1f} | '
            f'{mean([p.hops for p in plays]):.1f} | {mean([p.retreats for p in plays]):.1f} | '
            f'{herald}/{len(plays)} | {second}/{len(plays)} | {sum(p.off_footing for p in plays)} |'
        )


HEAD_ROW = (
    '| variant | deaths | death at, s (least / median / most) | lowest life share (least / median) | lowest, alive '
    '| rejuvenations | healing | Teleports | retreat lines | Herald dead | 2nd unique dead | hops off footing |\n'
    '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |'
)


def row(label: str, situation: Situation, values: Mapping[str, bool], seeds: Sequence[int], **kwargs: Any) -> Row:
    return Row(label, tuple(measures(play(situation, values, seed, **kwargs)) for seed in seeds))


def table(situation: Situation, seeds: Sequence[int], *, lap: float | None = None) -> list[Row]:
    """All off, all on, each alone, all but each (the findings' tables)."""
    variants = [('all off', ALL_OFF), ('all on', ALL_ON)]
    variants += [(f'only {name}', only(name)) for name in SWITCHES]
    variants += [(f'all but {name}', but(name)) for name in SWITCHES]
    return [row(label, situation, values, seeds, lap=lap) for label, values in variants]


def spawned(spawns: Sequence[Spawn]) -> int:
    return sum(len(spawn.mobs) for spawn in spawns)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('--cut', action='store_true', help='cut the fixtures again from the take')
    parser.add_argument('--seeds', type=int, default=5)
    parser.add_argument('--name', default='fane-death-24', choices=sorted(CUTS))
    parser.add_argument('--lap', type=float, default=None, help="a late look's timer, seconds a reading")
    parser.add_argument('--quick', action='store_true', help='all off and all on only')
    args = parser.parse_args(argv)
    if args.cut:
        for name in CUTS:
            dump(cut(name), FIXTURES / f'{name}.json')
        stored.cache_clear()
    situation = stored(args.name)
    seeds = range(1, args.seeds + 1)
    print(HEAD_ROW)
    if args.quick:
        for label, values in (('all off', ALL_OFF), ('all on', ALL_ON)):
            print(row(label, situation, values, seeds, lap=args.lap).text(), flush=True)
        return 0
    for found in table(situation, seeds, lap=args.lap):
        print(found.text(), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
