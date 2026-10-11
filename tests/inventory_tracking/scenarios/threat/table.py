"""The threat table: what makes each monster type dangerous to the Echoing Strike Warlock, read
from the game's tables and nothing else.

`threat_table.json` beside this file is the built table (checked in, so the tests run without the
git-ignored raw tables). Rebuild:

    PYTHONPATH=. uv run --offline python -m tests.inventory_tracking.scenarios.threat.table

What each number rests on:

- which types: levels.txt `nmon1..25` (the Hell columns) of the recorded areas (Catacombs 35-37, Chaos
  Sanctuary 108) and of every level of every Terror Zone (terror_zones/data/desecratedzones-game.json);
- `attack`: monstats `A1/A2/S1 MinD(H)..MaxD(H)`, percent of monlvl `DM(H)` at the monster's level, so a
  hit in points is `hit(row, level)`: no defence, block or resistance of the character applied. A
  caster's skill damage (skills.txt, by skill level) is NOT in it: the monstats number stands in, as
  it does in terror/data/threats.json;
- `elements`: monstats `El1..3` (mode, type, chance percent, min..max percent of `DM(H)`, frames);
  type `mana` burns mana, `pois` is damage over `frames`;
- `ranged`: monstats `rangedtype`, or the ranged flag of terror/data/threats.json (its builder adds
  five caster families by hand);
- `speed`: the larger of monstats `Velocity` and `Run` (the character runs at 9 in that unit; in the
  take 20261010T162810Z-35 the Velocity 6 types walked 6.0-7.25 world units a second and the
  character ran 18.75);
- `skills`, `curses`, `closes`: monstats `Skill1..8`;
- `death_damage`: monstats `deathDmg` (the corpse hurts what stands next to it);
- `resist_physical`, `resist_magic`: monstats `ResDm(H)`, `ResMa(H)`. Echoing Strike is a weapon
  attack with no element (skills.txt 388: `SrcDam` 116, no `EType`), so physical resistance is what
  cuts it and 100 stops it; Hex Purge's explosion (389) and Blade Warp (390) are magic;
- `multiple`: the type's row of terror/data/threats.json (physical, elemental, magic as multiples of
  `DM(H)`) and the factor terror/danger.py `DANGER.hard` puts on its family from the probe logs;
- `rules`: difficultylevels.txt (Hell), monumod.txt, and the Terror Zone config of the installed game:
  the zone's monster level is the character's + `boost_level` within the bounds, one modifier of
  `forced_modifiers` (monumod id -> weight) is forced on the zone's plain monsters, and a Herald of
  tier n has the listed life and damage boosts and minions.
"""

import csv
import json
from functools import cache
from pathlib import Path
from typing import Any

from inventory_tracking.terror.danger import DANGER, DATA as THREATS


HERE = Path(__file__).parent
TABLE = HERE / 'threat_table.json'
ROOT = HERE.parents[3]
EXCEL = ROOT / 'pricing' / 'raw' / 'game-excel'  # git-ignored: the installed game's tables (2026-10-06)
ZONES = ROOT / 'terror_zones' / 'data' / 'desecratedzones-game.json'
RECORDED = (35, 36, 37, 108)
CURSES = ('Amplify Damage', 'Decrepify', 'Lower Resist', 'Weaken', 'Defense Curse', 'Blood Mana')
CLOSING = ('Charge', 'SerpentCharge', 'MonLeap', 'MonLeapAttack', 'MonTeleport', 'Imp Teleport')
RAISERS = ('Resurrect', 'Resurrect2', 'SkeletonRaise', 'Self-resurrect')  # another agent's topic: only named
RESISTED = ('fire', 'ltng', 'cold', 'frze', 'rand')
PLAYER_RUN = 9  # the character's run in monstats speed units (terror/danger.py)
TERROR_LEVEL = 95  # the character is level 93 (terror/tracker.py: 'Terrorized: 95', 2026-10-06)


def rows(name: str) -> list[dict[str, str]]:
    with (EXCEL / f'{name}.txt').open(encoding='latin-1', newline='') as handle:
        return list(csv.DictReader(handle, delimiter='\t'))


def number(row: dict[str, str], column: str) -> int:
    return int(row.get(column) or 0)


