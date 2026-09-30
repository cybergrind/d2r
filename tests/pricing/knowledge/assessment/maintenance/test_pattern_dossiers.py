from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand
from pricing.knowledge.assessment.maintenance.guide_inventory import compile_inventory
from pricing.knowledge.assessment.maintenance.review_dossiers import compile_dossiers
from tests.pricing.knowledge.assessment.maintenance.test_guide_inventory import occurrence, profile
from tests.pricing.knowledge.assessment.maintenance.test_review_dossiers import reviewed


def pattern_fixture():
    role = profile(names=[], qualities=['magic'], slot='Amulets')
    use = reviewed(role, pattern=role['id'], pattern_label='Amulet of Teleportation')
    del use['item']
    row = occurrence(
        name=use['pattern_label'],
        original_label=use['pattern_label'],
        category=None,
        slot=role['slot'],
        source_status='verified',
        details={'recommended': True, 'resolution_status': 'pattern_or_unresolved'},
    )
    return role, use, row


def test_pattern_review_is_bound_to_one_occurrence_not_every_same_label():
    role, use, row = pattern_fixture()
    other = {**row, 'id': 'elsewhere', 'source_locator': '/items/1'}
    inventory = compile_inventory([row, other], [role], {})
    before = deepcopy(inventory)
    result = compile_dossiers(inventory, [role], [use])
    (entry,) = result['identities']
    assert entry['pattern_review_profile_ids'] == [role['id']]
    assert entry['reviewed_pattern_occurrence_ids'] == ['one']
    assert entry['guide_review_profile_ids'] == []
    assert entry['demand']['distinct_builds'] == 1
    assert entry['category'] == 'unresolved'
    assert entry['review_state'] == 'pending'
    assert entry['next_action'] == 'review_remaining_pattern_occurrences'
    assert result['review_queues']['bases_and_patterns'] == [entry['identity_id']]
    assert inventory == before


@pytest.mark.parametrize(
    'changes',
    [
        {'source_status': 'changed'},
        {'source_id': 'other.json'},
        {'source_locator': '/items/1'},
        {'slot': 'Weapon'},
        {'build': 'other'},
        {'variant': 'Hardcore'},
        {'side': 'player'},
        {'original_label': 'Other label'},
        {'details': {'recommended': False}},
        {'details': {'historical': True}},
    ],
)
def test_pattern_review_never_spills_into_incompatible_evidence(changes):
    role, use, row = pattern_fixture()
    inventory = compile_inventory([{**row, **changes}], [role], {})
    (entry,) = compile_dossiers(inventory, [role], [use])['identities']
    assert entry['pattern_review_profile_ids'] == []
    assert entry['reviewed_pattern_occurrence_ids'] == []
    assert entry['demand']['distinct_builds'] == 0


@pytest.mark.parametrize('label', ['', '   ', None, 123])
def test_pattern_label_requires_nonempty_text(label):
    role, use, _ = pattern_fixture()
    with pytest.raises(ValueError, match='Pattern label'):
        compile_demand([{**use, 'pattern_label': label}], [role])


def test_named_review_cannot_claim_a_pattern_label():
    role = profile()
    with pytest.raises(ValueError, match='Pattern label'):
        compile_demand([reviewed(role, pattern_label='Insight')], [role])


@pytest.mark.parametrize(
    'changes',
    [
        {'review_state': 'discovery_only'},
        {'historical': True},
        {'strength': 'mention'},
    ],
)
def test_unreviewed_or_out_of_scope_use_cannot_bind_pattern_occurrences(changes):
    role, use, row = pattern_fixture()
    inventory = compile_inventory([row], [role], {})
    (entry,) = compile_dossiers(inventory, [role], [{**use, **changes}])['identities']
    assert entry['reviewed_pattern_occurrence_ids'] == []
    assert entry['demand']['distinct_builds'] == 0


@pytest.mark.parametrize(('field', 'value'), [('scope', 'hardcore'), ('season', 'ladder')])
def test_out_of_scope_pattern_review_must_agree_with_its_profile(field, value):
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint

    role, use, row = pattern_fixture()
    inventory = compile_inventory([row], [role], {})
    with pytest.raises(ValueError, match='disagrees with reviewed profile'):
        compile_dossiers(inventory, [role], [{**use, field: value}])

    # A coherent archived review remains readable but contributes no SC/NL demand.
    role[field] = value
    use.update({field: value, 'profile_fingerprint': fingerprint(role)})
    inventory = compile_inventory([row], [role], {})
    (entry,) = compile_dossiers(inventory, [role], [use])['identities']
    assert entry['reviewed_pattern_occurrence_ids'] == []
    assert entry['demand']['distinct_builds'] == 0
