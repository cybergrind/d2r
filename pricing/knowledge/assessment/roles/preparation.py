"""Connect explicit build destinations to legal routes without simulating stats."""


def dependency_upgrade(rule, paths):
    # Compound predicates may include rerolled defense or changed requirements.
    # Do not mark them achievable by substituting only a hypothetical base code.
    if set(rule) != {'op', 'field', 'value'} or rule['op'] != 'fact_eq' or rule['field'] != 'base_code':
        return None
    return next((path for path in paths if path.target_code == rule['value']), None)


def describe_upgrade(path):
    steps = [f'{step["target_name"]}: ' + ' + '.join(step['resources']) for step in path.steps]
    return 'Upgrade to ' + '; then '.join(steps) + '.'
