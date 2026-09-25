"""Validate explicit legacy collector dates; never infer freshness from filenames."""

from datetime import UTC, date, datetime


def collection_day(document):
    if not isinstance(document, dict) or document.get('pulled') is None:
        return None, None
    value = document['pulled']
    try:
        if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
            raise ValueError
        pulled = date.fromisoformat(value)
    except TypeError, ValueError:
        return None, 'Invalid explicit cache collection day.'
    for row in document.get('listings', []):
        if not isinstance(row, dict) or not row.get('updated_at'):
            continue
        try:
            updated = datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00'))
            if updated.tzinfo is not None:
                updated = updated.astimezone(UTC)
        except TypeError, ValueError, AttributeError:
            return None, 'Invalid listing update timestamp prevents collection-day validation.'
        if updated.date() > pulled:
            return None, 'Listing was updated after the explicit cache collection day.'
    return value, None
