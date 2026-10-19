"""The game tables the combat mechanics key on, bundled from the installed game (as the terror
module does: runtime reads only `data/tables.json`; the install is a build input).

Run: PYTHONPATH=. uv run --offline python -m inventory_tracking.combat.mechanics.tables "<install>"

Bundled (2026-10-10): the Warlock skills Echoing Strike (388), Mirrored Blades (392), Blade Warp
(390), Sigil Lethargy (393) and Death Mark (375) with their parameters and damage columns; the
blade missiles 706 and 720; every monster's Hell level, HP percentages, defence and resistances
(monstats, by *hcIdx, the txt id in memory); monlvl's Hell columns (HP, defence, to-hit per
level); each area's Hell monster level (levels MonLvlEx(H)). A regular monster's points are the
area level's HP(H) times its MinHP(H)..MaxHP(H) percent (Chaos Sanctuary 108 is level 85: HP(H)
4637, so a Doom Knight at 120-150% has 5564-6956 points and a Venom Lord 9738-11593).

Since 2026-10-12, for what a unique's enchantments do (sim/monsters.py): the missiles an enchanted
monster lets go (`coldunique` 194, `lightunique` 195) with their element columns, monumod's constants
(`unique`: the elemental damage an enchantment adds to a blow, percent of the blow, by rank; the damage
and life bonuses) and the Terror Zone's Herald tiers (`heralds`: life and damage boosts of a Herald
and of its minions, terror_zones/data/desecratedzones-game.json), and `harmless_missiles`: the ids of
the missiles that take nothing off the character (takes/hurts.py leaves them out of a drop's `near`).
"""

import argparse
import csv
import io
import json
from functools import cache
from pathlib import Path
from typing import Any


DATA = Path(__file__).parent.parent / 'data' / 'tables.json'
EXCEL = 'data/global/excel/{}.txt'
SKILLS = {388: 'Echoing Strike', 392: 'Mirrored Blades', 390: 'Blade Warp', 393: 'Sigil Lethargy', 375: 'Death Mark'}
MISSILES = (706, 720, 194, 195)
SKILL_FIELDS = (
    'skill', 'charclass', 'srvmissilea', 'calc1', 'calc5', 'calc6', 'Param1', 'Param2', 'Param3', 'Param4', 'Param5',
    'Param6', 'Param7', 'Param8', 'Param9', 'Param10', 'ToHitCalc', 'SrcDam', 'MinDam', 'MinLevDam1', 'MinLevDam2',
    'MinLevDam3', 'MinLevDam4', 'MinLevDam5', 'MaxDam', 'MaxLevDam1', 'MaxLevDam2', 'MaxLevDam3', 'MaxLevDam4',
    'MaxLevDam5', 'DmgSymPerCalc', 'mana', 'lvlmana', 'aurarangecalc', 'auralencalc', 'maxlvl',
)  # fmt: skip
MISSILE_FIELDS = (
    'Missile', 'Vel', 'MaxVel', 'Range', 'CollideType', 'NextHit', 'NextDelay', 'Size', 'ToHit', 'ReturnFire',
    'MissileSkill', 'Skill', 'HitFlags', 'ExplosionMissile', 'Explosion', 'CollideKill',
    'EType', 'EMin', 'MinELev1', 'MinELev2', 'MinELev3', 'MinELev4', 'MinELev5', 'EMax', 'MaxELev1', 'MaxELev2',
    'MaxELev3', 'MaxELev4', 'MaxELev5', 'ELen', 'HitShift',
)  # fmt: skip
MONSTER_FIELDS = (
    'Id', 'NameStr', 'MonType', 'Level(H)', 'MinHP(H)', 'MaxHP(H)', 'AC(H)', 'ResDm(H)', 'ResMa(H)', 'ResFi(H)',
    'ResLi(H)', 'ResCo(H)', 'ResPo(H)', 'Velocity', 'Run', 'SizeX', 'SizeY', 'Align', 'boss', 'npc', 'killable',
    # How it moves and strikes (sim/monsters.py): the AI and its parameters, the attacks' damage and to-hit.
    'AI', 'aidel(H)', 'aidist(H)', 'aip1(H)', 'aip2(H)', 'aip3(H)', 'aip4(H)', 'aip5(H)', 'isMelee',
    'A1MinD(H)', 'A1MaxD(H)', 'A1TH(H)', 'A2MinD(H)', 'A2MaxD(H)', 'A2TH(H)',
)  # fmt: skip
# monumod.txt's constants (a second table in the file's last columns), by their description: Hell's.
UNIQUE_CONSTANTS = {
    'unique_element': ('Unique Elemental Min Damage % Bonus (Hell)', 'Unique Elemental Max Damage % Bonus (Hell)'),
    'champion_element': (
        'Champion Elemental Min Damage % Bonus (Hell)',
        'Champion Elemental Max Damage % Bonus (Hell)',
    ),
    'minion_element': (
        'Minion of Unique Elemental Min Damage % Bonus (Hell)',
        'Minion of Unique Elemental Max Damage % Bonus (Hell)',
    ),
    'champion_damage': ('Champion Damage % Bonus',),
    'strong_damage': ('Unique Damage % Bonus (strong)',),
    'minion_strong_damage': ('Minion of Unique Damage % Bonus (strong)',),
}
RANK_DAMAGE = {'unique_damage': 'UniqueDamageBonus', 'champion_rank_damage': 'ChampionDamageBonus'}  # difficultylevels
ZONES = Path(__file__).parents[3] / 'terror_zones' / 'data' / 'desecratedzones-game.json'
LEVEL_FIELDS = ('HP(H)', 'L-HP(H)', 'AC(H)', 'L-AC(H)', 'TH(H)', 'L-TH(H)', 'DM(H)', 'L-DM(H)')


