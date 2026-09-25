import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from pricing.knowledge.assessment import build_profiles


def test_failed_publication_preserves_existing_bundle_and_cleans_temporary_file(tmp_path, monkeypatch):
    output = tmp_path / 'profiles.json'
    output.write_text('previous valid bundle')
    monkeypatch.setattr(build_profiles, 'OUTPUT', output)
    monkeypatch.setattr(build_profiles, 'build', lambda: {'profiles': [], 'coverage': {}})
    monkeypatch.setattr('pricing.knowledge.assessment.profiles.validate_profiles', lambda _: None)

    def reject_replace(*args):
        raise OSError('publication failed')

    monkeypatch.setattr(build_profiles.os, 'replace', reject_replace)
    with pytest.raises(OSError, match='publication failed'):
        build_profiles.main()
    assert output.read_text() == 'previous valid bundle'
    assert list(tmp_path.iterdir()) == [output]


def test_overlapping_publications_use_distinct_files_and_publish_whole_bundle(tmp_path, monkeypatch):
    output = tmp_path / 'profiles.json'
    monkeypatch.setattr(build_profiles, 'OUTPUT', output)
    monkeypatch.setattr(build_profiles, 'build', lambda: {'profiles': [], 'coverage': {}})
    monkeypatch.setattr('pricing.knowledge.assessment.profiles.validate_profiles', lambda _: None)
    barrier = Barrier(2)
    replace = build_profiles.os.replace
    temporary_names = []

    def synchronized_replace(source, destination):
        temporary_names.append(str(source))
        barrier.wait(timeout=5)
        replace(source, destination)

    monkeypatch.setattr(build_profiles.os, 'replace', synchronized_replace)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(build_profiles.main) for _ in range(2)]
        for future in futures:
            future.result()
    assert len(set(temporary_names)) == 2
    assert json.loads(output.read_text()) == {'profiles': [], 'coverage': {}}
    assert list(tmp_path.iterdir()) == [output]
