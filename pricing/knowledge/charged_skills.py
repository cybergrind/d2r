"""Compile runeword charged skills from native PropertyFunc19 declarations."""


def charged_skills(record, properties, skill_ids):
    result = []
    for slot in range(1, 8):
        if record.get(f'T1Code{slot}') != 'charged':
            continue
        prop = properties.get('charged', {})
        if prop.get('func1') != 19 or prop.get('stat1') != 'item_charged_skill':
            raise ValueError('Unverified native charged-skill property function')
        skill = record.get(f'T1Param{slot}')
        if isinstance(skill, str):
            matches = {value for name, value in skill_ids.items() if name.casefold() == skill.casefold()}
            skill = next(iter(matches)) if len(matches) == 1 else None
        level, capacity = record.get(f'T1Max{slot}'), record.get(f'T1Min{slot}')
        if (
            type(skill) is not int
            or skill not in skill_ids.values()
            or type(level) is not int
            or not 1 <= level < 64
            or type(capacity) is not int
        ):
            raise ValueError('Runeword charged skill requires a verified fixed level and capacity')
        result.append({'skill_id': skill, 'level': level, 'capacity_parameter': capacity})
    return result
