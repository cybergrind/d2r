"""The experience an hour tool (the d2-loop-watch skill's tools/exphour.py, rca/2026-10-25/exp-hour-findings.md): exp
an hour of play and of wall clock, each level's exp a second with the travel before it, the shard and natural acts,
the time out of play with what the log said, and the comparison."""

import gzip
import importlib
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.agents' / 'skills' / 'd2-loop-watch' / 'tools'))
exphour = importlib.import_module('exphour')


def line(at: str, text: str) -> str:
    return f'2026-10-19 {at},000 INFO {text}'


def session(tmp_path: Path, name: str, lines: list[str]) -> Path:
    directory = tmp_path / name
    directory.mkdir(parents=True)
    log = directory / 'probe.log'
    log.write_text('\n'.join(lines) + '\n')
    written = datetime(2026, 10, 19, 10, 30).timestamp()
    os.utime(log, (written, written))  # the session is found by its log's last write (`sessions`)
    return directory


GAME = [
    line('10:00:00', 'Macro: Loop run: TZ leveling'),
    line('10:00:00', 'Macro: Loop on'),
    line('10:00:00', 'Macro: Loop: game 1, TZ waypoint'),
    line('10:00:01', 'Macro: tz: zone Act2-Sewers: Sewers 1 from 48: [48, 47]; skipped none'),
    line(
        '10:00:02',
        'Macro: tz: zone Act3-Manual + Act2-Sewers: Mephisto from 101: [101, 102]; Sewers 1 from 48: [48, 47]; skipped '
        'none',
    ),
    line('10:00:10', 'Macro: Loop: game 1, TZ level'),
    line('10:02:10', 'Macro: experience: Sewers Level 1: +240,000 in 120s (level 96)'),
    line('10:02:10', 'Macro: Loop: game 1, TZ waypoint'),
    line('10:02:30', 'Macro: Loop: game 1, TZ level'),
    line('10:04:30', 'Macro: experience: Durance of Hate Level 1: +480,000 in 120s (level 96)'),
    line('10:04:30', 'Macro: Loop: game 1, Save and Exit'),
    line('10:04:40', 'Macro: Loop: game 2, next game'),
    line('10:05:00', 'Macro: loop stopped: inventory full: no room for Unique Ballista'),
    line('10:10:00', 'Macro: resumed after a restart: loop on, pickup good, run TZ leveling'),
    line('10:10:00', 'Macro: Loop resumed after a restart'),
    line('10:10:00', 'Macro: Loop: game 2, TZ level'),
    line('10:12:00', 'Macro: experience: Sewers Level 1: +120,000 in 120s (level 96)'),
    line('10:12:00', 'Macro: Loop: game 2, Save and Exit'),
    line('10:12:10', 'Macro: Loop off'),
    line('10:20:00', 'Macro: experience: Sewers Level 2: +50,000 in 30s (level 96)'),  # the loop off: not counted
]
SINCE, UNTIL = datetime(2026, 10, 19, 9, 0), datetime(2026, 10, 19, 11, 0)


def test_exp_an_hour_of_play_and_of_wall_clock(tmp_path: Path) -> None:
    session(tmp_path, '20261019T070000Z-a', GAME)
    result = exphour.measure(exphour.read(SINCE, UNTIL, 'tz', tmp_path))

    assert result['play_seconds'] == pytest.approx(430.0)  # 10:00-10:05 and 10:10-10:12:10
    assert result['wall_seconds'] == pytest.approx(730.0)  # 10:00 to 10:12:10, the stop's gap in it
    assert result['exp'] == 840_000
    assert result['per_play_hour'] == pytest.approx(3600 * 840_000 / 430)
    assert result['per_wall_hour'] == pytest.approx(3600 * 840_000 / 730)
    assert result['outside'] == {'stays': 1, 'exp': 50_000}
    assert sorted((g['seconds'], g['exp']) for g in result['games']) == [(150.0, 120_000), (280.0, 720_000)]


