from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand
from pricing.knowledge.assessment.maintenance.guide_inventory import compile_inventory, fingerprint
from pricing.knowledge.assessment.maintenance.review_dossiers import compile_dossiers, expand_dossier
from tests.pricing.knowledge.assessment.maintenance.test_pattern_dossiers import pattern_fixture


def component_fixture():
    role, use, row = pattern_fixture()
    role['types'] = ['jewl']
    use['profile_fingerprint'] = fingerprint(role)
    use['pattern_label'] = "Andariel's Visage (ethereal, 15% IAS / 30% Fire Resist Jewel)"
    use['pattern_component'] = {'kind': 'socket_jewel', 'text': '15% IAS / 30% Fire Resist Jewel'}
    row.update(
        name="Andariel's Visage",
        original_label=use['pattern_label'],
        category='unique',
        details={'recommended': True, 'resolution_status': 'resolved'},
    )
    catalog = {'andy': {'name': "Andariel's Visage", 'category': 'unique'}}
    return role, use, row, catalog


def test_socket_jewel_review_is_separate_from_recipient_identity_demand():
    role, use, row, catalog = component_fixture()
    inventory = compile_inventory([row], [role], catalog)
    document = compile_dossiers(inventory, [role], [use])
    (entry,) = document['identities']
    assert entry['demand']['distinct_builds'] == 0
    assert entry['pattern_review_profile_ids'] == []
    assert entry['guide_review_profile_ids'] == []
    assert document['counts']['occurrences'] == 1
    (component,) = entry['component_reviews']
    assert component['profile_id'] == role['id']
    assert component['occurrence_ids'] == ['one']
    assert component['kind'] == 'socket_jewel'
    assert component['text'] == use['pattern_component']['text']
    expanded = expand_dossier(document, inventory, entry['identity_id'])
    assert component['configuration_id'] in {c['id'] for c in expanded['configurations']}


@pytest.mark.parametrize('change', [{'source_locator': '/other'}, {'source_status': 'changed'}, {'slot': 'Other'}])
def test_socket_component_requires_exact_verified_occurrence(change):
    role, use, row, catalog = component_fixture()
    inventory = compile_inventory([{**row, **change}], [role], catalog)
    (entry,) = compile_dossiers(inventory, [role], [use])['identities']
    assert entry['component_reviews'] == []


@pytest.mark.parametrize(
    'component',
    [
        None,
        {},
        {'kind': 'socket_jewel', 'text': 'not in source'},
        {'kind': 'staff', 'text': '15% IAS / 30% Fire Resist Jewel'},
        {'kind': 'socket_jewel', 'text': ''},
    ],
)
def test_socket_component_rejects_invalid_or_unquoted_witness(component):
    role, use, _, _ = component_fixture()
    with pytest.raises(ValueError, match='component'):
        compile_demand([{**use, 'pattern_component': component}], [role])


def test_socket_component_cannot_be_attached_to_non_jewel_profile():
    role, use, _, _ = component_fixture()
    role['types'] = ['staf']
    use['profile_fingerprint'] = fingerprint(role)
    with pytest.raises(ValueError, match='component'):
        compile_demand([use], [role])


def test_unreviewed_component_is_not_bound():
    role, use, row, catalog = component_fixture()
    use = deepcopy(use)
    use['review_state'] = 'pending'
    inventory = compile_inventory([row], [role], catalog)
    (entry,) = compile_dossiers(inventory, [role], [use])['identities']
    assert entry['component_reviews'] == []


def test_socket_jewel_cannot_be_a_completed_runeword_component():
    role, use, row, _ = component_fixture()
    use['pattern_label'] = 'Harmony (15% IAS / 30% Fire Resist Jewel)'
    row.update(name='Harmony', category='runeword', original_label=use['pattern_label'])
    inventory = compile_inventory([row], [role], {'harmony': {'name': 'Harmony', 'category': 'runeword'}})
    (entry,) = compile_dossiers(inventory, [role], [use])['identities']
    assert entry['component_reviews'] == []
    assert entry['pattern_review_profile_ids'] == []
    assert entry['demand']['distinct_builds'] == 0
