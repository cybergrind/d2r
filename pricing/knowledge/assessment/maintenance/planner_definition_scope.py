"""User-approved exclusion of dormant planner item definitions from source review.

A maxroll planner stores item definitions under `/items/<id>`; profiles and guide links
place some of them. `planner_source_audit.py` lists the rest as `unreachable_candidates`
per planner when every guide and source was read. The user approved excluding those
dormant definitions on 2026-09-30 (`planner_definitions` in value_scope_reviews.json).

Excludes only an unclaimed 'Unreferenced definitions' occurrence whose root definition is
a candidate of a planner report without issues, from an audit pinned to this inventory.
A definition that is placed or linked anywhere, a planner with issues, and every item
identity stay in scope.
"""

import re
from datetime import date

from pricing.knowledge.assessment.maintenance.value_scope import SCOPE


UNREFERENCED = 'Unreferenced definitions'
DEFINITION = re.compile(r'/items/([^/]+)(?:/socketedItems/\d+)*')


def definition_exclusions(review, audit, inventory, taken):
    """Occurrence id → exclusion; `taken` ids keep their other disposition."""
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint

    approval = (review or {}).get('planner_definitions')
    if approval is None:
        return {}
    if review.get('schema_version') != 1 or review.get('scope') != SCOPE:
        raise ValueError('Unsupported planner definition scope review')
    if (
        approval.get('classification') != 'unreachable_planner_definition'
        or approval.get('approved_by') != 'user'
        or not isinstance(approval.get('reason'), str)
        or not approval['reason'].strip()
    ):
        raise ValueError('Planner definition exclusion needs an explicit user approval and reason')
    date.fromisoformat(approval.get('approved_at', ''))
    if audit is None or audit.get('schema_version') != 1:
        raise ValueError('Planner definition exclusion needs the planner reachability audit')
    if audit.get('inventory_fingerprint') != fingerprint(inventory):
        raise ValueError('Stale planner reachability audit for definition exclusion')
    if audit.get('guide_issues') or audit.get('source_issues'):
        raise ValueError('Unread guides or sources leave planner definition absence unproven')
    candidates = {
        source: set(report['unreachable_candidates'])
        for source, report in audit['planner_reports'].items()
        if not report['issues']
    }
    disposition = {
        'state': 'excluded',
        'reason': approval['reason'],
        'source': {'artifact': 'value_scope', 'locator': '/planner_definitions'},
    }
    result = {}
    for row in inventory['occurrences']:
        if row['id'] in taken or row.get('variant') != UNREFERENCED or row.get('source_status') != 'verified':
            continue
        match = DEFINITION.fullmatch(row.get('source_locator', ''))
        if match is None or match.group(1) not in candidates.get(row.get('source_id'), ()):
            continue
        result[row['id']] = {
            'id': row['id'],
            **disposition,
            'source_id': row['source_id'],
            'source_locator': row['source_locator'],
            'identity_id': row.get('identity_id'),
        }
    return result
