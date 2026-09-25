from dataclasses import replace

from pricing.knowledge.assessment.engine import assess_result
from pricing.knowledge.assessment.maintenance.replay import replay


def test_saved_set_upgrade_preserves_flat_defense_and_enumerates_base_rolls():
    result = assess_result(replay('sazabi_mental_sheath')['extraction'], profiles=[])
    (path,) = result.upgrades
    outcome = path.to_dict().get('defense_outcome')
    assert outcome is not None
    assert outcome['min'] == 210
    assert outcome['max'] == 254
    assert outcome['possible_values'] == list(range(210, 255))
    assert outcome['flat_defense'] == 100
    assert result.facts.stats['31:0']['value'] == 177


def test_guardian_upgrade_uses_captured_ed_with_random_target_base():
    item = replay('guardian_angel')['extraction']
    item['item'].update(sockets=0, socket_contents='empty', filled_sockets=0, empty_sockets=0, socket_items=[])
    result = assess_result(item, profiles=[])
    assert result.contract is not None, result.price_gaps
    outcome = result.upgrades[0].to_dict().get('defense_outcome')
    assert outcome is not None
    assert (outcome['min'], outcome['max']) == (1208, 1521)
    assert outcome['enhanced_defense_percent'] == 187
    assert outcome['possible_values'] == sorted({base * 287 // 100 for base in range(421, 531)})
    assert 1209 not in outcome['possible_values']
    assert result.contract.properties['1855'] == 789


def test_unverified_socket_or_ethereal_outcome_does_not_get_a_defense_range():
    from pricing.knowledge.assessment.mechanics.upgrade_defense import with_defense_outcomes

    result = assess_result(replay('guardian_angel')['extraction'], profiles=[])
    assert all(path.defense_outcome is None for path in result.upgrades)
    known = assess_result(replay('sazabi_mental_sheath')['extraction'], profiles=[])
    bare = tuple(replace(path, defense_outcome=None) for path in known.upgrades)
    for facts in (replace(known.facts, ethereal=None), replace(known.facts, ethereal=True)):
        assert all(path.defense_outcome is None for path in with_defense_outcomes(facts, known.contract, bare))
