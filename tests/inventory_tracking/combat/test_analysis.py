"""Play metrics from a take (combat/analysis.py) on a small scripted take."""

import json
from pathlib import Path

from inventory_tracking.combat.analysis import analyse, write_analysis
from inventory_tracking.combat.takes import Take


NO_OWNER = 0xFFFFFFFF
RECT = [1920, 0, 2560, 1418]


def frame(n, mode, x=5000.0, monsters=(), pointer=(3200, 700, 0), rect=RECT):
    return {
        't': n * 0.04, 'n': n + 1, 'late': 0, 'game': True, 'panels': [], 'macro': False,
        'p': [1, mode, 108, x, 5000.0, 0, 388], 'm': list(monsters), 'x': [],
        'in': [*pointer, (pointer[0] - rect[0]) / rect[2], (pointer[1] - rect[1]) / rect[3], []], 'rect': rect,
    }  # fmt: skip


def foe(unit_id, life, mode=1, x=5010.0, y=5000.0, txt=310):
    return [unit_id, txt, mode, x, y, life, 128, 0, NO_OWNER, 0]


def take(tmp_path):
    # Ten frames running toward a monster, then a press and five frames of casting that hit and kill it.
    frames = [frame(n, 3, 4990.0 + n, [foe(7, 128)]) for n in range(10)]
    frames += [frame(10 + n, 10, 5000.0, [foe(7, 128 - 40 * min(n, 3), 12 if n >= 3 else 1)]) for n in range(5)]
    events = [
        {'t': 0.4, 'event': 'button', 'button': 3, 'down': True},
        {'t': 0.4, 'event': 'cast', 'mode': 10, 'macro': False},
        {'t': 0.44, 'event': 'hit', 'unit': 7, 'txt': 310, 'life': [128, 88], 'macro': False},
        {'t': 0.48, 'event': 'button', 'button': 3, 'down': False},
        {'t': 0.48, 'event': 'hit', 'unit': 7, 'txt': 310, 'life': [88, 48], 'macro': False},
        {'t': 0.52, 'event': 'hit', 'unit': 7, 'txt': 310, 'life': [48, 8], 'macro': False},
        {'t': 0.52, 'event': 'kill', 'unit': 7, 'txt': 310, 'macro': False},
    ]
    directory = tmp_path / '20261009T000000Z-108'
    directory.mkdir()
    (directory / 'manifest.json').write_text(json.dumps({'area': 108}))
    (directory / 'frames.jsonl').write_text(''.join(json.dumps(f) + '\n' for f in frames))
    (directory / 'events.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in events))
    return Take.load(directory)


def test_the_analysis_reads_cadence_aim_movement_and_kills(tmp_path):
    found = analyse(take(tmp_path))
    assert found['cadence']['casts'] == 1
    assert found['cadence']['presses'] == 1
    assert found['cadence']['casting_fraction'] == round(5 / 15, 3)
    aim = found['aim']
    assert aim['presses_with_a_hostile'] == 1
    assert aim['hits_within_window'] == {'3': 1}
    assert found['movement']['run_fraction'] == round(10 / 15, 3)
    assert found['movement']['bouts']['run']['count'] == 1
    assert found['movement']['bouts']['cast']['count'] == 1
    kills = found['kills']
    assert kills['kills'] == 1
    assert kills['by_txt_id'] == {'310': 1}
    assert kills['combat_seconds'] == round(13 * 0.56 / 14, 1)  # the last two frames show the corpse
    assert kills['lives_per_combat_second'] == round(120 / 128 / (13 * 0.56 / 14), 3)


def test_the_analysis_is_written_beside_the_take(tmp_path):
    found = write_analysis(take(tmp_path).directory)
    assert json.loads(Path(tmp_path / '20261009T000000Z-108' / 'analysis.json').read_text()) == found
