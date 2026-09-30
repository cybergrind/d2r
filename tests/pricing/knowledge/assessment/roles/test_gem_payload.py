from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.roles.predicates import evaluate, validate
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def gemmed(base='Mask', count=3):
    gem = next(b for b in metadata()['bases'].values() if b['name'] == 'Perfect Topaz')
    return replace(
        facts(base),
        sockets=count,
        socket_contents='filled',
        filled_sockets=count,
        empty_sockets=0,
        socket_items=[
            {'name': gem['name'], 'base_code': gem['code'], 'unit_id': i + 1, 'position': i} for i in range(count)
        ],
    )


@pytest.mark.parametrize(('base', 'count'), [('Mask', 3), ('Gothic Plate', 4)])
def test_exact_gems_require_correct_grade_and_complete_distinct_links(base, count):
    rule = {'op': 'socket_gems_equal', 'value': ['Perfect Topaz'] * count}
    validate(rule)
    item = gemmed(base, count)
    assert evaluate(rule, item).truth == 'true'
    flawed = next(b for b in metadata()['bases'].values() if b['name'] == 'Flawless Topaz')
    wrong = {**item.socket_items[0], 'name': flawed['name'], 'base_code': flawed['code']}
    assert evaluate(rule, replace(item, socket_items=[wrong, *item.socket_items[1:]])).truth == 'false'
    for changed in (
        replace(item, filled_sockets=None, empty_sockets=None, socket_items=item.socket_items[:-1]),
        replace(item, socket_contents='empty'),
        replace(item, socket_items=[{**c, 'unit_id': 1} for c in item.socket_items]),
        replace(item, socket_items=[{**c, 'position': 0} for c in item.socket_items]),
        replace(item, socket_items=[{**c, 'base_code': flawed['code']} for c in item.socket_items]),
    ):
        assert evaluate(rule, changed).truth == 'unknown'


@pytest.mark.parametrize(
    'value', [[], ['Perfect Topaz'] * 7, ['Topaz of Greed'], ['Ist Rune'], ['Jewel'], 'Perfect Topaz']
)
def test_exact_gem_schema_rejects_non_gems_and_invalid_counts(value):
    with pytest.raises(ValueError, match='exact gem payload'):
        validate({'op': 'socket_gems_equal', 'value': value})
