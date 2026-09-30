"""Compare verified equip requirements with the intended wearer's known attributes.

Meeting these numeric requirements does not prove class/slot legality or that a
build's companion conditions are satisfied.
"""

from pricing.knowledge.assessment.domain.context import AssessmentContext
from pricing.knowledge.assessment.domain.facts import FactStatus
from pricing.knowledge.item_requirements import fixed_requirements


def named_requirements(facts, definition, reviewed):
    """Apply observed ethereality to reviewed original-base equip costs.

    D2MOO Items.cpp computes socket level requirements from actual child items;
    empty sockets introduce neither child levels nor requirement modifiers.
    Filled, conflicting and unknown occupancy need separate variant evaluation.
    """
    sockets = facts.socket_state
    original_empty = (
        facts.base_code in definition['base_codes']
        and type(facts.ethereal) is bool
        and facts.socket_contents == 'empty'
        and sockets.total.status == FactStatus.KNOWN
        and sockets.occupied.status == FactStatus.KNOWN
        and sockets.occupied.value == 0
    )
    if not original_empty or not reviewed:
        return {}
    native = definition['game_definition']
    modifiers = [
        {'property': value, 'min': native.get('min' + key[4:]), 'max': native.get('max' + key[4:])}
        for key, value in native.items()
        if key.startswith('prop') and key[4:].isdigit() and value in ('ease', 'ethereal')
    ]
    inherent_ethereal = any(m['property'] == 'ethereal' and m['min'] == m['max'] == 1 for m in modifiers)
    if inherent_ethereal and facts.ethereal is False:
        return {}
    if facts.ethereal is False:
        return dict(reviewed)
    base = definition['base_definition']
    # Recompute from the base, not the already adjusted review: intrinsic
    # ethereality must never subtract ten twice. Percentage adjustment precedes it.
    requirements = fixed_requirements(
        {'strength': base.get('reqstr', 0), 'dexterity': base.get('reqdex', 0)},
        reviewed.get('level'),
        [*modifiers, {'property': 'ethereal', 'min': 1, 'max': 1}],
    )
    return requirements if all(type(v) is int and v >= 0 for v in requirements.values()) else {}


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
