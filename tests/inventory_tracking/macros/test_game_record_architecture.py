"""The game's one record (macros/midgame.py RECORD, terror/tracker.py RECORD_SECONDS; 2026-10-22,
rca/2026-10-22/restart-zone-findings.md; the player: "no copies, no stale records"): a game's state that must survive
a service restart is in its record only, written by its owners and read back from it. No restart blob of the game,
no file of the zone's facts of its own, no carried copy on the loop."""

import ast
import functools
import os
import re
import threading
from pathlib import Path

from inventory_tracking.macros.loop import Loop
from inventory_tracking.macros.runner import MacroRunner


ROOT = Path(__file__).resolve().parents[3] / 'inventory_tracking'
SERVICE_SETTINGS = {'loop', 'pickup_mode', 'loop_kind', 'loop_pending', 'gheeds'}


@functools.cache
def sources() -> dict[str, str]:
    """The package's modules by path; the runs' directories (the sessions' logs, large) not walked."""
    found = {}
    for top, dirs, files in os.walk(ROOT):
        dirs[:] = [name for name in dirs if name not in ('runs', '__pycache__')]
        for name in files:
            if name.endswith('.py'):
                path = Path(top) / name
                found[path.relative_to(ROOT).as_posix()] = path.read_text(encoding='utf-8')
    return found


def calls(source: str, name: str) -> int:
    """The calls of attribute `name` in `source`."""
    return sum(
        1
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == name
    )


def test_the_restart_blob_holds_the_services_settings_only():
    runner = MacroRunner(None, capture_lock=threading.Lock(), saved_games=Path('/nonexistent'))
    try:
        assert set(runner.resume_state()) == SERVICE_SETTINGS
    finally:
        runner.close()


def test_only_the_records_owners_write_it():
    writers = sorted(path for path, source in sources().items() if calls(source, 'record_note'))
    assert writers == ['macros/midgame.py', 'macros/sightings.py']


def test_the_agendas_and_the_sightings_state_go_to_the_record_only():
    # `Agenda.state` is the record's through midgame.py `snapshot`; `Sightings.state` through its own `keep`
    found = sorted(
        path for path, source in sources().items() if re.search(r'\bagenda\.state\(\)|\bsightings\.state\(\)', source)
    )
    assert found == ['macros/midgame.py']


def test_no_second_copy_of_the_games_state():
    assert 'carried' not in vars(Loop())  # the old blob's game, taken up at the first leg
    copies = re.compile(r"^ZONE_FILE = |^def zone_(keep|resume|store)\(|zone-facts\.json'", re.MULTILINE)
    for path, source in sources().items():
        assert not copies.search(source), path
        assert 'RESTORE_LEVEL' not in source, path  # the sightings' level is the record's, no switch of its own
