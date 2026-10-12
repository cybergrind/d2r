"""Ratchet: framework code (macros/, combat/) may not name build-specific things outside builds/.

Build-specific names (Echoing Strike, the Defiler, the blades) are found by AST in the framework
packages and recorded in ALLOWED, and so is an import of `inventory_tracking.builds` from framework
code (the framework is handed a build, it does not import one), recorded as '<builds import>'. A new
hit fails test_nothing_specific_is_named_outside_the_builds:
move the code into inventory_tracking/builds/, or, if the name is generic, remove it from SPECIFIC
with a reason. A recorded hit that disappeared fails test_the_allowed_list_only_shrinks: remove it
from ALLOWED so the list only ever shrinks.
"""

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SKILLS = ROOT / 'inventory_tracking' / 'macros' / 'skills.py'
FRAMEWORK = ('inventory_tracking/macros', 'inventory_tracking/combat')
ECHOING_MODULE = 'inventory_tracking.combat.mechanics.echoing_strike'
ECHOING_PSEUDO = '<echoing_strike module>'
BUILDS_PACKAGE = 'inventory_tracking.builds'
BUILDS_PSEUDO = '<builds import>'
GENERIC = frozenset({'TELEPORT', 'ATTACK', 'SWAP_WEAPONS'})
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
}


def derived_specific() -> set[str]:
    """UPPER_CASE module-level int constants in macros/skills.py, minus the generic skills."""
    tree = ast.parse(SKILLS.read_text(encoding='utf-8'), filename=str(SKILLS))
    names = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
            continue
        if type(node.value.value) is not int:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and UPPER.match(target.id):
                names.add(target.id)
    return names - GENERIC


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


ALLOWED: frozenset[tuple[str, str]] = frozenset(
    {
        ('inventory_tracking/combat/__main__.py', 'link_table'),
        ('inventory_tracking/combat/controller.py', 'LinePolicy'),
        ('inventory_tracking/combat/mechanics/damage.py', 'DEFILER'),
        ('inventory_tracking/combat/mechanics/damage.py', 'damage_table'),
        ('inventory_tracking/combat/mechanics/damage.py', 'link_table'),
        ('inventory_tracking/combat/mechanics/echoing_strike.py', 'BLADES'),
        ('inventory_tracking/combat/mechanics/hits.py', '<echoing_strike module>'),
        ('inventory_tracking/combat/mechanics/validate.py', '<echoing_strike module>'),
        ('inventory_tracking/combat/mechanics/validate.py', 'BLADES'),
        ('inventory_tracking/combat/policy.py', '<echoing_strike module>'),
        ('inventory_tracking/combat/policy.py', 'BLADES'),
        ('inventory_tracking/combat/policy.py', 'DEFILER'),
        ('inventory_tracking/combat/policy.py', 'DUPLICATE'),
        ('inventory_tracking/combat/policy.py', 'LinePolicy'),
        ('inventory_tracking/combat/policy.py', 'damage_table'),
        ('inventory_tracking/combat/policy.py', 'link_table'),
        ('inventory_tracking/combat/policy.py', 'linked_set'),
        ('inventory_tracking/combat/policy.py', 'virtual_cast'),
        ('inventory_tracking/combat/sim/engine.py', '<echoing_strike module>'),
        ('inventory_tracking/combat/sim/engine.py', 'BLADES'),
        ('inventory_tracking/combat/sim/engine.py', 'DEFILER'),
        ('inventory_tracking/combat/sim/engine.py', 'DUPLICATE'),
        ('inventory_tracking/combat/sim/engine.py', 'damage_table'),
        ('inventory_tracking/combat/sim/engine.py', 'link_table'),
        ('inventory_tracking/combat/sim/engine.py', 'linked_set'),
        ('inventory_tracking/combat/sim/policy.py', 'LinePolicy'),
        ('inventory_tracking/combat/sim/situation.py', '<echoing_strike module>'),
        ('inventory_tracking/combat/stance.py', 'BLADES_A_CAST'),
        ('inventory_tracking/combat/stance.py', 'LinePolicy'),
        ('inventory_tracking/combat/viz.py', '<echoing_strike module>'),
        # default.py `default_build`, temporary until the runner chooses the build: framework-plan.md Task 3.9
        ('inventory_tracking/macros/default.py', '<builds import>'),
        ('inventory_tracking/macros/hunt.py', 'CHARACTERS'),
        ('inventory_tracking/macros/hunt.py', 'CONSUME'),
        ('inventory_tracking/macros/hunt.py', 'DEATH_MARK'),
        ('inventory_tracking/macros/hunt.py', 'ECHOING_STRIKE'),
        ('inventory_tracking/macros/hunt.py', 'ENGORGE'),
        ('inventory_tracking/macros/hunt.py', 'LinePolicy'),
        ('inventory_tracking/macros/hunt.py', 'SUMMON_DEFILER'),
        ('inventory_tracking/macros/rotation.py', 'BLADES_A_CAST'),
        ('inventory_tracking/macros/rotation.py', 'DEATH_MARK'),
        ('inventory_tracking/macros/rotation.py', 'DEFILER_CLASS'),
        ('inventory_tracking/macros/rotation.py', 'ENGORGE'),
        ('inventory_tracking/macros/rotation.py', 'HEX_PURGE'),
        ('inventory_tracking/macros/rotation.py', 'LinePolicy'),
        ('inventory_tracking/macros/rotation.py', 'PSYCHIC_WARD'),
        ('inventory_tracking/macros/rotation.py', 'SIGIL_LETHARGY'),
        ('inventory_tracking/macros/routines.py', 'CHARACTERS'),
        ('inventory_tracking/macros/routines.py', 'CONSUME'),
        ('inventory_tracking/macros/routines.py', 'DEFILER'),
        ('inventory_tracking/macros/routines.py', 'DEFILER_CLASS'),
        ('inventory_tracking/macros/routines.py', 'HEX_PURGE'),
        ('inventory_tracking/macros/routines.py', 'PSYCHIC_WARD'),
        ('inventory_tracking/macros/routines.py', 'SUMMON_DEFILER'),
        ('inventory_tracking/macros/skills.py', 'BIND_DEMON'),
        ('inventory_tracking/macros/skills.py', 'BLADE_WARP'),
        ('inventory_tracking/macros/skills.py', 'CONSUME'),
        ('inventory_tracking/macros/skills.py', 'DEATH_MARK'),
        ('inventory_tracking/macros/skills.py', 'ECHOING_STRIKE'),
        ('inventory_tracking/macros/skills.py', 'ENGORGE'),
        ('inventory_tracking/macros/skills.py', 'HEX_PURGE'),
        ('inventory_tracking/macros/skills.py', 'PSYCHIC_WARD'),
        ('inventory_tracking/macros/skills.py', 'SIGIL_LETHARGY'),
        ('inventory_tracking/macros/skills.py', 'SUMMON_DEFILER'),
        ('inventory_tracking/macros/world.py', 'DEFILER_CLASS'),
    }
)


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


def test_the_scan_sees_names_attributes_imports_and_definitions_but_not_comments(
    tmp_path: Path,
) -> None:
    source = '''"""Module docstring naming ECHOING_STRIKE, which must not count."""
from inventory_tracking.macros.skills import DEFILER as D  # ECHOING_STRIKE in a comment
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
