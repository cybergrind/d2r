"""NO_DAMAGE (the d2-loop-watch skill's tools/anomalies.py) and its automatic RCA (tools/nodamage.py), 2026-10-24.

The player, 2026-10-24 ~20:35: "we need to have some king of debug message when we expect us to deliver damage but not
damaging the mob => and do automatic rca for such cases".

Synthetic takes: the character at (1000, 2000) striking unit 9; a blade cast (five blades, missile 706, in the frames'
`x`) every CAST s; the macro's `Strike` decision before each.
"""

import gzip
import importlib
import json
import struct
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / '.agents' / 'skills' / 'd2-loop-watch' / 'tools'
sys.path.insert(0, str(TOOLS))
anomalies = importlib.import_module('anomalies')
nodamage = importlib.import_module('nodamage')
watch = importlib.import_module('watch')

NO_OWNER = 4294967295
WALL = 1792605426.0  # the manifest's wall clock (2026-10-21 ~20:57 local)
FIELD = 123
RATE = 25.0
CAST = 0.36  # seconds between two chained Echoing Strike casts
NAME = '20261021T175706Z-123'
TOMB_DOOR_LEFT = 91  # objects.txt TombDoorLeft, 1 x 7 (levels/data/doors.json)


def path_hex(x: float, y: float) -> str:
    return struct.pack('<HHHH', int(x % 1 * 65536), int(x), int(y % 1 * 65536), int(y)).hex() + '00' * 40


def blade_take(
    base: Path,
    seconds: float = 4.0,
    target: tuple[float, float] = (1015.0, 2000.0),
    life: object = 128,
    blade_frames: int = 38,
    doors: list | None = None,
    hits: bool = False,
    flags: int | None = None,
) -> Path:
    """`seconds` of strikes at unit 9 at `target`; `life` its life of 128 (a callable of the frame index: falling);
    each blade lives `blade_frames`; `doors` the frames' `d`; `hits` a `hit` event a cast; `flags` its unit flags in
    records.jsonl."""
    frames, events, records = [], [], []
    n = int((seconds + 2.0) * RATE)
    blades: dict[int, int] = {}  # blade unit -> its birth frame
    next_cast, unit = 0.2, 1000
    for i in range(n):
        t = 100.0 + i / RATE
        if t - 100.0 >= next_cast and t - 100.0 <= seconds:
            events.append({'t': round(t - 0.05, 3), 'event': 'decision', 'chosen': 'Strike', 'target': 9})
            for _ in range(5):
                blades[unit] = i
                unit += 1
            if hits:
                events.append({'t': round(t + 0.3, 3), 'event': 'hit', 'unit': 9, 'txt': 673, 'life': [100, 99]})
            next_cast += CAST
        alive = [(b, i - born) for b, born in blades.items() if 0 <= i - born < blade_frames]
        x = [[b, 706, 3, 0, 0, path_hex(1000.8 + 1.12 * age, 2000.0)] for b, age in alive]
        now = life(i) if callable(life) else life
        frame = {'t': round(t, 3), 'n': i, 'game': True, 'panels': [],
                 'p': [1, 10, FIELD, 1000.0, 2000.0, 390, 388, 2907, 2907, 740, 740],
                 'm': [[9, 673, 1, *target, now, 128, 0, NO_OWNER, 0]], 'x': x, 'd': doors or [],
                 'in': [3767, 984, 4, 0.7215625, 0.694, []], 'rect': [1920, 0, 2560, 1418]}  # fmt: skip
        frames.append(frame)
        if flags is not None and i % 25 == 0:
            records.append({'t': round(t, 3), 'n': i, 'u': [[9, (b'\0' * 0x124 + struct.pack('<I', flags)).hex() +
                                                              '00' * 0x98, '00' * 32, '']]})  # fmt: skip
    events.append({'t': 100.1, 'event': 'log', 'text': 'Macro: Echoing Strike (right click) at the monster 673 (9), '
                   '128/128'})  # fmt: skip
    directory = base / NAME
    directory.mkdir(parents=True)
    manifest = {'area': FIELD, 'clock': {'monotonic': 100.0, 'wall': WALL}, 'started_at': '2026-10-21T17:57:06+00:00'}
    (directory / 'manifest.json').write_text(json.dumps(manifest))
    for file, rows in (('frames.jsonl.gz', frames), ('events.jsonl.gz', sorted(events, key=lambda e: e['t'])),
                       ('records.jsonl.gz', records)):  # fmt: skip
        with gzip.open(directory / file, 'wt') as handle:
            handle.writelines(json.dumps(row) + '\n' for row in rows)
    return directory


def detect(directory: Path, on: bool | None = True, **limits) -> list:
    found = anomalies.detect(directory, on=on, limits=anomalies.Limits(**limits), runs=directory.parent / 'no-runs')
    return [c for c in found if c.kind == 'NO_DAMAGE']


# --- The detector ---------------------------------------------------------------------------------------------------


def test_strikes_at_a_target_whose_life_stays_are_no_damage(tmp_path: Path) -> None:
    (case,) = detect(blade_take(tmp_path))
    assert case.data['unit'] == 9
    assert case.data['casts'] == 11
    assert case.data['counted'] == 'blade casts'
    assert case.data['life'] == [128, 128]
    assert case.data['dry'] is True
    line = case.line()
    assert line.startswith(f'ANOMALY: NO_DAMAGE {NAME} ')
    assert 'struck at the monster ' in line
    assert 'unit 9, 15.0 away (15-15), 11 blade casts, life 128->128/128, no hit on anything; cause?: ' in line


