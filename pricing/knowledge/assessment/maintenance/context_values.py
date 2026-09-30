"""Finite context alternatives for validating explicit source-review branches."""


def _mentions(predicate, field):
    if predicate.get('field') == field:
        return True
    return any(_mentions(child, field) for key in ('all', 'any') for child in predicate.get(key, [])) or (
        'not' in predicate and _mentions(predicate['not'], field)
    )


def _values(predicate, field):
    if 'not' in predicate:
        if _mentions(predicate['not'], field):
            raise ValueError('Negated context is not a finite affirmative source branch')
        return None
    if 'all' in predicate:
        bounded = [value for child in predicate['all'] if (value := _values(child, field)) is not None]
        return frozenset.intersection(*bounded) if bounded else None
    if 'any' in predicate:
        branches = [_values(child, field) for child in predicate['any']]
        return None if any(value is None for value in branches) else frozenset().union(*branches)
    if predicate.get('field') == field:
        value = predicate.get('value')
        if predicate.get('op') != 'context_eq' or not isinstance(value, str) or not value.strip():
            raise ValueError('Unsupported context restriction')
        return frozenset({value})
    return None


def context_values(predicate, field):
    """Return a finite restriction, or None when it cannot safely be established.

    This does not prove other item/loadout predicates satisfiable. Source review
    and positive item cases are still required. An empty set cannot justify a use.
    """
    try:
        return _values(predicate, field)
    except ValueError:
        return None