def terror_rules() -> dict[str, Any]:
    hell = json.loads(ZONES.read_text())['desecrated_zones'][0]['game_difficulties']['rotw']['hell']
    defaults = hell['defaults']
    return {
        'boost_level': defaults['boost_level'],
        'level_bounds': [defaults['bound_incl_min'], defaults['bound_incl_max']],
        'forced_modifiers': {str(m['unique_mod']): m['chance'] for m in hell['always_unique_mod_pool']},
        'heralds': [
            {
                'tier': tier,
                'life_boost_percent': row['herald_health_boost_percent'],
                'damage_boost_percent': row['herald_damage_boost_percent'],
                'minions': row['max_minions'],
                'minion_life_boost_percent': row['minion_health_boost_percent'],
                'minion_damage_boost_percent': row['minion_damage_boost_percent'],
                'modifiers': row['max_unique_mods'],
            }
            for tier, row in enumerate(defaults['herald_tiers'], 1)
        ],
    }


def zone_levels() -> dict[int, list[str]]:
    """Level id -> the Terror Zones it is terrorized with."""
    found: dict[int, list[str]] = {}
    for zone in json.loads(ZONES.read_text())['desecrated_zones'][0]['zones']:
        for level in zone['levels']:
            found.setdefault(level['level_id'], []).append(zone['id'])
    return found


def monster(row: dict[str, str], threat: dict[str, Any], areas: list[int]) -> dict[str, Any]:
    skills = [row[f'Skill{n}'] for n in range(1, 9) if row.get(f'Skill{n}')]
    elements = [
        {
            'mode': row[f'El{n}Mode'],
            'type': row[f'El{n}Type'],
            'chance': number(row, f'El{n}Pct(H)'),
            'min': number(row, f'El{n}MinD(H)'),
            'max': number(row, f'El{n}MaxD(H)'),
            'frames': number(row, f'El{n}Dur(H)'),
        }
        for n in (1, 2, 3)
        if row.get(f'El{n}Type')
    ]
    attacks = [(number(row, f'{mode}MinD(H)'), number(row, f'{mode}MaxD(H)')) for mode in ('A1', 'A2', 'S1')]
    least, most = max(attacks, key=lambda pair: pair[1])
    speed = max(number(row, 'Velocity'), number(row, 'Run'))
    ranged = row.get('rangedtype') == '1' or bool(threat.get('ranged'))
    hard = DANGER.hard.get(threat.get('name', ''), DANGER.hard.get(row['BaseId'], 1.0))
    found = {
        'id': row['Id'],
        'name': threat.get('name', row['NameStr']),
        'family': row['BaseId'],
        'areas': sorted(areas),
        'recorded': any(area in RECORDED for area in areas),
        'ranged': ranged,
        'speed': speed,
        'attack': [least, most],
        'elements': elements,
        'skills': skills,
        'curses': [skill for skill in skills if skill in CURSES],
        'closes': any(skill in CLOSING for skill in skills),
        'death_damage': row.get('deathDmg') == '1',
        'resist_physical': number(row, 'ResDm(H)'),
        'resist_magic': number(row, 'ResMa(H)'),
        'multiple': {
            'physical': threat.get('physical', 0.0),
            'elemental': threat.get('elemental', 0.0),
            'magic': threat.get('magic', 0.0),
            'hard': hard,
        },
    }
    found['why'] = why(found)
    return found


def why(row: dict[str, Any]) -> list[str]:
    """What makes the type dangerous to this character, each a fact of its row."""
    tags = []
    if row['ranged']:
        tags.append('ranged')
    if row['speed'] >= PLAYER_RUN:
        tags.append('as fast as the character runs')
    if row['closes']:
        tags.append('charges, leaps or teleports in')
    if row['curses']:
        tags.append('curses: ' + ', '.join(row['curses']))
    if any(element['type'] == 'mana' for element in row['elements']):
        tags.append('burns mana')
    if any(element['type'] in ('cold', 'frze') for element in row['elements']):
        tags.append('chills or freezes')
    if any(element['type'] == 'pois' for element in row['elements']):
        tags.append('poisons')
    if any(element['type'] == 'stun' for element in row['elements']):
        tags.append('stuns')
    if row['death_damage']:
        tags.append('corpse explodes')
    if row['resist_physical'] >= 100:
        tags.append('immune to the blades')
    elif row['resist_physical'] >= 50:
        tags.append(f'{row["resist_physical"]}% physical resistance: immune with Stone Skin')
    if row['multiple']['hard'] > 1:
        tags.append(f'hits x{row["multiple"]["hard"]:g} its table number (probe logs)')
    if any(skill in RAISERS for skill in row['skills']):
        tags.append('raises the dead')
    return tags


