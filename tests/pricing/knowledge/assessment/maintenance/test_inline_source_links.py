from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import compile_inventory
from pricing.knowledge.assessment.maintenance.review_dossiers import compile_dossiers
from tests.pricing.knowledge.assessment.maintenance.test_guide_inventory import occurrence, profile
from tests.pricing.knowledge.assessment.maintenance.test_review_dossiers import reviewed


HTML = 'pricing/raw/mr/guides__zeal-paladin.html'
LOCATOR = '/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/162'


def inline_review():
    role = profile(
        names=[],
        qualities=['rare'],
        variant='Guide mention',
        side='player',
        slot='Rings',
        source={'path': 'pricing/data/appraisal-guide-sections.json', 'locator': LOCATOR, 'sha256': 'pinned'},
    )
    row = occurrence(
        name='Rare Ring',
        original_label='Rare Ring',
        category=None,
        variant='Guide mention',
        side='player',
        slot='Rings',
        source_id=HTML,
        source_locator='/item-spans/162',
        source_status='verified',
        details={'recommended': True, 'resolution_status': 'unresolved'},
    )
    return role, row


def dossier(role, row):
    use = reviewed(role, pattern=role['id'], pattern_label='Rare Ring')
    del use['item']
    inventory = compile_inventory([row], [role], {})
    result = compile_dossiers(inventory, [role], [use])
    return inventory, result['identities'][0]


def test_exact_cached_inline_reference_links_its_original_guide_occurrence():
    role, row = inline_review()
    saved = deepcopy(row)
    inventory, result = dossier(role, row)
    assert inventory['occurrences'][0]['source_rule_ids'] == [role['id']]
    assert result['pattern_review_profile_ids'] == [role['id']]
    assert result['reviewed_pattern_occurrence_ids'] == [row['id']]
    assert result['demand']['distinct_builds'] == 1
    assert result['review_state'] == 'pending'
    assert inventory['complete'] is False
    assert row == saved


@pytest.mark.parametrize(
    'patch',
    [
        {'locator': LOCATOR.replace('/162', '/163')},
        {'locator': LOCATOR.replace('/item_spans/162', '/sections/32')},
        {'locator': LOCATOR.rsplit('/', 1)[0]},
        {'locator': LOCATOR + '/label'},
        {'path': 'other-cache.json'},
    ],
)
def test_inline_link_never_inherits_neighbour_or_whole_section_review(patch):
    role, row = inline_review()
    role['source'].update(patch)
    inventory, result = dossier(role, row)
    assert not inventory['occurrences'][0]['source_rule_ids']
    assert not result['pattern_review_profile_ids']
    assert result['demand']['distinct_builds'] == 0


@pytest.mark.parametrize(
    'patch',
    [
        {'variant': 'Other variant'},
        {'side': 'merc'},
        {'slot': 'Amulets'},
        {'source_status': 'unverified'},
        {'details': {'recommended': False}},
    ],
)
def test_inline_link_preserves_context_verification_and_endorsement_gates(patch):
    role, row = inline_review()
    row.update(patch)
    _, result = dossier(role, row)
    assert not result['pattern_review_profile_ids']
    assert result['demand']['distinct_builds'] == 0
