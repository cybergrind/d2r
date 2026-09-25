"""Compile fixed chance-to-cast identities from native property functions."""

EVENTS = {
    'att-skill': 'item_skillonattack',
    'hit-skill': 'item_skillonhit',
    'gethit-skill': 'item_skillongethit',
    'kill-skill': 'item_skillonkill',
    'death-skill': 'item_skillondeath',
    'levelup-skill': 'item_skillonlevelup',
}


def fixed_triggers(record, properties, stat_ids, skill_ids, *, runeword=False):
    result = []
    for slot in range(1, 13):
        code = record.get(f'T1Code{slot}' if runeword else f'prop{slot}')
        # Native unique rows use e.g. Gethit-skill; properties.json uses lowercase.
        code = code.casefold() if isinstance(code, str) else None
        if code not in EVENTS:
            continue
        prop = properties.get(code, {})
        skill = record.get(f'T1Param{slot}' if runeword else f'par{slot}')
        if isinstance(skill, str):
            matches = {identifier for name, identifier in skill_ids.items() if name.casefold() == skill.casefold()}
            skill = next(iter(matches)) if len(matches) == 1 else None
        chance = record.get(f'T1Min{slot}' if runeword else f'min{slot}')
        level = record.get(f'T1Max{slot}' if runeword else f'max{slot}')
        if (
            prop.get('func1') != 11
            or prop.get('stat1') != EVENTS[code]
            or EVENTS[code] not in stat_ids
            or type(skill) is not int
            or skill not in skill_ids.values()
            or type(chance) is not int
            or not 1 <= chance <= 100
            or type(level) is not int
            or not 1 <= level < 64
        ):
            continue
        result.append({'stat_id': stat_ids[EVENTS[code]], 'skill_id': skill, 'level': level, 'chance': chance})
    return result
