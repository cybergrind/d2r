"""The combat recorder (combat/record.py): takes open and close with the level, frames and the
events derived from them, the late-frame count; all on a scripted sample sequence and a fake clock."""

import json
import threading
from dataclasses import replace

from inventory_tracking.combat import macro_state
from inventory_tracking.combat.record import IDLE_SECONDS, LEVEL_SECONDS, NOTE_SECONDS, MacroLines, Recorder, Sample
from inventory_tracking.combat.takes import Take, carried, records, resists_by_frame, timeline
from inventory_tracking.levels.model import Level, Room, Walkable, pack_cells
from inventory_tracking.macros.world import Drop, Loot, Monster, Teleport, Thing, World
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


def test_path_records_are_written_when_they_change_past_the_position(tmp_path):
    def moved(position, rest):
        return Sample(world(monsters=[replace(foe(7, 100), path=position + rest), foe(8, 100)]), [], None, None)

    rec = recorder(
        tmp_path, Script(moved(b'A' * 8, b'\x01\x02'), moved(b'B' * 8, b'\x01\x02'), moved(b'B' * 8, b'\x03'))
    )
    for now in (1.0, 1.04, 1.08):
        rec.step(now)
    rec.close('test')
    rows = [json.loads(line) for line in (next(tmp_path.iterdir()) / 'paths.jsonl').read_text().splitlines()]
    # The position alone (the first 8 bytes) is in the frames already; the monster without a record is left out.
    assert rows == [
        {'t': 1.0, 'n': 1, 'm': [[7, (b'A' * 8 + b'\x01\x02').hex()]]},
        {'t': 1.08, 'n': 3, 'm': [[7, (b'B' * 8 + b'\x03').hex()]]},
    ]


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


def test_a_drop_of_the_characters_life_is_written_with_who_was_striking_and_what_flew_by(tmp_path):
    # itemstatcost 6 and 7: life and its maximum, with 8 fraction bits.
    life = iter((1500, 1500, 1290, 1290, 0))
    me = player(CHAOS, stats_at=0x20)
    target = b'\0' * 0x7C + me.unit_id.to_bytes(4, 'little')  # the path record names the character

    def stats(at):
        return {6: next(life) << 8, 7: 1783 << 8, 36: -90, 41: 108} if at == 0x20 else {12: 75, 367: 2}

    def sample(mode):
        herald = Monster(7, 55, mode, me.x + 8.0, me.y, 0xFFFFFFFF, 0x08, life=92, max_life=128, stats_at=0x10)
        herald = replace(herald, path=target, modifiers=(30, 28, 17))
        far = Monster(8, 55, 4, me.x + 40.0, me.y, 0xFFFFFFFF, 0x10, life=92, max_life=128, stats_at=0x10)
        pet = Monster(9, 361, 4, me.x + 1.0, me.y, me.unit_id, life=90, max_life=100, stats_at=0x10)
        point = bytes.fromhex('0080') + int(me.x + 2).to_bytes(2, 'little') + bytes.fromhex('0080')
        point += int(me.y).to_bytes(2, 'little')
        spark = {'unit_id': 50, 'txt_id': 195, 'mode': 3, 'xy': [0, 0], 'path': point.hex()}
        blade = {**spark, 'unit_id': 51, 'txt_id': 706}
        world = World(True, (), 'cyber1', (388, None), player=me, monsters=(herald, far, pet))
        return Sample(world, [spark, blade], None, None)

    rec = Recorder(Script(sample(2), sample(4), sample(4)), output=tmp_path, clock=lambda: 0.0, stats=stats)
    for now in (1.0, 1.04, 1.08, 1.12):  # the manifest's read of the stats, then 1500, 1290, 1290 and 0
        rec.step(now)
    rec.close('test')
    take = Take.load(next(tmp_path.iterdir()))

    # The character's own stats (its resistances) are in the manifest, each unit's enchantments with it.
    assert take.manifest['character_stats'] == {'6': 1500 << 8, '7': 1783 << 8, '36': -90, '41': 108}
    # (the character's own pet is among the units too, since 2026-10-13: its stat list is its damage)
    assert {unit['unit']: unit['mods'] for unit in take.units} == {7: [30, 28, 17], 8: [], 9: []}
    hurt = [event for event in take.events if event['event'] == 'hurt']
    # The Herald aimed at the character and swinging 8 units off is the suspect; the one 40 units off and
    # the character's own pet are not. The spark beside the character is listed, its own blade is not.
    assert [(e['t'], e['lost'], e['life'], e['max_life'], e['dead']) for e in hurt] == [
        (1.04, 210, 1290, 1783, False),
        (1.12, 1290, 0, 1783, True),
    ]
    assert hurt[0]['by'] == [[7, 55, 0x08, 4, 8.0, 1, [30, 28, 17]]]
    assert hurt[0]['near'] == [[195, 2.5]]
    # The character's resistances at that frame (physical, fire, lightning, cold, poison): Amplify Damage is on it.
    assert hurt[0]['resists'] == [-90, 0, 108, 0, 0]
    # And in the frames, at the first one and at every change, so a curse shows with no drop of life.
    assert [frame.get('r') for frame in take.frames] == [[-90, 0, 108, 0, 0], None, None, None]
    assert resists_by_frame(take) == [[-90, 0, 108, 0, 0]] * 4
    assert take.schema == 4


