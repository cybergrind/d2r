from copy import deepcopy

import pytest

from pricing.knowledge.definition_store import catalog
from pricing.knowledge.market import normalize_facets, normalize_listing


VARIANTS = (
    (392, '2368934470', 'Lightning Death'),
    (393, '3308865831', 'Cold Death'),
    (394, '2991746251', 'Fire Death'),
    (395, '2470315921', 'Poison Death'),
    (396, '3699123392', 'Lightning Level-up'),
    (397, '3807838496', 'Cold Level-up'),
    (398, '2722722130', 'Fire Level-up'),
    (399, '2188191106', 'Poison Level-up'),
)


def row(identity, label):
    raw = {'id': 'fixture', 'item_id': identity, 'seller_id': 'seller', 'amount': 1, 'properties': [], 'prices': []}
    return normalize_listing(raw, name='Rainbow Facet: ' + label, category='uniques', source='fixture')


@pytest.mark.parametrize(('table_id', 'identity', 'label'), VARIANTS)
def test_verified_facet_alias_retains_variant_and_supplies_shared_jewel_mechanics(table_id, identity, label):
    result = row(identity, label)
    definition = next(v for v in catalog().named_variants['unique', 'Rainbow Facet'] if v['table_id'] == table_id)
    assert result['name'] == 'Rainbow Facet'
    assert result['catalog_name'] == 'Rainbow Facet: ' + label
    assert result['catalog_id'] == identity
    assert result['facet_basis']['identity']['table_id'] == table_id
    assert result['base_code'] == definition['base_code']
    assert result['ethereal'] is False
    assert result['sockets'] == 0
    assert result['socket_contents'] == 'empty'
    before = deepcopy(result)
    normalize_facets(result)
    assert result == before


@pytest.mark.parametrize(('table_id', 'identity', 'label'), VARIANTS)
def test_name_and_catalog_must_agree_before_facet_canonicalization(table_id, identity, label):
    other = next(value for _, value, _ in VARIANTS if value != identity)
    assert row(other, label)['name'] == 'Rainbow Facet: ' + label
    assert row('2935638020', label)['name'] == 'Rainbow Facet: ' + label


@pytest.mark.parametrize(('table_id', 'identity', 'label'), VARIANTS)
@pytest.mark.parametrize(
    ('prop', 'kind', 'value', 'field'), [(738, 'bool', True, 'ethereal'), (402, 'number', 1, 'sockets')]
)
def test_native_facet_alias_never_erases_conflicting_advertised_variants(
    table_id, identity, label, prop, kind, value, field
):
    raw = {
        'id': 'fixture',
        'item_id': identity,
        'seller_id': 'seller',
        'amount': 1,
        'properties': [{'property_id': prop, 'type': kind, kind: value}],
        'prices': [],
    }
    result = normalize_listing(raw, name='Rainbow Facet: ' + label, category='uniques', source='fixture')
    assert result[field] == value
    assert result.get('mechanics_conflicts')


@pytest.mark.parametrize(
    ('field', 'value'),
    [('prop1', 'dmg-cold'), ('prop4', 'levelup-skill'), ('par4', 'Nova'), ('min4', 99), ('max4', 48)],
)
def test_facet_catalog_refuses_changed_native_discriminators(field, value):
    from pricing.knowledge.assessment.domain.facts import thaw
    from pricing.knowledge.market_facet_catalog import facet_catalog

    definition = thaw(next(v for v in catalog().named_variants['unique', 'Rainbow Facet'] if v['table_id'] == 392))
    definition['game_definition'][field] = value
    assert facet_catalog(definition) is None


def test_missing_native_definitions_leave_facet_alias_unresolved(monkeypatch):
    import pricing.knowledge.market_facet_catalog as facets

    def missing():
        raise OSError('definitions unavailable')

    monkeypatch.setattr(facets, 'catalog', missing)
    result = row('2368934470', 'Lightning Death')
    assert result['name'] == 'Rainbow Facet: Lightning Death'
