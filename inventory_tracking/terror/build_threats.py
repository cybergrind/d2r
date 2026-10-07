"""Regenerate terror/data/threats.json from the installed game's tables (danger-plan.md R1/R2).

Per monster type the numbers the danger model (terror/danger.py) weighs: Hell physical, elemental
and magic damage as multiples of the monster level's base damage (monlvl.txt `DM(H)`; monstats
damage columns are percents of it; d2data's monstats.json has the same values, 2026-10-06),
whether it attacks from range (then the numbers are the ranged attack's), how fast it moves (the
faster of `Velocity` and `Run`: what a melee attacker needs to reach the player), whether a skill
closes the distance for it (Charge, Leap) or doubles its swings (Frenzy), and the curses it casts. Also
the auras an aura-enchanted monster can carry (skills.txt rows by id, with their range) and the
names of the unique modifiers (monumod.txt ids).

Runtime code reads only the bundled table; the install is a build input.
Run: uv run --offline python -m inventory_tracking.terror.build_threats "<install>"
"""

import argparse
import csv
import io
import json
from pathlib import Path

from inventory_tracking.reports import publish
from terror_zones.game_files import GameFiles


OUTPUT = Path(__file__).parent / 'data' / 'threats.json'
EXCEL = 'data/global/excel/{}.txt'
STRINGS = 'data/local/lng/stringsmonsters.json'  # the manifest's own spelling (2026-10-06)
TABLES = ('monstats', 'skills', 'monumod')

# Elemental damage types that take life and that resistances cut ('rand' is one of them at
# random); 'mag' is magic damage, apart. Poison is slow; mana and stamina drains are not damage.
RESISTED = frozenset(('fire', 'ltng', 'cold', 'frze', 'rand'))
ATTACKS = ('A1', 'A2', 'S1')
SKILL_MODES = ('SC', 'S1', 'S2')
ALL_MODES = (*ATTACKS, 'SC', 'S2')
# Families (monstats BaseId) that fight from range though `rangedtype` is empty: their attack is
# a skill (Hydra, Unholy Bolt, the Doom Caster's missile).
EXTRA_RANGED = frozenset(('councilmember1', 'baalhighpriest', 'unraveler1', 'radament', 'fingermage1'))
CLOSING = frozenset(('Charge', 'SerpentCharge', 'MonLeap', 'MonLeapAttack'))  # reach the player whatever their speed
FRENZY = frozenset(('MonFrenzy', 'BloodLordFrenzy', 'Goatman Frenzy'))
CURSES = frozenset(('Amplify Damage', 'Decrepify', 'Lower Resist'))
# The auras seen on aura-enchanted monsters in the probe logs (stat 350, 2026-10-06).
AURAS = ('Might', 'Blessed Aim', 'Fanaticism', 'Conviction', 'MonHolyFreeze', 'MonHolyFire', 'MonHolyShock')
AURA_NAMES = {'MonHolyFreeze': 'Holy Freeze', 'MonHolyFire': 'Holy Fire', 'MonHolyShock': 'Holy Shock'}
MODIFIER_NAMES = {
    'strong': 'Extra Strong',
    'fast': 'Extra Fast',
    'curse': 'Cursed',
    'resist': 'Magic Resistant',
    'fire': 'Fire Enchanted',
    'lightning': 'Lightning Enchanted',
    'cold': 'Cold Enchanted',
    'manahit': 'Mana Burn',
    'teleport': 'Teleportation',
    'spectralhit': 'Spectral Hit',
    'stoneskin': 'Stone Skin',
    'multishot': 'Multiple Shots',
    'aura': 'Aura Enchanted',
    'champion': 'Champion',
    'ghostly': 'Ghostly',
    'fanatic': 'Fanatic',
    'possessed': 'Possessed',
    'berserk': 'Berserker',
}


def table(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text), delimiter='\t'))


def number(row, column) -> int:
    return int(row.get(column) or 0)


