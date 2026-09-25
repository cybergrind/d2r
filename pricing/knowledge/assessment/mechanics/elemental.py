"""Verify both fixed elemental endpoints before permitting listing omissions."""

ENDPOINTS = {
    'fire': ((48, '458'), (49, '459')),
    'lightning': ((50, '478'), (51, '479')),
    'cold': ((54, '482'), (55, '483')),
}


def fixed_elemental_properties(facts, effects):
    result = {}
    for kind, endpoints in ENDPOINTS.items():
        sources = [effect for effect in effects if effect.get('kind') == kind]
        if not sources:
            continue
        if kind == 'cold' and (
            len(sources) != 1 or not cold_duration_matches(facts, sources[0].get('duration_frames'))
        ):
            continue
        values = [(effect.get('minimum_damage'), effect.get('maximum_damage')) for effect in sources]
        if any(type(low) is not int or type(high) is not int or not 0 <= low <= high for low, high in values):
            continue
        totals = (sum(low for low, _ in values), sum(high for _, high in values))
        verified = {}
        for (stat, prop), expected in zip(endpoints, totals, strict=True):
            row = facts.stats.get(f'{stat}:0', {})
            if (
                row.get('status') != 'decoded'
                or type(row.get('raw')) is not int
                or row['raw'] != expected
                or type(row.get('value')) not in (int, float)
                or row['value'] != expected
                or type(facts.properties.get(prop)) not in (int, float)
                or facts.properties[prop] != expected
            ):
                break
            verified[prop] = expected
        else:
            result.update(verified)
    return result


def cold_duration_matches(facts, frames):
    row = facts.stats.get('56:0', {})
    return (
        type(frames) is int
        and frames > 0
        and row.get('status') == 'decoded'
        and type(row.get('raw')) is int
        and row['raw'] == frames
        and row.get('unit') == 'seconds'
        and type(row.get('value')) in (int, float)
        and row['value'] == frames / 25
    )