def test_a_change_of_the_resistances_is_written_in_the_frame_it_is_read_in(tmp_path):
    physical = iter((10, 10, -40, -40, 10))
    me = player(CHAOS, stats_at=0x20)

    def stats(at):
        return {6: 1500 << 8, 7: 1783 << 8, 36: next(physical), 39: 154}

    script = Script(*(Sample(World(True, (), 'cyber1', (388, None), player=me), [], None, None) for _ in range(3)))
    rec = Recorder(script, output=tmp_path, clock=lambda: 0.0, stats=stats)
    for now in (1.0, 1.04, 1.08, 1.12):  # the manifest's read of the stats, then 10, -40, -40 and 10
        rec.step(now)
    rec.close('test')
    take = Take.load(next(tmp_path.iterdir()))
    assert [frame.get('r') for frame in take.frames] == [
        [10, 154, 0, 0, 0],
        [-40, 154, 0, 0, 0],
        None,
        [10, 154, 0, 0, 0],
    ]
    assert resists_by_frame(take)[2] == [-40, 154, 0, 0, 0]


def test_objects_states_the_staff_and_the_belt_are_written_when_first_read_and_when_they_change(tmp_path):
    seal = Thing(960608137, 395, 0, 7655.0, 5275.0, True)
    opened = replace(seal, mode=2, selectable=False)
    staff, spent = Teleport(5, 40, False), Teleport(4, 40, True)
    belt = (517, 517, 517, 592)

    def sample(thing, held, cells, states=bytes(32)):
        return Sample(world(), things=(thing,), states=states, staff=held, belt=cells)

    script = Script(
        sample(seal, staff, belt),
        sample(seal, staff, belt),
        sample(opened, spent, (517, 517, None, 592), bytes([0, 2]) + bytes(30)),
        Sample(world()),  # the slow reads failed this frame: nothing is written, nothing is forgotten
    )
    rec = recorder(tmp_path, script)
    for now in (1.0, 1.04, 1.08, 1.12):
        rec.step(now)
    rec.close('test')
    take = Take.load(next(tmp_path.iterdir()))

    assert [frame.get('o') for frame in take.frames] == [
        [[960608137, 395, 0, 7655.0, 5275.0, True]],
        None,
        [[960608137, 395, 2, 7655.0, 5275.0, False]],
        None,
    ]
    assert [frame.get('w') for frame in take.frames] == [[5, 40, False], None, [4, 40, True], None]
    assert [frame.get('b') for frame in take.frames] == [[517, 517, 517, 592], None, [517, 517, None, 592], None]
    assert [frame.get('s') for frame in take.frames] == ['00' * 32, None, '0002' + '00' * 30, None]
    assert carried(take, 'o')[3] == [[960608137, 395, 2, 7655.0, 5275.0, False]]
    assert carried(take, 'w') == [[5, 40, False], [5, 40, False], [4, 40, True], [4, 40, True]]
    assert take.schema == 4


