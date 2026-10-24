"""The combat recorder in its own process (takes/recorder_process.py RECORDER_PROCESS, 2026-10-23,
rca/2026-10-23/realtime-3-findings.md): the service's events reach the take as the thread wrote them."""

import json
import logging
import threading
import time
from pathlib import Path

import pytest

from inventory_tracking.game.records import Player, World
from inventory_tracking.takes import decisions, recorder_process
from inventory_tracking.takes.record import Recorder, Sample
from inventory_tracking.takes.recorder_process import Fed, Feed, RecorderProcess, apply, wishes_of


def test_the_feed_stamps_an_input_with_its_thread_and_the_macros_routine():
    feed = Feed(clock=lambda: 5.0)
    feed.routine = lambda: 'attack'
    feed.sent('key', (38, 1))
    worker = threading.Thread(target=feed.sent, args=('button', (1, 0)), name='macro')
    worker.start()
    worker.join()
    feed.note('request', routine='attack')
    feed.decided({'looked_at': 4.9, 'chosen': 'Move'})

    assert feed.taken() == [
        ('sent', 5.0, 'key', (38, 1), 'MainThread', None),
        ('sent', 5.0, 'button', (1, 0), 'macro', 'attack'),
        ('note', 5.0, 'request', {'routine': 'attack'}),
        ('note', 5.0, 'decision', {'looked_at': 4.9, 'chosen': 'Move'}),
    ]
    assert feed.taken() == []


def test_the_loot_wishes_are_the_service_reads_arguments():
    assert wishes_of(lambda memory: memory.loot(rare=True, room=4)) == {'rare': True, 'room': 4}
    assert wishes_of(None) is None
    assert wishes_of(lambda memory: 1 / 0) is None


def chaos() -> Sample:
    return Sample(World(True, (), 'game-1', (), player=Player(1, 'Tester', 1, 108, 7800.0, 5500.0, None)))


def test_the_childs_messages_land_where_the_threads_calls_did(tmp_path):
    recorder = Recorder(chaos, output=tmp_path, areas=frozenset({108}), clock=lambda: 10.0)
    fed, stop = Fed(), threading.Event()
    attached = []
    sampler = type('S', (), {'attach': lambda self, *game: attached.append(game)})()

    apply(('attach', (11, 22, 33)), recorder, sampler, fed, stop)
    apply(('batch', [('note', 9.5, 'request', {'routine': 'x'}), ('sent', 9.6, 'key', (38, 1), 'macro', 'x')], True),
          recorder, sampler, fed, stop)  # fmt: skip
    apply(('state', {'attack_mode': True}, {'rare': True}, 'keyboard'), recorder, sampler, fed, stop)
    apply(('level', 'the level'), recorder, sampler, fed, stop)

    assert attached == [(11, 22, 33)]
    assert fed.game == (11, 22, 33)
    assert fed.working is True
    assert (fed.macro_state, fed.wishes, fed.input_mode, fed.level) == ({'attack_mode': True}, {'rare': True},
                                                                         'keyboard', 'the level')  # fmt: skip
    assert recorder.noted == [(9.5, 'request', {'routine': 'x'})]
    assert list(recorder.inputs) == [(9.6, 'key', (38, 1), 'macro', 'x')]
    apply(('stop',), recorder, sampler, fed, stop)
    assert stop.is_set()


class Source:
    pid, images, capture = 4242, {'candidate_base': 0x140000000}, None

    def ensure_connected(self) -> None:
        pass


def events_of(output: Path) -> list[dict]:
    takes = [path for path in output.iterdir() if path.is_dir()]
    assert len(takes) == 1
    return [json.loads(line) for line in (takes[0] / 'events.jsonl').read_text().splitlines()]