def test_each_level_gets_the_travel_before_it_and_its_class(tmp_path: Path) -> None:
    session(tmp_path, '20261019T070000Z-a', GAME)
    result = exphour.measure(exphour.read(SINCE, UNTIL, 'tz', tmp_path))

    durance, sewers = result['levels']
    assert (durance['level'], durance['act'], durance['on'], durance['travel']) == ('Durance of Hate Level 1', 3, 120,
                                                                                   20.0)  # fmt: skip
    assert durance['a_second'] == pytest.approx(480_000 / 140)
    assert (sewers['level'], sewers['act'], sewers['stays'], sewers['travel']) == ('Sewers Level 1', 2, 2, 0.0)
    assert sewers['a_second'] == pytest.approx(360_000 / 240)
    assert result['travel_seconds'] == pytest.approx(20.0)
    # Durance of Hate is act 3, terrorized by a shard; the Sewers are the game's own zone
    assert result['classes']['shard']['a_second'] == pytest.approx(480_000 / 140)
    assert result['classes']['natural act 2']['a_second'] == pytest.approx(360_000 / 240)


def test_the_time_sinks_and_the_time_out_of_play(tmp_path: Path) -> None:
    session(tmp_path, '20261019T070000Z-a', GAME)
    result = exphour.measure(exphour.read(SINCE, UNTIL, 'tz', tmp_path))

    doing = result['activities']
    assert doing['level other'] == pytest.approx(360.0)
    assert doing['travel'] == pytest.approx(30.0)
    assert doing['lobby'] == pytest.approx(40.0)
    (gap,) = result['gaps']
    assert gap['seconds'] == pytest.approx(300.0)
    assert gap['said'] == ['loop stopped: inventory full: no room for Unique Ballista', 'restart (loop on)']


def test_the_report_prints_the_rates_levels_and_gaps(tmp_path: Path, capsys) -> None:
    session(tmp_path, '20261019T070000Z-a', GAME)
    exphour.report(exphour.measure(exphour.read(SINCE, UNTIL, 'tz', tmp_path)), 3)
    out = capsys.readouterr().out
    assert 'tz: 840,000 exp in 0.12 h of play = 7.03 M an hour' in out
    assert '4.14 M a wall hour' in out
    assert 'Durance of Hate Level 1' in out
    assert 'loop stopped: inventory full' in out


def test_the_comparison_resamples_games() -> None:
    before = [{'game': f'a/{n}', 'seconds': 600.0, 'exp': 1_000_000 + 10_000 * n} for n in range(10)]
    after = [{'game': f'b/{n}', 'seconds': 600.0, 'exp': 1_500_000 + 10_000 * n} for n in range(10)]
    assert exphour.rate(before) == pytest.approx(3600 * sum(g['exp'] for g in before) / 6000)
    assert exphour.shift(before, after).endswith(': better)')
    assert exphour.shift(after, before).endswith(': worse)')
    assert exphour.shift(before[:3], after) == 'too few games (3 / 10) for a comparison'


def test_a_level_line_names_its_area_and_act() -> None:
    assert exphour.AREAS["Tal Rasha's Tomb 4"] == 69
    assert exphour.act_of(exphour.AREAS['Halls of Pain']) == 5
    assert exphour.act_of(exphour.AREAS['The Chaos Sanctuary']) == 4
    assert exphour.act_of(exphour.AREAS['Durance of Hate Level 1']) == 3


def test_the_weak_levels_are_slow_with_their_travel_and_on_the_level_itself() -> None:
    def row(level: str, a_second: float, on_level: float, on: int = 300, stays: int = 4) -> dict:
        return {
            'level': level,
            'a_second': a_second,
            'on_level': on_level,
            'on': on,
            'stays': stays,
            'exp': 1,
            'travel': 0.0,
        }

    result = {
        'exp': 2_000 * 1000,
        'play_seconds': 1000.0,  # an average of 2,000 a second
        'levels': [
            row('Plains of Despair', 949.0, 1223.0),
            row('Palace Cellar Level 1', 1197.0, 2864.0),  # slow by its travel only: not shortened
            row('Black Marsh', 1201.0, 1471.0),
            row('Den of Evil', 1500.0, 1515.0, on=60),  # too little time on it for a ruling
            row('Tamoe Highland', 1560.0, 1561.0, stays=2),  # too few stays
            row('Dry Hills', 1612.0, 2015.0),  # over the bar
        ],
    }
    assert [r['level'] for r in exphour.weak(result)] == ['Plains of Despair', 'Black Marsh']
    made = exphour.weak_file(result, SINCE, UNTIL)
    assert [(r['area'], r['name']) for r in made['levels']] == [(105, 'Plains of Despair'), (6, 'Black Marsh')]
    assert made['rule']['below_with_travel'] == exphour.WEAK_BELOW == 1600.0