def rows(game, name: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(game.read(EXCEL.format(name)).decode('latin-1')), delimiter='\t'))


def pick(row: dict[str, str], fields) -> dict[str, str]:
    return {field: row[field] for field in fields if row.get(field, '') != ''}


def build(install: Path) -> dict[str, Any]:
    from terror_zones.game_files import GameFiles

    game = GameFiles(install)
    skills = {int(r['*Id']): r for r in rows(game, 'skills') if r.get('*Id', '').isdigit()}
    missiles = {int(r['*ID']): r for r in rows(game, 'missiles') if r.get('*ID', '').isdigit()}
    monsters = {int(r['*hcIdx']): r for r in rows(game, 'monstats') if r.get('*hcIdx', '').isdigit()}
    levels = [r for r in rows(game, 'levels') if r.get('Id', '').isdigit() and r.get('MonLvlEx(H)')]
    constants = {r['*constant desc']: int(r['constants']) for r in rows(game, 'monumod') if r.get('*constant desc')}
    hell = json.loads(ZONES.read_text())['desecrated_zones'][0]['game_difficulties']['rotw']['hell']
    heralds = {
        str(tier): {
            'damage': row['herald_damage_boost_percent'],
            'life': row['herald_health_boost_percent'],
            'minion_damage': row['minion_damage_boost_percent'],
            'minion_life': row['minion_health_boost_percent'],
        }
        for tier, row in enumerate(hell['defaults']['herald_tiers'], 1)
    }
    difficulty = next(r for r in rows(game, 'difficultylevels') if r['Name'] == 'Hell')
    unique = {name: [constants[text] for text in texts] for name, texts in UNIQUE_CONSTANTS.items()}
    unique.update((name, [int(difficulty[column])]) for name, column in RANK_DAMAGE.items())
    # Missiles that take nothing off the character (takes/hurts.py): those that collide with nothing
    # and carry no damage (blood, ice breaking, a sigil's mark), and its own skills' and blades'.
    own = {mid for mid, r in missiles.items() if r.get('Skill') in SKILLS.values()} | set(MISSILES[:2])
    damage = ('MinDamage', 'MaxDamage', 'EMin', 'EMax')
    inert = {
        mid
        for mid, r in missiles.items()
        if r.get('CollideType', '') in ('', '0') and not any(r.get(column) for column in damage)
    }
    return {
        'harmless_missiles': sorted(own | inert),
        'unique': unique,
        'heralds': heralds,
        'source': f'D2R install {install.name}: data/global/excel skills, missiles, monstats, monlvl, levels, monumod',
        'skills': {str(sid): pick(skills[sid], SKILL_FIELDS) for sid in SKILLS},
        'missiles': {str(mid): pick(missiles[mid], MISSILE_FIELDS) for mid in MISSILES},
        'monsters': {str(hc): pick(r, MONSTER_FIELDS) for hc, r in monsters.items() if r.get('Level(H)')},
        'monlvl': {r['Level']: pick(r, LEVEL_FIELDS) for r in rows(game, 'monlvl') if r.get('Level', '').isdigit()},
        'areas': {r['Id']: r['MonLvlEx(H)'] for r in levels},
    }


@cache
def tables() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def area_level(area: int) -> int | None:
    found = tables()['areas'].get(str(area))
    return int(found) if found else None


def monster_points(txt_id: int, area: int) -> tuple[int, int] | None:
    """(least, most) life points of a regular monster of `txt_id` in `area` on Hell: the area's
    monster level row of monlvl scaled by the monster's HP percent range; None when unknown."""
    monster = tables()['monsters'].get(str(txt_id))
    level = area_level(area)
    if monster is None or level is None or not monster.get('MinHP(H)'):
        return None
    base = int(tables()['monlvl'][str(level)]['HP(H)'])
    return base * int(monster['MinHP(H)']) // 100, base * int(monster['MaxHP(H)']) // 100


def default_points(area: int) -> float:
    """A monster without a monstats row: the area level's base points (100%)."""
    level = area_level(area)
    return float(tables()['monlvl'][str(level)]['HP(H)']) if level else 0.0


def points_of(txt_id: int, area: int) -> float:
    """Life points of a monster at full health for the models: the mean of its range, else the area's base."""
    found = monster_points(txt_id, area)
    return sum(found) / 2 if found else default_points(area)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('install', type=Path, help='game folder (holds D2R.exe and data/)')
    args = parser.parse_args(argv)
    bundle = build(args.install)
    DATA.write_text(json.dumps(bundle, indent=1, sort_keys=True))
    print(f'{DATA}: {len(bundle["monsters"])} monsters, {len(bundle["monlvl"])} levels, {len(bundle["areas"])} areas')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
