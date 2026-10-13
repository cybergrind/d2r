"""The monster types a situation names in words, and what the arena plays of each (the fidelity table of
rca/2026-10-13/situations.md is printed from here: `python -m ...situations.bestiary`).

A txt id is a row of monstats. None is written from memory: each one below was looked up in
pricing/raw/game-excel/monstats.txt by its `NameStr` and the string table's name (2026-10-13), and
test_situations.py checks every one against the `NameStr` the repo's own tables hold
(combat/data/tables.json, which is checked in). Where the game has several rows of one name (a Black Soul is
rows 121 and 640), the row is the one the threat table knows, because the arena decides by that table whether
a type shoots or explodes (mobs.py `shooter`, `explodes`): row 121 has none and would walk up and swing.

Read against the game's table, not against how the types are spoken of:

- **the living Stygian Doll and Soul Killer do not explode**: monstats `deathDmg` is set for the `bonefetish`
  rows only (Undead Stygian Doll, Undead Soul Killer, Undead Flayer). A situation that wants the explosion
  names the undead one;
- a Death Lord is `bloodlord5`, a Minion of Destruction `baalminion1`.

`fidelity` says for a type what of it the arena plays and what it does not, from the model's own tables, so
the words follow the code: whether it is a shooter or a walker here, whether its swings and shots have a row
of their own in the fit (combat/data/monsters_fit.json) or the pooled one, whether its corpse explodes, and
the defining thing of the type that is missing (`MISSING`, written by hand from monstats' skill columns and
rca/2026-10-13/re/notes-mobs.md).
"""

from dataclasses import dataclass

from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.sim.casters import mind_of, row_of
from inventory_tracking.combat.sim.monsters import Traits, fitted, idle, shooter_of, swing_of
from tests.inventory_tracking.scenarios.arena.mobs import explodes, shooter, threat_row
from tests.inventory_tracking.scenarios.threat.harness import BLAST, BLAST_RADIUS


# name -> (txt, monstats NameStr)
TYPES: dict[str, tuple[int, str]] = {
    'Stygian Doll': (145, 'StygianDoll'),
    'Undead Stygian Doll': (216, 'Undead StygianDoll'),
    'Undead Soul Killer': (215, 'Undead SoulKiller'),
    'Gloam': (639, 'Gloam'),
    'Black Soul': (640, 'BlackSoul'),
    'Burning Soul': (641, 'BurningSoul'),
    'Death Lord': (510, 'Blood Lord5'),
    'Minion of Destruction': (571, 'Baals Minion'),
    'Storm Caster': (306, 'StormCaster'),
    'Doom Knight': (310, 'DoomKnight'),
    'Oblivion Knight': (312, 'OblivionKnight'),
    'Venom Lord': (362, 'VenomLord'),
    'Hell Bovine': (391, 'Hell Bovine'),
}
NAMES = {txt: name for name, (txt, _) in TYPES.items()}
# What defines the type in the game and the arena does not play. By hand; the sources are in the module text.
MISSING: dict[str, str] = {
    'Stygian Doll': 'its speed is monstats Velocity x 1.1, not measured; no death explosion in the game either',
    'Undead Stygian Doll': (
        "the explosion is the threat harness's 450 physical within 4 units, one number for every type and "
        'level (the game scales it with the corpse); it is dealt the tick after the kill, with no roll'
    ),
    'Undead Soul Killer': 'as the Undead Stygian Doll',
    'Gloam': 'see Burning Soul',
    'Black Soul': 'see Burning Soul',
    'Burning Soul': (
        'the lightning is a pooled shooter missile (a bolt flying 20.6 units a second that lands with the '
        'pooled chance, 0.024): no instant bolt, no chain, no mana burn of its touch; the takes hold none of '
        'the family. `lands=` gives a situation its own chance (an assumption)'
    ),
    'Death Lord': 'Frenzy (BloodLordFrenzy: faster and faster double swings) is not played; pooled swings',
    'Minion of Destruction': 'no threat-table row; pooled swings; Smite and its stun are not played',
    'Storm Caster': (
        'the lead missile only (the trail of 177s it leaves is taken to hurt nobody); its pack does not wake with it '
        '(rca/2026-10-13/sim-casters.md); the ward takes its physical part and stuns it after a swing that lands '
        '(sim/guard.py)'
    ),
    'Doom Knight': 'the ward takes the physical part of its swing and stuns it 72 frames after one that lands '
    '(sim/guard.py; the level behind the 72 is a stand-in, builds/warlock/ward.py)',
    'Oblivion Knight': (
        "MonCurseCast's choice of curse is drawn evenly (its server function is not read); Decrepify's slower run and "
        "attack are not played; the ward takes its bolts' physical points (sim/guard.py)"
    ),
    'Venom Lord': (
        'the flames are fire: the ward takes none of them (sim/guard.py), and the takes lose 8 to 12 times less to '
        'them than the arena for a cause not found (rca/2026-10-13/sim-casters.md section 9)'
    ),
    'Hell Bovine': 'pooled swings',
}


