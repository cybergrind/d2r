"""Resolve dimension citations against the pinned maintenance artifacts."""

from pricing.knowledge.assessment.policies.sources import resolve_pointer


def invalid_reference(source, documents):
    artifact = source.get('artifact')
    if artifact not in documents:
        return f'Unknown evidence artifact: {artifact}'
    document = documents[artifact]
    if 'configuration_id' in source:
        rows = document.get('stat_evaluation', {}).get('configurations', [])
        matches = [row for row in rows if row.get('id') == source['configuration_id']]
        if len(matches) != 1 or matches[0].get('version') != source.get('version'):
            return 'Missing or changed stat configuration citation.'
        return None
    try:
        resolve_pointer(document, source.get('locator'))
    except ValueError, KeyError, IndexError, TypeError:
        return f'Unresolved evidence locator in {artifact}: {source.get("locator")}'
    return None