def test_a_take_recorded_in_the_child_has_the_services_events(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(recorder_process, 'one_unit_table', lambda capture: 0x1000)
    monkeypatch.setattr(decisions, 'DECISION_EVENTS', True)
    caplog.set_level(logging.INFO, logger='inventory_tracking')
    found = RecorderProcess(
        Source(), capture_lock=threading.Lock(), output=tmp_path, areas=frozenset({108}), poll_interval=0.0,
        macro_working=lambda: True, macro_state=lambda: {'attack_mode': True},
        sampler='tests.inventory_tracking.takes.recorder_scene:scripted',
    )  # fmt: skip
    try:
        found.poll(time.monotonic())
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not any(path.is_dir() for path in tmp_path.iterdir()):
            time.sleep(0.05)
        found.recorder.note('request', routine='attack')
        found.recorder.sent('key', (38, 1))
        decisions.tell({'looked_at': 1.0, 'chosen': 'Move'})
        time.sleep(0.5)
    finally:
        found.close()
    assert decisions.listener is not found.recorder.decided  # put back at the close

    events = events_of(tmp_path)
    kinds = {event['event'] for event in events}
    assert {'request', 'sent', 'decision', 'state'} <= kinds
    sent_event = next(event for event in events if event['event'] == 'sent')
    assert (sent_event['input'], sent_event['code'], sent_event['by']) == ('key', 38, 'MainThread')
    take = next(path for path in tmp_path.iterdir() if path.is_dir())
    manifest = json.loads((take / 'manifest.json').read_text())
    assert manifest['recorder'] == 'process'
    assert manifest['reason'] == 'stopped'
    assert manifest['frames'] > 0
    said = [record.getMessage() for record in caplog.records]
    assert any(text.startswith('Combat take ') and 'opened in area 108' in text for text in said)  # the child's line


def test_with_the_switch_off_the_service_gets_the_thread_recorder(monkeypatch):
    monkeypatch.setattr(recorder_process, 'RECORDER_PROCESS', False)
    made = []
    monkeypatch.setattr('inventory_tracking.takes.record.CombatRecorder', lambda source, **kwargs: made.append(kwargs))
    recorder_process.combat_recorder('source', output='x')
    assert made == [{'output': 'x'}]


def test_a_child_that_dies_is_started_again(tmp_path, monkeypatch):
    monkeypatch.setattr(recorder_process, 'one_unit_table', lambda capture: 0x1000)
    found = RecorderProcess(
        Source(), capture_lock=threading.Lock(), output=tmp_path, areas=frozenset({108}), poll_interval=0.0,
        sampler='tests.inventory_tracking.takes.recorder_scene:scripted',
    )  # fmt: skip
    try:
        first = found.process.pid
        found.process.kill()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and (found.process is None or found.process.pid == first):
            time.sleep(0.05)
        assert found.process is not None
        assert found.process.pid != first
        assert len(found.starts) == 2
    finally:
        found.close()


# The child over a stand-in game process (tests/inventory_tracking/game/scene.py): its own GameMemory, frame for frame
# what the thread's sampler reads


@pytest.fixture
def game_process():
    import multiprocessing

    from inventory_tracking.game.memory import GameMemory
    from tests.inventory_tracking.game import scene

    context = multiprocessing.get_context('spawn')
    ours, theirs = context.Pipe()
    child = context.Process(target=scene.run_scene, args=(theirs, False), daemon=True)
    child.start()
    try:
        assert ours.poll(30), 'the stand-in game did not start'
        pid, base, table = ours.recv()
        try:
            GameMemory(pid, base, table).close()
        except OSError as exc:
            pytest.skip(f'this sandbox cannot read another process: {exc}')
        yield pid, base, table
    finally:
        ours.send('stop')
        child.join(timeout=5)
        if child.is_alive():
            child.kill()


def first_frame(output: Path) -> dict:
    take = next(path for path in output.iterdir() if path.is_dir())
    with (take / 'frames.jsonl').open() as frames:
        return json.loads(frames.readline())


def test_the_childs_frames_are_the_threads_over_the_same_game(tmp_path, monkeypatch, game_process):
    from inventory_tracking.takes.record import LiveSampler

    pid, base, table = game_process
    thread_out, process_out = tmp_path / 'thread', tmp_path / 'process'
    thread_out.mkdir()
    process_out.mkdir()
    sampler = LiveSampler()
    sampler.attach(pid, base, table)
    recorder = Recorder(sampler, output=thread_out, areas=frozenset({108}), stats=sampler.stats)  # as CombatRecorder
    recorder.step(time.monotonic())
    recorder.step(time.monotonic())
    recorder.close('done')
    sampler.detach()

    class Game:
        images, capture = {'candidate_base': base}, None

        def __init__(self) -> None:
            self.pid = pid

        def ensure_connected(self) -> None:
            pass

    monkeypatch.setattr(recorder_process, 'one_unit_table', lambda capture: table)
    found = RecorderProcess(
        Game(), capture_lock=threading.Lock(), output=process_out, areas=frozenset({108}), poll_interval=0.0
    )
    try:
        found.poll(time.monotonic())
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not any(path.is_dir() for path in process_out.iterdir()):
            time.sleep(0.05)
        time.sleep(0.3)
    finally:
        found.close()

    by_thread, by_process = first_frame(thread_out), first_frame(process_out)
    assert by_process['p'] == by_thread['p']  # the character
    assert by_process['m'] == by_thread['m']  # every monster as the thread wrote it
    assert by_process['x'] == by_thread['x']  # the missiles


def test_an_event_that_cannot_be_pickled_is_dropped_and_the_rest_sent(caplog):
    import pickle
    from types import SimpleNamespace

    caplog.set_level(logging.INFO, logger='inventory_tracking')
    sent_bytes: list[bytes] = []
    feed = SimpleNamespace(conn=SimpleNamespace(send_bytes=sent_bytes.append), unpicklable=set())
    items = [
        ('note', 1.0, 'request', {'routine': 'x'}),
        ('note', 1.1, 'odd', {'f': lambda: 1}),  # not picklable
        ('note', 1.2, 'odd', {}),
    ]

    RecorderProcess._batch(feed, items, True)  # pyrefly: ignore[bad-argument-type]
    RecorderProcess._batch(feed, items, True)  # pyrefly: ignore[bad-argument-type]

    kind, kept, working = pickle.loads(sent_bytes[0])
    assert (kind, working) == ('batch', True)
    assert kept == [items[0], items[2]]
    said = [record.getMessage() for record in caplog.records if 'cannot go' in record.getMessage()]
    assert len(said) == 1  # once a kind


def test_an_area_change_closes_the_take_and_the_child_packs_each_take(tmp_path, monkeypatch):
    # 2026-10-24 (realtime-4): live, the take packing ('tidy' threads) took 10-44 % of a core for a second at each area
    # change on the service's GIL; in the child it is the child's, and the close waits for the last take's packing
    monkeypatch.setattr(recorder_process, 'one_unit_table', lambda capture: 0x1000)
    state = {'area': 108}
    found = RecorderProcess(
        Source(), capture_lock=threading.Lock(), output=tmp_path, areas=frozenset({107, 108}), poll_interval=0.0,
        keep=10 * 1024**3, macro_working=lambda: True, macro_state=lambda: dict(state),
        sampler='tests.inventory_tracking.takes.recorder_scene:walking',
    )  # fmt: skip

    def takes() -> list[Path]:
        return sorted(path for path in tmp_path.iterdir() if path.is_dir())

    try:
        found.poll(time.monotonic())
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not takes():
            time.sleep(0.05)
        found.recorder.note('request', routine='in 108')
        time.sleep(0.5)
        state['area'] = 107  # the next state the feed sends moves the character
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and len(takes()) < 2:
            time.sleep(0.05)
        found.recorder.note('request', routine='in 107')
        time.sleep(0.5)
    finally:
        found.close()

    first, second = sorted(takes(), key=lambda take: json.loads((take / 'manifest.json').read_text())['started_at'])
    assert json.loads((first / 'manifest.json').read_text())['area'] == 108
    assert json.loads((second / 'manifest.json').read_text())['area'] == 107
    for take in (first, second):
        assert not list(take.glob('*.jsonl'))  # packed: the first at the area change, the last before the close ended
        assert (take / 'frames.jsonl.gz').exists()
    assert [requests(first), requests(second)] == [['in 108'], ['in 107']]


def requests(take: Path) -> list[str]:
    import gzip

    with gzip.open(take / 'events.jsonl.gz', 'rt') as events:
        return [event.get('routine') for event in map(json.loads, events) if event['event'] == 'request']
