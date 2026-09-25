import json

from pricing.knowledge.assessment.build_profiles import build


def test_repository_pins_immutable_generation_and_reloads_changed_artifacts(tmp_path):
    from pricing.knowledge.assessment.repository import ProfileRepository

    path = tmp_path / 'profiles.json'
    document = build()
    path.write_text(json.dumps(document))
    repository = ProfileRepository(path)
    first = repository.load()
    document['profiles'][0]['conditions'].append('New reviewed condition.')
    path.write_text(json.dumps(document))
    second = repository.load()
    assert first.bundle.generation != second.bundle.generation
    assert 'New reviewed condition.' not in first.bundle.profiles[0]['conditions']
    assert 'New reviewed condition.' in second.bundle.profiles[0]['conditions']
    assert not second.issues


def test_invalid_publication_preserves_last_valid_snapshot(tmp_path):
    from pricing.knowledge.assessment.repository import ProfileRepository

    path = tmp_path / 'profiles.json'
    path.write_text(json.dumps(build()))
    repository = ProfileRepository(path)
    valid = repository.load()
    path.write_text('{broken')
    failed = repository.load()
    assert failed.bundle is valid.bundle
    assert failed.issues
    empty_reader = ProfileRepository(path).load()
    assert empty_reader.bundle is None
    assert empty_reader.issues


def test_unreviewed_source_cannot_enter_executable_profile_bundle(tmp_path):
    from pricing.knowledge.assessment.repository import ProfileRepository

    document = build()
    document['profiles'][0]['review_status'] = 'discovery_only'
    path = tmp_path / 'profiles.json'
    path.write_text(json.dumps(document))
    result = ProfileRepository(path).load()
    assert result.bundle is None
    assert result.issues


def test_compiler_rejects_changed_source_even_when_rule_shape_is_valid(tmp_path):
    import hashlib

    import pytest

    from pricing.knowledge.assessment.maintenance.compile import compile_profiles

    document = build()
    source = tmp_path / 'source.json'
    source.write_text(json.dumps({'reviewed': 'source'}))
    for profile in document['profiles']:
        profile['source']['path'] = 'source.json'
        profile['source']['locator'] = '/reviewed'
        profile['source']['sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    assert compile_profiles(document, tmp_path) == document
    source.write_text('changed source')
    with pytest.raises(ValueError, match='Source changed'):
        compile_profiles(document, tmp_path)


def test_profile_snapshot_preserves_generation_and_fallback_issues(tmp_path):
    from pricing.knowledge.assessment.repository import ProfileRepository

    path = tmp_path / 'profiles.json'
    document = build()
    path.write_text(json.dumps(document))
    repository = ProfileRepository(path)
    with repository.snapshot() as original:
        document['profiles'][0]['conditions'].append('New generation.')
        path.write_text(json.dumps(document))
        assert repository.load() is original
        with repository.snapshot() as nested:
            assert nested is original
    updated = repository.load()
    assert updated.bundle.generation != original.bundle.generation
    path.unlink()
    with repository.snapshot() as fallback:
        assert fallback.bundle is updated.bundle
        assert fallback.issues
        path.write_text(json.dumps(document))
        assert repository.load() is fallback
    assert not repository.load().issues


def test_engine_records_the_profile_generation_used_across_publication(tmp_path, monkeypatch):
    from pricing.knowledge.assessment import engine, profiles
    from pricing.knowledge.assessment.repository import ProfileRepository
    from tests.pricing.knowledge.assessment.test_family_contracts import facts

    path = tmp_path / 'profiles.json'
    document = build()
    path.write_text(json.dumps(document))
    repository = ProfileRepository(path)
    original = repository.load().bundle.generation
    monkeypatch.setattr(profiles, '_repository', repository)
    normalize = engine.normalize

    def publish_during_capture(extraction):
        document['profiles'][0]['conditions'] = ['Updated during appraisal.']
        path.write_text(json.dumps(document))
        assert repository.load().bundle.generation == original
        return normalize(extraction)

    monkeypatch.setattr(engine, 'normalize', publish_during_capture)
    extraction = {
        'item': facts('Ring', 'magic').to_dict(),
        'decoded_stats': [],
        'source': {'stat_capture_complete': True},
    }
    result = engine.assess(extraction)
    assert result['profile_generation'] == original
    monkeypatch.setattr(engine, 'normalize', normalize)
    assert engine.assess(extraction)['profile_generation'] != original
    assert engine.assess(extraction, profiles=[])['profile_generation'] is None
