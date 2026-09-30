"""Explicit aliases from validated native-identity tooltips to their visible labels."""

from pricing.knowledge.assessment.maintenance.embedded_dream_prose import dream_label_links
from pricing.knowledge.assessment.maintenance.embedded_negative import negative_label_links
from pricing.knowledge.assessment.maintenance.embedded_reviews import embedded_identity
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq


FIELDS = (
    'id',
    'name',
    'original_label',
    'kind',
    'source_id',
    'source_locator',
    'build',
    'class',
    'variant',
    'side',
    'slot',
    'category',
    'identity_id',
    'identity_status',
)
# These policies prove native item identity and corrected wearer semantics.
# Generic table reviews and exclusions do not yet supply that same proof.
UNIQUE_KINDS = frozenset({'echoing_enchant', 'echoing_pairing'})
SUPPORTED_KINDS = (
    frozenset(
        {
            'abyss_recipe',
            'dream_equipment',
            'echoing_fade',
            'echoing_malice',
            'echoing_insight',
            'echoing_cure',
            'echoing_enigma',
        }
    )
    | UNIQUE_KINDS
)


def compile_embedded_occurrence_links(document, dispositions, occurrences, profiles):
    if document is None:
        return []
    by_disposition = {r['id']: r for r in dispositions}
    by_occurrence = {r['id']: r for r in occurrences}
    by_profile = {r['id']: r for r in profiles}
    result, seen = [], set()
    for review in document['rows']:
        links = review.get('occurrence_links', [])
        if not isinstance(links, list):
            raise ValueError('Embedded occurrence links must be an explicit list')
        if not links:
            continue
        evidence = review['evidence']
        identity = embedded_identity({'source_id': evidence['guide']['path'], 'reference': evidence['reference']})
        disposition = by_disposition.get(identity, {})
        if review.get('kind') in {'echoing_gheed_removal', 'dream_pair_prose'}:
            linker = dream_label_links if review['kind'] == 'dream_pair_prose' else negative_label_links
            negative = linker(review, disposition, by_occurrence, FIELDS)
            for row in negative:
                if row['occurrence_id'] in seen:
                    raise ValueError('Duplicate embedded occurrence link')
                seen.add(row['occurrence_id'])
            result.extend(negative)
            continue
        role = by_profile.get(review.get('profile_id'))
        if (
            review.get('kind') not in SUPPORTED_KINDS
            or disposition.get('state') != 'reviewed'
            or not role
            or disposition.get('profile_id') != role['id']
        ):
            raise ValueError('Embedded occurrence link lacks validated native use semantics')
        context = evidence['expected_context']
        for expected in links:
            if not isinstance(expected, dict) or set(expected) != set(FIELDS):
                raise ValueError('Embedded occurrence identity/context evidence is incomplete')
            occurrence = by_occurrence.get(expected['id'])
            if not occurrence or any(occurrence.get(key) != expected[key] for key in FIELDS):
                raise ValueError('Embedded occurrence evidence is missing or stale')
            oid = occurrence['id']
            if oid in seen:
                raise ValueError('Duplicate embedded occurrence link')
            seen.add(oid)
            if (
                occurrence['source_id'] != evidence['guide']['path']
                or occurrence['source_locator'] != f'/item-spans/{context["span_index"]}'
                or occurrence['original_label'] != context['label']
                or not context['label']
                or any(occurrence[key] != context[key] for key in ('side', 'slot'))
                or occurrence['kind'] != 'demand'
                or occurrence['variant'] != 'Guide mention'
                or occurrence['category'] != ('unique' if review['kind'] in UNIQUE_KINDS else 'runeword')
                or occurrence['identity_status'] != 'resolved'
                or occurrence.get('source_status') != 'verified'
                or occurrence['build'] != role['build']
                or role.get('names') != [occurrence['name']]
                or (
                    review['kind'] not in UNIQUE_KINDS
                    and not requires_eq(role['must'], 'fact_eq', 'runeword', occurrence['name'])
                )
                or not requires_eq(role['must'], 'context_eq', 'player_class', occurrence['class'])
            ):
                raise ValueError('Embedded occurrence differs from the validated span, identity or class')
            result.append(
                {
                    'occurrence_id': oid,
                    'profile_id': role['id'],
                    'embedded_id': identity,
                    'state': 'reviewed',
                    'reason': review['reason'],
                    'review_date': review['review_date'],
                }
            )
    return result
