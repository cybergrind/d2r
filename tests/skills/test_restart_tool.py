"""The restart tool (the d2-loop-watch skill's tools/restart.py): `--when town|safe` asks the service for a restart at
the loop's next safe point mid-game (macros/midgame.py, 2026-10-21) and follows its lines; the lobby default and the
loop-off restart are as before. A thread plays the service on a fake runs directory."""

import importlib
import json
import sys
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.agents' / 'skills' / 'd2-loop-watch' / 'tools'))
restart = importlib.import_module('restart')

ON = '2026-10-21 14:40:12,166 INFO Macro: Loop: game 1, TZ level\n'
HELD = '2026-10-21 14:41:00,000 INFO Macro: loop: a restart waits for a safe point (safe)\n'
NOT_YET = '2026-10-21 14:41:01,000 INFO Macro: loop: no safe point for the restart yet: a hostile 12 away\n'
SAFE = (
    '2026-10-21 14:41:09,000 INFO Macro: loop: safe point: River of Flame, cyber41 (player unit 7): the loop stands '
    'for the restart\n'
)
DROPPED = '2026-10-21 14:41:02,000 INFO Macro: loop: the restart no longer waits for a safe point\n'
RESUMED = '2026-10-21 14:41:15,000 INFO Macro: resumed after a restart: loop on, pickup good, run Shard: Act 4\n'


def session(runs: Path, name: str, *lines: str) -> Path:
    log = runs / name / 'probe.log'
    log.parent.mkdir(parents=True)
    log.write_text(''.join(lines))
    return log


def append(log: Path, line: str) -> None:
    with log.open('a') as handle:
        handle.write(line)


def service(runs: Path, log: Path, answer, seen: list) -> threading.Thread:
    """The service: takes the request when it comes (removed, its JSON kept in `seen`), then `answer(request)`."""

    def play() -> None:
        request = runs / restart.REQUEST_FILE
        deadline = time.time() + 10
        while not request.exists() and time.time() < deadline:
            time.sleep(0.02)
        text = request.read_text()
        request.unlink()
        seen.append(json.loads(text) if text else {})
        answer(seen[-1])

    worker = threading.Thread(target=play, daemon=True)
    worker.start()
    return worker


def test_a_safe_point_restart_is_asked_at_once_and_seen_through_to_the_new_service(tmp_path, capsys):
    log = session(tmp_path, '20261021T113933Z-a', ON)
    seen: list[dict] = []

    def answer(request: dict) -> None:
        for line in (HELD, NOT_YET, SAFE):
            append(log, line)
            time.sleep(0.05)
        session(tmp_path, '20261021T114110Z-b', RESUMED)

    worker = service(tmp_path, log, answer, seen)
    assert (
        restart.main(['--runs', str(tmp_path), '--when', 'safe', '--loop', 'on', '--kind', 'act3', '--wait', '20']) == 0
    )
    worker.join(5)
    assert seen == [{'loop': True, 'loop_pending': 'act3', 'when': 'safe'}]  # the game goes on as its own kind
    out = capsys.readouterr().out
    assert 'not yet: a hostile 12 away' in out
    assert 'at a safe point:' in out
    assert 'resumed after a restart: loop on' in out


def test_no_safe_point_within_the_wait_cancels_the_hold(tmp_path, capsys):
    log = session(tmp_path, '20261021T113933Z-a', ON)
    seen: list[dict] = []

    def answer(request: dict) -> None:
        append(log, HELD)
        cancel = service(tmp_path, log, lambda request: append(log, DROPPED), seen)
        cancel.join(10)

    worker = service(tmp_path, log, answer, seen)
    assert restart.main(['--runs', str(tmp_path), '--when', 'town', '--wait', '1']) == 1
    worker.join(10)
    assert seen == [{'when': 'town'}, {'when': 'cancel'}]
    assert 'nothing restarted' in capsys.readouterr().out


def test_with_the_loop_off_the_restart_is_at_once_whatever_when(tmp_path):
    log = session(tmp_path, '20261021T113933Z-a', ON, '2026-10-21 14:40:20,000 INFO Macro: Loop off\n')
    seen: list[dict] = []
    worker = service(tmp_path, log, lambda request: session(tmp_path, '20261021T114110Z-b', RESUMED), seen)
    assert restart.main(['--runs', str(tmp_path), '--when', 'safe', '--kind', 'act4']) == 0
    worker.join(5)
    assert seen == [{'loop_kind': 'act4'}]  # no hold: the lobby request as before


TRIP = (
    '2026-10-24 13:50:01,000 INFO Macro: loop: safe moment for the restart: Catacombs Level 3, cyber41 (player unit '
    '7): Town Portal to town for it, back through it after\n'
)
TOWN = (
    '2026-10-24 13:50:04,000 INFO Macro: loop: safe point: Rogue Encampment, cyber41 (player unit 7): the loop stands '
    'for the restart\n'
)


def test_a_trip_restart_is_followed_past_the_wait_once_the_portal_is_cast(tmp_path, capsys):
    # --when trip (macros/midgame.py TRIP, 2026-10-24): the portal begun just before --wait ends is no cancel
    log = session(tmp_path, '20261024T104000Z-a', ON)
    seen: list[dict] = []

    def answer(request: dict) -> None:
        append(log, HELD.replace('(safe)', '(trip)'))
        time.sleep(0.5)
        append(log, TRIP)
        time.sleep(1.5)  # past --wait 1
        append(log, TOWN)
        session(tmp_path, '20261024T105010Z-b', RESUMED)

    worker = service(tmp_path, log, answer, seen)
    assert restart.main(['--runs', str(tmp_path), '--when', 'trip', '--loop', 'keep', '--wait', '1']) == 0
    worker.join(5)
    assert seen == [{'when': 'trip'}]  # never a cancel
    out = capsys.readouterr().out
    assert 'portal trip for the restart from Catacombs Level 3' in out
    assert 'at a safe point:' in out
    assert 'resumed after a restart: loop on' in out
