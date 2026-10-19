"""Ratchet: framework code (macros/, combat/) may not name build-specific things outside builds/.

Build-specific names (Echoing Strike, the Defiler, the blades) are found by AST in the framework
packages and recorded in ALLOWED, and so is an import of `inventory_tracking.builds` from framework
code (the framework is handed a build, it does not import one), recorded as '<builds import>'. A new
hit fails test_nothing_specific_is_named_outside_the_builds:
move the code into inventory_tracking/builds/, or, if the name is generic, remove it from SPECIFIC
with a reason. A recorded hit that disappeared fails test_the_allowed_list_only_shrinks: remove it
from ALLOWED so the list only ever shrinks.

What is left after the build's model, simulator and analysis moved under builds/ (framework-plan.md
Task 3.8) is the residue, and each piece of it says why it is still there:

- RESIDUE: one reason per pair of ALLOWED, the names the scan finds in the framework;
- UNSEEN: what is the Warlock's in the framework under a name the scan cannot tell from a plain word,
  or as a number, kept by hand: a note, checked only for the name still being in the file;
- ELSEWHERE: the same names in the packages that are neither the framework nor a build (routes/,
  tracking/, osd/, the service that hands the builds in). They are not part of this refactor: the list
  records them, and a new one fails test_nothing_new_is_named_in_the_other_packages.
"""

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SKILLS = ROOT / 'inventory_tracking' / 'builds' / 'warlock' / 'skills.py'  # the Warlock's skill ids
SHARED_SKILLS = ROOT / 'inventory_tracking' / 'macros' / 'skills.py'  # the skills any character has
FRAMEWORK = ('inventory_tracking/macros', 'inventory_tracking/combat')
ECHOING_MODULE = 'inventory_tracking.combat.mechanics.echoing_strike'
ECHOING_PSEUDO = '<echoing_strike module>'
BUILDS_PACKAGE = 'inventory_tracking.builds'
BUILDS_PSEUDO = '<builds import>'
# Town Portal: any character with a tome has it on a key (macros/portal.py, the KP_6 loop's phase 3), and any wearing
# the Sling, a unique Ring of no class (uniqueitems.txt `oskill` "Townportal O Skill": macros/sling-plan.md)
GENERIC = frozenset({'TELEPORT', 'TOWN_PORTAL', 'SLING_TOWN_PORTAL', 'ATTACK', 'SWAP_WEAPONS'})
UPPER = re.compile(r'^[A-Z][A-Z0-9_]*$')

NAMED: dict[str, str] = {
    'LinePolicy': "Echoing Strike's cast policy",
    'virtual_cast': "Echoing Strike's blades",
    'BLADES': 'the blades of one cast',
    'BLADES_A_CAST': 'blade contacts a cast is priced by',
    'DUPLICATE': 'the duplicate-blade rule',
    'CHARACTERS': "one character's weapon sets",
    'DEFILER': 'a Warlock summon',
    'DEFILER_CLASS': 'a Warlock summon',
    'damage_table': "this build's damage file",
    'link_table': "the Defiler's Health Link",
    'linked_set': "the Defiler's Health Link",
    # The Warlock's buffs as the world reads them off the character (macros/game/records.py `Player`)
    'HEX_PURGE_BIT': 'the state bit of Hex: Purge',
    'PSYCHIC_WARD_BIT': 'the state bit of Psychic Ward',
    'hex_purge': 'whether Hex: Purge is on the character',
    'ward': 'whether Psychic Ward is on the character',
    'consume': "the Warlock's Consume buff",
    'read_consume': "the reader of the Warlock's Consume buff",
}


def int_constants(path: Path) -> set[str]:
    """UPPER_CASE module-level int constants of one Python file."""
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    names = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
            continue
        if type(node.value.value) is not int:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and UPPER.match(target.id):
                names.add(target.id)
    return names


def derived_specific() -> set[str]:
    """The skill ids a build defines (builds/warlock/skills.py), minus the generic skills."""
    return int_constants(SKILLS) - GENERIC


SPECIFIC: frozenset[str] = frozenset(derived_specific() | set(NAMED))


ECHOING_PACKAGE, ECHOING_LEAF = ECHOING_MODULE.rsplit('.', 1)


