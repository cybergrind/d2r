"""Exact paired Dream prose, preserving qualified labels and source-specific scope."""

from pricing.knowledge.assessment.maintenance.embedded_dream import (
    CONTEXTS,
    validate_component,
    validate_native_item,
)
from pricing.knowledge.assessment.maintenance.embedded_evidence import _read_pin, validate_embedded_evidence
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory


GUIDE = 'pricing/raw/mr/guides__dream-paladin.html'
PAIRS = {
    0: (1, 4, True),
    1: (0, 4, False),
    13: (14, 14, True),
    14: (13, 14, False),
    200: (201, 52, True),
    201: (200, 52, False),
}
CLAIMS = {
    4: ('Advertisement', 'Commanding a Level 30 Holy Shock Aura from both a Dream Helmet and Dream Shield'),
    14: (
        'Skills',
        'Resist Lightning and Salvation are Synergies for the Level 30 Holy Shock Aura '
        'provided by the combination of Dream Helmet and Dream Shield.',
    ),
    52: (
        'Summary',
        'The Dream Paladin requires both a Dream Helmet and a Dream Shield. '
        "This build doesn't work without these items.",
    ),
}


def validate_dream_prose(review, resolved, role, root):
    evidence, context = review['evidence'], resolved['context']
    entry = PAIRS.get(context['span_index'])
    if not entry or evidence['guide']['path'] != GUIDE:
        raise ValueError('Dream pair prose context has not been reviewed')
    partner, section_id, head = entry
    reference = evidence['reference']
    if (
        context['label'] != ('Dream Helmet' if head else 'Dream Shield')
        or context['side'] != 'player'
        or context['slot'] != 'unspecified'
        or reference.get('format') != 'legacy_item'
        or reference.get('set_id') is not None
        or reference['section_locator'] != f'/sections/{section_id}'
    ):
        raise ValueError('Dream pair prose label or context differs')
    section = section_inventory(_read_pin(evidence['guide'], root))['sections'][section_id]
    heading, claim = CLAIMS[section_id]
    if section['heading'] != heading or claim not in section['text']:
        raise ValueError('Dream pair prose lacks the reviewed joint-equipment claim')
    companion_evidence = review['companion_evidence']
    if (
        companion_evidence['guide'] != evidence['guide']
        or companion_evidence['planner'] != evidence['planner']
        or companion_evidence['reference'].get('format') != 'legacy_item'
        or companion_evidence['reference'].get('set_id') is not None
        or companion_evidence['reference']['section_locator'] != reference['section_locator']
    ):
        raise ValueError('Dream companion must be the paired reference in the same source section')
    companion = validate_embedded_evidence(companion_evidence, root, allow_legacy=True)
    other = companion['context']
    if (
        other['span_index'] != partner
        or other['label'] != ('Dream Shield' if head else 'Dream Helmet')
        or other['side'] != 'player'
        or other['slot'] != 'unspecified'
    ):
        raise ValueError('Dream companion is not the complementary prose item')
    code, runes = validate_component(review, resolved, role, root, CONTEXTS[73 if head else 65])
    validate_native_item(companion['item'], code, runes)


def dream_label_links(review, disposition, occurrences, fields):
    """Resolve only this qualified occurrence; do not rewrite its extraction identity."""
    context = review['evidence']['expected_context']
    entry = PAIRS.get(context['span_index'])
    if not entry or disposition.get('state') != 'reviewed' or disposition.get('profile_id') != review['profile_id']:
        raise ValueError('Dream qualified label lacks validated pair semantics')
    head = entry[2]
    name = 'Dream Helmet' if head else 'Dream Shield'
    slot = 'Helmets' if head else 'Off-Hand'
    result = []
    for expected in review['occurrence_links']:
        occurrence = occurrences.get(expected.get('id')) if isinstance(expected, dict) else None
        if (
            not occurrence
            or set(expected) != set(fields)
            or any(occurrence.get(k) != expected[k] for k in fields)
            or any(
                occurrence.get(k) != v
                for k, v in {
                    'name': name,
                    'original_label': name,
                    'category': None,
                    'identity_status': 'unresolved',
                    'kind': 'demand',
                    'variant': 'Guide mention',
                    'side': 'player',
                    'slot': 'unspecified',
                    'source_id': GUIDE,
                    'source_locator': f'/item-spans/{context["span_index"]}',
                    'build': 'dream-paladin',
                    'class': 'Paladin',
                    'source_status': 'verified',
                }.items()
            )
        ):
            raise ValueError('Dream qualified occurrence is missing or differs from reviewed context')
        result.append(
            {
                'occurrence_id': occurrence['id'],
                'profile_id': review['profile_id'],
                'embedded_id': disposition['id'],
                'state': 'reviewed',
                'reason': review['reason'],
                'review_date': review['review_date'],
                'resolved_identity': {'name': 'Dream', 'category': 'runeword', 'slot': slot},
            }
        )
    return result
