"""The elite kills an hour tool (the d2-loop-watch skill's tools/elites.py, macros/goals-plan.md §8): the kind's play
time, its kills once a unit, the phases, the stalls cut, and the comparison."""

import importlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.agents' / 'skills' / 'd2-loop-watch' / 'tools'))
elites = importlib.import_module('elites')


def line(at: str, text: str) -> str:
    return f'2026-10-19 {at},000 INFO {text}'


def utc(at: str) -> str:
    return datetime.strptime(f'2026-10-19 {at}', '%Y-%m-%d %H:%M:%S').astimezone().astimezone(UTC).isoformat()


def session(tmp_path: Path, name: str, lines: list[str], kills: list[tuple[str, int, str, int]]) -> Path:
    directory = tmp_path / name
    directory.mkdir(parents=True)
    log = directory / 'probe.log'
    log.write_text('\n'.join(lines) + '\n')
    written = datetime(2026, 10, 19, 10, 30).timestamp()
    os.utime(log, (written, written))  # the session is found by its log's last write (`sessions`)
    rows = [
        {'at': utc(at), 'event': 'elite_kill', 'unit_id': unit, 'kind': kind, 'area': area}
        for at, unit, kind, area in kills
    ]
    rows.append({'at': utc('10:00:01'), 'event': 'seen', 'unit_id': 1})
    (directory / 'terror-probe.jsonl').write_text('\n'.join(json.dumps(row) for row in rows) + '\n')
    return directory


GAME = [
    line('10:00:00', 'Macro: Loop run: TZ leveling'),
    line('10:00:00', 'Macro: Loop on'),
    line('10:00:00', 'Macro: Loop: game 1, TZ waypoint'),
    line('10:00:10', 'Macro: Loop: game 1, TZ level'),
    line('10:02:10', 'Macro: Loop: game 1, TZ next level'),
    line('10:02:20', 'Macro: Loop: game 1, TZ level'),
    line('10:04:20', 'Macro: Loop: game 1, TZ loot'),
    line('10:04:30', 'Macro: Loop: game 1, Save and Exit'),
    line('10:04:40', 'Macro: Loop: game 2, next game'),
    line('10:05:00', 'Macro: Loop off'),
]
KILLS = [
    ('10:01:00', 11, 'champion', 34),
    ('10:01:00', 11, 'champion', 34),  # the same unit said twice: once
    ('10:03:00', 12, 'unique', 37),
    ('10:03:30', 13, 'herald', 37),
    ('10:06:00', 14, 'champion', 34),  # with the loop off: not the kind's
]


def test_the_kinds_play_time_its_kills_once_a_unit_and_the_phases(tmp_path: Path) -> None:
    session(tmp_path, '20261019T070000Z-a', GAME, KILLS)
    window = elites.read(datetime(2026, 10, 19, 9, 0), datetime(2026, 10, 19, 11, 0), 'tz', tmp_path)
    result = elites.measure(window)

    assert result['hours'] == pytest.approx(300 / 3600)
    assert result['kills'] == 3
    assert result['per_hour'] == pytest.approx(36.0)
    assert result['by_kind'] == {'champion': 1, 'unique': 1, 'herald': 1}
    assert result['by_area'] == {37: 2, 34: 1}
    assert result['phases']['level']['seconds'] == pytest.approx(240.0)
    assert result['phases']['level']['kills'] == 3
    assert result['phases']['travel']['seconds'] == pytest.approx(20.0)
    assert result['phases']['lobby']['seconds'] == pytest.approx(30.0)  # Save and Exit, the next game
    assert result['off_kind'] == 1
    assert (
        elites.measure(elites.read(datetime(2026, 10, 19, 9), datetime(2026, 10, 19, 11), 'andariel', tmp_path))[
            'kills'
        ]
        == 0
    )  # another kind's window: none of these