def _imports_echoing(node: ast.Import | ast.ImportFrom) -> bool:
    """`import ...echoing_strike`, `from ...echoing_strike import x`, `from ...mechanics import echoing_strike`."""
    if isinstance(node, ast.Import):
        return any(alias.name == ECHOING_MODULE for alias in node.names)
    if node.module == ECHOING_MODULE:
        return True
    return node.module == ECHOING_PACKAGE and any(alias.name == ECHOING_LEAF for alias in node.names)


def _imports_a_build(node: ast.Import | ast.ImportFrom) -> bool:
    """`import inventory_tracking.builds[.x]`, `from inventory_tracking.builds[.x] import y`,
    `from inventory_tracking import builds`: at a module's top or late, inside a function."""

    def within(name: str | None) -> bool:
        return name is not None and (name == BUILDS_PACKAGE or name.startswith(BUILDS_PACKAGE + '.'))

    if isinstance(node, ast.Import):
        return any(within(alias.name) for alias in node.names)
    if within(node.module):
        return True
    package, leaf = BUILDS_PACKAGE.rsplit('.', 1)
    return node.module == package and any(alias.name == leaf for alias in node.names)


def scan(path: Path, specific: frozenset[str] | set[str]) -> set[str]:
    """Build-specific identifiers that one Python file names in code (not in comments or strings)."""
    tree = ast.parse(Path(path).read_text(encoding='utf-8'), filename=str(path))
    hits: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in specific:
            hits.add(node.id)
        elif isinstance(node, ast.Attribute) and node.attr in specific:
            hits.add(node.attr)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name in specific:
                hits.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                for sub in ast.walk(target):
                    if isinstance(sub, ast.Name) and sub.id in specific:
                        hits.add(sub.id)
        elif isinstance(node, ast.ImportFrom):
            hits.update(alias.name for alias in node.names if alias.name in specific)
            if _imports_echoing(node):
                hits.add(ECHOING_PSEUDO)
            if _imports_a_build(node):
                hits.add(BUILDS_PSEUDO)
        elif isinstance(node, ast.Import):
            if _imports_echoing(node):
                hits.add(ECHOING_PSEUDO)
            if _imports_a_build(node):
                hits.add(BUILDS_PSEUDO)
    return hits


def found() -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for package in FRAMEWORK:
        for path in sorted((ROOT / package).rglob('*.py')):
            rel = path.relative_to(ROOT).as_posix()
            pairs.update((rel, ident) for ident in scan(path, SPECIFIC))
    return pairs


LAYOUT = 'inventory_tracking/macros/game/layout.py'
RECORDS = 'inventory_tracking/macros/game/records.py'
DECODE = 'inventory_tracking/macros/game/decode.py'

# Why each allowed pair is still in the framework. All of it is the world's reading of the game: what
# the Warlock's own units and buffs look like in memory, read for every character and used by the
# build alone. A build cannot be asked for it yet: `World` is read before a build is chosen, and a
# build has no part in reading memory (architecture.md 4.0; framework-plan.md Task 3.8, out of scope).
RESIDUE: dict[tuple[str, str], str] = {
    (LAYOUT, 'DEFILER_CLASS'): "the Defiler's txt id: its raw unit bytes are read into `Monster.raw` for research",
    (LAYOUT, 'HEX_PURGE_BIT'): "the state bit `Player.hex_purge` is read from; the build's buff row asks the field",
    (LAYOUT, 'PSYCHIC_WARD_BIT'): "the state bit `Player.ward` is read from; the build's buff row asks the field",
    (DECODE, 'DEFILER_CLASS'): 'the import of the txt id, for the raw bytes of the Defiler `monsters_and_dead` keeps',
    (DECODE, 'HEX_PURGE_BIT'): 'the import of the state bit `local_player` reads into `Player.hex_purge`',
    (DECODE, 'PSYCHIC_WARD_BIT'): 'the import of the state bit `local_player` reads into `Player.ward`',
    (DECODE, 'consume'): '`local_player` fills `Player.consume` as tracking/consume.py reads it',
    (DECODE, 'read_consume'): 'the import of tracking/consume.py, the reader behind `Player.consume`',
    (DECODE, 'ward'): '`local_player` fills `Player.ward`',
    (
        RECORDS,
        'consume',
    ): "`Player.consume`, the Consume buff as tracking/consume.py reads it; the build's caster asks it",
    (RECORDS, 'hex_purge'): "`Player.hex_purge`: a Warlock buff as a field of every character's record",
    (RECORDS, 'ward'): "`Player.ward`: a Warlock buff as a field of every character's record",
}
ALLOWED: frozenset[tuple[str, str]] = frozenset(RESIDUE)

