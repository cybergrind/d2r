import json

from pricing.knowledge.artifacts import artifact_snapshot
from pricing.knowledge.assessment.policies import named_tiers
from tests.pricing.knowledge.assessment.policies.test_named_tiers import traveler


def test_tier_rules_and_source_are_pinned_until_next_assessment(tmp_path, monkeypatch):
    document = json.loads(named_tiers.RULES.read_bytes())
    rule = next(r for r in document['policies'] if r['name'] == 'War Traveler')
    source = tmp_path / rule['source']['path']
    source.parent.mkdir(parents=True)
    source.write_bytes((named_tiers.ROOT / rule['source']['path']).read_bytes())
    rules = tmp_path / 'tiers.json'
    rules.write_text(json.dumps({'schema_version': 1, 'policies': [rule]}))
    monkeypatch.setattr(named_tiers, 'ROOT', tmp_path)
    monkeypatch.setattr(named_tiers, 'RULES', rules)
    with artifact_snapshot([rules, source]):
        expected = named_tiers.assess_tier(traveler(50))
        assert expected['tier'] == 'high'
        rules.write_text(json.dumps({'schema_version': 1, 'policies': []}))
        source.unlink()
        assert named_tiers.assess_tier(traveler(50)) == expected
    assert named_tiers.assess_tier(traveler(50))['status'] == 'pending_review'


def test_all_named_tier_sources_participate_in_assessment_snapshot():
    from pricing.knowledge.assessment.inputs import artifact_inputs

    registered = artifact_inputs()
    assert named_tiers.RULES.resolve() in registered
    for rule in json.loads(named_tiers.RULES.read_bytes())['policies']:
        assert (named_tiers.ROOT / rule['source']['path']).resolve() in registered
