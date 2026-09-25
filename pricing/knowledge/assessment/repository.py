"""Immutable reviewed profile snapshots; malformed updates retain the last good one."""

import hashlib
import json
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.domain.facts import freeze
from pricing.knowledge.assessment.roles.candidates import CandidateIndex


@dataclass(frozen=True)
class ProfileBundle:
    generation: str
    profiles: tuple
    scope: str
    candidates: CandidateIndex
    stat_candidates: CandidateIndex


@dataclass(frozen=True)
class BundleLoad:
    bundle: ProfileBundle | None
    issues: tuple[str, ...] = ()


class ProfileRepository:
    def __init__(self, path):
        self.path = Path(path)
        self._current = None
        self._pinned = ContextVar('reviewed_profile_bundle', default=None)

    @contextmanager
    def snapshot(self):
        loaded = self.load()
        token = self._pinned.set(loaded)
        try:
            yield loaded
        finally:
            self._pinned.reset(token)

    def load(self):
        from pricing.knowledge.assessment.profiles import validate_profiles

        if pinned := self._pinned.get():
            return pinned
        try:
            raw = read_artifact(self.path)
            generation = hashlib.sha256(raw).hexdigest()
            if self._current and self._current.generation == generation:
                return BundleLoad(self._current)
            document = json.loads(raw)
            if document.get('schema_version') != 1 or document.get('rules_version') != 'assessment-1':
                raise ValueError('incompatible profile schema/rules version')
            validate_profiles(document['profiles'])
            from pricing.knowledge.assessment.stat_bundle import validate_stat_bundle

            validate_stat_bundle(document)
            bundle = ProfileBundle(
                generation,
                freeze(document['profiles']),
                document['coverage']['scope'],
                CandidateIndex(document['profiles']),
                CandidateIndex(document.get('stat_evaluation', {}).get('configurations', [])),
            )
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            return BundleLoad(self._current, (f'Reviewed profile update unavailable: {error}',))
        self._current = bundle
        return BundleLoad(bundle)
