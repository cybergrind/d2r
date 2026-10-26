"""The anomalies of a combat take (the d2-loop-watch skill's tools/anomalies.py, 2026-10-21): the character idle, a
long fight with one target, jumps that go nowhere; their log words; the live watch saying them when a take closes.

The player, 2026-10-21 ~21:08: "monitor all time that we weren't moving/killing/doing something - all the cases where
we were engaging with mob for a more than 30 seconds - all cases where we have jumped a lot in short period of time
staying withing small area".
"""

import gzip
import importlib
import json
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / '.agents' / 'skills' / 'd2-loop-watch' / 'tools'
PRODUCTION = ROOT / 'inventory_tracking'
sys.path.insert(0, str(TOOLS))
anomalies = importlib.import_module('anomalies')
logwords = importlib.import_module('logwords')
watch = importlib.import_module('watch')

NO_OWNER = 4294967295
WALL = 1792605426.0  # 2026-10-21 ~20:57 local: the manifest's clock
FIELD = 123  # Halls of Pain
RATE = 25.0


# --- The log words (real lines, runs/alt-d/*/probe.log 2026-10-21) --------------------------------------------------

REAL = [
    (
        'TAKE_CLOSED',
        "2026-10-21 14:25:32,336 INFO Combat take 20261021T112517Z-75 closed (changed level): {'frames': 365}",
        ('20261021T112517Z-75', 'changed level'),
    ),
    (
        'HERALD_WAIT',
        '2026-10-21 18:38:18,443 INFO Macro: run: a Herald comes at (7649.5, 5088.5) in 5 s: the run waits for it '
        'there',
        ('5',),
    ),
    (
        'STRIKE',
        '2026-10-21 18:27:48,375 INFO Macro: Echoing Strike (right click) at the monster 142 (1181201124), 126/128',
        ('monster', '142', '1181201124', '126'),
    ),
    (
        'STRIKE',
        '2026-10-21 18:27:57,919 INFO Macro: Echoing Strike (right click) at the elite 99 (730608447), 23/128',
        ('elite', '99', '730608447', '23'),
    ),
    (
        'STRIKE',
        '2026-10-21 20:57:10,800 INFO Macro: line through the monster 673 (719323509), 27/128, 19.4 away, focal '
        '(10126.9, 14907.6), worth 1296, pointer (2721, 1068)',
        ('monster', '673', '719323509', '27'),
    ),
    (
        'ELITE_TARGET',
        '2026-10-21 18:37:44,446 INFO Macro: agenda: target the elite 142 (3577680779) (kill, tier 4, 1 leaders known '
        'here)',
        ('142', '3577680779', '4'),
    ),
    ('JUMP_CAST', '2026-10-21 19:35:02,297 INFO Macro: Blade Warp on s, player mode 1', ('Blade Warp',)),
    ('JUMP_CAST', '2026-10-21 20:57:07,300 INFO Macro: Teleport on t, player mode 1', ('Teleport',)),
    (
        'JUMP_REASON',
        '2026-10-21 20:57:12,300 INFO Macro: Teleport toward full clear: a group of 13: 19 left after this',
        ('full clear: a group of 13', None, None, None, None),
    ),
    (
        'JUMP_REASON',
        '2026-10-21 20:57:13,400 INFO Macro: run: a better place in the fight with 1 of 62 hostiles in reach, from '
        '(10106.5, 14882.5): a place at (10091.5, 14879.5), a jump by Teleport of 15 (0.3s)',
        (None, 'a better place', None, None, None),
    ),
    (
        'JUMP_REASON',
        '2026-10-21 18:30:24,893 INFO Macro: Pack: keeping range: mana burn: 2 of the pack on the character within 18 '
        '(the nearest at 17.0)',
        (None, None, 'keeping range', 'mana burn', None),
    ),
    (
        'JUMP_REASON',
        '2026-10-25 21:32:00,557 INFO Macro: Mana: leaving: mana 258 of 745, burnt 489 0.5 s ago, 2 drainers in reach',
        (None, None, None, None, 'leaving'),
    ),
]


@pytest.mark.parametrize(('name', 'line', 'groups'), REAL, ids=[f'{n}-{i}' for i, (n, _, _) in enumerate(REAL)])
def test_a_real_line_yields_its_groups(name: str, line: str, groups: tuple) -> None:
    found = getattr(logwords, name).search(line)
    assert found is not None
    assert found.groups() == groups


