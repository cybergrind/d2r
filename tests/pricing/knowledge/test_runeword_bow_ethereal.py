import pytest

from pricing.knowledge.market import normalize_listing


def listing(word, base, ethereal=None):
    props = [{'property_id': 1888, 'property': 'Base Item (Ranged) 4', 'type': 'string', 'string': base}]
    if ethereal is not None:
        props.append({'property_id': 738, 'type': 'bool', 'bool': ethereal})
    raw = {'id': 'fixture', 'amount': 1, 'properties': props}
    return normalize_listing(raw, name=word, category='runewords', source='fixture')


@pytest.mark.parametrize(
    ('word', 'base'), [('Brand', 'Grand Matron Bow'), ('Faith', 'Diamond Bow'), ('Insight', 'Blade Bow')]
)
def test_verified_completed_bow_recipe_has_nonethereal_base(word, base):
    row = listing(word, base)
    assert row['ethereal'] is False
    assert row['sockets'] == 4
    assert row['socket_contents'] == 'filled'
    assert '738' not in row['properties']
    assert row['facet_basis']['ethereal']['kind'] == 'bow_ethereal_mechanics'
    bad = listing(word, base, True)
    assert bad['ethereal'] is True
    assert bad['mechanics_conflicts']


@pytest.mark.parametrize(
    ('word', 'base'),
    [('Brand', 'No base'), ('Brand', 'Monarch'), ('Unknown word', 'Blade Bow'), ('Insight', 'Thresher')],
)
def test_no_ethereal_inference_from_word_name_or_unverified_bow_selector(word, base):
    assert listing(word, base).get('ethereal') is None
