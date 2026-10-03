"""Pin one loaded KB publication per request; newer publications load in the background.

Validating a generation costs ~20 s of CPU, so no request ever loads one. Requests use the
generation this process already holds; a new pointer is validated in a retrieval process,
reused there by the other processes, and only then adopted here (`refresh`).
"""

import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from inventory_tracking.common import LOG
from pricing.knowledge.definition_store import fingerprint
from pricing.knowledge.pipeline import retrieve_draft
from pricing.knowledge.publication import pointer_generation, published_generation
from pricing.knowledge.published_runtime import LoadedRuntime, load_runtime, published_snapshot


@dataclass(frozen=True)
class Loaded:
    runtime: LoadedRuntime
    index_signature: tuple


@dataclass(frozen=True)
class RequestState:
    runtime: object
    issues: tuple
    as_of: object
    index_signature: tuple


@dataclass(frozen=True)
class PinnedPublication:
    """A request scope's publication as plain values, so another process can reload and re-check it."""

    store: Path
    generation: str
    as_of: date
    index_signature: tuple
    issues: tuple


class LoadedPublications:
    """Runtimes by generation in one process; the newest `keep` stay so a request pinned to the
    previous generation can still finish after a newer one is adopted."""

    def __init__(self, store, *, keep=2):
        self.store, self.keep = Path(store), keep
        self.loaded: OrderedDict[str, Loaded] = OrderedDict()
        self.lock = threading.Lock()

    def holds(self, generation) -> bool:
        with self.lock:
            return generation in self.loaded

    def get(self, generation, *, validate) -> Loaded:
        """A cached generation is returned as loaded: only one process validates a generation."""
        with self.lock:
            if generation in self.loaded:
                return self.loaded[generation]
        bundle = published_generation(self.store, generation)
        before = fingerprint(bundle.database.stat())
        runtime = load_runtime(bundle, validate=validate)
        if fingerprint(bundle.database.stat()) != before:
            raise ValueError('Published index changed during runtime loading')
        loaded = Loaded(runtime, before)
        with self.lock:
            self.loaded[generation] = loaded
            while len(self.loaded) > self.keep:
                self.loaded.popitem(last=False)
        return loaded


class PublishedAppraisal:
    def __init__(self, store, *, today=lambda: datetime.now(UTC).date(), publications=None):
        self.store = Path(store)
        self.today = today
        self.publications = publications or LoadedPublications(store)
        self.serving: tuple[Loaded | None, tuple] = (None, ())  # replaced whole, so readers see one pair
        self.failed = None  # a generation that failed to load is not retried until the pointer moves
        self._active = ContextVar('published_appraisal_request', default=None)

    def start(self):
        """Blocking first (validated) load, before the service accepts hotkeys."""
        try:
            self.serving = (self.publications.get(pointer_generation(self.store), validate=True), ())
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            raise ValueError(f'No valid offline publication: {error}') from error

    def refresh(self, prepare=lambda generation: None):
        """Background step: adopt a newly published generation once `prepare` made the retrieval
        processes hold it (the first one validates it); until then requests keep the current one."""
        current = self.serving[0]
        try:
            generation = pointer_generation(self.store)
        except (OSError, ValueError) as error:
            self.serving = (current, (f'Publication update unavailable: {error}',))
            return
        if current is not None and generation == current.runtime.generation:
            self.serving = (current, ())  # the pointer names what is served: no pending update issue
            return
        if generation == self.failed:
            return
        LOG.info('Appraisal publication %s: loading in the background', generation[:12])
        try:
            prepare(generation)
            loaded = self.publications.get(generation, validate=False)
        except Exception as error:
            LOG.warning('Appraisal publication %s rejected: %s', generation[:12], error)
            self.failed = generation
            self.serving = (current, (f'Publication update unavailable: {error}',))
            return
        self.serving, self.failed = (loaded, ()), None
        LOG.info('Appraisal publication %s: now serving', generation[:12])

    @contextmanager
    def request_scope(self):
        current, issues = self.serving
        if current is None:
            raise ValueError('; '.join(issues) or 'No valid offline publication')
        if fingerprint(current.runtime.database.stat()) != current.index_signature:
            raise ValueError('Published index changed after loading')
        state = RequestState(current.runtime, issues, self.today(), current.index_signature)
        with published_snapshot(state.runtime):
            token = self._active.set(state)
            try:
                yield
            finally:
                self._active.reset(token)

    def _state(self):
        state = self._active.get()
        if state is None:
            raise ValueError('Published appraisal requires a request scope')
        return state

    def cache_context(self):
        state = self._state()
        return state.runtime.generation, state.as_of.isoformat(), state.issues

    def pinned(self) -> PinnedPublication:
        state = self._state()
        return PinnedPublication(self.store, state.runtime.generation, state.as_of, state.index_signature, state.issues)

    def retrieve(self, observation):
        state = self._state()
        if fingerprint(state.runtime.database.stat()) != state.index_signature:
            raise ValueError('Published index changed after item capture')
        result = retrieve_draft(observation, state.runtime.database, as_of=state.as_of)
        result['assessment']['publication_generation'] = state.runtime.generation
        result['assessment']['publication_issues'] = list(state.issues)
        return result


