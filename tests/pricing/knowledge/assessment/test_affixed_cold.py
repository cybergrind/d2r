from dataclasses import replace

from pricing.knowledge.assessment.handlers import HANDLERS
from pricing.knowledge.assessment.maintenance.replay import replay
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def cold(base='Long Sword', low=1, high=3, frames=75, rarity='rare'):
    return replace(
        facts(base, rarity),
        properties={'510': 0, '482': low, '483': high},
        stats={
            **{f'{s}:0': {'status': 'decoded', 'value': 0} for s in (17, 18)},
            '54:0': {'status': 'decoded', 'raw': low, 'value': low},
            '55:0': {'status': 'decoded', 'raw': high, 'value': high},
            '56:0': {'status': 'decoded', 'raw': frames, 'value': frames / 25, 'unit': 'seconds'},
        },
        projection_gaps=['No verified market mapping for native stat 56:0.'],
    )


def test_weapon_endpoints_can_prove_fixed_cold_duration():
    contract, gaps = HANDLERS['affixed'].contract(cold(), 'weapon')
    assert contract is not None, gaps
    assert contract.properties == {'510': 0, '482': 1, '483': 3}
    assert HANDLERS['affixed'].contract(cold(frames=50), 'weapon')[0] is None
    item = cold()
    missing = replace(item, projection_gaps=[], stats={k: v for k, v in item.stats.items() if k != '56:0'})
    assert HANDLERS['affixed'].contract(missing, 'weapon')[0] is None


def test_two_cold_affixes_must_not_be_mistaken_for_one_duration():
    # Small charms: Snowy prefix alone or prefix+suffix can share endpoints but not duration.
    item = cold('Small Charm', low=2, high=4, frames=25, rarity='magic')
    assert HANDLERS['affixed'].contract(item, 'charm')[0] is None


def test_cold_projection_requires_consistent_native_endpoints_and_units():
    item = cold()
    for key, change in [('54:0', {'raw': 2}), ('56:0', {'unit': None}), ('56:0', {'value': 5})]:
        changed = replace(item, projection_gaps=[], stats={**item.stats, key: {**item.stats[key], **change}})
        assert HANDLERS['affixed'].contract(changed, 'weapon')[0] is None
    assert HANDLERS['affixed'].contract(replace(item, properties={'510': 0, '482': 2, '483': 3}), 'weapon')[0] is None


def test_saved_dread_edge_can_form_exact_contract_after_all_modifier_projections():
    result = replay('dread_edge')['assessment']
    assert result['price_gaps'] == []
    assert result['contract']['properties']['535'] == 0.5
    assert result['contract']['properties']['536'] == 16.5
    assert result['contract']['properties']['482'] == 1
    assert result['contract']['properties']['483'] == 3