@pytest.mark.parametrize(
    'line',
    [
        '2026-10-21 20:43:04,316 INFO Macro: run: Throne of Destruction: the hall is clear: waiting for the waves at '
        'the Throne',
        '2026-10-21 18:49:32,842 INFO Macro: At Lister the Tormentor: the stand for the waves',
    ],
)
def test_the_thrones_wave_wait_reads(line: str) -> None:
    assert logwords.WAVES.search(line)


def test_the_census_gold_and_the_keys_name_no_cause() -> None:
    noise = [
        'Macro: ground: magic Ring at (10091, 14891): taken (material)',
        'Macro: gold pile 592390601: 1374 gold (the full stat list)',
        'Macro: Teleport on t, player mode 1',
        'Macro: line through the monster 673 (719323509), 27/128, 19.4 away',
    ]
    assert all(logwords.NOISE.search(text) for text in noise)
    assert not logwords.NOISE.search('Macro: idle: 40 hostiles, none in reach; nearest the monster 673 (1) 25 away')
    assert (
        anomalies.kind_of('Macro: idle: 40 hostiles, none in reach; nearest ...') == 'idle: N hostiles, none in reach'
    )
    assert anomalies.kind_of(
        'Macro: pursuit: the inventory has no room for Ring at (10091, 14891), 12 away: the run stands by it'
    ) == ('the inventory has no room for Ring, N away: the run stands by it')


@pytest.mark.parametrize(
    ('path', 'anchor'),
    [
        ('takes/record.py', 'Combat take %s closed (%s)'),
        ('macros/hunt.py', 'a Herald comes at'),
        ('macros/hunting/throne.py', 'waiting for the waves at the Throne'),
        ('macros/routines.py', '%s on %s, player mode %s'),
    ],
)
def test_the_production_code_says_the_line(path: str, anchor: str) -> None:
    assert anchor in (PRODUCTION / path).read_text(), f'{path} no longer says {anchor!r}: change logwords.py with it'


# --- A synthetic take ------------------------------------------------------------------------------------------------


def hostile(unit: int, x: float, y: float, life: int = 128, mode: int = 1, cls: int = 673) -> list:
    return [unit, cls, mode, x, y, life, 128, 0, NO_OWNER, 0]


def frame(t: float, x: float, y: float, monsters: list, area: int = FIELD, mode: int = 1, **more) -> dict:
    return {'t': round(t, 3), 'game': True, 'panels': [], 'p': [1, mode, area, x, y, 390, 388, 2907, 2907, 740, 740],
            'm': monsters, **more}  # fmt: skip


def write_take(base: Path, frames: list[dict], events: list[dict], area: int = FIELD, name: str = '') -> Path:
    directory = base / (name or f'20261021T175706Z-{area}')
    directory.mkdir(parents=True)
    first = frames[0]['t']
    manifest = {'area': area, 'clock': {'monotonic': first, 'wall': WALL}, 'started_at': '2026-10-21T17:57:06+00:00'}
    (directory / 'manifest.json').write_text(json.dumps(manifest))
    for file, rows in (('frames.jsonl.gz', frames), ('events.jsonl.gz', events)):
        with gzip.open(directory / file, 'wt') as handle:
            handle.writelines(json.dumps(row) + '\n' for row in rows)
    return directory


def still_take(base: Path, still: float = 10.0, area: int = FIELD, **more) -> Path:
    """2 s walking, then `still` s at one spot with a hostile 20 away; an `idle:` line said in it."""
    frames = []
    t = 100.0
    for i in range(int(2 * RATE)):
        frames.append(frame(t, 1000 + i * 0.3, 2000, [hostile(7, 1035, 2000)], area=area, **more))
        t += 1 / RATE
    for _ in range(int(still * RATE)):
        frames.append(frame(t, 1015, 2000, [hostile(7, 1035, 2000)], area=area, **more))
        t += 1 / RATE
    events = [{'t': 103.0, 'event': 'log', 'text': 'Macro: idle: 1 hostiles, none in reach; nearest the monster 673'}]
    return write_take(base, frames, events, area=area)


def detect(directory: Path, on: bool | None = True, **limits) -> list:
    return anomalies.detect(directory, on=on, limits=anomalies.Limits(**limits), runs=directory.parent / 'no-runs')