def day(at: str, text: str) -> str:
    return f'2026-10-24 {at} INFO {text}'


# A real Den of Evil stay (session 20261024T093946Z-fe26932b, game cybergg6, 12:47:38-12:48:17 on 2026-10-24): its
# agenda targets as the log said them, each once
DEN = [
    day('12:46:00,000', 'Macro: Loop run: TZ leveling'),
    day('12:46:00,000', 'Macro: Loop on'),
    day('12:46:01,000', 'Macro: Loop: game 1, TZ level'),
    day('12:47:38,396', 'Macro: Loop: game 1, TZ next level'),
    day('12:47:38,845', 'Macro: experience: Blood Moor: +211,505 in 97s (level 96)'),
    day('12:47:38,882', 'Macro: Loop: game 1, TZ level'),
    *[
        day(at, f'Macro: agenda: target {label} ({kind}, tier {tier}, 0 leaders known here)')
        for at, label, kind, tier in [
            ('12:47:40,408', 'a group of 10', 'kill', 4),
            ('12:47:42,614', 'a group of 4', 'kill', 4),
            ('12:47:43,409', 'a group of 8', 'kill', 4),
            ('12:47:45,954', 'a group of 7', 'kill', 4),
            ('12:47:46,478', 'a group of 5', 'kill', 4),
            ('12:47:46,921', 'a group of 8', 'kill', 4),
            ('12:47:49,394', 'a group of 5', 'kill', 4),
            ('12:47:49,935', 'an unexplored room', 'explore', 7),
            ('12:47:52,858', 'a group of 4', 'kill', 4),
            ('12:47:55,169', 'an unexplored room', 'explore', 7),
            ('12:47:56,156', 'a group of 6', 'kill', 4),
            ('12:48:03,022', 'a group of 10', 'kill', 4),
            ('12:48:03,427', 'a group of 9', 'kill', 4),
            ('12:48:04,397', 'a group of 5', 'kill', 4),
            ('12:48:04,616', 'a group of 11', 'kill', 4),
            ('12:48:06,892', 'a group of 14', 'kill', 4),
            ('12:48:09,922', 'a group of 12', 'kill', 4),
            ('12:48:10,153', 'a group of 6', 'kill', 4),
            ('12:48:10,423', 'a group of 5', 'kill', 4),
            ('12:48:10,966', 'a group of 4', 'kill', 4),
        ]
    ],
    day('12:48:12,726', 'Macro: Loop: game 1, TZ loot'),
    day('12:48:12,812', 'Macro: Loop: game 1, TZ Town Portal'),
    day('12:48:17,447', 'Macro: experience: Den of Evil: +88,744 in 39s (level 96)'),
    day('12:48:17,465', 'Macro: Loop: game 1, TZ waypoint'),
    day('12:48:30,000', 'Macro: Loop off'),
]


def test_the_short_levels_replay_on_a_real_den_of_evil_stay(tmp_path: Path) -> None:
    directory = tmp_path / '20261024T094000Z-den'
    directory.mkdir()
    log = directory / 'probe.log'
    log.write_text('\n'.join(DEN) + '\n')
    written = datetime(2026, 10, 24, 12, 50).timestamp()
    os.utime(log, (written, written))
    window = exphour.read(datetime(2026, 10, 24, 12, 0), datetime(2026, 10, 24, 13, 0), 'tz', tmp_path)
    result = exphour.measure(window, frozenset((8,)))  # Den of Evil
    (den,) = result['shortened']['levels']
    assert (den['level'], den['stays'], den['on']) == ('Den of Evil', 1, 39)
    # SHORT leaves the two rooms (2.92 + 0.99 s) and the groups under 8 (14.27 s): 18.18 of its 39 s. The last group's
    # time ends at the loot leg (12:48:12.726), not at the level line
    assert den['dropped'] == pytest.approx(18.182, abs=0.01)
    average = result['exp'] / result['play_seconds']
    # The gain is that time at the window's average less the level's own rate, never below nothing (here the short
    # window's average is under Den of Evil's own rate)
    assert den['gain_exp'] == pytest.approx(18.182 * max(average - 88_744 / 39, 0.0), abs=50)
    assert exphour.dropped('a group of 7', 'kill')
    assert not exphour.dropped('a group of 8', 'kill')
    assert exphour.dropped('an unexplored room', 'explore')
    assert not exphour.dropped('the elite 279 (1)', 'kill')


