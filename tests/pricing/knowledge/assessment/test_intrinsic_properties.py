from dataclasses import replace

from pricing.knowledge.assessment.comparables import reject_reasons
from pricing.knowledge.assessment.handlers.runeword import RunewordHandler
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def spirit():
    return replace(
        facts('Crystal Sword'),
        name='Spirit',
        runeword='Spirit',
        sockets=4,
        socket_contents='filled',
        properties={'520': 35, '400': 112, '818': 8, '587': 2},
        stats={
            f'{s}:0': {'id': s, 'value': v, 'status': 'decoded', 'market_property': p}
            for s, v, p in [(105, 35, '520'), (9, 112, '400'), (147, 8, '818'), (127, 2, '587')]
        },
    )


def listing(contract, properties):
    return {
        **{
            k: contract[k]
            for k in ('name', 'rarity', 'ethereal', 'sockets', 'socket_contents', 'base_code', 'base_rarity')
        },
        'properties': properties,
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'seller',
        'ask_ist': 1,
    }


def test_fixed_recipe_bonus_may_be_omitted_but_never_contradicted():
    contract, gaps = RunewordHandler().contract(spirit(), 'weapon')
    assert not gaps
    data = contract.to_dict()
    assert data['intrinsic_properties'] == {'587': 2}
    properties = {'520': 35, '400': 112, '818': 8}
    assert not reject_reasons(data, listing(data, properties))
    assert reject_reasons(data, listing(data, properties | {'587': 3}))
    assert reject_reasons(data, listing(data, {'400': 112, '818': 8}))
    assert reject_reasons(data, listing(data, properties | {'99999': 1}))


def test_augmented_or_unmapped_totals_are_not_intrinsic_recipe_bonuses():
    item = spirit()
    stats = {**item.stats, '127:0': {**item.stats['127:0'], 'value': 3}}
    contract, _ = RunewordHandler().contract(
        replace(item, stats=stats, properties={**item.properties, '587': 3}), 'weapon'
    )
    assert contract.intrinsic_properties == {}
