"""Build-time test for an evidence-supported price split."""

import json
from math import isfinite

from pricing.triage.roll_comparisons import lower_quartile, seller_rows


def worthwhile(groups):
    groups = list(groups)
    if len(groups) < 2:
        return False
    votes = [seller_rows(group) for group in groups]
    if any(len(group) < 3 for group in votes):
        return False
    prices = [lower_quartile([row['ask_ist'] for row in group]) for group in votes]
    return min(prices) > 0 and max(prices) >= 1.5 * min(prices)


def roll_split(rows, prop):
    from pricing.triage.roll_comparisons import numeric

    values = sorted({r.get('properties', {}).get(prop) for r in rows if numeric(r.get('properties', {}).get(prop))})
    for boundary in values[1:]:
        low, high = [], []
        for row in rows:
            value = row.get('properties', {}).get(prop)
            if numeric(value):
                (low if value < boundary else high).append(row)
        if worthwhile([low, high]):
            return True
    return False


def numeric_partition(members, values):
    """First supported boundary in ascending roll order; never infer missing rolls."""
    if any(type(v) not in (int, float) or not isfinite(v) for v in values):
        return None
    for boundary in sorted(set(values))[1:]:
        low = [m for m, v in zip(members, values, strict=True) if v < boundary]
        high = [m for m, v in zip(members, values, strict=True) if v >= boundary]
        if worthwhile([[r for r, _ in low], [r for r, _ in high]]):
            return {
                'split_at': boundary,
                'minimum': min(values),
                'groups': {json.dumps(min(values)): low, json.dumps(boundary): high},
            }
    return None
