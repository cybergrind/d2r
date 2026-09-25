"""Source-checked coverage exclusions, never runtime valuation or stat rules."""

import hashlib
from datetime import date
from pathlib import Path

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint


def validate_stat_dispositions(reviews, profiles, *, root):
    roles = {role['id']: role for role in profiles['profiles']}
    if len(roles) != len(profiles['profiles']):
        raise ValueError('Duplicate role identities')
    configured = {row['role_id'] for row in profiles.get('stat_evaluation', {}).get('configurations', [])}
    root = Path(root).resolve()
    result = {}
    for index, review in enumerate(reviews):
        role_id = review['role_id']
        role = roles.get(role_id)
        if role_id in result:
            raise ValueError('Duplicate stat disposition')
        if not role or review.get('profile_fingerprint') != fingerprint(role):
            raise ValueError(f'Stale stat disposition: {role_id}')
        if role_id in configured or role.get('important_stats'):
            raise ValueError(f'Stat disposition conflicts with priorities: {role_id}')
        if role.get('review_status') != 'reviewed_candidate_rule':
            raise ValueError('Stat disposition requires a reviewed role')
        if review.get('disposition') != 'no_stat_priority':
            raise ValueError('Unsupported stat disposition')
        reason = review.get('reason')
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError('Stat disposition requires a reason')
        date.fromisoformat(review['review_date'])
        source = role['source']
        if not source.get('locator'):
            raise ValueError('Stat disposition requires an exact source locator')
        path = (root / source['path']).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError('Missing or out-of-scope stat disposition source')
        if hashlib.sha256(path.read_bytes()).hexdigest() != source['sha256']:
            raise ValueError('Changed stat disposition source')
        result[role_id] = {
            'state': 'excluded',
            'reason': reason,
            'sources': [
                {
                    'artifact': 'stat_dispositions',
                    'locator': f'/{index}',
                    'evidence': dict(source),
                    'profile_fingerprint': review['profile_fingerprint'],
                    'review_date': review['review_date'],
                }
            ],
        }
    return result