def test_a_target_losing_life_or_hit_is_no_case(tmp_path: Path) -> None:
    assert detect(blade_take(tmp_path / 'a', life=lambda i: max(128 - i // 10, 1))) == []
    assert detect(blade_take(tmp_path / 'b', hits=True)) == []


def test_a_short_stretch_is_no_case(tmp_path: Path) -> None:
    assert detect(blade_take(tmp_path / 'a', seconds=0.9)) == []  # 3 casts
    assert detect(blade_take(tmp_path / 'b', seconds=1.3)) == []  # 4 casts in 1.1 s
    assert [c.data['casts'] for c in detect(blade_take(tmp_path / 'c', seconds=1.3), dry_seconds=1.0)] == [4]


def test_no_case_with_the_loop_off(tmp_path: Path) -> None:
    assert detect(blade_take(tmp_path), on=False) == []


def test_the_casts_are_the_blades_births() -> None:
    frames = [{'t': 0.0, 'x': [[1, 706], [2, 706]]}, {'t': 0.04, 'x': [[1, 706], [3, 706]]},
              {'t': 0.4, 'x': [[4, 706], [9, 513]]}]  # fmt: skip
    take = anomalies.Take(Path('.'), {}, frames, [], 0.0)
    assert anomalies.blade_casts(take) == [0.0, 0.4]


# --- The RCA ---------------------------------------------------------------------------------------------------------


@pytest.fixture
def no_serve(monkeypatch):
    monkeypatch.setattr(anomalies, 'serve_of', lambda *_: None)


def rca(directory: Path, out: Path | None, **more) -> list:
    return nodamage.reports(directory, out=out, **more)


def test_a_closed_door_on_the_line_is_the_verdict(tmp_path: Path, no_serve) -> None:
    door = [[555, TOMB_DOOR_LEFT, 0, 1008.0, 2000.0]]
    (report,) = rca(blade_take(tmp_path, doors=door, blade_frames=8), tmp_path / 'rca')
    assert report.causes[0].name == 'door'
    assert report.top.startswith('door: a closed door on the line in ')
    assert any('verified by the blades' in e for e in report.causes[0].evidence)
    assert report.summary().startswith(f'NO_DAMAGE RCA: {NAME} 20:57:06 unit 9: door: ')
    written = tmp_path / 'rca' / '2026-10-21' / 'nodamage-205706-9.md'
    assert written.exists()
    assert '**Verdict: door: a closed door on the line' in written.read_text()


def test_an_open_door_is_no_cause(tmp_path: Path, no_serve) -> None:
    door = [[555, TOMB_DOOR_LEFT, 2, 1008.0, 2000.0]]
    (report,) = rca(blade_take(tmp_path, doors=door), None)
    cause = next(c for c in report.causes if c.name == 'door')
    assert cause.score == 0.0
    assert cause.verdict == 'only open doors'


def test_a_target_beyond_the_blades_is_out_of_reach(tmp_path: Path, no_serve) -> None:
    (report,) = rca(blade_take(tmp_path, target=(1030.0, 2000.0)), None)
    assert report.causes[0].name == 'range'
    assert report.causes[0].verdict == "out of the blades' reach"


def test_a_target_the_game_will_not_let_be_attacked(tmp_path: Path, no_serve) -> None:
    (report,) = rca(blade_take(tmp_path, flags=0x30000001), None)
    assert report.causes[0].name == 'untargetable'
    assert report.causes[0].score >= 0.9


def test_blades_through_it_with_nothing_else_is_unexplained(tmp_path: Path, no_serve) -> None:
    (report,) = rca(blade_take(tmp_path, flags=0x3000000F), None)
    assert report.top.startswith('unexplained (hint: blades: the blades went through it and took nothing')


def test_at_a_time_with_no_case_looks_at_the_slow_stretches(tmp_path: Path, no_serve) -> None:
    directory = blade_take(tmp_path, life=lambda i: max(128 - i // 20, 1))
    assert rca(directory, None, at='20:57:07', unit=9) == []
    (report,) = rca(directory, None, at='20:57:07')
    assert report.slow
    assert report.summary().startswith('slow stretch: ')


# --- The live watch ---------------------------------------------------------------------------------------------------


def test_the_watch_says_a_no_damage_case_and_runs_its_rca(tmp_path: Path, monkeypatch, capsys) -> None:
    directory = blade_take(tmp_path)
    monkeypatch.setattr(watch, 'COMBAT', tmp_path)
    monkeypatch.setattr(anomalies, 'serve_of', lambda *_: None)
    ran: list[list[str]] = []

    real = watch.nodamage_command

    def command(case) -> list[str]:
        ran.append(real(case))
        return [sys.executable, '-c', f'print("NO_DAMAGE RCA: {case.take} unit {case.data["unit"]}: door")']

    monkeypatch.setattr(watch, 'nodamage_command', command)
    seen = watch.Watch(1e9, 1e9)
    seen.full = set()
    seen.line('2026-10-21 20:57:06,409 INFO Macro: Loop on')
    seen.line(f'2026-10-21 20:57:06,500 INFO Combat take {directory.name} opened in area 123')
    seen.line(f"2026-10-21 20:57:20,000 INFO Combat take {directory.name} closed (changed level): {{'frames': 150}}")
    out = ''
    deadline = time.monotonic() + 20
    while 'NO_DAMAGE RCA:' not in out and time.monotonic() < deadline:
        time.sleep(0.05)
        seen.drain()
        out += capsys.readouterr().out
    assert f'ANOMALY: NO_DAMAGE {directory.name} ' in out
    assert f'NO_DAMAGE RCA: {directory.name} unit 9: door' in out
    (sent,) = ran
    assert sent[:4] == ['uv', 'run', '--offline', 'python']
    assert sent[4].endswith('nodamage.py')
    assert sent[5:] == [directory.name, '--at', '20:57:06', '--unit', '9']
