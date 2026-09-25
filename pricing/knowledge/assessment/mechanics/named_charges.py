"""Named rechargeable skill invariants, verified with ITEMMODS_PropertyFunc19.

Market scalar fields encode skill level, never remaining uses. Non-ethereal
items can recharge; irreversible ethereal charge depletion needs separate evidence.
"""

from inventory_tracking.items.metadata import metadata


# Exact cached appraisal-properties charge labels, reviewed 2026-09-25.
MARKET_FIELDS = {
    6: '565',
    7: '464',
    8: '465',
    11: '466',
    12: '467',
    14: '468',
    16: '469',
    21: '470',
    24: '471',
    31: '472',
    34: '473',
    36: '521',
    38: '522',
    39: '558',
    43: '523',
    44: '524',
    45: '525',
    48: '450',
    49: '529',
    52: '533',
    53: '564',
    54: '526',
    55: '559',
    56: '554',
    59: '560',
    64: '561',
    66: '648',
    67: '502',
    71: '503',
    72: '474',
    73: '475',
    74: '693',
    75: '891',
    76: '774',
    77: '451',
    81: '504',
    82: '505',
    83: '697',
    84: '506',
    86: '507',
    87: '626',
    90: '773',
    91: '508',
    92: '476',
    93: '509',
    95: '741',
    96: '493',
    101: '494',
    106: '495',
    111: '496',
    126: '489',
    139: '490',
    144: '491',
    150: '492',
    221: '777',
    226: '725',
    236: '732',
    240: '527',
    245: '528',
    246: '733',
    278: '748',
    393: '1861',
    395: '1860',
    396: '1858',
    401: '1859',
}


def fixed_charge_properties(facts, definition):
    properties, consumed, gaps = {}, set(), []
    record = definition.get('game_definition', {})
    if definition.get('rarity') == 'runeword':
        if 'charged_skills' not in definition:
            return {}, set(), ['Runeword charged-skill definitions need an offline rebuild.']
        record = {}
        for slot, effect in enumerate(definition['charged_skills'], 1):
            record.update(
                {
                    f'prop{slot}': 'charged',
                    f'par{slot}': effect['skill_id'],
                    f'max{slot}': effect['level'],
                    f'min{slot}': effect['capacity_parameter'],
                }
            )
    skills = metadata()['skills']
    for slot in range(1, 13):
        if record.get(f'prop{slot}') != 'charged':
            continue
        skill = record.get(f'par{slot}')
        if isinstance(skill, str):
            normalized = skill.replace(' ', '').casefold()
            matches = [
                int(key)
                for key, value in skills.items()
                if value.get('internal_name', value['name']).replace(' ', '').casefold() == normalized
            ]
            skill = matches[0] if len(matches) == 1 else None
        level, capacity = record.get(f'max{slot}'), record.get(f'min{slot}')
        if (
            type(skill) is not int
            or str(skill) not in skills
            or type(level) is not int
            or not 1 <= level < 64
            or type(capacity) is not int
        ):
            gaps.append('Named charged skill has no verified fixed definition.')
            continue
        if capacity < 0:
            capacity = level * -capacity // 8 - capacity
        capacity = min(255, max(1, capacity)) if capacity else 5
        key = f'204:{skill * 64 + level}'
        row = facts.stats.get(key, {})
        charges = row.get('charges', {})
        remaining = charges.get('remaining')
        if (
            row.get('status') != 'decoded'
            or row.get('unit') != 'charges_remaining'
            or type(remaining) is not int
            or not 0 <= remaining <= capacity
            or type(charges.get('maximum')) is not int
            or charges['maximum'] != capacity
            or type(row.get('raw')) is not int
            or row['raw'] != (capacity << 8) + remaining
            or type(row.get('value')) is not int
            or row['value'] != remaining
        ):
            gaps.append(f'Named charged skill {key} is missing, changed or unverified.')
            continue
        if facts.ethereal is not False:
            gaps.append('Ethereal charged-item comparisons require remaining-use evidence from listings.')
            continue
        prop = MARKET_FIELDS.get(skill)
        if row.get('market_property') not in (None, prop):
            gaps.append(f'Named charged skill {key} has an unverified market projection.')
            continue
        if prop:
            if prop in properties and properties[prop] != level:
                gaps.append(f'Named charged skills conflict on market property {prop}.')
                continue
            properties[prop] = level
        consumed.add(key)
    return properties, consumed, gaps