POLICY = 'inventory_tracking/combat/policy.py'
TABLES = 'inventory_tracking/combat/mechanics/tables.py'
# The Warlock's in the framework where the scan is blind: a plain word, or a number behind a plain name.
UNSEEN: dict[tuple[str, str], str] = {
    (
        POLICY,
        'linked',
    ): "`Observation.linked`: the monsters the Defiler's Health Link holds, filled by the attack's `sees`",
    (POLICY, 'share'): "`Observation.share`: Health Link's share of the damage dealt again",
    (POLICY, 'marked'): '`Observation.marked`: the monsters under Death Mark',
    (POLICY, 'MIN_FOCAL'): "tuned with the blades; read by macros/hunt.py `off_labels` and by the build's sweep",
    (POLICY, 'MIN_SCORE'): "tuned with the blades' points; read by combat/stance.py `camp` and by the build's sweep",
    (POLICY, 'STRIKE_REACH'): "the hunt's reach, set two units short of the blades' flight",
    ('inventory_tracking/combat/stance.py', 'CAST_SECONDS'): "one cast of this build's held strike, 9 frames",
    (TABLES, 'SKILLS'): "the Warlock's skill rows bundled into data/tables.json, by id",
    (TABLES, 'MISSILES'): 'the blade missiles 706 and 720 bundled beside the two any monster casts',
    ('inventory_tracking/combat/viz_moments.py', 'blade_life'): "a default of 38 frames: the blades' life",
}

# The packages that are neither the framework nor a build, with what they name of the Warlock's.
OTHER = (
    'appraisal',
    'automation',
    'collection',
    'corpus',
    'hover',
    'hud',
    'identify',
    'input',
    'items',
    'levels',
    'loot',
    'native',
    'osd',
    'probes',
    'routes',
    'shop',
    'terror',
    'tracking',
)
ELSEWHERE: dict[tuple[str, str], str] = {
    ('inventory_tracking/appraisal/service.py', BUILDS_PSEUDO): 'the process start: it hands the builds to the runner',
    ('inventory_tracking/config.py', 'consume'): "the OSD's settings for the Consume widget",
    ('inventory_tracking/models.py', 'consume'): 'the Consume buff in the tracked state the OSD shows',
    ('inventory_tracking/osd/presenter.py', 'consume'): 'the Consume widget',
    ('inventory_tracking/osd/widgets/consume.py', 'consume'): 'the Consume widget',
    ('inventory_tracking/routes/catalog/act3.py', 'BLADE_WARP'): "a route's step by the Warlock's jump",
    ('inventory_tracking/routes/catalog/act3.py', 'DEATH_MARK'): "a route's opener at Mephisto",
    ('inventory_tracking/routes/catalog/act3.py', 'SIGIL_LETHARGY'): "a route's opener at Mephisto",
    ('inventory_tracking/routes/model.py', 'BLADE_WARP'): 'its own copy of the skill id (builds/warlock/skills.py)',
    ('inventory_tracking/routes/model.py', 'DEATH_MARK'): 'its own copy of the skill id (builds/warlock/skills.py)',
    ('inventory_tracking/routes/model.py', 'SIGIL_LETHARGY'): 'its own copy of the skill id (builds/warlock/skills.py)',
    ('inventory_tracking/tracking/consume.py', 'read_consume'): "the reader of the Warlock's Consume buff",
}


def found_elsewhere() -> set[tuple[str, str]]:
    package = ROOT / 'inventory_tracking'
    paths = sorted(package.glob('*.py'))
    for name in OTHER:
        paths += sorted((package / name).rglob('*.py'))
    pairs: set[tuple[str, str]] = set()
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        pairs.update((rel, ident) for ident in scan(path, SPECIFIC))
    return pairs


def test_nothing_specific_is_named_outside_the_builds() -> None:
    new = sorted(found() - ALLOWED)
    listing = '\n'.join(f'  {path}: {ident}' for path, ident in new)
    assert not new, (
        'New build-specific names in framework code:\n'
        f'{listing}\n'
        'Move it into inventory_tracking/builds/ or, if it is generic, take the name out of '
        'SPECIFIC with a reason.'
    )


def test_the_allowed_list_only_shrinks() -> None:
    gone = sorted(ALLOWED - found())
    listing = '\n'.join(f'  {path}: {ident}' for path, ident in gone)
    assert not gone, f'Recorded hits no longer found:\n{listing}\nno longer found: remove it from ALLOWED'