# --- Baal games: the experience from the combat takes, the kills, the phases ----------------------------------------

BAAL_GAME = [
    line('10:00:00', 'Macro: Loop run: Baal'),
    line('10:00:00', 'Macro: Loop on'),
    line('10:00:00', 'Macro: Loop: game 1, next game'),
    line('10:00:12', 'Macro: Loop: game 1, a Northern shard for act 5'),
    line(
        '10:00:15',
        'Macro: terrorize: Northern Worldstone Shard used for act 5 (stack 93 -> 92); the act read terrorized',
    ),
    line('10:00:19', 'Macro: Loop: game 1, to the Worldstone Keep'),
    line('10:00:25', 'Macro: Loop: game 1, down the Worldstone Keep'),
    line('10:00:45', "Macro: Loop: game 1, the Throne's waves"),
    line('10:02:45', 'Macro: Loop: game 1, what is left'),
    line('10:02:50', 'Macro: Loop: game 1, into the Worldstone Chamber'),
    line('10:03:10', 'Macro: Loop: game 1, Baal'),
    line('10:03:35', 'Macro: Loop: game 1, what is left'),
    line('10:03:40', 'Macro: Loop: game 1, Save and Exit'),
    line('10:03:42', 'Macro: Loop: game 2, next game'),
    line('10:03:55', 'Macro: Loop: game 2, to the Worldstone Keep'),
    line('10:04:00', 'Macro: Loop off'),
]


def local_at(at: str) -> datetime:
    return datetime.strptime(f'2026-10-19 {at}', '%Y-%m-%d %H:%M:%S')


def take(combat: Path, start: str, end: str, area: int, experience: int, kills: int = 0, who: str = 'Cyber') -> None:
    """A combat take as takes/record.py leaves it: its manifest (the stats as it opened) and its events."""
    opened, closed = local_at(start).astimezone(UTC), local_at(end).astimezone(UTC)
    directory = combat / f'{opened:%Y%m%dT%H%M%SZ}-{area}'
    directory.mkdir(parents=True)
    manifest = {
        'area': area,
        'character': who,
        'character_stats': {'12': 96, '13': experience - 2**32 if experience >= 2**31 else experience},
        'started_at': opened.isoformat(),
        'finished_at': closed.isoformat(),
        'seconds': (closed - opened).total_seconds(),
    }
    (directory / 'manifest.json').write_text(json.dumps(manifest))
    events = [{'t': 1.0, 'event': 'kill', 'unit': n, 'txt': 697, 'macro': True} for n in range(kills)]
    events.append({'t': 1.0, 'event': 'log', 'level': 'INFO', 'text': 'Macro: a "kill" word in a log text'})
    with gzip.open(directory / 'events.jsonl.gz', 'wt') as stream:
        stream.write(''.join(json.dumps(event) + '\n' for event in events))


def baal(tmp_path: Path) -> tuple[Path, Path]:
    runs, combat = tmp_path / 'alt-d', tmp_path / 'combat'
    directory = session(runs, '20261019T070000Z-baal', BAAL_GAME)
    kills = [
        {'at': local_at('10:01:00').astimezone(UTC).isoformat(), 'event': 'elite_kill', 'unit_id': 1, 'txt_id': 62,
         'area': 131, 'kind': 'super'},
        {'at': local_at('10:03:30').astimezone(UTC).isoformat(), 'event': 'elite_kill', 'unit_id': 2, 'txt_id': 544,
         'area': 132, 'kind': 'unique'},
    ]  # fmt: skip
    (directory / 'terror-probe.jsonl').write_text(''.join(json.dumps(kill) + '\n' for kill in kills))
    big = 2_900_000_000  # past 2**31: the stat reads signed (macros/experience.py `reading`)
    take(combat, '10:00:00', '10:00:12', 109, big)  # Harrogath: no gain, no stay
    take(combat, '10:00:25', '10:00:35', 129, big)
    take(combat, '10:00:35', '10:00:45', 130, big, kills=2)
    take(combat, '10:00:45', '10:02:50', 131, big, kills=30)  # the waves: their gain shows at the Chamber's opening
    take(combat, '10:02:50', '10:03:40', 132, big + 499_000, kills=5)
    take(combat, '10:03:55', '10:04:00', 129, big + 560_000)  # the next game's: Baal's gain shows here
    return runs, combat


