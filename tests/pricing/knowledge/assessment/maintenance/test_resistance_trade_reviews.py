import copy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions
from tests.pricing.knowledge.assessment.item_bank.cases.metalgrid_trade import CASES
from tests.pricing.knowledge.assessment.maintenance.test_scalar_trade_reviews import PATH, data


IDENTITY = ('unique', 'Metalgrid')


def setup_review():
    doc, context = data(IDENTITY, CASES)
    doc['rows'][0]['scope'] = 'compound_named_jewelry'
    return doc, context


@pytest.mark.parametrize(
    'omit',
    [
        None,
        'roll-400-25-300',
        'roll-450-35-350',
        'component-19-None',
        'component-31-299',
        *('component-' + str(s) + '-None' for s in (39, 41, 43, 45)),
        *('unequal-' + str(s) for s in (39, 41, 43, 45)),
        'unknown-sockets',
    ],
)
def test_all_resistance_review_requires_joint_endpoints_and_every_native_member(omit):
    doc, context = setup_review()
    if omit:
        del doc['rows'][0]['cases']['metalgrid-trade/' + omit]
        if omit == 'roll-450-35-350':
            del doc['rows'][0]['cases']['metalgrid-trade/complete-perfect-no-price']
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == ('pending' if omit else 'reviewed')
    assert accepted == (set() if omit else {PATH})


@pytest.mark.parametrize('stat', ['39', '41', '43', '45'])
@pytest.mark.parametrize('mutation', ['missing', 'property', 'range', 'duplicate', 'layer'])
def test_all_resistance_review_requires_four_equal_native_definitions(stat, mutation):
    doc, context = setup_review()
    context['definitions'] = dict(context['definitions'])
    variants = copy.deepcopy(context['definitions'][IDENTITY])
    rolls = variants[0]['roll_ranges']
    if mutation == 'missing':
        del rolls[stat]
    if mutation == 'property':
        rolls[stat]['property'] = 'res-fire'
    if mutation == 'range':
        rolls[stat]['max'] = 34
    if mutation == 'duplicate':
        rolls['duplicate'] = copy.deepcopy(rolls[stat])
    if mutation == 'layer':
        rolls[stat]['layer'] = 1
    context['definitions'][IDENTITY] = variants
    doc['rows'][0]['definition_fingerprint'] = fingerprint(variants)
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize(
    ('field', 'value'),
    [('name', 'other'), ('property_id', '441'), ('shift', 8), ('op', 13), ('encode', 1), ('parameter_bits', 1)],
)
def test_all_resistance_review_cannot_ignore_member_metadata(field, value):
    doc, context = setup_review()
    context['stat_specs'] = copy.deepcopy(context['stat_specs'])
    context['stat_specs']['45'][field] = value
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize('scope', ['scalar_named_jewelry', 'compound_colossal_jewel'])
def test_all_resistance_compound_cannot_borrow_other_scopes(scope):
    doc, context = setup_review()
    doc['rows'][0]['scope'] = scope
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


def test_all_resistance_definition_must_match_its_native_shared_property():
    doc, context = setup_review()
    context['definitions'] = copy.deepcopy(context['definitions'])
    variants = context['definitions'][IDENTITY]
    variants[0]['game_definition']['prop2'] = 'res-fire'
    doc['rows'][0]['definition_fingerprint'] = fingerprint(variants)
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize('stat', ['39:0', '41:0', '43:0', '45:0'])
def test_shared_resistance_equality_checks_every_component(stat):
    from pricing.knowledge.assessment.maintenance.trade_compound_rolls import agree

    keys = ('39:0', '41:0', '43:0', '45:0')
    values = dict.fromkeys(keys, 35)
    assert agree(keys, tuple(values[k] for k in keys), ('all_resistances',))
    values[stat] = 25
    assert not agree(keys, tuple(values[k] for k in keys), ('all_resistances',))
