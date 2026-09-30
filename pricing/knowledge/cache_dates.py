"""Validate explicit legacy collector dates; never infer freshness from filenames."""

from datetime import UTC, date, datetime


def collection_day(document):
    day, error, _ = collection_day_evidence(document)
    return day, error


def collection_day_evidence(document):
    """Return day, validation error and exact source field for explicit dates."""
    if not isinstance(document, dict):
        return None, None, None
    values = {}
    if document.get('pulled') is not None:
        values['/pulled'] = document['pulled']
    meta = document.get('_meta')
    if isinstance(meta, dict) and meta.get('pulled') is not None:
        values['/_meta/pulled'] = meta['pulled']
    if not values:
        return None, None, None
    for value in values.values():
        try:
            if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
                raise ValueError
        except TypeError, ValueError:
            return None, 'Invalid explicit cache collection day.', None
    if len(set(values.values())) != 1:
        return None, 'Conflicting explicit cache collection days.', None
    field = '/pulled' if '/pulled' in values else '/_meta/pulled'
    value = values[field]
    pulled = date.fromisoformat(value)
    for row in document.get('listings', []):
        if not isinstance(row, dict) or not row.get('updated_at'):
            continue
        try:
            updated = datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00'))
            if updated.tzinfo is not None:
                updated = updated.astimezone(UTC)
        except TypeError, ValueError, AttributeError:
            return None, 'Invalid listing update timestamp prevents collection-day validation.', None
        if updated.date() > pulled:
            return None, 'Listing was updated after the explicit cache collection day.', None
    return value, None, field
