"""Resolve reviewed label collections without collapsing their configurations.

Discovery proves that every occurrence has an exact semantic binding. It does
not close variant, stat, leveling, report or market dimensions for the collection.
The validated quality union can prove unique/set tiering inapplicable; a missing
quality list remains unknown.
"""

from datetime import date

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint


def validate_collection(review, identity, occurrences, profiles, validated_links, *, excluded_occurrences=None):
    """Validate a reviewed collection against independently compiled source links."""
    try:
        date.fromisoformat(review['review_date'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Collection requires a dated review') from exc
    if (
        identity.get('category') != 'unresolved'
        or review.get('identity_id') != identity['id']
        or review.get('identity_fingerprint') != fingerprint(identity)
        or not review.get('reason')
    ):
        raise ValueError('Changed or invalid collection identity')
    records = {o['id']: o for o in occurrences if o['identity_id'] == identity['id']}
    members = review.get('members', [])
    ids = [m['occurrence_id'] for m in members]
    if not ids or len(ids) != len(set(ids)) or set(ids) != set(records) or set(ids) != set(identity['occurrence_ids']):
        raise ValueError('Collection must cover every occurrence exactly once')
    roles = {p['id']: p for p in profiles}
    excluded_occurrences = excluded_occurrences or {}
    excluded_ids = set()
    for member in members:
        if 'excluded_by' in member:
            oid = member['occurrence_id']
            proof = excluded_occurrences.get(oid, {})
            if (
                set(member) != {'occurrence_id', 'occurrence_fingerprint', 'excluded_by'}
                or member['occurrence_fingerprint'] != fingerprint(records[oid])
                or proof.get('id') != member['excluded_by']
                or proof.get('state') != 'excluded'
            ):
                raise ValueError('Collection member lacks a validated scope exclusion')
            excluded_ids.add(oid)
            continue
        oid, pid = member['occurrence_id'], member['profile_id']
        if (
            (oid, pid) not in validated_links
            or pid not in roles
            or member.get('occurrence_fingerprint') != fingerprint(records[oid])
            or member.get('profile_fingerprint') != fingerprint(roles[pid])
        ):
            raise ValueError('Collection member lacks an unchanged validated source configuration')
    retained_roles = {m['profile_id'] for m in members if m['occurrence_id'] not in excluded_ids}
    member_roles = [roles[pid] for pid in retained_roles]
    qualities = (
        sorted({quality for role in member_roles for quality in role['qualities']})
        if all(role.get('qualities') for role in member_roles)
        else []
    )
    return {
        'qualities': qualities,
        'identity_id': identity['id'],
        'occurrence_ids': sorted(ids),
        'excluded_occurrence_ids': sorted(excluded_ids),
        'profile_ids': sorted(retained_roles),
        'reason': review['reason'],
    }


def compile_collections(
    reviews, inventory, profiles, uses, table_reviews, root, *, context_reviews=None, hardcore_reviews=None
):
    from pricing.knowledge.assessment.maintenance.hardcore_mentions import compile_hardcore_mentions
    from pricing.knowledge.assessment.maintenance.review_dossiers import _pattern_bindings, compile_dossiers
    from pricing.knowledge.assessment.maintenance.source_context_reviews import compile_source_context_reviews
    from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence

    if reviews.get('schema_version') != 1:
        raise ValueError('Unsupported collection review schema')
    compile_dossiers(inventory, profiles, uses)  # Validates source/predicate reviews.
    roles = {p['id']: p for p in profiles}
    bindings = _pattern_bindings(inventory['occurrences'], uses, roles)
    links = {(oid, use['profile_id']) for use, ids in bindings for oid in ids}
    links.update(
        (row['occurrence_id'], row['profile_id'])
        for row in compile_table_equivalence(table_reviews, inventory['occurrences'], profiles, uses, root)
        if row['state'] == 'reviewed'
    )
    links.update(
        (row['occurrence_id'], profile_id)
        for row in compile_source_context_reviews(context_reviews, inventory['occurrences'], profiles, uses, root)
        if row['state'] == 'reviewed'
        for profile_id in row['profile_ids']
    )
    identities = {i['id']: i for i in inventory['identities']}
    exclusions = {
        row['occurrence_id']: row for row in compile_hardcore_mentions(hardcore_reviews, inventory['occurrences'], root)
    }
    result = {}
    for index, review in enumerate(reviews['rows']):
        identity_id = review['identity_id']
        if identity_id in result or identity_id not in identities:
            raise ValueError('Duplicate or missing collection identity')
        row = validate_collection(
            review, identities[identity_id], inventory['occurrences'], profiles, links, excluded_occurrences=exclusions
        )
        result[identity_id] = {**row, 'review_index': index}
    return result