def test_a_still_with_a_hostile_near_is_an_idle(tmp_path: Path) -> None:
    (case,) = detect(still_take(tmp_path))
    assert case.kind == 'IDLE'
    assert 9.5 <= case.seconds <= 10.2
    assert case.data['within'] == 1
    assert case.cause == ['idle: N hostiles, none in reach x1']
    assert case.line().startswith('ANOMALY: IDLE 20261021T175706Z-123 ')
    assert 'cause?: idle: N hostiles, none in reach x1' in case.line()


def test_one_strike_between_two_stills_at_one_spot_is_one_idle(tmp_path: Path) -> None:
    """A strike at a corpse (0/128) split a 170 s stand in four (20261021T162429Z-114 19:25:54): pieces at one spot
    MERGE_GAP s apart are one case."""
    take = with_line(
        still_take(tmp_path, still=12.0), 107.0, 'Macro: Echoing Strike (right click) at the monster 673 (7), 0/128'
    )
    (case,) = detect(take)
    assert case.data['pieces'] == 2
    assert 'in 2 pieces' in case.facts


def test_a_short_still_is_no_idle(tmp_path: Path) -> None:
    assert detect(still_take(tmp_path, still=6.0)) == []


@pytest.mark.parametrize(('more', 'area'), [({}, 109), ({'panels': ['inventory']}, FIELD), ({'game': False}, FIELD)])
def test_no_idle_in_town_with_a_panel_or_out_of_the_game(tmp_path: Path, more: dict, area: int) -> None:
    assert detect(still_take(tmp_path, area=area, **more)) == []


def test_no_idle_with_the_loop_off(tmp_path: Path) -> None:
    assert detect(still_take(tmp_path), on=False) == []


def with_line(directory: Path, t: float, text: str) -> Path:
    path = directory / 'events.jsonl.gz'
    with gzip.open(path, 'rt') as handle:
        events = [json.loads(line) for line in handle]
    events.append({'t': t, 'event': 'log', 'text': text})
    with gzip.open(path, 'wt') as handle:
        handle.writelines(json.dumps(e) + '\n' for e in sorted(events, key=lambda e: e['t']))
    return directory


def test_the_thrones_wave_wait_is_no_idle(tmp_path: Path) -> None:
    take = with_line(still_take(tmp_path, area=131), 101.0, 'Macro: run: Throne of Destruction: the hall is clear: '
                     'waiting for the waves at the Throne')  # fmt: skip
    assert detect(take) == []


def test_a_heralds_wait_is_no_idle_until_its_pack_is_near(tmp_path: Path) -> None:
    line = 'Macro: run: a Herald comes at (1015.5, 2000.5) in 20 s: the run waits for it there'
    far = tmp_path / 'far'
    frames = [frame(100 + i / RATE, 1015, 2000, [hostile(7, 1095, 2000)]) for i in range(int(12 * RATE))]
    assert detect(with_line(write_take(far, frames, []), 100.5, line)) == []
    near = tmp_path / 'near'  # the pack is there and no strike comes: a fight not made (20261021T175851Z-123)
    frames = [frame(100 + i / RATE, 1015, 2000, [hostile(7, 1025, 2000)]) for i in range(int(12 * RATE))]
    (case,) = detect(with_line(write_take(near, frames, []), 100.5, line))
    assert case.kind == 'IDLE'


