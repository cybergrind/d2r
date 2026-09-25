"""Explicit source variant dispositions for the Softcore guide census."""

import re
from copy import deepcopy


def variant_contexts(document, source, *, prefix=''):
    rows = []
    for ordinal, variant in enumerate(document.get('variants', [])):
        hardcore = bool(re.match(r'^Hardcore\b', variant['name'], re.I))
        rows.append(
            {
                'source_id': source,
                'locator': f'{prefix}/variants/{ordinal}',
                'build': document['slug'],
                'variant': variant['name'],
                'demand_eligibility': 'excluded_hardcore'
                if hardcore
                else 'planner_endorsement_review'
                if variant.get('planner_only') is True
                else 'requires_review',
                'scope_basis': 'Explicit Hardcore variant title' if hardcore else 'No reviewed endorsement inferred',
                'inheritance_status': 'unresolved_delta' if variant.get('delta_only') is True else 'not_declared',
                'parent_variant': None,
                'evidence': {k: deepcopy(v) for k, v in variant.items() if k not in {'player', 'merc'}},
            }
        )
    return rows