def test_the_macros_requests_and_lines_are_events_of_the_take_with_their_own_time(tmp_path):
    now = [0.0]
    rec = Recorder(Script(Sample(world())), output=tmp_path, clock=lambda: now[0], stats=lambda at: {})
    rec.note('said', text='before any take: with the first frame of one')
    rec.step(1.0)
    now[0] = 1.013
    rec.note('request', routine='teleport', age=0.0, during='hunt any')
    now[0] = 1.02
    rec.note('said', text='8 monsters by Vizier seal 1: the fight first')
    rec.step(1.04)
    rec.close('test')
    take = Take.load(next(tmp_path.iterdir()))

    told = [
        (e['t'], e['event'], e.get('routine') or e.get('text'))
        for e in take.events
        if e['event'] in ('request', 'said')
    ]
    assert told == [
        (0.0, 'said', 'before any take: with the first frame of one'),
        (1.013, 'request', 'teleport'),
        (1.02, 'said', '8 monsters by Vizier seal 1: the fight first'),
    ]
    assert take.manifest['events']['request'] == 1


def test_what_the_macro_said_on_the_way_in_is_kept_for_the_take_and_what_is_old_is_not(tmp_path):
    now = [0.0]
    script = Script(Sample(world(area=1)), Sample(world(area=1)), None, Sample(world()))
    rec = Recorder(script, output=tmp_path, clock=lambda: now[0], stats=lambda at: {})
    rec.note('log', text='Macro: too long ago')
    now[0] = NOTE_SECONDS + 1.0
    rec.step(now[0])  # in town: no take, the old line is let go
    rec.note('request', routine='prebuff')
    now[0] += 1.0
    rec.step(now[0])  # still in town
    rec.note('log', text='Macro: Teleport')
    now[0] += 1.0
    rec.step(now[0])  # a read that failed
    now[0] += 1.0
    rec.step(now[0])  # the level: the take opens with what was asked and said on the way
    rec.close('test')
    take = Take.load(next(tmp_path.iterdir()))

    assert [
        (e['event'], e.get('routine') or e.get('text')) for e in take.events if e['event'] in ('request', 'log')
    ] == [
        ('request', 'prebuff'),
        ('log', 'Macro: Teleport'),
    ]
    assert [e['t'] for e in take.events] == sorted(e['t'] for e in take.events)


def test_no_staff_worn_is_written_as_such_once_a_staff_was(tmp_path):
    seal = Thing(1, 395, 0, 7655.0, 5275.0, True)
    script = Script(
        Sample(world(), things=(seal,), staff=Teleport(5, 40, True)),
        Sample(world(), things=(seal,), staff=None),
        Sample(world()),  # no slow read: nothing known, nothing written
    )
    rec = recorder(tmp_path, script)
    for now in (1.0, 1.04, 1.08):
        rec.step(now)
    rec.close('test')
    take = Take.load(next(tmp_path.iterdir()))

    assert [frame.get('w', 'absent') for frame in take.frames] == [[5, 40, True], None, 'absent']