def build() -> dict[str, Any]:
    threats = json.loads(THREATS.read_text(encoding='utf-8'))
    zones = zone_levels()
    wanted = set(zones) | set(RECORDED)
    stats = {row['Id']: row for row in rows('monstats')}
    areas: dict[str, list[int]] = {}
    levels = {}
    for row in rows('levels'):
        if not row['Id'].isdigit() or int(row['Id']) not in wanted:
            continue
        area = int(row['Id'])
        named = sorted({row[f'nmon{n}'] for n in range(1, 26) if row.get(f'nmon{n}')})
        levels[str(area)] = {
            'name': row['LevelName'],
            'level': number(row, 'MonLvlEx(H)'),
            'zones': zones.get(area, []),
        }
        for name in named:
            areas.setdefault(name, []).append(area)
    monsters = {}
    for name, where in areas.items():
        row = stats[name]
        monsters[row['*hcIdx']] = monster(row, threats['monsters'].get(row['*hcIdx'], {}), where)
    hell = next(row for row in rows('difficultylevels') if row['Name'] == 'Hell')
    skill = next(row for row in rows('skills') if row['*Id'] == '388')
    return {
        'source': 'pricing/raw/game-excel (installed game, 2026-10-06): monstats, levels, monlvl, skills, '
        'difficultylevels, monumod; terror_zones/data/desecratedzones-game.json; terror/data/threats.json',
        'skill': {'id': 388, 'name': skill['skill'], 'src_damage': number(skill, 'SrcDam'), 'element': skill['EType']},
        'damage_by_level': {row['Level']: number(row, 'DM(H)') for row in rows('monlvl') if row['Level'].isdigit()},
        'rules': {
            'hell': {
                'unique_damage_bonus_percent': number(hell, 'UniqueDamageBonus'),
                'champion_damage_bonus_percent': number(hell, 'ChampionDamageBonus'),
                'fire_enchant_explosion_percent': number(hell, 'MonsterFireEnchantExplosionDamagePercent'),
                'corpse_explosion_percent': number(hell, 'MonsterCEDamagePercent'),
            },
            'modifiers': {row['id']: row['uniquemod'] for row in rows('monumod') if row.get('enabled') == '1'},
            'terror': terror_rules(),
        },
        'levels': levels,
        'monsters': dict(sorted(monsters.items(), key=lambda item: int(item[0]))),
    }


@cache
def table() -> dict[str, Any]:
    return json.loads(TABLE.read_text(encoding='utf-8'))


def row_of(txt: int) -> dict[str, Any]:
    return table()['monsters'][str(txt)]


def base_damage(level: int) -> int:
    """monlvl `DM(H)` at a monster level: the points a 100% attack does."""
    return table()['damage_by_level'][str(level)]


def hit(txt: int, level: int) -> tuple[float, float]:
    """(least, most) points of the type's strongest plain attack at monster `level`."""
    least, most = row_of(txt)['attack']
    return base_damage(level) * least / 100, base_damage(level) * most / 100


def multiple(txt: int, resisted: float = DANGER.resisted) -> float:
    """The type's damage a second in multiples of `DM(H)`, as terror/danger.py counts a hit: physical
    and magic in full, fire, lightning and cold cut to `resisted` (75% resistances), times the
    family's factor from the probe logs. One hit a second is this harness's assumption."""
    found = row_of(txt)['multiple']
    return (found['physical'] + found['elemental'] * resisted + found['magic']) * found['hard']


def main() -> int:
    built = build()
    TABLE.write_text(json.dumps(built, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'{TABLE}: {len(built["monsters"])} monster types of {len(built["levels"])} levels')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
