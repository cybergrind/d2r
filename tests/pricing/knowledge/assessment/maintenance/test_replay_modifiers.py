import json

from pricing.knowledge.assessment.maintenance import replay as replay_module


def test_replay_recovers_owned_weapon_ed_when_precomputed_copy_is_absent(tmp_path, monkeypatch):
    source = replay_module.ROOT / 'tests/inventory_tracking/fixtures/superior_phase_blade.json'
    saved = json.loads(source.read_text())
    row = saved['snapshot']['resources']['items'][0]
    row['resource_stats'].pop('damage_modifiers')
    destination = tmp_path / 'tests/inventory_tracking/fixtures/superior_phase_blade.json'
    destination.parent.mkdir(parents=True)
    destination.write_text(json.dumps(saved))
    monkeypatch.setattr(replay_module, 'ROOT', tmp_path)
    result = replay_module.replay('superior_phase_blade')
    ed = [r for r in result['extraction']['decoded_stats'] if r.get('name') == 'item_damage_percent']
    assert len(ed) == 1
    assert ed[0]['value'] == 14
    assert ed[0]['origin'] == 'owned_modifier_list'
    assert result['assessment']['contract'] is not None


def test_replay_never_uses_another_units_weapon_ed(tmp_path, monkeypatch):
    source = replay_module.ROOT / 'tests/inventory_tracking/fixtures/superior_phase_blade.json'
    saved = json.loads(source.read_text())
    row = saved['snapshot']['resources']['items'][0]
    row['resource_stats'].pop('damage_modifiers')
    row['unit_id'] += 1
    destination = tmp_path / 'tests/inventory_tracking/fixtures/superior_phase_blade.json'
    destination.parent.mkdir(parents=True)
    destination.write_text(json.dumps(saved))
    monkeypatch.setattr(replay_module, 'ROOT', tmp_path)
    result = replay_module.replay('superior_phase_blade')
    assert result['assessment']['contract'] is None
    assert not any(r.get('origin') == 'owned_modifier_list' for r in result['extraction']['decoded_stats'])
