"""Resolve abbreviated armor-rune summaries through exact reviewed equipment links."""

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.source_matching import requires, requires_eq
from pricing.knowledge.assessment.maintenance.structured_named_variants import (
    KIND as NAMED_KIND,
    validate_link as validate_equipment,
)
from pricing.knowledge.assessment.policies.sources import resolve_pointer


KIND = 'structured_prose_socket'
VARIANT_ALIASES = {'MF': 'Magic Find'}


def validate_link(review, occurrence, role, equipment_review, equipment, uses, root, read_json):
    """A summary does not establish a free rune's value or a different recipient."""
    if (
        not occurrence
        or not role
        or not equipment_review
        or not equipment
        or review.get('occurrence_fingerprint') != fingerprint(occurrence)
        or review.get('profile_fingerprint') != fingerprint(role)
        or review.get('profile_id') != role['id']
        or review.get('occurrence_id') != occurrence['id']
        or not isinstance(review.get('reason'), str)
        or not review['reason'].strip()
        or occurrence.get('kind') != 'demand'
        or occurrence.get('source_status') != 'verified'
        or occurrence.get('details', {}).get('recommended') is not True
        or occurrence.get('identity_status') != 'unresolved'
        or occurrence.get('variant') != 'Prose alternatives'
        or occurrence.get('side') != 'unspecified'
        or occurrence.get('slot') != 'unspecified'
        or occurrence.get('build') != role.get('build')
        or occurrence.get('class') != equipment.get('class')
        or role.get('slot') != 'Body Armor'
        or role.get('side') != 'player'
        or review.get('equipment_occurrence_id') != equipment['id']
        or equipment_review.get('pattern_kind') != NAMED_KIND
        or equipment_review.get('profile_id') != role['id']
    ):
        raise ValueError('Invalid prose socket context')
    source = role['source']
    parts = occurrence['source_locator'].removeprefix('/').split('/')
    if (
        occurrence.get('source_id') != source['path']
        or source['path'] != 'pricing/data/wp-a-builds.json'
        or len(parts) != 3
        or parts[:2] != [role['build'], 'prose_only_items']
        or not parts[2].isdecimal()
        or str(int(parts[2])) != parts[2]
        or VARIANT_ALIASES.get(review.get('variant_alias')) != role.get('variant')
    ):
        raise ValueError('Prose socket source or variant differs')
    document = read_json(source)
    label = resolve_pointer(document, occurrence['source_locator'])
    rune = review.get('rune')
    if (
        not isinstance(rune, str)
        or not rune.endswith(' Rune')
        or not isinstance(label, str)
        or label != occurrence.get('name')
        or label != occurrence.get('original_label')
        or label.casefold() != f'{rune} ({review["variant_alias"]} variant)'.casefold()
        or not requires(role.get('must'), {'op': 'socket_runes_equal', 'value': [rune]})
        or not requires_eq(role.get('must'), 'fact_eq', 'sockets', 1)
        or not requires_eq(role.get('must'), 'fact_eq', 'socket_contents', 'filled')
    ):
        raise ValueError('Prose socket rune or mandatory payload differs')
    # The existing exact equipment validator checks source hashes, native identity,
    # ownership, class, all reviewed predicates and the independently pinned use.
    validate_equipment(equipment_review, equipment, role, uses, root, read_json)
    variant = resolve_pointer(document, source['locator'])
    purpose = variant.get('purpose', '')
    if (
        variant.get('planner_only') is True
        or variant.get('player', {}).get('Body Armor') != [equipment['original_label']]
        or purpose not in source.get('quotes', [])
        or rune.casefold() not in purpose.casefold()
        or 'armor' not in purpose.casefold()
        or rune not in equipment['original_label']
    ):
        raise ValueError('Prose socket purpose does not establish this exact armor payload')
    return {
        'occurrence_id': occurrence['id'],
        'profile_id': role['id'],
        'state': 'reviewed',
        'reason': review['reason'],
        'review_date': review['review_date'],
    }
