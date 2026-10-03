"""Recognize paid combinations independently of their sellable roll thresholds."""


def matched_patterns(item, rows):
    from pricing.triage.engine import matches

    return [r for r in rows if r.get('pattern') and matches(item, {**r, **r['pattern']})]


def check_reason(item, rule):
    differences = []
    for key, condition in rule.get('properties', {}).items():
        value = item.get('properties', {}).get(key)
        label = rule.get('labels', {}).get(key, f'property {key}')
        if value is None:
            differences.append(f'{label} unreadable')
        elif isinstance(condition, dict):
            if 'min' in condition and value < condition['min']:
                differences.append(f'{label} {value:g} of {condition["min"]:g}')
            elif 'max' in condition and value > condition['max']:
                differences.append(f'{label} {value:g} outside bucket maximum {condition["max"]:g}')
        elif value != condition:
            differences.append(f'{label} {value} of {condition}')
    prefix = rule.get('pattern_label', 'Paid pattern complete')
    return prefix + '; ' + ('; '.join(differences) if differences else 'no supported price for these rolls')