def test_a_stall_the_player_sorted_out_is_no_play(tmp_path: Path) -> None:
    lines = [
        line('10:00:00', 'Macro: Loop run: TZ leveling'),
        line('10:00:00', 'Macro: Loop on'),
        line('10:00:00', 'Macro: Loop: game 1, TZ level'),
        line('10:10:00', 'Macro: Loop off'),  # 600 s with no leg: a stall, then the player's KP_6
    ]
    session(tmp_path, '20261019T070000Z-b', lines, [])
    window = elites.read(datetime(2026, 10, 19, 9), datetime(2026, 10, 19, 11), 'tz', tmp_path)
    assert elites.measure(window)['hours'] == 0.0


def test_the_kind_is_told_by_the_legs_and_the_name_said() -> None:
    assert elites.kind_of_leg('TZ level', None) == 'tz'
    assert elites.kind_of_leg('TZ level', 'tzclear') == 'tzclear'
    assert elites.kind_of_leg('down the Catacombs', 'tz') == 'andariel'
    assert elites.kind_of_leg('town visit', 'tz') is None
    assert elites.NAMES['TZ leveling'] == 'tz'
    assert elites.NAMES['Full clear TZ'] == 'tzclear'


def test_the_comparison_wants_games_and_says_its_interval() -> None:
    few = [{'game': 'a', 'seconds': 300.0, 'kills': 5}]
    assert 'too few games' in elites.shift(few, few)
    before = [{'game': str(n), 'seconds': 300.0, 'kills': 2 + n % 2} for n in range(20)]
    after = [{'game': str(n), 'seconds': 300.0, 'kills': 8 + n % 2} for n in range(20)]
    said = elites.shift(before, after)
    assert said.startswith('30.0 -> 102.0 elite kills an hour')
    assert said.endswith('better)')


def test_engaging_is_the_fights_seconds_and_the_rest_of_a_level_goes_by_its_target(tmp_path: Path) -> None:
    """The player, 2026-10-19: "track: time what we're spending engaging vs other activities (traveling, town,
    creating game)"."""
    lines = [
        line('10:00:00', 'Macro: Loop run: TZ leveling'),
        line('10:00:00', 'Macro: Loop on'),
        line('10:00:00', 'Macro: Loop: game 1, TZ waypoint'),
        line('10:00:10', 'Macro: Loop: game 1, TZ level'),
        line('10:00:12', 'Macro: agenda: target an unexplored room 3 (explore, tier 8, 0 leaders known here)'),
        line('10:00:30', 'Macro: agenda: target the elite 8 (93694182) (kill, tier 4, 1 leaders known here)'),
        line('10:00:50', 'Macro: fight (right click): 4 casts seen in 6.0s, 5 down; Nothing left'),
        line('10:00:50', 'Macro: agenda: target Amulet, on the way (pickup, tier 3, 0 leaders known here)'),
        line('10:00:55', 'Macro: Loop: game 1, TZ loot'),
        line('10:01:00', 'Macro: Loop: game 1, town visit'),
        line('10:01:20', 'Macro: Loop: game 1, Save and Exit'),
        line('10:01:22', 'Macro: Loop: game 2, next game'),
        line('10:01:40', 'Macro: Loop off'),
    ]
    session(tmp_path, '20261019T070000Z-c', lines, [])
    doing = elites.measure(elites.read(datetime(2026, 10, 19, 9), datetime(2026, 10, 19, 11), 'tz', tmp_path))[
        'activities'
    ]
    assert doing['level other'] == pytest.approx(2.0)
    assert doing['explore'] == pytest.approx(18.0)
    assert doing['approach'] == pytest.approx(14.0)  # 20 s toward the elite, 6 of them the fight
    assert doing['engaging'] == pytest.approx(6.0)
    assert doing['pickup'] == pytest.approx(10.0)  # the pickup target, then the loot leg
    assert doing['travel'] == pytest.approx(10.0)
    assert doing['town'] == pytest.approx(20.0)
    assert doing['lobby'] == pytest.approx(20.0)


def test_the_baal_kind_is_told_by_its_legs_and_its_name() -> None:
    assert elites.kind_of_leg("the Throne's waves", None) == 'baal'
    assert elites.kind_of_leg('a Northern shard for act 5', 'tz') == 'baal'
    assert elites.NAMES['Baal'] == 'baal'
    assert elites.PHASE_OF['to the Worldstone Keep'] == elites.TRAVEL
    assert elites.PHASE_OF['Baal'] == elites.LEVEL
