"""Run KB retrieval in a warm worker process instead of a service thread.

Retrieval is pure Python. In the service process it holds the GIL, and every small game-memory
read on the service loop then waits ~2 ms to get it back, so a 0.5-2 s lookup stalled the level
map, rune marks and the Alt+D hover checks. A child process has its own interpreter.
"""

import multiprocessing
import queue
import signal
import threading
import time
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool

from inventory_tracking.common import LOG


def _start_child(warm, args):
    signal.signal(signal.SIGINT, signal.SIG_IGN)  # Ctrl+C stops the service, which shuts this down
    if warm is not None:
        warm(*args)


def _context():
    context = multiprocessing.get_context('forkserver')
    # Preload the lookup code instead of the default '__main__': children fork warm, and the
    # service's entry module (or a stdin script) is never re-imported. Lookups are therefore
    # importable module-level functions, never ones defined in __main__.
    context.set_forkserver_preload(
        ['inventory_tracking.appraisal.memory_backend', 'inventory_tracking.appraisal.published_backend']
    )
    return context


def _ready():
    return True


def _timed_call(function, args):
    started = time.perf_counter()
    result = function(*args)
    return result, started, time.perf_counter()


class RetrievalProcess:
    """One warm child process; `call` blocks the calling (pool) thread, never the service loop."""

    def __init__(self, warm=None, warm_args=(), *, clock=time.monotonic):
        self._initargs = (warm, warm_args)
        self._lock = threading.Lock()
        self._clock = clock
        self._active = 0
        self._used = clock()
        self._pool = self._start()

    def _start(self):
        pool = ProcessPoolExecutor(
            max_workers=1,
            mp_context=_context(),
            initializer=_start_child,
            initargs=self._initargs,
        )
        pool.submit(_ready)  # start and warm the child now, not on the first Alt+D
        return pool

    def call(self, function, *args):
        with self._lock:
            pool = self._pool
            self._active += 1
        try:
            submitted = time.perf_counter()
            result, started, finished = pool.submit(_timed_call, function, args).result()
            received = time.perf_counter()
            if received - submitted >= 0.05:
                timing = {
                    'function': function.__name__,
                    'dispatch_ms': (started - submitted) * 1000,
                    'work_ms': (finished - started) * 1000,
                    'return_ms': (received - finished) * 1000,
                    'total_ms': (received - submitted) * 1000,
                }
                LOG.info(
                    'Retrieval %s: dispatch %.1f ms, work %.1f ms, return %.1f ms, total %.1f ms',
                    timing['function'],
                    timing['dispatch_ms'],
                    timing['work_ms'],
                    timing['return_ms'],
                    timing['total_ms'],
                    extra={'retrieval_timing': timing},
                )
            return result
        except BrokenProcessPool:
            with self._lock:
                if self._pool is pool:
                    self._pool = self._start()
            raise ValueError('Retrieval process stopped; press the hotkey again') from None
        finally:
            with self._lock:
                self._active -= 1
                self._used = self._clock()

    def idle_seconds(self):
        """Seconds since the last call finished; 0 while one is running."""
        with self._lock:
            return 0.0 if self._active else self._clock() - self._used

    def close(self):
        with self._lock:
            self._pool.shutdown(wait=True, cancel_futures=True)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class RetrievalGroup:
    """Several warm processes behind one `call`: each call takes a free process, so lookups
    submitted from different threads run in parallel."""

    def __init__(self, count, warm=None, warm_args=()):
        self.processes = [RetrievalProcess(warm, warm_args) for _ in range(count)]
        self._free: queue.SimpleQueue[RetrievalProcess] = queue.SimpleQueue()
        for process in self.processes:
            self._free.put(process)

    def call(self, function, *args):
        process = self._free.get()
        try:
            return process.call(function, *args)
        finally:
            self._free.put(process)

    def close(self):
        for process in self.processes:
            process.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class KeepWarm:
    """Thread that runs `touch(process)` (a real lookup) at start and whenever a process sat idle.

    A child builds its lookup caches on the first call (3-6 s), and an idle child's ~0.8 GB heap is
    paged out under memory pressure: the first lookup after ten idle minutes took 8 s in the median
    and up to 37 s, against ~0.6 s warm (probe.log, 2026-10-03). A touch may delay a real lookup
    that arrives meanwhile by one warm lookup.
    """

    def __init__(self, processes, touch, *, interval):
        self.processes, self.touch, self.interval = list(processes), touch, interval
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self._run, name='retrieval-keep-warm', daemon=True)

    def step(self, *, idle_for):
        for process in self.processes:
            if self.stopped.is_set():
                return
            if process.idle_seconds() >= idle_for:
                try:
                    self.touch(process)
                except Exception as exc:
                    LOG.debug('Retrieval keep-warm skipped: %s', exc)

    def _run(self):
        self.step(idle_for=0.0)
        while not self.stopped.wait(self.interval):
            self.step(idle_for=self.interval)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stopped.set()
        self.thread.join(timeout=5)