def test_a_strike_or_a_hostile_hurt_breaks_a_still(tmp_path: Path) -> None:
    struck = still_take(tmp_path / 'a')
    for t in range(103, 112, 2):  # a strike every 2 s: no piece of PIECE s
        struck = with_line(struck, t + 0.5, 'Macro: Echoing Strike (right click) at the monster 673 (7), 128/128')
    assert detect(struck) == []
    frames = [frame(100 + i / RATE, 1015, 2000, [hostile(7, 1035, 2000, life=128 - i // 25)]) for i in range(250)]
    assert detect(write_take(tmp_path / 'b', frames, [])) == []
    flicker = [frame(100 + i / RATE, 1015, 2000, [hostile(7, 1035, 2000, life=128 - i % 2)]) for i in range(250)]
    assert [c.kind for c in detect(write_take(tmp_path / 'c', flicker, []))] == ['IDLE']  # 127/128 is regeneration


def fight_take(base: Path, seconds: float, dies: bool = True) -> Path:
    """A strike at unit 9 each second for `seconds`; it dies after the last when `dies`."""
    n = int(seconds * RATE) + 25
    frames = [frame(100 + i / RATE, 1000 + (i % 50) * 0.2, 2000, [hostile(9, 1010, 2000, life=max(128 - i // 10, 1))])
              for i in range(n)]  # fmt: skip
    events = [{'t': 100.0 + s, 'event': 'log', 'text': f'Macro: Echoing Strike (right click) at the monster 673 (9), '
               f'{128 - s}/128'} for s in range(int(seconds) + 1)]  # fmt: skip
    events += [{'t': 100.0 + s + 0.1, 'event': 'cast', 'mode': 10, 'macro': True} for s in range(int(seconds) + 1)]
    if dies:
        events.append({'t': 100.0 + seconds + 0.5, 'event': 'kill', 'unit': 9, 'txt': 673, 'macro': True})
    return write_take(base, frames, sorted(events, key=lambda e: e['t']))


def test_a_fight_with_one_target_over_30_s_is_a_long_fight(tmp_path: Path) -> None:
    (case,) = [c for c in detect(fight_take(tmp_path, 35)) if c.kind == 'LONG_FIGHT']
    assert 35 <= case.seconds <= 36
    assert case.data['unit'] == 9
    assert case.data['end'] == 'dead'
    assert 'Heirophant (cantor5, 673)' in case.facts or 'class 673' in case.facts  # monstats.txt is git-ignored


def test_a_fight_under_30_s_is_none(tmp_path: Path) -> None:
    assert [c for c in detect(fight_take(tmp_path, 25)) if c.kind == 'LONG_FIGHT'] == []


def jump_take(base: Path, spots: list[tuple[float, float]], kills: int = 0) -> Path:
    """A jump to each spot every 1.2 s (the frames between stand on it)."""
    frames, t = [], 100.0
    for x, y in spots:
        for _ in range(30):
            frames.append(frame(t, x, y, [hostile(7, 1050, 2000)]))
            t += 1 / RATE
    events = [{'t': 100.5 + 1.5 * k, 'event': 'kill', 'unit': 100 + k, 'txt': 673, 'macro': True} for k in range(kills)]
    events += [{'t': 100.0 + 1.2 * i, 'event': 'log', 'text': 'Macro: Teleport toward full clear: the elite 216 '
                '(510263862): 0 left after this'} for i in range(len(spots))]  # fmt: skip
    return write_take(base, frames, sorted(events, key=lambda e: e['t']))


BACK_AND_FORTH = [(1000.0, 2000.0), (1012.0, 2000.0)] * 5


def test_jumps_back_and_forth_in_a_small_area_are_a_cluster(tmp_path: Path) -> None:
    (case,) = [c for c in detect(jump_take(tmp_path, BACK_AND_FORTH)) if c.kind == 'JUMP_CLUSTER']
    assert case.data['jumps'] == 9
    assert case.data['radius'] <= 7
    assert case.cause == ['toward full clear: the elite N (N) x9']
    assert 'reasons: toward full clear' in case.line()


# The 23:23:57 hops of take 20261025T202255Z-71 and the 21:32:00 leave of 20261025T182826Z-74 as probe.log says them
# (the clock in seconds of the minute): each hop says its reason and, ms later, `Teleport toward` the goal
HOP_A = 'Macro: Teleport toward full clear: the elite 41 (3846488025): clearing the way (14 near): 0 left after this'
HOP_B = 'Macro: Teleport toward full clear: the elite 40 (2260900621): clearing the way (8 near): 0 left after this'
TWIN_LINES = [
    (57.092, 'Macro: Pack: keeping range: extra fast: surrounded: 13 of the pack within 5'),
    (57.096, 'Macro: pursuit: Teleport toward full clear: the elite 41 (3846488025): clearing the way (14 near) at '
     '(22669.8, 12593.7), 24 away from (22647.5, 12602.5): to (22669.8, 12593.7) within pressed goal'),
    (57.100, HOP_A),
    (57.191, 'Macro: Pack: keeping range: extra fast: 14 of the pack on the character within 18 (the nearest at 13.2)'),
    (57.198, HOP_A.replace('14 near', '15 near')),
    (57.209, 'Macro: Teleport on t, player mode 1'),
    (60.557, 'Macro: Mana: leaving: mana 258 of 745, burnt 489 0.5 s ago, 2 drainers in reach'),
    (60.573, HOP_B),
    (62.000, HOP_B),
]  # fmt: skip


def test_one_hop_gives_one_reason_and_the_mana_leave_counts() -> None:
    found = anomalies.reasons(TWIN_LINES, 0.0, 100.0)
    assert sorted(found) == [
        'keeping range: extra fast x2',
        'mana: leaving x1',
        'toward full clear: the elite N (N): clearing the way (N near) x1',  # 62.000: a jump of its own
    ]


def test_jumps_that_kill_or_go_somewhere_are_none(tmp_path: Path) -> None:
    killing = detect(jump_take(tmp_path / 'a', BACK_AND_FORTH, kills=8))  # a kill each 1.5 s
    onward = detect(jump_take(tmp_path / 'b', [(1000.0 + 20 * i, 2000.0) for i in range(10)]))
    assert [c for c in killing + onward if c.kind == 'JUMP_CLUSTER'] == []


def test_a_torn_take_reads_as_far_as_it_got(tmp_path: Path) -> None:
    directory = still_take(tmp_path)
    data = (directory / 'frames.jsonl.gz').read_bytes()
    (directory / 'frames.jsonl.gz').write_bytes(data[: len(data) * 2 // 3])
    assert anomalies.Take.load(directory).frames  # an open take's gzip ends mid-stream


# --- The command and the live watch ----------------------------------------------------------------------------------


def test_the_command_prints_one_line_a_case_and_json(tmp_path: Path, monkeypatch, capsys) -> None:
    directory = still_take(tmp_path)
    monkeypatch.setattr(anomalies, 'serve_of', lambda *_: None)
    monkeypatch.setattr(sys, 'argv', ['anomalies.py', str(directory)])
    anomalies.main()
    (line,) = capsys.readouterr().out.splitlines()
    assert line.startswith('ANOMALY: IDLE ')
    monkeypatch.setattr(sys, 'argv', ['anomalies.py', str(directory), '--json'])
    anomalies.main()
    (found,) = json.loads(capsys.readouterr().out)
    assert found['kind'] == 'IDLE'
    assert found['seconds'] >= 9.5


def test_the_watch_says_a_closed_takes_anomalies(tmp_path: Path, monkeypatch, capsys) -> None:
    directory = still_take(tmp_path)
    monkeypatch.setattr(watch, 'COMBAT', tmp_path)
    monkeypatch.setattr(anomalies, 'serve_of', lambda *_: None)
    seen = watch.Watch(1e9, 1e9)
    seen.full = set()
    seen.line('2026-10-21 20:57:06,409 INFO Macro: Loop on')
    seen.line(f'2026-10-21 20:57:06,500 INFO Combat take {directory.name} opened in area 123')
    seen.line(f"2026-10-21 20:57:20,000 INFO Combat take {directory.name} closed (changed level): {{'frames': 300}}")
    deadline = time.monotonic() + 10
    while seen.found.empty() and time.monotonic() < deadline:
        time.sleep(0.05)
    seen.drain()
    out = capsys.readouterr().out
    assert f'ANOMALY: IDLE {directory.name} ' in out


def test_a_quiet_read_runs_no_detector(tmp_path: Path) -> None:
    seen = watch.Watch(1e9, 1e9)
    seen.loud = False
    seen.line("2026-10-21 20:57:20,000 INFO Combat take 20261021T175706Z-123 closed (changed level): {'frames': 3}")
    assert seen.worker is None
    assert seen.closed.empty()


# --- Real takes of 2026-10-21 (skipped where the runs are not kept) -------------------------------------------------


@pytest.mark.parametrize(
    ('take', 'after', 'least'),
    [
        ('20261021T175706Z-123', (20.0, 30.0), 40.0),  # stands by a Grand Charm with no room, 40 hostiles near
        ('20261021T175851Z-123', (10.0, 14.0), 8.0),  # the Herald's pack within 11 and no strike: Defilers summoned
    ],
)
def test_a_known_still_of_a_real_take_is_found(take: str, after: tuple[float, float], least: float) -> None:
    directory = anomalies.COMBAT / take
    if not (directory / 'frames.jsonl.gz').exists():
        pytest.skip(f'{take} is not kept here')
    idle = [c for c in anomalies.detect(directory) if c.kind == 'IDLE']
    assert any(after[0] <= c.data['at'] <= after[1] and c.seconds >= least for c in idle), [c.line() for c in idle]