def test_every_line_the_macro_logs_is_a_note_and_other_lines_are_not():
    import logging

    told = []
    lines = MacroLines(lambda kind, **fields: told.append((kind, fields)))
    for name, text in (
        ('INFO', 'Macro: route Diablo: use Vizier seal 1'),
        ('INFO', 'Combat take opened'),
        ('WARNING', 'Macro stopped: the hop dropped'),
    ):
        lines.handle(logging.LogRecord('inventory_tracking', getattr(logging, name), __file__, 1, '%s', (text,), None))

    assert told == [
        ('log', {'level': 'INFO', 'text': 'Macro: route Diablo: use Vizier seal 1'}),
        ('log', {'level': 'WARNING', 'text': 'Macro stopped: the hop dropped'}),
    ]


def test_buffs_the_ground_and_the_inventory_are_written_when_they_change(tmp_path):
    potion = Drop(77, 5010.0, 5020.0, 'a super healing potion', 'healing')
    room = ('..#', '...')
    warded = replace(player(CHAOS), ward=True, hex_purge=False)
    script = Script(
        Sample(world(), loot=Loot((potion,), room=room)),
        Sample(World(True, (), 'cyber1', (388, None), player=warded), loot=Loot((), room=('.##', '...'))),
        Sample(World(True, (), 'cyber1', (388, None), player=warded)),
    )
    rec = recorder(tmp_path, script)
    for now in (1.0, 1.04, 1.08):
        rec.step(now)
    rec.close('test')
    take = Take.load(next(tmp_path.iterdir()))

    assert [frame.get('g') for frame in take.frames] == [
        [[77, 5010.0, 5020.0, 'healing', 'a super healing potion', 1, 1, True]],
        [],
        None,
    ]
    assert [frame.get('i') for frame in take.frames] == [['..#', '...'], ['.##', '...'], None]
    assert carried(take, 'f')[0][:2] != [True, False]
    assert carried(take, 'f')[1][:2] == [True, False]
    assert 'f' not in take.frames[2]


def test_the_macros_state_is_an_event_at_the_takes_start_and_at_each_change(tmp_path):
    idle, fighting = {'attack_mode': False, 'routine': 'teleport'}, {'attack_mode': True, 'routine': 'hunt any'}
    script = Script(*(Sample(world(), macro_state=state) for state in (idle, idle, fighting, None, fighting)))
    rec = recorder(tmp_path, script)
    for now in (1.0, 1.04, 1.08, 1.12, 1.16):
        rec.step(now)
    rec.close('test')
    take = Take.load(next(tmp_path.iterdir()))

    states = [(e['t'], e['attack_mode'], e['routine']) for e in take.events if e['event'] == 'state']
    assert states == [(1.0, False, 'teleport'), (1.08, True, 'hunt any')]


def test_safety_decisions_are_separate_events_only_when_the_decision_changes(tmp_path):
    decision = {'goal': 'a stand', 'budget': 100, 'candidates': [{'T': 1, 'H': 20, 'veto': None}]}
    script = Script(
        *(
            Sample(world(), macro_state={'attack_mode': True, 'decision': d})
            for d in (
                decision,
                decision,
                {**decision, 'budget': 50},
            )
        )
    )
    rec = recorder(tmp_path, script)
    for now in (1.0, 1.04, 1.08):
        rec.step(now)
    rec.close('test')
    take = Take.load(next(tmp_path.iterdir()))
    assert [e['budget'] for e in take.events if e['event'] == 'decision'] == [100, 50]
    assert len([e for e in take.events if e['event'] == 'state']) == 1


def test_a_units_raw_record_is_written_at_a_change_of_mode_and_once_a_second(tmp_path):
    def held(mode, raw):
        monster = replace(foe(7, 100, mode=mode), record=raw)
        return Sample(world(monsters=[monster, foe(8, 100)]))  # the second one carries no record: none written

    script = Script(held(1, b'\x01\x02'), held(1, b'\x01\x03'), held(4, b'\x04'), held(4, b'\x05'), held(4, b'\x06'))
    rec = recorder(tmp_path, script)
    for now in (1.0, 1.04, 1.08, 1.12, 2.1):
        rec.step(now)
    rec.close('test')
    directory = next(tmp_path.iterdir())

    assert [(row['t'], row['u']) for row in records(directory)] == [
        (1.0, [[7, '0102', '', '']]),
        (1.08, [[7, '04', '', '']]),  # the mode changed
        (2.1, [[7, '06', '', '']]),  # a second on
    ]