def test_every_allowed_pair_says_why_it_is_still_there() -> None:
    assert set(RESIDUE) == ALLOWED
    assert all(reason.strip() for reason in RESIDUE.values())


def test_what_the_scan_cannot_see_is_still_where_the_note_says() -> None:
    gone = sorted((path, name) for path, name in UNSEEN if name not in scan(ROOT / path, {name}))
    assert not gone, f'No longer in the file: {gone}\nremove the note from UNSEEN'
    assert all(reason.strip() for reason in UNSEEN.values())
    assert not set(UNSEEN) & ALLOWED


def test_the_other_packages_are_all_the_packages_there_are() -> None:
    package = ROOT / 'inventory_tracking'
    has_code = {path.name for path in package.iterdir() if path.is_dir() and any(path.glob('*.py'))}
    assert has_code - {'macros', 'combat', 'builds'} == set(OTHER)


def test_nothing_new_is_named_in_the_other_packages() -> None:
    seen = found_elsewhere()
    new = sorted(seen - set(ELSEWHERE))
    listing = '\n'.join(f'  {path}: {ident}' for path, ident in new)
    assert not new, (
        'New build-specific names outside the framework and the builds:\n'
        f'{listing}\n'
        'Ask the build for it, or record it in ELSEWHERE with a reason; a generic name comes out of SPECIFIC.'
    )
    gone = sorted(set(ELSEWHERE) - seen)
    assert not gone, f'Recorded hits no longer found: {gone}\nremove them from ELSEWHERE'
    assert all(reason.strip() for reason in ELSEWHERE.values())


def test_the_scan_sees_names_attributes_imports_and_definitions_but_not_comments(
    tmp_path: Path,
) -> None:
    source = '''"""Module docstring naming ECHOING_STRIKE, which must not count."""
from inventory_tracking.macros.world import DEFILER as D  # ECHOING_STRIKE in a comment
import inventory_tracking.combat.mechanics.echoing_strike
x = ECHOING_STRIKE
y = mod.BLADES
BLADES_A_CAST = 3


def virtual_cast():
    """Docstring naming BLADES, which must not count."""
'''
    path = tmp_path / 'sample.py'
    path.write_text(source, encoding='utf-8')
    assert scan(path, SPECIFIC) == {
        'DEFILER',
        ECHOING_PSEUDO,
        'ECHOING_STRIKE',
        'BLADES',
        'BLADES_A_CAST',
        'virtual_cast',
    }


def test_the_scan_sees_an_import_of_a_build_at_the_top_and_inside_a_function(tmp_path: Path) -> None:
    sources = {
        'top.py': 'from inventory_tracking.builds.generic import GENERIC\n',
        'late.py': 'def default():\n    from inventory_tracking.builds.generic import GENERIC\n    return GENERIC\n',
        'plain.py': 'import inventory_tracking.builds.generic\n',
        'package.py': 'from inventory_tracking import builds\n',
        'other.py': 'from inventory_tracking.macros.build import Build\nimport inventory_tracking.buildsmith\n',
    }
    seen = {}
    for name, source in sources.items():
        path = tmp_path / name
        path.write_text(source, encoding='utf-8')
        seen[name] = scan(path, SPECIFIC)
    assert seen == {
        'top.py': {BUILDS_PSEUDO},
        'late.py': {BUILDS_PSEUDO},
        'plain.py': {BUILDS_PSEUDO},
        'package.py': {BUILDS_PSEUDO},
        'other.py': set(),
    }


def test_the_generic_skills_are_not_specific() -> None:
    assert GENERIC.isdisjoint(SPECIFIC)
    assert 'ECHOING_STRIKE' in SPECIFIC


def test_the_framework_defines_the_generic_skills_and_no_other() -> None:
    assert int_constants(SHARED_SKILLS) <= GENERIC  # Swap Weapons is -1, no constant to the parser


def test_the_ten_skills_of_the_warlock_are_guarded() -> None:
    assert derived_specific() == {
        'BIND_DEMON',
        'BLADE_WARP',
        'CONSUME',
        'DEATH_MARK',
        'ECHOING_STRIKE',
        'ENGORGE',
        'HEX_PURGE',
        'PSYCHIC_WARD',
        'SIGIL_LETHARGY',
        'SUMMON_DEFILER',
    }
