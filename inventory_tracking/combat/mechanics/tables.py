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
MISSILES = (706, 720)
SKILL_FIELDS = (
    'skill', 'charclass', 'srvmissilea', 'calc1', 'calc5', 'calc6', 'Param1', 'Param2', 'Param3', 'Param4', 'Param5',
    'Param6', 'Param7', 'Param8', 'Param9', 'Param10', 'ToHitCalc', 'SrcDam', 'MinDam', 'MinLevDam1', 'MinLevDam2',
    'MinLevDam3', 'MinLevDam4', 'MinLevDam5', 'MaxDam', 'MaxLevDam1', 'MaxLevDam2', 'MaxLevDam3', 'MaxLevDam4',
    'MaxLevDam5', 'DmgSymPerCalc', 'mana', 'lvlmana', 'aurarangecalc', 'auralencalc', 'maxlvl',
)  # fmt: skip
MISSILE_FIELDS = (
    'Missile', 'Vel', 'MaxVel', 'Range', 'CollideType', 'NextHit', 'NextDelay', 'Size', 'ToHit', 'ReturnFire',
    'MissileSkill', 'Skill', 'HitFlags', 'ExplosionMissile', 'Explosion', 'CollideKill',
)  # fmt: skip
MONSTER_FIELDS = (
    'Id', 'NameStr', 'MonType', 'Level(H)', 'MinHP(H)', 'MaxHP(H)', 'AC(H)', 'ResDm(H)', 'ResMa(H)', 'ResFi(H)',
    'ResLi(H)', 'ResCo(H)', 'ResPo(H)', 'Velocity', 'Run', 'SizeX', 'SizeY', 'Align', 'boss', 'npc', 'killable',
)  # fmt: skip
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
    return {
        'source': f'D2R install {install.name}: data/global/excel skills, missiles, monstats, monlvl, levels',
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