def test_a_monsters_states_and_skill_go_with_its_record_and_the_clients_tick_into_every_frame(tmp_path):
    caster = replace(foe(7, 100, mode=8), record=b'\xaa', states=b'\x00\x02', skill=b'\x57\x00')
    script = Script(Sample(world(monsters=[caster]), tick=b'\x01\x00'), Sample(world(monsters=[caster])))
    rec = recorder(tmp_path, script)
    for now in (1.0, 1.04):
        rec.step(now)
    rec.close('test')
    directory = next(tmp_path.iterdir())

    assert [row['u'] for row in records(directory)] == [[[7, 'aa', '0002', '5700']]]
    assert [frame.get('k') for frame in Take.load(directory).frames] == ['0100', None]


def test_companions_are_in_the_units_and_a_take_names_its_game_its_clock_and_the_take_before(tmp_path):
    pet = replace(foe(9, 80), owner=1, ally=True)
    script = Script(Sample(world(monsters=[pet])), Sample(world(area=107, monsters=[pet])), Sample(world(area=107)))
    rec = recorder(tmp_path, script, areas=None)
    for now in (1.0, 1.04, 1.08):
        rec.step(now)
    rec.close('test')
    first, second = (
        Take.load(directory) for directory in sorted(tmp_path.iterdir(), key=lambda d: d.name[-3:], reverse=True)
    )

    assert [unit['unit'] for unit in first.units] == [9]
    assert first.units[0]['ally'] is True
    assert not [e for e in first.events if e['event'] in ('hit', 'kill')]
    assert first.manifest['game'] == 'cyber1'
    assert first.manifest['clock']['monotonic'] == 1.0
    assert first.manifest['clock']['wall'] > 1.7e9
    assert first.manifest['previous'] is None
    assert second.manifest['previous'] == first.directory.name


def test_a_town_is_recorded_only_when_asked(tmp_path):
    for town, takes in ((False, 0), (True, 1)):
        output = tmp_path / str(town)
        rec = Recorder(Script(Sample(world(area=103))), output=output, areas=None, clock=lambda: 0.0, town=town)
        rec.step(1.0)
        rec.close('test')
        assert len(list(output.iterdir()) if output.exists() else []) == takes


def test_the_macros_state_is_read_off_a_runner_and_a_broken_part_is_left_out():
    class Sweep:
        steps = 3

    class Hunter:
        sweep = Sweep()

    class Runner:
        attack_mode, working, routine = True, False, 'hunt any'
        build = None
        hunter = Hunter()
        progress = None
        target = None

    found = macro_state.snapshot(Runner())
    assert found == {
        'attack_mode': True, 'working': False, 'routine': 'hunt any', 'build': None, 'settings': None,
        'sweep': 3, 'route': None, 'card': None,
    }  # fmt: skip
    assert macro_state.snapshot(object()) == {}


def test_the_unit_under_the_pointer_is_written_when_it_changes_and_nothing_under_it_is_told_from_unread(tmp_path):
    script = Script(
        Sample(world(), hovered=(1, 7), hover_read=True),
        Sample(world(), hovered=(1, 7), hover_read=True),
        Sample(world(), hovered=None, hover_read=True),
        Sample(world()),  # not read: nothing written
        Sample(world(), hovered=(2, 395), hover_read=True),
    )
    rec = recorder(tmp_path, script)
    for now in (1.0, 1.04, 1.08, 1.12, 1.16):
        rec.step(now)
    rec.close('test')
    take = Take.load(next(tmp_path.iterdir()))

    assert [frame.get('h', 'absent') for frame in take.frames] == [[1, 7], 'absent', None, 'absent', [2, 395]]


