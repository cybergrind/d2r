from copy import deepcopy

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.stat_bundle import validate_stat_bundle


def test_compiled_stats_are_embedded_and_tampering_is_rejected():
    document = build()
    assert len(document['stat_evaluation']['configurations']) == 256
    validate_stat_bundle(document)
    changed = deepcopy(document)
    changed['stat_evaluation']['configurations'][0]['priorities'][0]['desirability'] = 'supporting'
    with pytest.raises(ValueError, match='stat configuration'):
        validate_stat_bundle(changed)
    validate_stat_bundle({'profiles': []})  # Older generations make no stat claim.


def test_pinned_bundle_supplies_stats_and_legacy_bundle_cannot_read_worktree_reviews(tmp_path, monkeypatch):
    import json

    from pricing.knowledge.assessment import profiles
    from pricing.knowledge.assessment.engine import assess
    from pricing.knowledge.assessment.repository import ProfileRepository
    from tests.pricing.knowledge.assessment.test_base_use import capture

    document = build()
    path = tmp_path / 'profiles.json'
    path.write_text(json.dumps(document))
    repository = ProfileRepository(path)
    monkeypatch.setattr(profiles, '_repository', repository)
    extraction = capture('Amulet', quality='magic', sockets=0, ethereal=False)
    extraction['decoded_stats'] = [
        {'status': 'decoded', 'value': value, 'memory_stat': {'id': stat, 'layer': layer, 'raw': value}}
        for stat, layer, value in [(188, 9, 3), (105, 0, 10)]
    ]
    with repository.snapshot():
        result = assess(extraction)
        assert len(result['stat_evaluation']['configurations']) == 13
        assert set(result['stat_evaluation']['annotations']) == {'188:9', '105:0'}
        assert {r['status'] for r in result['stat_evaluation']['configurations']} == {'failed', 'matched'}
        assert 'stat_evaluation' not in assess(extraction, profiles=[])
        del document['stat_evaluation']
        path.write_text(json.dumps(document))
        assert assess(extraction)['stat_evaluation'] == result['stat_evaluation']
    assert 'stat_evaluation' not in assess(extraction)
