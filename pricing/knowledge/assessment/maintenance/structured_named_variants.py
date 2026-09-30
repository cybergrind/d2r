"""Bind decorated named-item entries to exact, reviewed variant configurations.

A label is not stripped to its named identity: explicit reviewed predicates must
remain mandatory. This records source coverage, never price or global discovery.
"""

from pathlib import Path

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.paired_swap_links import allows_slot, validate_pair
from pricing.knowledge.assessment.maintenance.planner_endorsement import validate_endorsement
from pricing.knowledge.assessment.maintenance.source_matching import requires, requires_eq
from pricing.knowledge.assessment.policies.sources import resolve_pointer
from pricing.knowledge.assessment.profile_sources import validate_profile_sources


KIND = 'structured_named_variant'


def _reviewed_role(review, role):
    if role.get('review_status') == 'reviewed_candidate_rule':
        return 'required_setup' not in review
    if role.get('review_status') != 'reviewed_setup' or role.get('side') != 'merc' or role.get('qualities') != ['set']:
        return False
    setup = review.get('required_setup')
    fields = {'required_rune', 'companions', 'mercenary_type'}
    if not isinstance(setup, dict) or set(setup) != fields or any(setup[key] != role.get(key) for key in fields):
        return False
    companions = setup['companions']
    return (
        isinstance(companions, list)
        and bool(companions)
        and all(isinstance(name, str) and name.strip() and name not in role['names'] for name in companions)
        and len(set(companions)) == len(companions)
        and isinstance(setup['required_rune'], str)
        and bool(setup['required_rune'].strip())
        and isinstance(setup['mercenary_type'], str)
        and requires_eq(role.get('must', {}), 'context_eq', 'mercenary_type', setup['mercenary_type'])
    )