class PublicationRefresher:
    """Thread that keeps calling `backend.refresh(prepare)`; the loading itself happens in the
    retrieval processes, this thread mostly waits for them."""

    def __init__(self, backend, prepare, *, interval):
        self.backend, self.prepare, self.interval = backend, prepare, interval
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self._run, name='publication-refresh', daemon=True)

    def _run(self):
        while not self.stopped.wait(self.interval):
            try:
                self.backend.refresh(self.prepare)
            except Exception:
                LOG.exception('Publication refresh failed')

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stopped.set()
        self.thread.join(timeout=5)


def prepare_processes(processes, store, *, stopped, poll=1.0, timeout=300.0, clock=None):
    """`prepare` for `PublicationRefresher`: the first process validates the generation, then the
    others load it unvalidated; each loads in its own background thread between lookups."""
    clock = clock or time.monotonic

    def prepare(generation):
        for index, process in enumerate(processes):
            deadline = clock() + timeout
            while not process.call(prepare_publication, store, generation, index == 0):
                if stopped.is_set():
                    raise ValueError('Service stopping')
                if clock() > deadline:
                    raise ValueError(f'Retrieval process did not load the publication in {timeout:g} s')
                stopped.wait(poll)

    return prepare


# --- retrieval-process side -------------------------------------------------------------------

_PROCESS_PUBLICATIONS: dict[Path, LoadedPublications] = {}
_LOADER = ThreadPoolExecutor(max_workers=1, thread_name_prefix='publication-load')
_LOADING: dict[tuple[Path, str], object] = {}


def process_publications(store) -> LoadedPublications:
    """One cache per store in this process (a retrieval process keeps its runtimes warm)."""
    store = Path(store)
    if store not in _PROCESS_PUBLICATIONS:
        _PROCESS_PUBLICATIONS[store] = LoadedPublications(store)
    return _PROCESS_PUBLICATIONS[store]


def warm_publication(store, generation):
    """Retrieval-process initializer: hold the generation the service validated at startup."""
    process_publications(store).get(generation, validate=False)


def prepare_publication(store, generation, validate) -> bool:
    """Retrieval-process entry: True once `generation` is held here; otherwise starts (or keeps)
    loading it in a thread so lookups continue meanwhile. A failed load raises once, then may retry."""
    publications = process_publications(store)
    if publications.holds(generation):
        return True
    key = (Path(store), generation)
    job = _LOADING.get(key)
    if job is None:
        _LOADING[key] = _LOADER.submit(publications.get, generation, validate=validate)
        return False
    if not job.done():
        return False
    del _LOADING[key]
    job.result()  # re-raises the load failure
    return True


def retrieve_pinned(pinned: PinnedPublication, observation):
    """Retrieval-process entry: run against exactly the generation the request pinned."""
    # Normally prepared already; a restarted process validates it here.
    loaded = process_publications(pinned.store).get(pinned.generation, validate=True)
    if (
        loaded.index_signature != pinned.index_signature
        or fingerprint(loaded.runtime.database.stat()) != pinned.index_signature
    ):
        raise ValueError('Published index changed after item capture')
    with published_snapshot(loaded.runtime):
        result = retrieve_draft(observation, loaded.runtime.database, as_of=pinned.as_of)
    result['assessment']['publication_generation'] = loaded.runtime.generation
    result['assessment']['publication_issues'] = list(pinned.issues)
    return result
