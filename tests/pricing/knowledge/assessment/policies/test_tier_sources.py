import hashlib
import json

from pricing.knowledge.assessment.policies import named_tiers
from tests.pricing.knowledge.assessment.policies.test_named_tiers import traveler


def test_runtime_tier_invalidates_changed_source_and_recovers_after_review(tmp_path, monkeypatch):
    policy = next(p for p in json.loads(named_tiers.RULES.read_text())['policies'] if p['name'] == 'War Traveler')
    source = tmp_path / 'evidence.json'
    source.write_text(json.dumps({'record': {'name': 'War Traveler', 'type': 'unique'}}))
    rules = tmp_path / 'rules.json'

    def publish(locator='/record'):
        policy['source'].update(
            path='evidence.json', sha256=hashlib.sha256(source.read_bytes()).hexdigest(), locator=locator
        )
        rules.write_text(json.dumps({'schema_version': 1, 'policies': [policy]}))

    publish()
    monkeypatch.setattr(named_tiers, 'ROOT', tmp_path, raising=False)
    monkeypatch.setattr(named_tiers, 'RULES', rules)
    assert named_tiers.assess_tier(traveler(50))['tier'] == 'high'
    source.write_text(json.dumps({'record': {'name': 'War Traveler', 'type': 'unique', 'revised': True}}))
    stale = named_tiers.assess_tier(traveler(50))
    assert stale['tier'] is None
    assert 'fingerprint' in stale['source_error'].lower()
    publish()
    assert named_tiers.assess_tier(traveler(50))['tier'] == 'high'
    publish('/wrong')
    assert named_tiers.assess_tier(traveler(50))['tier'] is None
    publish()
    source.unlink()
    assert named_tiers.assess_tier(traveler(50))['tier'] is None


def test_runtime_checks_source_identity_even_with_matching_hash(tmp_path, monkeypatch):
    policy = next(p for p in json.loads(named_tiers.RULES.read_text())['policies'] if p['name'] == 'War Traveler')
    source = tmp_path / 'evidence.json'
    source.write_text(json.dumps({'record': {'name': 'Different Item', 'type': 'unique'}}))
    policy['source'].update(
        path='evidence.json', sha256=hashlib.sha256(source.read_bytes()).hexdigest(), locator='/record'
    )
    rules = tmp_path / 'rules.json'
    rules.write_text(json.dumps({'schema_version': 1, 'policies': [policy]}))
    monkeypatch.setattr(named_tiers, 'ROOT', tmp_path)
    monkeypatch.setattr(named_tiers, 'RULES', rules)
    result = named_tiers.assess_tier(traveler(50))
    assert result['tier'] is None
    assert 'identify' in result['source_error']
