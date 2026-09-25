"""Compare verified equip requirements with the intended wearer's known attributes.

Meeting these numeric requirements does not prove class/slot legality or that a
build's companion conditions are satisfied.
"""

from pricing.knowledge.assessment.domain.context import AssessmentContext


def assess_requirements(requirements, side, loadout=None):
    context = AssessmentContext.from_input(loadout)
    prefix = {'player': 'player', 'merc': 'mercenary'}.get(side)
    checks, shortfalls = [], []
    for attribute in ('level', 'strength', 'dexterity'):
        required = requirements.get(attribute)
        observed = getattr(context, f'{prefix}_{attribute}', None) if prefix else None
        valid = type(required) is int and required >= 0
        status = (
            'unknown'
            if not valid or not prefix
            else 'met'
            if required == 0
            else 'unknown'
            if observed is None
            else 'met'
            if observed >= required
            else 'unmet'
        )
        checks.append({'attribute': attribute, 'required': required, 'observed': observed, 'status': status})
        if status == 'unmet':
            shortfalls.append(f'{prefix.title()} {attribute} {observed}; requires {required}.')
    statuses = {check['status'] for check in checks}
    return {
        'status': 'unmet' if 'unmet' in statuses else 'unknown' if 'unknown' in statuses else 'met',
        'checks': checks,
        'shortfalls': shortfalls,
    }
