import pytest

from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand
from pricing.knowledge.assessment.maintenance.guide_inventory import compile_inventory
from pricing.knowledge.assessment.maintenance.review_dossiers import compile_dossiers
from tests.pricing.knowledge.assessment.maintenance.test_pattern_dossiers import pattern_fixture


def test_composite_charge_alternative_does_not_lend_demand_to_named_runeword():
    role, use, row = pattern_fixture()
    use['pattern_label'] = 'Staff of Teleportation or Harmony'
    row.update(
        name='Harmony',
        original_label=use['pattern_label'],
        category='runeword',
        details={'recommended': True, 'resolution_status': 'resolved'},
    )
    catalog = {'harmony': {'name': 'Harmony', 'category': 'runeword'}}
    inventory = compile_inventory([row], [role], catalog)
    (entry,) = compile_dossiers(inventory, [role], [use])['identities']
    assert entry['pattern_review_profile_ids'] == []
    assert entry['demand']['distinct_builds'] == 0


def test_reviewed_source_slot_mapping_keeps_runtime_use_slot_separate():
    role, use, row = pattern_fixture()
    row['slot'] = 'Other'
    # Source ledger links require exact slot, so a deliberate mapping is explicit.
    inventory = compile_inventory([row], [role], {})
    use['pattern_source_slot'] = 'Other'
    (entry,) = compile_dossiers(inventory, [role], [use])['identities']
    assert entry['reviewed_pattern_occurrence_ids'] == ['one']
    assert role['slot'] == 'Amulets'


@pytest.mark.parametrize('slot', [None, '', '  ', 5])
def test_invalid_source_slot_mapping_is_rejected(slot):
    role, use, _ = pattern_fixture()
    with pytest.raises(ValueError, match='Pattern source slot'):
        compile_demand([{**use, 'pattern_source_slot': slot}], [role])


def test_source_slot_override_does_not_allow_other_source_or_unverified_evidence():
    role, use, row = pattern_fixture()
    use['pattern_source_slot'] = 'Other'
    for change in ({'source_locator': '/other'}, {'source_status': 'changed'}, {'slot': 'Weapon'}):
        inventory = compile_inventory([{**row, 'slot': 'Other', **change}], [role], {})
        (entry,) = compile_dossiers(inventory, [role], [use])['identities']
        assert entry['reviewed_pattern_occurrence_ids'] == []
