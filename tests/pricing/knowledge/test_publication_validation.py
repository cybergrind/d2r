import hashlib
import json

import pytest

from pricing.knowledge import definition_store
from pricing.knowledge.artifacts import Artifact, artifact_snapshot, supplied_artifacts
from pricing.knowledge.assessment.mechanics.base_tiers import CATALOG
from pricing.knowledge.assessment.policies import named_tiers
from pricing.knowledge.publication_validation import validate_definition_metadata, validate_runtime_inputs
from pricing.knowledge.published_runtime import METADATA, runtime_inputs


def test_metadata_must_match_compiled_definitions_not_only_source_fingerprints():
    definitions = json.loads(definition_store.STORE.path.read_bytes())
    metadata = json.loads(METADATA.read_bytes())
    validate_definition_metadata(definitions, metadata, json.loads(CATALOG.read_bytes()))
    identity = next(iter(metadata['identities']['unique'].values()))
    identity['fixed_triggers'] = [{'stat_id': 201, 'skill_id': 68, 'level': 63, 'chance': 99}]
    with pytest.raises(ValueError, match='metadata identity'):
        validate_definition_metadata(definitions, metadata, json.loads(CATALOG.read_bytes()))


@pytest.mark.parametrize('failure', ['tier', 'native_stat', 'source'])
def test_semantic_publication_rejects_invalid_tier_policy_or_changed_evidence(failure):
    with definition_store.definition_snapshot(), artifact_snapshot(runtime_inputs()) as snapshot:
        mapping = dict(snapshot)
        path = named_tiers.RULES.resolve()
        document = json.loads(mapping[path].data)
        policy = document['policies'][0]
        if failure == 'tier':
            policy['default_tier'] = 'legendary'
        elif failure == 'native_stat':
            policy['valid_if'] = {'op': 'stat_at_least', 'key': '99999:0', 'value': 1}
        else:
            policy['source']['sha256'] = '0' * 64
        raw = json.dumps(document).encode()
        mapping[path] = Artifact(raw, hashlib.sha256(raw).hexdigest())
        with supplied_artifacts(mapping), pytest.raises(ValueError, match=r'tier|stat|source'):
            validate_runtime_inputs()


def test_current_runtime_inputs_pass_semantic_publication_checks():
    with definition_store.definition_snapshot(), artifact_snapshot(runtime_inputs()):
        report = validate_runtime_inputs()
    assert report['named_policies'] >= 92
    assert report['profiles'] >= 249


def test_publication_collects_all_profile_source_files():
    from pricing.knowledge.assessment.build_profiles import OUTPUT
    from pricing.knowledge.published_runtime import ROOT

    document = json.loads(OUTPUT.read_bytes())
    expected = {(ROOT / p['source']['path']).resolve() for p in document['profiles']}
    assert expected <= set(runtime_inputs())


@pytest.mark.parametrize('failure', ['hash', 'locator'])
def test_publication_validates_pinned_profile_evidence(failure):
    from pricing.knowledge.assessment.build_profiles import OUTPUT
    from pricing.knowledge.published_runtime import ROOT

    with definition_store.definition_snapshot(), artifact_snapshot(runtime_inputs()) as snapshot:
        mapping = dict(snapshot)
        document = json.loads(mapping[OUTPUT.resolve()].data)
        if failure == 'hash':
            path = (ROOT / document['profiles'][0]['source']['path']).resolve()
            raw = b'{"changed_source": true}'
        else:
            path = OUTPUT.resolve()
            document['profiles'][0]['source']['locator'] = '/missing-profile-location'
            raw = json.dumps(document).encode()
        mapping[path] = Artifact(raw, hashlib.sha256(raw).hexdigest())
        with supplied_artifacts(mapping), pytest.raises(ValueError, match=r'Source changed|source locator'):
            validate_runtime_inputs()


@pytest.mark.parametrize('failure', ['defense', 'missing', 'original_base'])
def test_upgrade_metadata_must_match_ascending_catalog_chains(failure):
    definitions = json.loads(definition_store.STORE.path.read_bytes())
    item_metadata = json.loads(METADATA.read_bytes())
    identity = next(r for r in item_metadata['identities']['unique'].values() if r['name'] == 'Tarnhelm')
    variants = identity['upgrade_variants']
    if failure == 'defense':
        next(iter(variants.values()))['base_defense_range']['min'] += 1
    elif failure == 'missing':
        variants.clear()
    else:
        variants[identity['base_code']] = next(iter(variants.values()))
    with pytest.raises(ValueError, match='upgrade'):
        validate_definition_metadata(definitions, item_metadata, json.loads(CATALOG.read_bytes()))
