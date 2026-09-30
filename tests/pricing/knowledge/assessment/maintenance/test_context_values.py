import pytest


def merc(value):
    return {'op': 'context_eq', 'field': 'mercenary_type', 'value': value}


@pytest.mark.parametrize(
    ('predicate', 'expected'),
    [
        (merc('Act 2 Might'), frozenset({'Act 2 Might'})),
        ({'any': [merc('Act 2 Might'), merc('Act 5 Frenzy')]}, frozenset({'Act 2 Might', 'Act 5 Frenzy'})),
        (
            {'all': [merc('Act 2 Might'), {'op': 'fact_eq', 'field': 'identified', 'value': True}]},
            frozenset({'Act 2 Might'}),
        ),
        ({'any': [merc('Act 2 Might'), {'op': 'fact_eq', 'field': 'identified', 'value': True}]}, None),
        ({'all': [merc('Act 2 Might'), merc('Act 5 Frenzy')]}, frozenset()),
        (
            {'all': [{'any': [merc('Act 2 Might'), merc('Act 5 Frenzy')]}, merc('Act 2 Might')]},
            frozenset({'Act 2 Might'}),
        ),
        ({'not': merc('Act 2 Might')}, None),
        ({'all': [merc('Act 2 Might'), {'not': merc('Act 2 Might')}]}, None),
        ({'all': []}, None),
        ({'any': []}, frozenset()),
        ({'op': 'context_eq', 'field': 'player_class', 'value': 'Paladin'}, None),
    ],
)
def test_finite_context_constraints_do_not_accept_optional_or_unbounded_branches(predicate, expected):
    from pricing.knowledge.assessment.maintenance.context_values import context_values

    assert context_values(predicate, 'mercenary_type') == expected
