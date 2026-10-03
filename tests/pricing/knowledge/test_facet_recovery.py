from copy import deepcopy

import pytest

from pricing.knowledge.facet_recovery import reconcile_facets


def historical_facet():
    return {
        'id': 'observation',
        'name': 'Rainbow Facet: Lightning Death',
        'catalog_id': '2368934470',
        'category': 'uniques',
        'rarity': 'unique',
        'seller_id': 'seller',
        'listing_id': 'listing',
        'observed_at': '2026-09-18',
        'ask_ist': 1,
        'properties': {'743': 5, '736': 5},
        'raw_properties': [
            {'property_id': 743, 'type': 'number', 'number': 5},
            {'property_id': 736, 'type': 'number', 'number': 5},
        ],
        'socket_contents': 'unknown',
    }


def test_recovery_preserves_market_evidence_other_items_and_is_idempotent():
    facet = historical_facet()
    original = deepcopy(facet)
    unrelated = {'id': 'other', 'name': 'Ring', 'custom': ['untouched']}
    output, changes = reconcile_facets([facet, unrelated])
    assert facet == original
    assert output[1] == unrelated
    assert len(changes) == 1
    assert output[0]['name'] == 'Rainbow Facet'
    assert output[0]['catalog_name'] == original['name']
    assert output[0]['ethereal'] is False
    assert output[0]['sockets'] == 0
    for key in ('id', 'seller_id', 'listing_id', 'observed_at', 'ask_ist', 'raw_properties', 'properties'):
        assert output[0][key] == original[key]
    second, changes = reconcile_facets(output)
    assert second == output
    assert changes == []


def test_recovery_rejects_properties_that_no_longer_match_raw_listing():
    facet = historical_facet()
    facet['properties']['743'] = 4
    with pytest.raises(ValueError, match='raw'):
        reconcile_facets([facet])


@pytest.mark.parametrize(('field', 'value'), [('catalog_id', '2935638020'), ('name', 'Rainbow Facet: Cold Death')])
def test_recovery_does_not_guess_generic_or_mismatched_variant(field, value):
    facet = historical_facet()
    facet[field] = value
    assert reconcile_facets([facet]) == ([facet], [])


def test_recovery_preserves_and_flags_conflicting_advertised_ethereal_state():
    facet = historical_facet()
    facet['properties']['738'] = True
    facet['raw_properties'].append({'property_id': 738, 'type': 'bool', 'bool': True})
    output, _ = reconcile_facets([facet])
    assert output[0]['ethereal'] is True
    assert output[0]['mechanics_conflicts']