def test_a_baal_games_experience_comes_from_the_takes(tmp_path: Path) -> None:
    """Baal games say no experience lines (macros/loop.py TZ_KINDS only): a take's gain is the next take's reading at
    its opening less its own."""
    runs, combat = baal(tmp_path)
    result = exphour.measure(exphour.read(SINCE, UNTIL, 'baal', runs, combat))

    assert result['play_seconds'] == pytest.approx(240.0)
    assert result['exp'] == 560_000
    assert result['from_takes'] == result['stays'] == 4  # the Keep's two, the Throne, the Chamber: no town stay
    rows = {row['level']: row['exp'] for row in result['levels']}
    assert rows == {
        'Throne of Destruction': 499_000,
        'The Worldstone Chamber': 61_000,
        'The Worldstone Keep Level 2': 0,
        'The Worldstone Keep Level 3': 0,
    }
    assert (result['kills'], result['elites'], result['bosses']) == (37, 1, 1)
    assert result['kills_per_hour'] == pytest.approx(3600 * 37 / 240)
    assert set(result['classes']) == {'shard', 'shard act 5'}  # the game's shard line: act 5 terrorized


def test_a_baal_games_phases_by_its_legs(tmp_path: Path, capsys) -> None:
    runs, combat = baal(tmp_path)
    result = exphour.measure(exphour.read(SINCE, UNTIL, 'baal', runs, combat))

    first, second = result['games']
    assert first['whole']
    assert first['terrorized']
    assert not second['whole']
    phases = {'lobby': 14.0, 'town': 0.0, 'shard': 7.0, 'keep': 26.0, 'throne': 120.0, 'portal': 20.0, 'baal': 25.0,
              'loot': 10.0, 'trip': 0.0, 'other': 0.0}  # fmt: skip
    assert first['baal'] == pytest.approx(phases)
    assert (first['exp'], first['kills'], first['elites'], first['bosses']) == (560_000, 37, 1, 1)
    summary = result['baal']
    assert (summary['games'], summary['whole'], summary['terrorized']) == (2, 1, 1)  # game 2 used no shard
    assert summary['median']['throne'] == pytest.approx(120.0)
    exphour.report(result, 3)
    out = capsys.readouterr().out
    assert 'Baal games: 2 (1 terrorized, 1 whole)' in out
    assert 'kills: 37 monsters' in out


def test_a_tz_games_level_lines_win_over_its_takes(tmp_path: Path) -> None:
    """The level lines are the TZ games' experience; their takes add the kills only."""
    runs, combat = tmp_path / 'alt-d', tmp_path / 'combat'
    session(runs, '20261019T070000Z-a', GAME)
    take(combat, '10:00:10', '10:02:10', 48, 1_000_000, kills=12)
    take(combat, '10:02:30', '10:04:30', 101, 1_300_000, kills=4)
    take(combat, '10:04:40', '10:04:45', 103, 9_000_000)
    result = exphour.measure(exphour.read(SINCE, UNTIL, 'tz', runs, combat))
    assert result['exp'] == 840_000  # the lines', not the takes' 8,000,000
    assert result['from_takes'] == 0
    assert result['kills'] == 16


def test_a_takes_gain_wants_the_same_character_soon_after() -> None:
    def at(minute: int, who: str = 'a', experience: int | None = 100) -> exphour.Take:
        start = datetime(2026, 10, 19, 10, minute)
        return exphour.Take(start, start + timedelta(seconds=30), 131, who, experience, Path('.'))

    takes = [at(0), at(1, experience=150), at(2, who='b', experience=900), at(30, who='b', experience=950), at(31)]
    assert exphour.gains(takes) == [50, None, None, None, None]


def test_a_game_carried_over_a_restart_keeps_its_shard(tmp_path: Path) -> None:
    runs = tmp_path / 'alt-d'
    session(runs, '20261019T070000Z-a', BAAL_GAME[:11])  # stopped at the Chamber's portal for a restart
    later = [
        line('10:03:00', 'Macro: resumed after a restart: loop on, pickup most, run Baal'),
        line('10:03:00', 'Macro: Loop resumed after a restart'),
        *BAAL_GAME[10:],
    ]
    session(runs, '20261019T070250Z-b', later)
    result = exphour.measure(exphour.read(SINCE, UNTIL, 'baal', runs, tmp_path / 'combat'))
    carried = next(g for g in result['games'] if g['game'] == '20261019T070250Z-b/1')
    assert carried['terrorized']
