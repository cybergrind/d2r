"""Shared scalar distinction for ordinary and seasonal named definitions."""

import math


def select_scalar_candidates(candidates, stats):
    """Shared scalar comparison after each caller verifies capture completeness."""
    left, right = candidates
    ranges = [c.get('roll_ranges', {}) for c in candidates]
    keys = {k for k in ranges[0].keys() | ranges[1].keys() if ranges[0].get(k) != ranges[1].get(k)}
    # Keep this evidence boundary explicit: these season-15 changes add or
    # replace scalar FCR, IAS or FRW bonuses. Sockets, requirements and custom
    # properties need their own discriminators, not scalar absence guesses.
    keys &= {'105', '93', '96'}
    if not keys or left.get('table_id') != right.get('table_id'):
        return candidates
    observed = {}
    for key in keys:
        stat = stats.get(key + ':0')
        if stat is None:
            observed[key] = 0
            continue
        value = stat.get('value')
        if stat.get('status') != 'decoded' or type(value) not in (int, float) or not math.isfinite(value):
            return candidates
        observed[key] = value
    return [
        candidate
        for candidate in candidates
        if all(
            bounds['min'] <= value <= bounds['max']
            if (bounds := candidate.get('roll_ranges', {}).get(key))
            else value == 0
            for key, value in observed.items()
        )
    ]
