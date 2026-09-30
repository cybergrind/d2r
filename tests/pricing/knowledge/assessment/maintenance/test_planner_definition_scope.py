"""Approved dormant planner definitions exclude only their own source mentions."""

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.planner_definition_scope import definition_exclusions
from pricing.knowledge.assessment.maintenance.value_scope import SCOPE


PLANNER = 'pricing/raw/mr/planners/ab01cd23.json'
UNREFERENCED = 'Unreferenced definitions'


def occurrence(oid, locator, **extra):
    return {
        'id': oid,
        'variant': UNREFERENCED,
        'source_id': PLANNER,
        'source_locator': locator,
        'source_status': 'verified',
        'identity_id': 'identity-' + oid,
        **extra,
    }


def inputs():
    occurrences = [
        occurrence('dormant', '/items/7'),
        occurrence('dormant-child', '/items/7/socketedItems/1'),
        occurrence('reachable', '/items/3'),
        occurrence('claimed', '/items/8'),
        occurrence('profile', '/profiles/0/items/head', variant='Standard'),
        occurrence('unverified', '/items/9', source_status='missing'),
        occurrence('other-planner', '/items/7', source_id='pricing/raw/mr/planners/zz.json'),
        occurrence('odd-locator', '/items/7/notes'),
    ]
    inventory = {'occurrences': occurrences}
    audit = {
        'schema_version': 1,
        'inventory_fingerprint': fingerprint(inventory),
        'guide_issues': [],
        'source_issues': [],
        'planner_reports': {
            PLANNER: {'reachable': ['3'], 'unreachable_candidates': ['7', '8', '9'], 'issues': []},
            'pricing/raw/mr/planners/zz.json': {'reachable': [], 'unreachable_candidates': [], 'issues': [{}]},
        },
    }
    review = {
        'schema_version': 1,
        'scope': SCOPE,
        'planner_definitions': {
            'classification': 'unreachable_planner_definition',
            'approved_by': 'user',
            'approved_at': '2026-09-30',
            'reason': 'Planner item definitions placed in no profile and linked by no guide; identities stay in scope.',
        },
    }
    return review, audit, inventory


def test_only_unclaimed_dormant_definitions_are_excluded():
    review, audit, inventory = inputs()
    result = definition_exclusions(review, audit, inventory, {'claimed'})
    assert set(result) == {'dormant', 'dormant-child'}
    row = result['dormant-child']
    assert row['state'] == 'excluded'
    assert row['source'] == {'artifact': 'value_scope', 'locator': '/planner_definitions'}
    assert row['identity_id'] == 'identity-dormant-child'
    assert row['source_locator'] == '/items/7/socketedItems/1'


def test_without_approval_nothing_is_excluded():
    review, audit, inventory = inputs()
    del review['planner_definitions']
    assert definition_exclusions(review, audit, inventory, set()) == {}
    assert definition_exclusions(None, audit, inventory, set()) == {}


@pytest.mark.parametrize(
    'mutation', ['stale-audit', 'guide-issues', 'source-issues', 'approver', 'date', 'kind', 'reason']
)
def test_invalid_approval_or_incomplete_audit_is_rejected(mutation):
    review, audit, inventory = inputs()
    approval = review['planner_definitions']
    if mutation == 'stale-audit':
        inventory['occurrences'].append(occurrence('new', '/items/1'))
    elif mutation == 'guide-issues':
        audit['guide_issues'] = [{'kind': 'missing_planner'}]
    elif mutation == 'source-issues':
        audit['source_issues'] = [{'source': 'x.html'}]
    elif mutation == 'approver':
        approval['approved_by'] = 'agent'
    elif mutation == 'date':
        approval['approved_at'] = 'today'
    elif mutation == 'kind':
        approval['classification'] = 'generic_leveling'
    elif mutation == 'reason':
        approval['reason'] = ''
    with pytest.raises(ValueError, match=r'(?i)planner|isoformat'):
        definition_exclusions(review, audit, inventory, set())
