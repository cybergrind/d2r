"""The combat recorder (combat/record.py): takes open and close with the level, frames and the
events derived from them, the late-frame count; all on a scripted sample sequence and a fake clock."""

import json
import threading

from inventory_tracking.combat.record import IDLE_SECONDS, LEVEL_SECONDS, Recorder, Sample
from inventory_tracking.combat.takes import Take, timeline
from inventory_tracking.levels.model import Level, Room, Walkable, pack_cells
from inventory_tracking.macros.world import Monster, World
from tests.inventory_tracking.macros.fakes import player


CHAOS = 108
RECT = (1920, 0, 2560, 1418)


def world(area=CHAOS, monsters=(), mode=5, in_game=True):
    return World(in_game, (), 'cyber1', (388, None), player=player(area, mode=mode), monsters=tuple(monsters))


def foe(unit_id, life, max_life=100, mode=1):
    return Monster(unit_id, 19, mode, 5010.0, 5020.0, 0xFFFFFFFF, life=life, max_life=max_life, stats_at=0x10)


class Script:
    """Samples in order; the last one repeats."""

    def __init__(self, *samples):
        self.samples = list(samples)

    def __call__(self):
        if len(self.samples) > 1:
            return self.samples.pop(0)
        return self.samples[0]


def recorder(tmp_path, script, **extra):
    return Recorder(
        script, output=tmp_path, clock=lambda: 0.0, sleep=lambda s: None, stats=lambda at: {12: 85}, **extra
    )


def test_a_take_opens_in_the_level_and_closes_after_a_while_elsewhere(tmp_path):
    rec = recorder(tmp_path, Script(Sample(world(area=107)), Sample(world()), Sample(world()), Sample(world(area=107))))
    rec.step(0.0)
    assert rec.take is None
    rec.step(0.04)
    assert rec.take is not None
    assert rec.take.directory.name.endswith('-108')
    rec.step(0.08)
    rec.step(0.12)  # away: still recording
    assert rec.take is not None
    rec.step(0.12 + IDLE_SECONDS)
    assert rec.take is None
    take = Take.load(next(tmp_path.iterdir()))
    assert take.manifest['area'] == CHAOS
    assert take.manifest['character'] == 'CybergrindAA'
    assert take.manifest['reason'] == 'left the level'
    assert take.manifest['frames'] == 3
    assert take.manifest['seconds'] == 0.08
    assert take.summary()['frames'] == 3


def test_leaving_the_game_closes_the_take_at_once(tmp_path):
    rec = recorder(tmp_path, Script(Sample(world()), Sample(world(in_game=False))))
    rec.step(0.0)
    rec.step(0.04)
    assert rec.take is None
    assert Take.load(next(tmp_path.iterdir())).manifest['reason'] == 'left the game'


def test_entering_another_recorded_level_closes_the_take_and_opens_the_next(tmp_path):
    # The first Catacombs take (2026-10-10) ran through levels 1-3 as one take, so the guide's level
    # (level 3 by then) never matched its area and no level map was written.
    script = Script(Sample(world(area=35)), Sample(world(area=35)), Sample(world(area=36)), Sample(world(area=36)))
    rec = recorder(tmp_path, script, areas=frozenset((35, 36)))
    rec.step(0.0)
    rec.step(0.04)
    rec.step(0.08)
    assert rec.take is not None
    assert rec.take.manifest['area'] == 36
    rec.step(0.12)
    rec.close('test')
    takes = [Take.load(d) for d in sorted(tmp_path.iterdir())]
    assert [(t.manifest['area'], t.manifest['reason'], t.manifest['frames']) for t in takes] == [
        (35, 'changed level', 2),
        (36, 'test', 2),
    ]


def test_the_level_map_grows_with_the_walls_the_guide_reads_and_never_shrinks(tmp_path):
    grid = Walkable(996, 996, 8, 8, pack_cells('1' * 1600))
    levels = [None]  # the guide has not shown the level yet when the take opens
    rec = recorder(tmp_path, Script(Sample(world())), level=lambda: levels[0])
    rec.step(0.0)
    assert 'level' not in rec.take.manifest
    levels[0] = Level(CHAOS, (Room(1, 996, 996, 8, 8),), ())
    rec.step(0.04)  # too soon to look again
    assert 'level' not in rec.take.manifest
    rec.step(LEVEL_SECONDS)
    assert rec.take.manifest['level_grids'] == 0
    levels[0] = Level(CHAOS, (Room(1, 996, 996, 8, 8),), (grid,))
    rec.step(2 * LEVEL_SECONDS)
    assert rec.take.manifest['level_grids'] == 1
    levels[0] = Level(CHAOS, (Room(1, 996, 996, 8, 8),), ())  # left the game: the guide forgot the walls
    rec.close('left the game')
    take = Take.load(next(tmp_path.iterdir()))
    assert take.manifest['level_grids'] == 1
    assert len(json.loads((take.directory / 'level.json').read_text())['ground']) == 1


