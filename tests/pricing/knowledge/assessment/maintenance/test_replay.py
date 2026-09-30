import json

from pricing.knowledge.assessment.maintenance.replay import ROOT, replay


def test_observation_replay_preserves_captured_facts_and_reports_base_use():
    path = ROOT / 'tests/inventory_tracking/fixtures/sacred_rondache_res27.json'
    raw = path.read_bytes()
    result = replay('sacred_rondache_res27')
    assert result['input_format'] == 'decoded_observation'
    assert result['extraction'] == json.loads(raw)
    assert 'Spirit / Paladin caster: needs sockets' in result['text']
    assert '+27 all resistances' in result['text']
    assert result['assessment']['facts']['sockets'] == 0
    assert path.read_bytes() == raw


def test_legacy_snapshot_replay_still_decodes_raw_item():
    result = replay('large_charm_life35')
    assert result['input_format'] == 'raw_snapshot'
    assert '+35 (6-35) to Life' in result['text']
