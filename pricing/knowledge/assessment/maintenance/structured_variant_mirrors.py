"""Exact duplicate structured variant references, separate from HTML evidence."""

from pathlib import Path

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq
from pricing.knowledge.assessment.policies.sources import resolve_pointer
from pricing.knowledge.assessment.profile_sources import validate_profile_sources


KIND = 'structured_player_variant_mirror'


def validate_mirror(review, occurrence, role, uses, root, read_json):
    if (
        not occurrence
        or not role
        or fingerprint(occurrence) != review['occurrence_fingerprint']
        or fingerprint(role) != review['profile_fingerprint']
        or not isinstance(review.get('reason'), str)
        or not review['reason'].strip()
        or occurrence.get('source_status') != 'verified'
        or occurrence.get('details', {}).get('recommended') is not True
        or occurrence.get('identity_status') != 'unresolved'
        or occurrence.get('side') != 'player'
        or role.get('side') != 'player'
        or role.get('review_status') != 'reviewed_candidate_rule'
        or role.get('names')
        or any(occurrence.get(k) != role.get(k) for k in ('build', 'variant', 'slot'))
        or occurrence.get('original_label') != occurrence.get('name')
    ):
        raise ValueError('Invalid structured mirror context')
    source = role['source']
    parts = source['locator'].removeprefix('/').split('/')
    if (
        source['path'] != 'pricing/data/wp-a-builds.json'
        or len(parts) != 6
        or parts[:2] != [role['build'], 'variants']
        or parts[3] != 'player'
        or parts[4] != role['slot'].replace('~', '~0').replace('/', '~1')
        or any(not parts[i].isdecimal() or str(int(parts[i])) != parts[i] for i in (2, 5))
    ):
        raise ValueError('Structured mirror requires an exact primary variant equipment entry')
    mirror = review['mirror']
    locator = '/' + '/'.join(parts[1:])
    if (
        mirror['path'] != f'pricing/data/wp-a-variants/{role["build"]}.json'
        or occurrence['source_id'] != mirror['path']
        or occurrence['source_locator'] != locator
    ):
        raise ValueError('Structured mirror source or locator differs')
    validate_profile_sources({'profiles': [role]}, root, Path.read_bytes)
    primary, secondary = read_json(source)[role['build']], read_json(mirror)
    variant_index = int(parts[2])
    try:
        left, right = primary['variants'][variant_index], secondary['variants'][variant_index]
        klass = primary['class']
        label = resolve_pointer(secondary, locator)
        if (
            left != right
            or left['name'] != role['variant']
            or left.get('planner_only') is True
            or klass not in CLASS_NAMES
            or secondary['class'] != klass
            or occurrence.get('class', klass) != klass
            or secondary['slug'] != role['build']
            or primary['url'] != secondary['url']
            or label != occurrence['original_label']
            or not requires_eq(role.get('must', {}), 'context_eq', 'player_class', klass)
        ):
            raise ValueError('Structured mirror changed its full variant or equipment label')
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError('Structured mirror variant is missing or malformed') from exc
    endorsements = [
        u
        for u in uses
        if u['profile_id'] == role['id']
        and fingerprint(u) == review['use_fingerprint']
        and u.get('pattern') == role['id']
        and u.get('pattern_label') == label
        and u.get('review_state') == 'reviewed'
        and u.get('scope') == 'softcore'
        and u.get('strength') in ('required', 'preferred', 'alternative')
        and not u.get('historical')
        and not u.get('source_coverage')
    ]
    if len(endorsements) != 1:
        raise ValueError('Structured mirror lacks its exact reviewed endorsement')
    return {
        'occurrence_id': occurrence['id'],
        'profile_id': role['id'],
        'state': 'reviewed',
        'reason': review['reason'],
        'review_date': review['review_date'],
    }
