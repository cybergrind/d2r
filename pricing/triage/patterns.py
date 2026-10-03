"""Recognize paid combinations independently of their sellable roll thresholds."""


def matched_patterns(item, rows, *, socket_preparation=None):
    from pricing.triage.engine import matches

    return [
        r
        for r in rows
        if r.get('pattern') and matches(item, {**r, **r['pattern']}) and preparation_matches(r, socket_preparation)
    ]


def preparation_matches(rule, preparation):
    targets = rule.get('required_socket_counts')
    if targets is None:
        return True
    if not preparation:
        return False
    possible = preparation['larzuk'] + preparation['cube']
    return any(target in possible for target in targets)


def support_pattern(rule):
    """Require positive supporting rolls without weakening counts or structural gates."""
    result = dict(rule)
    if 'properties' in rule:
        result['properties'] = {
            key: condition | {'min': 1} if isinstance(condition, dict) and condition.get('min', 0) > 1 else condition
            for key, condition in rule['properties'].items()
        }
    if group := rule.get('at_least'):
        result['at_least'] = group | {'of': [support_pattern(option) for option in group['of']]}
    return result


SUPPORT_LABELS = {
    '418': 'life',
    '400': 'mana',
    '437': 'strength',
    '429': 'dexterity',
    '427': 'fire resistance',
    '428': 'lightning resistance',
    '426': 'cold resistance',
    '401': 'poison resistance',
    '441': 'all resistances',
}


def roll_differences(item, rule, labels):
    from pricing.triage.engine import matches

    differences = []
    for key, condition in rule.get('properties', {}).items():
        value = item.get('properties', {}).get(key)
        label = labels.get(key, f'property {key}')
        if value is None:
            differences.append(f'{label} unreadable')
        elif isinstance(condition, dict):
            if 'min' in condition and value < condition['min']:
                differences.append(f'{label} {value:g} of {condition["min"]:g}')
            elif 'max' in condition and value > condition['max']:
                differences.append(f'{label} {value:g} outside bucket maximum {condition["max"]:g}')
        elif value != condition:
            differences.append(f'{label} {value} of {condition}')
    if (group := rule.get('at_least')) and not matches(item, {'at_least': group}):
        for option in group['of']:
            if matches(item, support_pattern(option)) and not matches(item, option):
                differences.extend(roll_differences(item, option, labels))
    return differences


def check_reason(item, rule):
    differences = roll_differences(item, rule, SUPPORT_LABELS | rule.get('labels', {}))
    prefix = rule.get('pattern_label', 'Paid pattern complete')
    return prefix + '; ' + ('; '.join(differences) if differences else 'no supported price for these rolls')
