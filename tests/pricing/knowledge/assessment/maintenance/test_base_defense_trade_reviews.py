import copy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions
from tests.pricing.knowledge.assessment.item_bank.cases.horazon_legacy_trade import CASES
from tests.pricing.knowledge.assessment.maintenance.test_scalar_trade_reviews import PATH, data


IDENTITY = ('set', "Horazon's Legacy")


def setup_review():
    doc, context = data(IDENTITY, CASES)
    doc['rows'][0]['scope'] = 'base_defense_set_boots'
    return doc, context


@pytest.mark.parametrize(
    'omit',
    [
        None,
        '59-10-10-20',
        '68-15-15-30',
        'stat-31-None',
        'stat-31-58',
        'incomplete',
        'extra-16',
        'extra-214',
        'extra-215',
    ],
)
def test_base_defense_review_needs_joint_rolls_and_contribution_guards(omit):
    doc, context = setup_review()
    if omit:
        del doc['rows'][0]['cases']['horazon-legacy-trade/' + omit]
        if omit == '68-15-15-30':
            # This independent movement-speed case also covers the same legal maxima.
            del doc['rows'][0]['cases']['horazon-legacy-trade/conditional-walk']
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == ('pending' if omit else 'reviewed')
    assert accepted == (set() if omit else {PATH})


@pytest.mark.parametrize('mutation', ['item-bonus', 'conditional-defense', 'base-range', 'nonelite', 'socket-capacity'])
def test_base_defense_review_rejects_changed_native_definition(mutation):
    doc, context = setup_review()
    context['definitions'] = dict(context['definitions'])
    variants = copy.deepcopy(context['definitions'][IDENTITY])
    d = variants[0]
    if mutation == 'item-bonus':
        d['game_definition']['prop7'] = 'ac'
    if mutation == 'conditional-defense':
        d['game_definition']['aprop1a'] = 'ac%'
    if mutation == 'base-range':
        d['base_defense_range']['max'] = 69
    if mutation == 'nonelite':
        d['base_definition']['ultracode'] = 'different'
    if mutation == 'socket-capacity':
        d['base_definition']['gemsockets'] = 1
    context['definitions'][IDENTITY] = variants
    doc['rows'][0]['definition_fingerprint'] = fingerprint(variants)
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize('scope', ['scalar_named_jewelry', 'scalar_colossal_jewel', 'scalar_named_charm'])
def test_base_defense_does_not_borrow_scalar_scopes(scope):
    doc, context = setup_review()
    doc['rows'][0]['scope'] = scope
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


def test_base_defense_does_not_accept_shifted_native_armor_stat():
    doc, context = setup_review()
    context['stat_specs'] = copy.deepcopy(context['stat_specs'])
    context['stat_specs']['31']['shift'] = 8
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted
