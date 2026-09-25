"""Verify which observed properties are unchanged fixed definition bonuses."""


def fixed_properties(facts, ranges):
    result = {}
    for spec in ranges.values():
        if spec['min'] != spec['max']:
            continue
        row = facts.stats.get(f'{spec["stat_id"]}:{spec.get("layer", 0)}', {})
        prop = row.get('market_property')
        value = row.get('value')
        if (
            prop
            and row.get('status') == 'decoded'
            and type(value) in (int, float)
            and value == spec['min']
            and facts.properties.get(prop) == value
        ):
            result[prop] = value
    return result