def validate_link(review, occurrence, role, uses, root, read_json):
    identity_matches = bool(occurrence) and (
        (
            occurrence.get('identity_status') == 'unresolved'
            and occurrence.get('name') == occurrence.get('original_label')
        )
        or (
            occurrence.get('identity_status') == 'resolved'
            and occurrence.get('identity_basis') == 'canonical_name'
            and occurrence.get('name') == review.get('canonical_name')
        )
    )
    if (
        not occurrence
        or not role
        or fingerprint(occurrence) != review['occurrence_fingerprint']
        or fingerprint(role) != review['profile_fingerprint']
        or not isinstance(review.get('reason'), str)
        or not review['reason'].strip()
        or occurrence.get('kind') != 'demand'
        or occurrence.get('source_status') != 'verified'
        or occurrence.get('details', {}).get('recommended') is not True
        or not identity_matches
        or occurrence.get('side') not in ('player', 'merc')
        or any(occurrence.get(k) != role.get(k) for k in ('build', 'variant', 'side'))
        or (occurrence.get('slot') != role.get('slot') and not allows_slot(review, occurrence, role))
        or not _reviewed_role(review, role)
        or role.get('names') != [review.get('canonical_name')]
        or not isinstance(review.get('canonical_name'), str)
        or review['canonical_name'] not in occurrence['original_label']
    ):
        raise ValueError('Incompatible named variant context')
    predicates = review.get('required_predicates')
    if (
        not isinstance(predicates, list)
        or not predicates
        or not all(isinstance(p, dict) and bool(p) and requires(role.get('must'), p) for p in predicates)
    ):
        raise ValueError('Named variant lost mandatory reviewed predicates')
    socket = review.get('required_socket')
    if socket is not None and (
        not isinstance(socket, dict)
        or len(socket) != 1
        or not set(socket) <= {'required_rune', 'required_socket_item'}
        or any(
            not isinstance(value, str) or not value.strip() or role.get(key) != value for key, value in socket.items()
        )
    ):
        raise ValueError('Named variant lost its required socket item')
    dependencies = review.get('required_dependencies', [])
    if not isinstance(dependencies, list) or not all(
        isinstance(predicate, dict)
        and bool(predicate)
        and any(requires(dep.get('when'), predicate) for dep in role.get('depends_on', []))
        for predicate in dependencies
    ):
        raise ValueError('Named variant lost a required dependency')
    preferences = review.get('required_preferences', [])
    if not isinstance(preferences, list) or not all(
        isinstance(preference, dict) and bool(preference) and preference in role.get('preferences', [])
        for preference in preferences
    ):
        raise ValueError('Named variant lost a reviewed preference')
    conditions = review.get('required_conditions', [])
    if not isinstance(conditions, list) or not all(
        isinstance(condition, str) and bool(condition.strip()) and condition in role.get('conditions', [])
        for condition in conditions
    ):
        raise ValueError('Named variant lost a required qualification')
    source = role['source']
    parts = occurrence['source_locator'].removeprefix('/').split('/')
    if (
        source['path'] != 'pricing/data/wp-a-builds.json'
        or occurrence['source_id'] != source['path']
        or len(parts) != 6
        or parts[:2] != [role['build'], 'variants']
        or parts[3] != role['side']
        or parts[4] != occurrence['slot'].replace('~', '~0').replace('/', '~1')
        or any(not parts[i].isdecimal() or str(int(parts[i])) != parts[i] for i in (2, 5))
        or source['locator'] != '/' + '/'.join(parts[:3])
    ):
        raise ValueError('Named variant requires an exact structured equipment entry')
    validate_profile_sources({'profiles': [role]}, root, Path.read_bytes)
    document = read_json(source)
    variant = resolve_pointer(document, source['locator'])
    klass = document[role['build']]['class']
    label = resolve_pointer(document, occurrence['source_locator'])
    if socket and any(name not in label for name in socket.values()):
        raise ValueError('Named variant required socket item disagrees with source label')
    label_quote = review.get('source_label_quote', label)
    # Reviewed set setups store the exact decorated equipment entry separately
    # from the quoted full-set prose. Both remain bound to this pinned source.
    setup_label_matches = (
        role.get('review_status') == 'reviewed_setup' and role.get('setup_label') == label_quote == label
    )
    if role.get('review_status') == 'reviewed_setup':
        equipment = variant.get('merc', {})
        pieces = [item for items in equipment.values() if isinstance(items, list) for item in items]
        if (
            not setup_label_matches
            or role['required_rune'] not in label
            or equipment.get('type') != role['mercenary_type']
            or any(not any(companion in item for item in pieces) for companion in role['companions'])
        ):
            raise ValueError('Named set setup disagrees with source equipment')
    if (
        variant['name'] != role['variant']
        or 'hardcore' in variant['name'].casefold()
        or klass not in CLASS_NAMES
        or occurrence.get('class') != klass
        or not requires_eq(role.get('must', {}), 'context_eq', 'player_class', klass)
        or label != occurrence['original_label']
        or not isinstance(label_quote, str)
        or (label_quote not in source.get('quotes', []) and not setup_label_matches)
        or label not in label_quote
    ):
        raise ValueError('Named variant source label or context changed')
    if 'paired_swap' in review:
        validate_pair(review, occurrence, role, variant, klass, label)
    if variant.get('planner_only') is True:
        validate_endorsement(review, role, document[role['build']], root, read_json)
    endorsed = [
        u
        for u in uses
        if u['profile_id'] == role['id']
        and fingerprint(u) == review['use_fingerprint']
        and u.get('profile_fingerprint') == fingerprint(role)
        and u.get('source') == source
        and all(u.get(k) == role.get(k) for k in ('build', 'variant', 'side'))
        and u.get('item') == review['canonical_name']
        and u.get('review_state') == 'reviewed'
        and u.get('scope') == 'softcore'
        and u.get('strength') in ('required', 'preferred', 'alternative')
        and not u.get('historical')
        and not u.get('source_coverage')
    ]
    if len(endorsed) != 1:
        raise ValueError('Named variant lacks its exact reviewed endorsement')
    return {
        'occurrence_id': occurrence['id'],
        'profile_id': role['id'],
        'state': 'reviewed',
        'reason': review['reason'],
        'review_date': review['review_date'],
    }