def test_the_wards_pool_goes_into_the_frames_and_a_hurt_says_what_the_ward_and_the_companions_took(tmp_path):
    # itemstatcost 361 psychicward, 362 psychicwardmax, x256: 185 points when cast (the manifests of 2026-10-13).
    me = player(CHAOS, stats_at=0x20)
    vitals = iter([(1500, 185), (1500, 185), (1400, 120), (1400, 120), (1400, None)])

    def stats(at):
        if at != 0x20:
            return {12: 85}  # a companion's, at first sight
        life, ward = next(vitals)
        found = {6: life << 8, 7: 1783 << 8}
        return found | ({361: ward << 8, 362: 185 << 8} if ward is not None else {})

    def sample(pet_life, mercenary_life):
        pet = Monster(9, 744, 1, me.x + 1.0, me.y, me.unit_id, life=pet_life, max_life=900, stats_at=0x10)
        mercenary = Monster(10, 338, 1, me.x + 2.0, me.y, 0xFFFFFFFF, ally=True, life=mercenary_life, max_life=2367)
        stranger = Monster(11, 744, 1, me.x + 3.0, me.y, 77, life=50, max_life=50)  # another's pet: not ours
        return Sample(World(True, (), 'cyber1', (388, None), player=me, monsters=(pet, mercenary, stranger)))

    rec = Recorder(
        Script(sample(900, 2367), sample(700, 2367), sample(700, 2367), sample(700, 2367)),
        output=tmp_path, clock=lambda: 0.0, stats=stats,
    )  # fmt: skip
    for now in (1.0, 1.04, 1.08, 1.12):  # the manifest's read, then the four frames' reads
        rec.step(now)
    rec.close('test')
    take = Take.load(next(tmp_path.iterdir()))

    assert [frame.get('a') for frame in take.frames] == [[185.0, 185.0], [120.0, 185.0], None, [0.0, 0.0]]
    assert carried(take, 'a')[2] == [120.0, 185.0]
    [hurt] = [event for event in take.events if event['event'] == 'hurt']
    assert (hurt['t'], hurt['lost']) == (1.04, 100)
    assert hurt['absorb'] == [185.0, 120.0, 185.0]  # 65 points taken by the ward beside the 100 of life
    assert hurt['companions'] == [[9, 744, 900, 700, 900], [10, 338, 2367, 2367, 2367]]


def test_the_server_frame_of_the_life_message_is_read_only_where_the_life_changed(tmp_path):
    lives = iter((1500, 1500, 1500, 1400, 1400, 1450))
    me = player(CHAOS, stats_at=0x20)
    asked = []

    def server_frame(character):
        asked.append(character.unit_id)
        return 1000 + 3 * len(asked)

    rec = Recorder(
        Script(Sample(World(True, (), 'cyber1', (388, None), player=me))),
        output=tmp_path, clock=lambda: 0.0, stats=lambda at: {6: next(lives) << 8, 7: 1783 << 8},
        server_frame=server_frame,
    )  # fmt: skip
    for now in (1.0, 1.04, 1.08, 1.12, 1.16):  # the manifest's read, then 1500, 1500, 1400, 1400, 1450
        rec.step(now)
    rec.close('test')
    take = Take.load(next(tmp_path.iterdir()))

    assert asked == [1, 1, 1]  # the first frame, the drop and the rise: not the frames whose life stood still
    assert [frame.get('sf') for frame in take.frames] == [1003, None, 1006, None, 1009]
    assert [event['sf'] for event in take.events if event['event'] == 'hurt'] == [1006]


