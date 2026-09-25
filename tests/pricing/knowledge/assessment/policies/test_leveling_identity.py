from dataclasses import replace

from pricing.knowledge.assessment.handlers.definitions import named_definitions
from pricing.knowledge.assessment.policies.leveling import assess_leveling
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_same_slot_wrong_base_does_not_inherit_named_leveling_recommendation():
    assert assess_leveling(facts('Light Gauntlets', 'unique', 'Bloodfist')) == []
    assert assess_leveling(facts('Heavy Gloves', 'set', "Death's Hand")) == []


def test_leveling_rejects_conflicting_captured_table_identity():
    item = replace(
        facts('Heavy Gloves', 'unique', 'Bloodfist'),
        provenance={'capture': {'item_identity': {'table': 'unique', 'table_id': -1}}},
    )
    assert assess_leveling(item) == []


def test_verified_upgraded_leveling_candidate_requires_variant_requirements_review():
    item = facts('Sharkskin Gloves', 'unique', 'Bloodfist')
    assert assess_leveling(item) == []
    definition = named_definitions()['unique', 'Bloodfist']
    item = replace(
        item, provenance={'capture': {'item_identity': {'table': 'unique', 'table_id': definition['table_id']}}}
    )
    use = assess_leveling(item, loadout={'player_level': 99})[0]
    assert use['tier'] == 'high'
    assert use['status'] == 'conditional'
    assert use['required_level'] is None
    assert use['requirements_fit']['status'] == 'unknown'
    assert any('requirements' in condition for condition in use['conditions'])


def test_upgraded_set_keeps_companion_and_requirement_conditions_in_report():
    from inventory_tracking.appraisal.sections import leveling_lines

    definition = named_definitions()['set', "Death's Hand"]
    item = replace(
        facts('Demonhide Gloves', 'set', "Death's Hand"),
        provenance={'capture': {'item_identity': {'table': 'set', 'table_id': definition['table_id']}}},
    )
    uses = assess_leveling(item)
    assert uses
    assert uses[0]['status'] == 'conditional'
    assert uses[0]['required_level'] is None
    assert any("Death's Guard" in condition for condition in uses[0]['conditions'])
    report = '\n'.join(leveling_lines({'assessment': {'leveling': uses}}))
    assert "Death's Guard" in report
    assert 'Equip requirements for this variant' in report
    assert 'equip level 6' not in report
