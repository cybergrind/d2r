"""Compile explicit stat-priority reviews against unchanged executable roles."""

import hashlib
from datetime import date
from pathlib import Path

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.stat_evaluation import StatConfiguration, StatPriority


def compile_stat_configurations(reviews, profiles, *, root=None):
    by_id = {p['id']: p for p in profiles}
    if len(by_id) != len(profiles):
        raise ValueError('Duplicate role identities')
    compiled = {}
    root = Path(root).resolve() if root is not None else None
    for review in reviews:
        role = by_id.get(review['role_id'])
        if not role or review.get('profile_fingerprint') != fingerprint(role):
            raise ValueError(f'Stale stat review: {review["role_id"]}')
        if not role.get('must') or not role.get('types'):
            raise ValueError('Stat compiler requires an explicit role predicate and base types')
        source = role['source']
        if root is not None:
            path = (root / source['path']).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError('Missing or out-of-scope stat source')
            if hashlib.sha256(path.read_bytes()).hexdigest() != source['sha256']:
                raise ValueError('Changed stat source')
        date.fromisoformat(review['review_date'])
        advisory = review.get('advisory_conditions', [])
        if not isinstance(advisory, list) or any(v not in role.get('conditions', ()) for v in advisory):
            raise ValueError('Advisory review must name exact role conditions')
        config = StatConfiguration(
            id=review['id'],
            version=review['version'],
            role_id=role['id'],
            qualities=tuple(role['qualities']),
            types=tuple(role['types']),
            required=identity_bound_requirement(role),
            priorities=tuple(StatPriority(**priority) for priority in review['priorities']),
            source={
                **source,
                'stat_review_date': review['review_date'],
                'profile_fingerprint': review['profile_fingerprint'],
            },
            review_state=review['review_state'],
            rationale=review['rationale'],
            advisory_conditions=tuple(advisory),
        )
        if config.id in compiled:
            raise ValueError(f'Duplicate stat configuration: {config.id}')
        compiled[config.id] = config
    return tuple(compiled[key] for key in sorted(compiled))


def identity_bound_requirement(role):
    """Keep named selectors in the stat gate, even when evaluated outside the index."""
    names = role.get('names')
    if not names:
        return role['must']
    if not isinstance(names, list) or any(not isinstance(n, str) or not n.strip() for n in names):
        raise ValueError('Stat compiler requires explicit valid item names')
    return {
        'all': [
            {'any': [{'op': 'fact_eq', 'field': 'name', 'value': name} for name in names]},
            role['must'],
        ]
    }
