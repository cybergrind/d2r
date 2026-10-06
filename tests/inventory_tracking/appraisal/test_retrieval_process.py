import os
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from inventory_tracking.appraisal.retrieval_process import KeepWarm, RetrievalGroup, RetrievalProcess


def child_pid(_observation):
    return os.getpid()


def crash(_observation):
    os._exit(3)


def slow_pid(seconds):
    time.sleep(seconds)
    return os.getpid()


def test_lookup_runs_in_another_process_and_survives_a_crashed_child():
    with RetrievalProcess() as process:
        first = process.call(child_pid, {})
        assert first != os.getpid()
        with pytest.raises(ValueError, match='Retrieval process stopped'):
            process.call(crash, {})
        assert process.call(child_pid, {}) not in (first, os.getpid())


def test_group_runs_lookups_from_different_threads_in_parallel_processes():
    with RetrievalGroup(2) as group, ThreadPoolExecutor(max_workers=2) as threads:
        group.call(child_pid, {})  # both children are started with the group; this waits for one
        pids = list(threads.map(lambda _: group.call(slow_pid, 0.5), range(2)))
    assert len(set(pids)) == 2  # the second lookup did not queue behind the first


class FakeProcess:
    def __init__(self, idle):
        self.idle = idle

    def idle_seconds(self):
        return self.idle


def test_keep_warm_touches_every_process_at_start_then_only_idle_ones():
    busy, idle, touched = FakeProcess(0.0), FakeProcess(20.0), []
    keeper = KeepWarm([busy, idle], touched.append, interval=15.0)
    keeper.step(idle_for=0.0)
    assert touched == [busy, idle]
    keeper.step(idle_for=keeper.interval)
    assert touched == [busy, idle, idle]


def test_keep_warm_survives_a_failed_touch():
    first, second, touched = FakeProcess(20.0), FakeProcess(20.0), []

    def touch(process):
        if process is first:
            raise ValueError('No valid offline publication')
        touched.append(process)

    KeepWarm([first, second], touch, interval=15.0).step(idle_for=15.0)
    assert touched == [second]


def test_idle_time_restarts_after_each_call():
    now = [100.0]
    with RetrievalProcess(clock=lambda: now[0]) as process:
        now[0] = 130.0
        assert process.idle_seconds() == 30.0
        process.call(child_pid, {})
        assert process.idle_seconds() == 0.0


def hold_detail_queue(started, release):
    started.touch()
    deadline = time.monotonic() + 15
    while not release.exists():
        if time.monotonic() > deadline:
            raise TimeoutError('Test did not release detail worker')
        time.sleep(0.01)


def test_identify_finishes_while_detail_worker_is_busy(tmp_path):
    from inventory_tracking.appraisal.service import identify_retrieval
    from pricing.triage.runtime import enabled, fast_retrieve, warm
    from tests.inventory_tracking.appraisal.test_text import saved_result

    observation = saved_result()['result']['extraction']
    assert enabled(observation)
    started, release = tmp_path / 'started', tmp_path / 'release'
    with RetrievalProcess() as detail, RetrievalProcess(warm, (observation,)) as fast:
        assert fast.call(fast_retrieve, observation) is not None
        with ThreadPoolExecutor(max_workers=2) as threads:
            blocked = threads.submit(detail.call, hold_detail_queue, started, release)
            try:
                deadline = time.monotonic() + 5
                while not started.exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                assert started.exists()
                retrieve = identify_retrieval(fast, detail, None, tmp_path / 'unused.sqlite')
                result = threads.submit(retrieve, observation).result(timeout=2)
                assert 'triage' in result
                assert not blocked.done()
            finally:
                release.touch()
            blocked.result(timeout=5)
