"""Order repeated listing observations only when fetch timestamps prove recency."""

from datetime import UTC, datetime, time


def observation_interval(value):
    if not isinstance(value, str):
        return None
    try:
        start = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        end = datetime.combine(start.date(), time.max, tzinfo=UTC) if len(value) == 10 else start
        return start, end
    except ValueError:
        return None


def superseded_rows(rows):
    """Undated/day-precision observations are never given invented within-day order."""
    latest = {}
    intervals = [observation_interval(row.get('observed_at')) for row in rows]
    for row, interval in zip(rows, intervals, strict=True):
        identity = row.get('listing_id')
        if identity and interval:
            latest[identity] = max(latest.get(identity, interval[0]), interval[0])
    return {
        index
        for index, (row, interval) in enumerate(zip(rows, intervals, strict=True))
        if interval and row.get('listing_id') in latest and interval[1] < latest[row['listing_id']]
    }