def test_a_change_of_a_monsters_states_writes_its_record_and_a_changed_stat_list_again(tmp_path):
    lists = iter(({39: 75, 6: 128 << 8}, {39: 20, 6: 128 << 8}, {39: 20, 6: 128 << 8}))
    plain, cursed, also_cold = (
        bytes(32),
        bytes([0, 0, 0, 0, 0, 0, 0, 0x20]) + bytes(24),
        bytes([0, 8, 0, 0, 0, 0, 0, 0x20]) + bytes(24),
    )

    def held(states, mode=1):
        return Sample(world(monsters=[replace(foe(7, 100, mode=mode), record=b'\x01', states=states)]))

    script = Script(held(plain), held(plain), held(cursed), held(cursed), held(also_cold))
    rec = Recorder(script, output=tmp_path, clock=lambda: 0.0, stats=lambda at: next(lists))
    for now in (1.0, 1.04, 1.08, 1.12, 1.16):
        rec.step(now)
    rec.close('test')
    take = Take.load(next(tmp_path.iterdir()))

    # Lower Resist (state 61: word 1, bit 29) lands at 1.08: the record again at once, not a second later.
    assert [(row['t'], row['u'][0][2]) for row in records(take.directory)] == [
        (1.0, plain.hex()), (1.08, cursed.hex()), (1.16, also_cold.hex()),
    ]  # fmt: skip
    assert take.units[0]['stats'] == {'39': 75, '6': 128 << 8}
    # Its stat list read again at each change of states, written where it differs from the one written last.
    assert [(e['t'], e['unit'], e['states'], e['stats']) for e in take.events if e['event'] == 'stats'] == [
        (1.08, 7, cursed.hex(), {'39': 20, '6': 128 << 8}),
    ]


class Memory:
    """Bytes at addresses, read as /proc/<pid>/mem is."""

    def __init__(self, blocks, table=0x1000):
        self.blocks, self.table, self.reads = blocks, table, 0

    def read(self, address, size):
        self.reads += 1
        for start, data in self.blocks.items():
            if start <= address and address + size <= start + len(data):
                return data[address - start : address - start + size]
        raise OSError('unmapped')


def item_unit(unit_id, class_id, data, following=0):
    record = bytearray(0x160)
    record[0:16] = (4).to_bytes(4, 'little') + class_id.to_bytes(4, 'little') + unit_id.to_bytes(4, 'little') + bytes(4)
    record[0x10:0x18] = data.to_bytes(8, 'little')
    record[0x158:0x160] = following.to_bytes(8, 'little')
    return bytes(record)


def test_a_drop_is_named_by_its_code_and_quality_read_once_while_it_lies_there(tmp_path):
    from inventory_tracking.combat.record import LiveSampler, item_identity
    from inventory_tracking.items.metadata import item_base

    # Item unit 300 hashes to bucket 44 (300 % 128), behind another item in the same chain; a rune of class
    # 640, quality 2 (normal). Its code is the game's tables', not written here.
    heads = bytearray(1024 * 5)
    heads[4 * 1024 + 8 * 44 : 4 * 1024 + 8 * 45] = (0x5000).to_bytes(8, 'little')
    memory = Memory({
        0x1000: bytes(heads),
        0x5000: item_unit(172, 606, 0x7000, following=0x6000),
        0x6000: item_unit(300, 640, 0x8000),
        0x7000: (4).to_bytes(4, 'little'),
        0x8000: (2).to_bytes(4, 'little'),
    })  # fmt: skip
    code = item_base(640)['code']
    assert item_identity(memory.read, memory.table, 300) == (code, 2)
    assert item_identity(memory.read, memory.table, 428) == (None, None)  # same chain, not in it

    sampler = LiveSampler()
    rune = Drop(300, 5010.0, 5020.0, 'Ber Rune', 'valuable')
    found = sampler.identify(memory, Loot((rune,)))
    reads = memory.reads
    assert found == {300: (code, 2)}
    assert sampler.identify(memory, Loot((rune,))) == found
    assert memory.reads == reads  # read once a drop

    rec = recorder(tmp_path, Script(Sample(world(), loot=Loot((rune,)), items=found)))
    rec.step(1.0)
    rec.close('test')
    take = Take.load(next(tmp_path.iterdir()))
    assert take.frames[0]['g'] == [[300, 5010.0, 5020.0, 'valuable', 'Ber Rune', 1, 1, True, code, 2]]


