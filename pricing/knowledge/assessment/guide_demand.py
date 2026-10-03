"""Prepared identity demand from the pinned profile bundle; never infer item fit."""

import json
from copy import deepcopy
from functools import lru_cache

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.build_profiles import OUTPUT


@lru_cache(maxsize=2)
def _prepared_summaries(raw):
    """Retain only demand summaries, keyed by the exact pinned source bytes."""
    return json.loads(raw).get('guide_demand', {}).get('summaries', {})


def _summaries(document):
    if document is not None:
        return document.get('guide_demand', {}).get('summaries', {})
    return _prepared_summaries(read_artifact(OUTPUT))


def demand_for(name, document=None):
    return deepcopy(_summaries(document).get(name))


def demand_for_item(name, roles, document=None):
    """Select prepared demand only after a complete item predicate succeeds.

    Loadout dependencies may remain conditional; false/unknown item predicates
    never contribute. Exact profile IDs keep incompatible combinations separate.
    """
    from pricing.knowledge.assessment.demand_counts import summarize_demand

    summaries = _summaries(document)
    named = deepcopy(summaries.get(name))
    if named is not None:
        return named
    eligible = {
        r['id']
        for r in roles
        if (r.get('rule_trace') or {}).get('truth') == 'true' and r.get('status') in {'matched', 'partial'}
    }
    patterns = {
        key: deepcopy(value)
        for key, value in summaries.items()
        if value.get('scope') == 'pattern' and eligible.intersection(value['profile_ids']) and value['distinct_builds']
    }
    if not patterns:
        return None
    uses = [
        {**context, 'review_state': 'reviewed', 'scope': 'softcore'}
        for summary in patterns.values()
        for context in summary['contexts']
    ]
    result = summarize_demand(uses, complete=False)
    result['scope'] = 'matched_patterns'
    result['patterns'] = sorted(patterns)
    result['role_presentation'] = {
        key: value for summary in patterns.values() for key, value in summary.get('role_presentation', {}).items()
    }
    return result


def validate_demand(document):
    from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand

    if 'guide_demand' not in document:
        return
    data = document['guide_demand']
    expected = compile_demand(data['uses'], document['profiles'])
    if expected != data['summaries']:
        raise ValueError('Published guide demand differs from reviewed uses')
