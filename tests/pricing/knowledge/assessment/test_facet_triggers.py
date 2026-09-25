from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.assessment.handlers.facet import facet_trigger
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('table_id', 'stat', 'skill', 'level', 'field'),
    [
        (392, 197, 53, 47, '780'),
        (393, 197, 59, 37, '781'),
        (394, 197, 56, 31, '782'),
        (395, 197, 92, 51, '784'),
        (396, 199, 48, 41, '785'),
        (397, 199, 44, 43, '786'),
        (398, 199, 46, 29, '787'),
    ],
)
def test_facet_trigger_requires_exact_native_chance_skill_level_and_event(table_id, stat, skill, level, field):
    key = f'{stat}:{skill * 64 + level}'
    item = replace(
        facts('Jewel', 'unique', 'Rainbow Facet'),
        provenance={'capture': {'item_identity': {'table': 'unique', 'table_id': table_id}}},
        stats={key: {'status': 'decoded', 'value': 100}},
    )
    definition, _ = resolve_named_definition(item)
    properties, consumed, gaps = facet_trigger(item, definition)
    assert properties == {field: 100}
    assert consumed == {key}
    assert not gaps
    for stats in (
        {},
        {key: {'status': 'decoded', 'value': 99}},
        {f'{stat}:{skill * 64 + level + 1}': {'status': 'decoded', 'value': 100}},
    ):
        assert facet_trigger(replace(item, stats=stats), definition)[2]


def test_named_handler_consumes_only_verified_facet_trigger_projection_gap():
    from pricing.knowledge.assessment.handlers.named import NamedHandler

    key = f'197:{53 * 64 + 47}'
    item = replace(
        facts('Jewel', 'unique', 'Rainbow Facet'),
        provenance={'capture': {'item_identity': {'table': 'unique', 'table_id': 392}}},
        stats={
            key: {'status': 'decoded', 'value': 100},
            '50:0': {'status': 'decoded', 'value': 1},
            '51:0': {'status': 'decoded', 'value': 74},
            '334:0': {'status': 'decoded', 'value': 5},
            '330:0': {'status': 'decoded', 'value': 5},
        },
        properties={'478': 1, '479': 74, '736': 5, '743': 5},
        projection_gaps=[f'No verified market mapping for native stat {key}.'],
    )
    contract, gaps = NamedHandler().contract(item, 'jewel')
    assert not gaps
    assert contract.properties['780'] == 100
    extra = replace(item, projection_gaps=[*item.projection_gaps, 'Unmapped poison duration'])
    assert NamedHandler().contract(extra, 'jewel')[0] is None
    assert NamedHandler().contract(replace(item, properties={'780': 47}), 'jewel')[0] is None