def test_the_server_frame_is_read_through_the_player_data_and_the_block_pointer_is_kept():
    from inventory_tracking.combat.record import LIFE_BLOCK, LIFE_FRAME, LiveSampler

    record = bytes(0x10) + (0x9000).to_bytes(8, 'little') + bytes(0x1C0 - 0x18)
    memory = Memory(
        {0x9000 + LIFE_BLOCK: (0xA000).to_bytes(8, 'little'), 0xA000 + LIFE_FRAME: (51234).to_bytes(4, 'little')}
    )
    sampler = LiveSampler()
    sampler.memory = memory
    me = player(CHAOS, record=record)

    assert sampler.server_frame(me) == 51234
    assert sampler.server_frame(me) == 51234
    assert memory.reads == 3  # the block pointer once, the frame twice
    assert sampler.server_frame(player(CHAOS)) is None  # no record read: nothing to go through


def test_the_macros_memory_is_read_off_a_hunter_as_clock_times():
    import math

    from inventory_tracking import builds
    from inventory_tracking.macros.hunt import Hunter
    from inventory_tracking.macros.journey import Journey

    hunter = Hunter(build=builds.FALLBACK)
    hunter.sweep.start(100.0)
    hunter.sweep.failed(101.0, (5010.0, 5020.0))
    hunter.travel.jump_failed[390] = 102.5
    hunter.travel.jumped_at[390] = 103.25
    hunter.buffs.cast_at[387, None] = 90.0
    hunter.untouchable[77] = 130.0
    hunter.held = Drop(300, 5010.0, 5020.0, 'Ber Rune', 'valuable')

    class Runner:
        attack_mode, working, routine = True, True, 'hunt any'
        build = None
        progress = None
        target = None
        quiet_until = -math.inf
        attack_declined = False
        journey = Journey()

    Runner.hunter = hunter
    found = macro_state.snapshot(Runner())
    json.dumps(found, allow_nan=False)  # no infinity: a never is None
    memory = found['memory']
    assert memory['quiet_until'] is None
    assert memory['sweep']['until'] > 100.0
    assert memory['sweep']['fails'] == 1
    assert memory['sweep']['shunned'] == [[5010.0, 5020.0, 101.0]]
    assert memory['travel']['jump_failed'] == {'390': 102.5}
    assert memory['travel']['warped_at'] == 103.25
    assert memory['buffs']['cast_at'] == [[387, None, 90.0]]
    assert memory['untouchable'] == {'77': 130.0}
    assert memory['held'] == 300
    assert memory['judged'] == [None, None, False]


def test_the_input_mode_is_in_the_manifest_and_its_flips_and_the_controllers_target_are_events(tmp_path):
    # rca/2026-10-13/controller-mode.md plan steps 1 and 7: tracking/input_mode.py notes them, the take keeps them.
    sample = Sample(world(monsters=[foe(7, 100)]), [], None, None, frozenset())
    rec = recorder(tmp_path, Script(sample), manifest=lambda: {'input_mode': 'keyboard'})
    rec.note('input_mode', mode='controller', pending=False, flip={'from': 'keyboard', 'to': 'controller'})
    rec.note('ctl', target=[1, 7], record=3, skill=388)
    rec.step(1.0)
    rec.close('test')
    take = Take.load(next(tmp_path.iterdir()))
    assert take.manifest['input_mode'] == 'keyboard'
    flip = next(e for e in take.events if e['event'] == 'input_mode')
    assert (flip['mode'], flip['flip']['to']) == ('controller', 'controller')
    assert next(e for e in take.events if e['event'] == 'ctl')['target'] == [1, 7]
