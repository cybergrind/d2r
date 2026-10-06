"""Opt-in appraisal against one published offline generation."""

import hashlib
import json
import os
import sys
import tempfile
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from inventory_tracking.items import metadata as item_metadata
from pricing.knowledge import artifacts, definition_store
from pricing.knowledge.assessment.build_profiles import OUTPUT
from pricing.knowledge.assessment.inputs import artifact_inputs
from pricing.knowledge.assessment.profile_sources import profile_source_paths
from pricing.knowledge.documented_cache_dates import REVIEW_PATH, parse_reviews
from pricing.knowledge.pipeline import retrieve_draft


ROOT = Path(__file__).resolve().parents[2]
METADATA = Path(item_metadata.__file__).parent / 'data/item_metadata.json'
VALIDATED = 'validated.json'  # in a generation directory: which code approved these bytes
# Every module `validate_runtime_inputs` runs (tests/pricing/knowledge/test_published_runtime.py).
VALIDATION_CODE = (
    Path(__file__).resolve().parent,
    Path(item_metadata.__file__).resolve().parent,
    ROOT / 'inventory_tracking/__init__.py',
    ROOT / 'inventory_tracking/common.py',
)


@dataclass(frozen=True)
class LoadedRuntime:
    bundle: object
    mapping: object
    definitions: definition_store.DefinitionCatalog

    @property
    def database(self):
        return self.bundle.database

    @property
    def generation(self):
        return self.bundle.generation


def runtime_inputs(profile_document=None, collection_reviews=None):
    if profile_document is None:
        profile_document = json.loads(artifacts.read_artifact(OUTPUT))
    return [
        *artifact_inputs(collection_reviews),
        OUTPUT,
        METADATA,
        definition_store.STORE.path,
        *sorted(profile_source_paths(profile_document, ROOT)),
    ]


def validation_sources():
    return sorted(path for entry in VALIDATION_CODE for path in (entry.rglob('*.py') if entry.is_dir() else [entry]))


def validation_code():
    """Fingerprint of the interpreter and sources that validate a generation."""
    code = hashlib.sha256(sys.version.encode())
    for path in validation_sources():
        code.update(path.relative_to(ROOT).as_posix().encode() + b'\0' + hashlib.sha256(path.read_bytes()).digest())
    return code.hexdigest()


def _validated_by(bundle):
    """The code fingerprint that approved exactly this generation, if one was recorded."""
    with suppress(OSError, ValueError, AttributeError):
        record = json.loads((bundle.directory / VALIDATED).read_bytes())
        if record.get('generation') == bundle.generation:
            return record.get('code')
    return None


def _record_validation(bundle, code):
    with suppress(OSError):  # a read-only store is validated again next time
        with tempfile.NamedTemporaryFile('w', dir=bundle.directory, prefix='.validated-', delete=False) as stream:
            json.dump({'generation': bundle.generation, 'code': code}, stream)
        os.replace(stream.name, bundle.directory / VALIDATED)


def load_runtime(bundle, *, validate=True):
    """Hash-checked runtime of one generation; `validate=False` skips the policy re-validation
    (seconds of CPU) for a process that only reuses a generation another process validated.

    A passed validation is recorded next to the generation, so the same bytes are validated
    again only by changed code (`validation_code`): a restart loads in a fraction of the time.
    """
    profile_name = OUTPUT.relative_to(ROOT).as_posix()
    profile_artifact = artifacts._read(bundle.artifact(profile_name))
    if profile_artifact.generation != bundle.artifacts[profile_name]['sha256']:
        raise ValueError('Published profile artifact changed')
    profile_document = json.loads(profile_artifact.data)
    if REVIEW_PATH not in bundle.artifacts:
        raise ValueError('Incomplete runtime publication: documented collection-date registry is missing')
    collection_artifact = artifacts._read(bundle.artifact(REVIEW_PATH))
    if collection_artifact.generation != bundle.artifacts[REVIEW_PATH]['sha256']:
        raise ValueError('Published collection-date registry changed')
    collection_reviews = parse_reviews(collection_artifact.data)
    required = {p.resolve().relative_to(ROOT).as_posix() for p in runtime_inputs(profile_document, collection_reviews)}
    missing = required - bundle.artifacts.keys()
    if missing:
        raise ValueError(f'Incomplete runtime publication: {sorted(missing)}')
    mapping = {}
    for name in sorted(required):
        expected = bundle.artifacts[name]
        artifact = artifacts._read(bundle.artifact(name))
        if artifact.generation != expected['sha256']:
            raise ValueError(f'Published artifact changed: {name}')
        mapping[(ROOT / name).resolve()] = artifact
    definitions = definition_store.DefinitionStore(
        bundle.artifact(definition_store.STORE.path.relative_to(ROOT).as_posix())
    ).load()
    if definitions.generation != mapping[definition_store.STORE.path.resolve()].generation:
        raise ValueError('Published definitions changed during load')
    loaded = LoadedRuntime(bundle, MappingProxyType(mapping), definitions)
    if not validate:
        return loaded
    code = validation_code()
    if _validated_by(bundle) == code:
        return loaded
    from pricing.knowledge.publication_validation import validate_runtime_inputs

    with published_snapshot(loaded):
        validate_runtime_inputs()
    _record_validation(bundle, code)
    return loaded


@contextmanager
def published_snapshot(bundle):
    loaded = bundle if isinstance(bundle, LoadedRuntime) else load_runtime(bundle)
    with (
        artifacts.supplied_artifacts(loaded.mapping),
        item_metadata.metadata_snapshot(loaded.mapping[METADATA.resolve()].data),
        definition_store.definition_snapshot(loaded.definitions),
    ):
        yield


def retrieve_published(extraction, bundle, *, loadout=None, as_of=None):
    with published_snapshot(bundle):
        result = retrieve_draft(extraction, bundle.database, loadout=loadout, as_of=as_of)
        result['assessment']['publication_generation'] = bundle.generation
        return result
