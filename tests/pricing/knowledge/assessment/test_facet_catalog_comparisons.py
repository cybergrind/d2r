"""Native facet variants compare only with their explicit market catalogs."""

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.comparables import reject_reasons
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.market import normalize_listing
from tests.pricing.knowledge.assessment.item_bank.models import Item


VARIANTS = (
    (392, '2368934470', 'Lightning Death', 197, 53, 47, 330, 334, ((50, 1), (51, 74)), '780'),
    (393, '3308865831', 'Cold Death', 197, 59, 37, 331, 335, ((54, 24), (55, 38), (56, 3)), '781'),
    (394, '2991746251', 'Fire Death', 197, 56, 31, 329, 333, ((48, 17), (49, 45)), '782'),
    (395, '2470315921', 'Poison Death', 197, 92, 51, 332, 336, ((57, 187), (58, 187), (59, 50), (326, 1)), '784'),
    (396, '3699123392', 'Lightning Level-up', 199, 48, 41, 330, 334, ((50, 1), (51, 74)), '785'),
    (397, '3807838496', 'Cold Level-up', 199, 44, 43, 331, 335, ((54, 24), (55, 38), (56, 3)), '786'),
    (398, '2722722130', 'Fire Level-up', 199, 46, 29, 329, 333, ((48, 17), (49, 45)), '787'),
    (399, '2188191106', 'Poison Level-up', 199, 278, 23, 332, 336, ((57, 187), (58, 187), (59, 50), (326, 1)), None),
)


def capture(spec):
    table, _, _, event, skill, level, damage, pierce, fixed, _ = spec
    raw = ((damage, 0, 5), (pierce, 0, 5), (event, skill * 64 + level, 100))
    raw += tuple((stat, 0, value) for stat, value in fixed)
    return normalize(Item('Jewel', 'unique', 'Rainbow Facet', raw, named_table_id=table, complete=True).capture())


@pytest.mark.parametrize('spec', VARIANTS, ids=lambda spec: spec[2])
def test_complete_capture_binds_catalog_and_accepts_omitted_intrinsic_trigger(spec):
    facts = capture(spec)
    contract, gaps = NamedHandler().contract(facts, 'jewel')
    assert contract is not None, gaps
    assert contract.catalog_id == spec[1]
    if spec[-1] is not None:
        assert contract.intrinsic_properties[spec[-1]] == 100
    properties = {k: v for k, v in contract.properties.items() if k not in contract.intrinsic_properties}
    properties.update({'799': 'softcore', '800': False, '798': 'PC', '1854': 'reign of the warlock'})
    raw = {
        'id': 'facet',
        'item_id': spec[1],
        'seller_id': 'seller',
        'amount': 1,
        'properties': [
            {
                'property_id': int(k),
                'type': 'bool' if type(v) is bool else 'number' if type(v) in (int, float) else 'string',
                'bool' if type(v) is bool else 'number' if type(v) in (int, float) else 'string': v,
            }
            for k, v in properties.items()
        ],
        'prices': [{'name': 'Ist Rune', 'quantity': 1, 'group': 0}],
    }
    row = normalize_listing(
        raw, name='Rainbow Facet: ' + spec[2], category='uniques', source='fixture', currencies={'ist': 1}
    )
    assert reject_reasons(contract.to_dict(), row) == []
    for other in VARIANTS:
        if other[1] != spec[1]:
            assert 'Different or unknown market catalog variant.' in reject_reasons(
                contract.to_dict(), {**row, 'catalog_id': other[1]}
            )
    if spec[-1] is not None:
        row['properties'][spec[-1]] = 99
        assert reject_reasons(contract.to_dict(), row)
