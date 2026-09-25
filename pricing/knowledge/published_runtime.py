"""Opt-in appraisal against one published offline generation."""

import json
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from inventory_tracking.items import metadata as item_metadata
from pricing.knowledge import artifacts, definition_store
from pricing.knowledge.assessment.build_profiles import OUTPUT
from pricing.knowledge.assessment.inputs import artifact_inputs
from pricing.knowledge.assessment.profile_sources import profile_source_paths
from pricing.knowledge.pipeline import retrieve_draft


ROOT = Path(__file__).resolve().parents[2]
METADATA = Path(item_metadata.__file__).parent / 'data/item_metadata.json'


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


def runtime_inputs(profile_document=None):
    if profile_document is None:
        profile_document = json.loads(artifacts.read_artifact(OUTPUT))
    return [
        *artifact_inputs(),
        OUTPUT,
        METADATA,
        definition_store.STORE.path,
        *sorted(profile_source_paths(profile_document, ROOT)),
    ]


def load_runtime(bundle):
    profile_name = OUTPUT.relative_to(ROOT).as_posix()
    profile_artifact = artifacts._read(bundle.artifact(profile_name))
    if profile_artifact.generation != bundle.artifacts[profile_name]['sha256']:
        raise ValueError('Published profile artifact changed')
    profile_document = json.loads(profile_artifact.data)
    required = {p.resolve().relative_to(ROOT).as_posix() for p in runtime_inputs(profile_document)}
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
    from pricing.knowledge.publication_validation import validate_runtime_inputs

    with published_snapshot(loaded):
        validate_runtime_inputs()
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
