"""Freeze one published KB/date through capture, asynchronous retrieval and cache."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime

from pricing.knowledge.definition_store import fingerprint
from pricing.knowledge.pipeline import retrieve_draft
from pricing.knowledge.publication_repository import PublicationRepository
from pricing.knowledge.published_runtime import published_snapshot


@dataclass(frozen=True)
class RequestState:
    runtime: object
    issues: tuple
    as_of: object
    index_signature: tuple


class PublishedAppraisal:
    def __init__(self, store, *, today=lambda: datetime.now(UTC).date()):
        self.repository = PublicationRepository(store)
        self.today = today
        self._active = ContextVar('published_appraisal_request', default=None)

    @contextmanager
    def request_scope(self):
        loaded = self.repository.load()
        if loaded.runtime is None:
            raise ValueError('; '.join(loaded.issues) or 'No valid offline publication')
        state = RequestState(loaded.runtime, loaded.issues, self.today(), fingerprint(loaded.runtime.database.stat()))
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

    def retrieve(self, observation):
        state = self._state()
        if fingerprint(state.runtime.database.stat()) != state.index_signature:
            raise ValueError('Published index changed after item capture')
        result = retrieve_draft(observation, state.runtime.database, as_of=state.as_of)
        result['assessment']['publication_generation'] = state.runtime.generation
        result['assessment']['publication_issues'] = list(state.issues)
        return result
