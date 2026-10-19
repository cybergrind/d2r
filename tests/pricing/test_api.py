"""The host/pricing boundary: `inventory_tracking` reaches pricing only through `pricing.api`."""

import ast
import subprocess
import sys
from importlib import import_module
from pathlib import Path

import pricing.api as api


ROOT = Path(__file__).resolve().parents[2]
# Host packages pricing must not reach into: the service glue lives there (cleanup phase 3 step 10).
HOST_ONLY = ('inventory_tracking.appraisal', 'inventory_tracking.corpus')
# Frozen maintenance tools that render host reports (study A2 splits maintenance/); no new entries.
RENDERS_HOST_REPORTS = {
    'pricing/knowledge/assessment/maintenance/named_gate.py',
    'pricing/knowledge/assessment/maintenance/replay.py',
}


def imported_modules(path):
    for node in ast.walk(ast.parse(path.read_text(), str(path))):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


def sources(directory):
    return sorted(p for p in (ROOT / directory).rglob('*.py') if '__pycache__' not in p.parts)


def test_host_imports_pricing_only_through_the_api():
    deep = [
        f'{path.relative_to(ROOT)}: {module}'
        for path in sources('inventory_tracking')
        for module in imported_modules(path)
        if (module == 'pricing' or module.startswith('pricing.')) and module != 'pricing.api'
    ]
    assert deep == []


def test_pricing_does_not_import_the_host_appraisal_or_corpus():
    reaching = [
        f'{name}: {module}'
        for path in sources('pricing')
        if (name := path.relative_to(ROOT).as_posix()) not in RENDERS_HOST_REPORTS
        for module in imported_modules(path)
        if module.startswith(HOST_ONLY)
    ]
    assert reaching == []


def test_every_api_name_is_its_home_modules_object():
    assert sorted(api.__all__) == sorted(api._EXPORTS)
    for name, (module, attribute) in api._EXPORTS.items():
        assert getattr(api, name) is getattr(import_module(module), attribute), name


def test_type_checking_imports_match_the_runtime_table():
    tree = ast.parse(Path(api.__file__).read_text())
    block = next(node for node in tree.body if isinstance(node, ast.If) and ast.unparse(node.test) == 'TYPE_CHECKING')
    typed = {
        alias.asname or alias.name: (node.module, alias.name)
        for node in block.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert typed == api._EXPORTS


def test_importing_the_api_loads_no_pricing_module():
    code = 'import sys, pricing.api; print(sorted(m for m in sys.modules if m.startswith("pricing.")))'
    loaded = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True, check=True)
    assert loaded.stdout.strip() == "['pricing.api']"
