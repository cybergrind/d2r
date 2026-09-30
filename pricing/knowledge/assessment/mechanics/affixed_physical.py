"""Physical modifiers on non-weapons are flat bonuses, not base damage totals."""

from pricing.knowledge.assessment.adapters.capture import bases_by_code


# Local properties.json and D2MOO ItemMods.cpp PropertyFunc05/06 mirror these
# bonuses onto primary, secondary and thrown stats for non-weapon items.
GROUPS = ((('21:0', '23:0', '159:0'), '416'), (('22:0', '24:0', '160:0'), '448'))


def affixed_physical_properties(facts):
    base = bases_by_code().get(facts.base_code, {})
    if base.get('category') not in ('armor', 'misc'):
        return {}, set(), []
    properties, consumed, errors = {}, set(), []
    for keys, prop in GROUPS:
        present = [key for key in keys if key in facts.stats]
        if not present:
            continue
        rows = [facts.stats[key] for key in present]
        if keys[0] not in present or any(
            row.get('status') != 'decoded' or type(row.get('value')) is not int for row in rows
        ):
            errors.append(f'Physical damage property {prop} is not completely decoded.')
            continue
        values = {row['value'] for row in rows}
        if len(values) != 1:
            errors.append(f'Physical damage property {prop} has conflicting mirrored stats.')
            continue
        properties[prop] = values.pop()
        consumed.update(present)
    return properties, consumed, errors
