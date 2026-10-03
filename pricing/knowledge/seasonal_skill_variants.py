"""Reviewed Rogue's Bow seasonal skill distinction, independent of UI labels."""

# Verified in native skills.json and the compiled roguesbow-affix1 property group.
ARROW_SKILLS = ((7, 'Fire Arrow'), (11, 'Cold Arrow'))


def select_skill_candidates(candidates, stats):
    """Return None for unsupported definitions; callers own capture completeness."""
    if len(candidates) != 2 or any(c.get('table_id') != 62 for c in candidates):
        return None
    ordinary = [c for c in candidates if not c.get('property_groups')]
    seasonal = [c for c in candidates if _reviewed_group(c.get('property_groups', []))]
    if len(ordinary) != 1 or len(seasonal) != 1:
        return None
    observed = []
    for skill, _ in ARROW_SKILLS:
        stat = stats.get(f'107:{skill}')
        if stat is None:
            continue
        value = stat.get('value')
        if stat.get('status') != 'decoded' or type(value) not in (int, float):
            return candidates
        if value == 0:
            continue
        if value not in (1, 2, 3):
            return []
        observed.append(skill)
    if len(observed) > 1:
        return []
    return seasonal if observed else ordinary


def _reviewed_group(groups):
    if len(groups) != 1 or groups[0].get('code') != 'roguesbow-affix1':
        return False
    row = groups[0].get('game_definition', {})
    if row.get('PickMode') != 2:
        return False
    for index, (_, name) in enumerate(ARROW_SKILLS, 1):
        expected = {'Prop': 'skill', 'ParMin': name, 'ParMax': name, 'ModMin': 1, 'ModMax': 3, 'Chance': 1}
        if any(row.get(f'{key}{index}') != value for key, value in expected.items()):
            return False
    return 'Prop3' not in row
