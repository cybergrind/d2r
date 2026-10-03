"""Preserve cold duration even when compound damage compilation omitted it.

Native dmg-cold/dmg-elem use PropertyFunc17: a nonzero parameter fixes frames;
otherwise min/max roll frames inclusively. cold-len rolls its own range. Fixed
sources add, while any rolled source must remain a market comparison dimension.
"""

from pricing.knowledge.assessment.mechanics.elemental import ENDPOINTS, cold_duration_matches


COLD_PROPERTIES = frozenset({'dmg-cold', 'dmg-elem', 'cold-len'})


def cold_duration_keys(facts, definition):
    record = definition.get('game_definition', {})
    low_total = high_total = 0
    present = False
    error = ['Named cold duration is missing, changed or outside its native frame range.']
    for slot in range(1, 13):
        code = record.get(f'prop{slot}')
        if code not in COLD_PROPERTIES:
            continue
        present = True
        low, high = record.get(f'min{slot}'), record.get(f'max{slot}')
        if code == 'dmg-elem':
            # Functions15/16 write each of the three fixed endpoint pairs.
            # Reject mixtures rather than misread a captured total as this source.
            other_damage = {
                'dmg-elem',
                'dmg-fire',
                'dmg-ltng',
                'dmg-cold',
                'fire-min',
                'fire-max',
                'ltng-min',
                'ltng-max',
                'cold-min',
                'cold-max',
            }
            if any(record.get(f'prop{i}') in other_damage for i in range(1, 13) if i != slot):
                return set(), ['Named compound elemental sources require separate total verification.']
            if type(low) is not int or type(high) is not int or not 0 < low <= high:
                return set(), error
            for endpoints in ENDPOINTS.values():
                for (stat, prop), expected in zip(endpoints, (low, high), strict=True):
                    endpoint = facts.stats.get(f'{stat}:0', {})
                    if (
                        endpoint.get('status') != 'decoded'
                        or type(endpoint.get('raw')) is not int
                        or endpoint['raw'] != expected
                        or type(endpoint.get('value')) not in (int, float)
                        or endpoint['value'] != expected
                        or facts.properties.get(prop) != expected
                    ):
                        return set(), ['Named compound elemental damage is missing, changed or unverified.']
        parameter = record.get(f'par{slot}', 0)
        if code != 'cold-len' and parameter:
            low = high = parameter
        if type(low) is not int or type(high) is not int or min(low, high) < 0:
            return set(), error
        low_total += min(low, high)
        high_total += max(low, high)
    if not present or high_total == 0:
        return set(), []
    row = facts.stats.get('56:0', {})
    frames = row.get('raw')
    if not cold_duration_matches(facts, frames) or not low_total <= frames <= high_total:
        return set(), error
    if low_total != high_total:
        return set(), ['Named rolled cold duration requires a verified frame-aware market comparison.']
    if row.get('market_property') is not None:
        return set(), ['Named cold duration has an unverified market projection.']
    return {'56:0'}, []
