import json

from pricing.knowledge.artifacts import artifact_snapshot
from pricing.knowledge.assessment.adapters import market_projection
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.inputs import artifact_inputs
from tests.pricing.knowledge.assessment.test_market_projection import extraction


def test_market_projection_uses_pinned_catalog_then_observes_new_publication(tmp_path, monkeypatch):
    path = tmp_path / 'projections.json'
    old = {'schema_version': 1, 'mappings': {'83:2': {'property_id': '498'}}}
    path.write_text(json.dumps(old))
    monkeypatch.setattr(market_projection, 'CATALOG', path)
    captured = extraction([(83, 2, 2, 2)])
    with artifact_snapshot([path]):
        assert normalize(captured).properties == {'498': 2}
        path.write_text(json.dumps({'schema_version': 1, 'mappings': {}}))
        assert normalize(captured).properties == {'498': 2}
        path.unlink()
        assert normalize(captured).properties == {'498': 2}
    path.write_text(json.dumps({'schema_version': 1, 'mappings': {}}))
    after = normalize(captured)
    assert not after.properties
    assert 'No verified market mapping for native stat 83:2.' in after.projection_gaps


def test_projection_catalog_is_registered_in_the_assessment_snapshot():
    assert market_projection.CATALOG.resolve() in artifact_inputs()