def element(row, n) -> float:
    return number(row, f'El{n}MaxD(H)') * number(row, f'El{n}Pct(H)') / 100


def damage(row, modes) -> tuple[float, float, float]:
    """(physical, elemental, magic) percents of the attacks in `modes` (monstats El*Mode names)."""
    physical = max((number(row, f'{mode}MaxD(H)') for mode in modes if mode in ATTACKS), default=0)
    found = [(row[f'El{n}Type'], element(row, n)) for n in (1, 2, 3) if row.get(f'El{n}Mode') in modes]
    elemental = sum(value for kind, value in found if kind in RESISTED)
    return physical, elemental, sum(value for kind, value in found if kind == 'mag')


def ranged_damage(row) -> tuple[float, float, float]:
    """What the ranged attack does: the attack that fires the missile, with its elements. A caster
    without a missile column does its damage in a skill the monstats row does not hold: the
    elements of its skill modes count, or else its melee swing stands in, as magic."""
    for column, mode in (('MissA1', 'A1'), ('MissA2', 'A2'), ('MissS1', 'S1'), ('MissC', 'SC')):
        if row.get(column):
            found = damage(row, (mode,))
            if any(found):
                return found
    found = damage(row, SKILL_MODES)
    return found if any(found) else (0, 0, number(row, 'A1MaxD(H)'))


def monster(row, names) -> dict:
    ranged = row.get('rangedtype') == '1' or row['BaseId'] in EXTRA_RANGED
    physical, elemental, magic = ranged_damage(row) if ranged else damage(row, ALL_MODES)
    skills = {row.get(f'Skill{n}') for n in range(1, 9)}
    result = {
        'name': names.get(row['NameStr'], row['NameStr']),
        'family': row['BaseId'],
        'physical': round(physical / 100, 2),
        'elemental': round(elemental / 100, 2),
        'magic': round(magic / 100, 2),
        'speed': max(number(row, 'Velocity'), number(row, 'Run')),
    }
    if ranged:
        result['ranged'] = True
    if skills & CLOSING:
        result['closes'] = True
    if skills & FRENZY:
        result['frenzy'] = True
    if curses := sorted(skills & CURSES):
        result['curses'] = curses
    return result


def build(tables: dict[str, list[dict[str, str]]], names: dict[str, str], source: str) -> dict:
    monsters = {
        row['*hcIdx']: monster(row, names)
        for row in tables['monstats']
        if row.get('*hcIdx') and row.get('enabled') == '1' and row.get('killable') == '1' and row.get('npc') != '1'
    }
    auras = {
        row['*Id']: {
            'name': AURA_NAMES.get(row['skill'], row['skill']),
            # skills.txt aurarangecalc `ln12`: Param1 + (level - 1) x Param2, in world units.
            'range': [number(row, 'Param1'), number(row, 'Param2')],
        }
        for row in tables['skills']
        if row['skill'] in AURAS
    }
    modifiers = {
        row['id']: MODIFIER_NAMES[row['uniquemod']] for row in tables['monumod'] if row['uniquemod'] in MODIFIER_NAMES
    }
    return {'source': source, 'monsters': monsters, 'auras': auras, 'modifiers': modifiers}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('install', type=Path, help='game folder (holds D2R.exe and data/)')
    args = parser.parse_args(argv)
    game = GameFiles(args.install)
    tables = {name: table(game.read(EXCEL.format(name)).decode('latin-1')) for name in TABLES}
    strings = json.loads(game.read(STRINGS).decode('utf-8-sig'))
    names = {entry['Key']: entry['enUS'] for entry in strings}
    config = (args.install / 'data' / '.build.config').read_text()
    version = next((line.split('=', 1)[1].strip() for line in config.splitlines() if line.startswith('build-name')), '')
    source = f'D2R install data/global/excel monstats, skills, monumod ({version or "unknown build"})'
    publish(OUTPUT, build(tables, names, source))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
