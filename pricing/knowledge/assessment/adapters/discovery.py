"""Evidence-search facets from the assessment's already normalized facts.

Search candidates are not comparison contracts. OCR retains its supplied facets;
native skill identities never fall back to display-label matching.
"""

from pricing.knowledge.assessment.domain.facts import thaw


SKILL_STATS = frozenset({83, 97, 107, 126, 151, 188})


def properties(facts):
    result = thaw(facts.properties)
    for row in facts.stats.values():
        if row.get('status') != 'decoded' and row.get('market_property'):
            result.pop(row['market_property'], None)
    return result


def skill_properties(facts, extraction):
    candidates = properties(facts)
    if 'decoded_stats' not in extraction:
        # OCR candidates have no native identity proof. Preserve their existing
        # label-gated discovery behavior, never infer another property ID.
        selected = {
            str(row['property_id']) for row in extraction['item'].get('affixes', []) if 'Only)' in row.get('label', '')
        }
    else:
        selected = {
            row['market_property']
            for row in facts.stats.values()
            if row.get('id') in SKILL_STATS and row.get('status') == 'decoded' and row.get('market_property')
        }
    return {key: candidates[key] for key in sorted(selected) if key in candidates}
