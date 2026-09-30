"""Bounded negative advice, distinct from an item's positive uses elsewhere."""

import json

from pricing.knowledge.assessment.maintenance.embedded_evidence import _read_pin
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory


GUIDE = 'pricing/raw/mr/guides__echoing-strike-warlock-guide.html'
REMOVAL = "Make sure to replace a Gheed's Fortune with more damage or survivability, if you're using one."


def validate_gheed_removal(review, resolved, root):
    evidence = review['evidence']
    context, item = resolved['context'], resolved['item']
    if (
        any(key in review for key in ('profile_id', 'profile_fingerprint', 'use_fingerprint'))
        or evidence['guide']['path'] != GUIDE
        or evidence['reference']['section_locator'] != '/sections/24'
        or context['span_index'] != 11
        or context['label'] != "Gheed's Fortune"
        or context['side'] != 'player'
        or context['slot'] != 'unspecified'
        or item.get('unique') != 'unique359'
        or item.get('base') != 'cm3'
        or item.get('quality') != 6
    ):
        raise ValueError('Gheed removal is not the exact negative Ubers reference')
    if review['native_source']['path'] != 'third-parties/d2data/json/uniqueitems.json':
        raise ValueError('Gheed removal requires native identity evidence')
    native = json.loads(_read_pin(review['native_source'], root))['359']
    if native.get('index') != "Gheed's Fortune" or native.get('code') != item['base']:
        raise ValueError('Gheed removal native identity changed')
    sections = section_inventory(_read_pin(evidence['guide'], root))['sections']
    section = next(s for s in sections if s['locator'] == '/sections/24')
    if (
        section['heading'] != 'Setup'
        or not section['text'].startswith('The Uber variant')
        or REMOVAL not in section['text']
    ):
        raise ValueError('Gheed removal lacks explicit source advice')


def negative_label_links(review, disposition, occurrences, fields):
    """Close only the corrected negative occurrence, never a positive use alias."""
    if disposition.get('state') != 'excluded' or disposition.get('profile_id'):
        raise ValueError('Unvalidated negative demand disposition')
    result = []
    for expected in review['occurrence_links']:
        occurrence = occurrences.get(expected.get('id')) if isinstance(expected, dict) else None
        if (
            not occurrence
            or set(expected) != set(fields)
            or any(occurrence.get(key) != expected[key] for key in fields)
            or occurrence.get('details', {}).get('recommended') is not False
            or any(
                occurrence.get(key) != value
                for key, value in {
                    'source_id': GUIDE,
                    'source_locator': '/item-spans/11',
                    'name': "Gheed's Fortune",
                    'original_label': "Gheed's Fortune",
                    'build': 'echoing-strike-warlock-guide',
                    'class': 'Warlock',
                    'variant': 'Guide mention',
                    'kind': 'demand',
                    'side': 'player',
                    'slot': 'unspecified',
                    'category': 'unique',
                    'identity_status': 'resolved',
                    'source_status': 'verified',
                }.items()
            )
        ):
            raise ValueError('Changed or still recommended negative demand occurrence')
        result.append(
            {
                'occurrence_id': occurrence['id'],
                'embedded_id': disposition['id'],
                'state': 'excluded',
                'reason': review['reason'],
                'review_date': review['review_date'],
            }
        )
    return result
