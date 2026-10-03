import pytest

from pricing.knowledge.assessment.mechanics.market_named_defense import with_variant_evidence


def contract(code='xvb'):
    return {'policy': 'named', 'rarity': 'unique', 'name': 'Waterwalk', 'ethereal': False, 'base_code': code}


def listing(ed=210, total=124, code=None):
    return {
        'rarity': 'unique',
        'name': 'Waterwalk',
        'base_code': code,
        'ethereal': None,
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': {'425': ed, '1855': total},
    }


def test_original_defense_proves_base_and_nonethereal_without_mutating_cache():
    row = listing()
    result = with_variant_evidence(contract(), row)
    assert result['base_code'] == 'xvb'
    assert result['ethereal'] is False
    assert result['base_upgrade'] is False
    assert row['base_code'] is None
    assert row['ethereal'] is None
    assert result['facet_basis']['ethereal']['observed_properties'] == {'425': 210, '1855': 124}


def test_explicit_upgraded_identity_has_its_own_defense_range():
    result = with_variant_evidence(contract('uvb'), listing(total=198, code='uvb'))
    assert result['ethereal'] is False
    assert result['base_upgrade'] is True


@pytest.mark.parametrize(
    ('ed', 'total'), [(179, 111), (211, 124), (210, 125), (210, 123), (210, 186), (True, 124), (210, 124.0)]
)
def test_illegal_or_ethereal_totals_do_not_prove_nonethereal(ed, total):
    result = with_variant_evidence(contract(), listing(ed, total))
    assert result['ethereal'] is None


@pytest.mark.parametrize(('key', 'value'), [('738', True), ('1216', True), ('930', 'Elite'), ('399', 124), ('402', 1)])
def test_contradictory_original_facets_cannot_be_overwritten(key, value):
    row = listing()
    row['properties'][key] = value
    result = with_variant_evidence(contract(), row)
    assert result['ethereal'] is None


def test_upgraded_total_without_base_identity_is_not_assumed_upgraded():
    assert with_variant_evidence(contract('uvb'), listing(total=198))['ethereal'] is None