def test_frames_carry_the_world_the_input_and_the_level_map(tmp_path):
    level = Level(CHAOS, (Room(1, 996, 996, 8, 8),), ())
    missile = {'unit_id': 3, 'txt_id': 750, 'mode': 0, 'xy': [5012, 5030], 'path': 'ab'}
    sample = Sample(world(monsters=[foe(7, 100)]), [missile], (3200, 700, 1 << 10), RECT, frozenset({38}), macro=True)
    rec = recorder(tmp_path, Script(sample), level=lambda: level, manifest=lambda: {'keys': {'38': 'a'}})
    rec.step(1.0)
    rec.close('test')
    take = Take.load(next(tmp_path.iterdir()))
    frame = take.frames[0]
    assert frame['p'][2:5] == [CHAOS, 5000.0, 5000.0]
    assert frame['m'] == [[7, 19, 1, 5010.0, 5020.0, 100, 100, 0, 0xFFFFFFFF, 0]]
    assert frame['x'] == [[3, 750, 0, 5012, 5030, 'ab']]
    assert frame['in'] == [3200, 700, 1 << 10, 0.5, 0.4937, [38]]
    assert frame['macro'] is True
    assert take.manifest['level'] == 'level.json'
    assert take.manifest['keys'] == {'38': 'a'}
    assert json.loads((take.directory / 'level.json').read_text())['rooms'][0]['preset'] == 1
    assert take.units[0]['unit'] == 7
    assert take.units[0]['stats'] == {'12': 85}
    assert take.missiles[0]['unit_id'] == 3


def test_the_vitals_are_life_max_life_mana_and_max_mana_not_the_stamina(tmp_path):
    # itemstatcost: 6 hitpoints, 7 maxhp, 8 mana, 9 maxmana, 11 maxstamina; the first Catacombs take read 9
    # and 11 and so recorded a flat maximum mana for the mana (2026-10-10).
    stats = {6: 1778 << 8, 7: 1800 << 8, 8: 311 << 8, 9: 503 << 8, 10: 400 << 8, 11: 476 << 8}
    alive = World(True, (), 'cyber1', (388, None), player=player(CHAOS, stats_at=0x20))
    rec = Recorder(Script(Sample(alive)), output=tmp_path, clock=lambda: 0.0, stats=lambda at: dict(stats))
    rec.step(0.0)
    rec.close('test')
    assert Take.load(next(tmp_path.iterdir())).frames[0]['p'][7:11] == [1778, 1800, 311, 503]


def test_events_are_derived_casts_hits_kills_unloads_buttons_and_keys(tmp_path):
    frames = [
        Sample(world(monsters=[foe(7, 100), foe(8, 50)]), pointer=(0, 0, 0)),
        Sample(world(monsters=[foe(7, 100), foe(8, 50)], mode=10), pointer=(0, 0, 1 << 10), keys=frozenset({38})),
        Sample(world(monsters=[foe(7, 60), foe(8, 50)], mode=10), pointer=(0, 0, 1 << 10), keys=frozenset({38})),
        Sample(world(monsters=[foe(7, 60, mode=12)], mode=5), pointer=(0, 0, 0)),
        Sample(world(monsters=[]), pointer=(0, 0, 0)),
    ]
    rec = recorder(tmp_path, Script(*frames))
    for index in range(5):
        rec.step(index * 0.04)
    rec.close('test')
    take = Take.load(next(tmp_path.iterdir()))
    kinds = [(e['t'], e['event']) for e in take.events]
    assert kinds == [
        (0.04, 'cast'), (0.04, 'button'), (0.04, 'keys'),
        (0.08, 'hit'),
        (0.12, 'cast_end'), (0.12, 'kill'), (0.12, 'gone'), (0.12, 'button'), (0.12, 'keys'),
    ]  # fmt: skip
    hit = next(e for e in take.events if e['event'] == 'hit')
    assert hit['unit'] == 7
    assert hit['life'] == [100, 60]
    assert hit['macro'] is False
    assert next(e for e in take.events if e['event'] == 'gone')['unit'] == 8  # unloaded alive, not a kill
    assert take.summary()['events'] == {
        'cast': 1,
        'button': 2,
        'keys': 2,
        'hit': 1,
        'cast_end': 1,
        'kill': 1,
        'gone': 1,
    }
    assert take.summary()['manual_casts'] == 1
    assert timeline(take, every=0.1)[-1].endswith('casts   1  hits   1  kills   1  ')


def test_late_frames_are_counted_not_caught_up(tmp_path):
    clock = {'now': 0.0}
    waits = []
    stop = threading.Event()

    def sleep(seconds):
        waits.append(seconds)
        clock['now'] += seconds

    rec = Recorder(Script(Sample(world())), output=tmp_path, clock=lambda: clock['now'], sleep=sleep, rate=25.0)
    real_step = rec.step

    def step(now, late=0):
        real_step(now, late)
        clock['now'] += 0.1 if rec.take and rec.take.count == 2 else 0.01  # the second frame takes 100 ms
        if rec.take and rec.take.count >= 4:
            stop.set()

    rec.step = step
    rec.run(stop)
    manifest = json.loads((next(tmp_path.iterdir()) / 'manifest.json').read_text())
    assert manifest['frames'] == 4
    assert manifest['late_frames'] == 1
    assert manifest['reason'] == 'stopped'
    assert [round(wait, 2) for wait in waits] == [0.03, 0.03, 0.03]  # after the slow frame the schedule restarts
    assert [f['late'] for f in Take.load(next(tmp_path.iterdir())).frames] == [0, 0, 1, 0]