def txt_of(name: str | int) -> int:
    """The monstats row of a type named in words (TYPES), or the id itself."""
    if isinstance(name, int):
        return name
    if name not in TYPES:
        raise KeyError(f'{name!r} is not in the bestiary: {", ".join(sorted(TYPES))} (or give the txt id)')
    return TYPES[name][0]


def name_of(txt: int) -> str:
    """The type's name: the bestiary's, else the monstats `NameStr`, else its number."""
    if txt in NAMES:
        return NAMES[txt]
    return str(tables()['monsters'].get(str(txt), {}).get('NameStr') or f'monster {txt}')


@dataclass(frozen=True)
class Fidelity:
    name: str
    txt: int
    plays: str  # what the arena does with it
    lacks: str


def fidelity(name: str, level: int = 85) -> Fidelity:
    txt = txt_of(name)
    traits = Traits.of(txt, level)
    fit = fitted()
    if mind_of(txt) is not None:
        row = row_of(txt) or {}
        skills = ', '.join(row[f'Skill{n}'] for n in range(1, 9) if row.get(f'Skill{n}'))
        plays = (
            f'its AI as read in the client ({mind_of(txt)}, sim/casters.py): wakes within 35, the nearest of the '
            f'character and its companions; {skills or "no skill"} from the game tables, curses as states'
        )
    elif shooter(txt):
        own = str(txt) in fit['shots']['types']
        row = shooter_of(txt)
        kinds = '/'.join(
            threat_row(txt).get('multiple', {})
            and [k for k, v in threat_row(txt)['multiple'].items() if v and k != 'hard']
        )
        plays = (
            f'shooter ({"own" if own else "pooled"} row): {row["rate"]["value"]:.2f} shots/s within 30 units in '
            f'sight, a missile at {row["speed"]["value"]:.1f} u/s that takes life with chance '
            f'{row["takes_life"]["value"]:.3f}; shot from the threat table ({kinds}); never swings'
        )
    elif idle(txt):
        plays = 'stands (the takes show it never striking)'
    else:
        own = str(txt) in fit['melee']['types']
        row = swing_of(txt)
        plays = (
            f'melee walker ({"own" if own else "pooled"} row): walks {traits.speed * 25:.1f} u/s, a swing of '
            f'{row["frames"]["value"]} frames that takes life with chance {row["takes_life"]["value"]:.2f}, '
            f'{traits.damage[0]:.0f}-{traits.damage[1]:.0f} physical before the spread'
        )
    if explodes(txt):
        plays += f'; corpse explodes: {BLAST:.0f} physical within {BLAST_RADIUS:g} units'
    if not threat_row(txt):
        plays += '; no threat-table row'
    return Fidelity(name, txt, plays, MISSING.get(name, ''))


def table(level: int = 85) -> str:
    rows = [fidelity(name, level) for name in TYPES]
    lines = ['| type (txt) | what the arena plays | what it does not |', '| --- | --- | --- |']
    lines += [f'| {row.name} ({row.txt}) | {row.plays} | {row.lacks} |' for row in rows]
    return '\n'.join(lines)


if __name__ == '__main__':
    print(table())
