import copy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions
from tests.pricing.knowledge.assessment.item_bank.cases.girth_trade import CASES
from tests.pricing.knowledge.assessment.maintenance.test_scalar_trade_reviews import PATH, data


IDENTITY = ('set', "Trang-Oul's Girth")


def setup_review():
    doc, context = data(IDENTITY, CASES)
    doc['rows'][0]['scope'] = 'total_defense_set_belt'
    return doc, context


@pytest.mark.parametrize(
    'omit',
    [
        None,
        'roll-134-25',
        'roll-134-49',
        'roll-134-50',
        'component-9-None',
        'component-31-133',
        'fractional-mana',
        'incomplete',
        'extra-defense-16',
        'extra-defense-214',
        'extra-defense-215',
    ],
)
def test_total_defense_review_requires_decoded_mana_thresholds_and_capture_guards(omit):
    doc, context = setup_review()
    if omit:
        del doc['rows'][0]['cases']['girth-trade/' + omit]
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == ('pending' if omit else 'reviewed')
    assert accepted == (set() if omit else {PATH})


@pytest.mark.parametrize(
    'mutation',
    [
        'conditional-mana',
        'conditional-defense',
        'base-range',
        'nonelite',
        'socket-capacity',
        'flat-range',
        'flat-property',
        'mana-range',
    ],
)
def test_total_defense_review_rejects_changed_native_semantics(mutation):
    doc, context = setup_review()
    context['definitions'] = dict(context['definitions'])
    variants = copy.deepcopy(context['definitions'][IDENTITY])
    d = variants[0]
    if mutation == 'conditional-mana':
        d['game_definition']['aprop2a'] = 'mana'
    if mutation == 'conditional-defense':
        d['game_definition']['aprop2a'] = 'ac'
    if mutation == 'base-range':
        d['base_definition']['maxac'] = 67
    if mutation == 'nonelite':
        d['base_definition']['ultracode'] = 'other'
    if mutation == 'socket-capacity':
        d['base_definition']['gemsockets'] = 1
    if mutation == 'flat-range':
        d['roll_ranges']['31']['max'] = 101
    if mutation == 'flat-property':
        d['game_definition']['prop1'] = 'ac%'
    if mutation == 'mana-range':
        d['roll_ranges']['9']['max'] = 51
    context['definitions'][IDENTITY] = variants
    doc['rows'][0]['definition_fingerprint'] = fingerprint(variants)
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize(
    ('stat', 'field', 'value'),
    [
        ('9', 'shift', 0),
        ('9', 'encode', 1),
        ('9', 'name', 'other'),
        ('9', 'property_id', '401'),
        ('31', 'shift', 8),
        ('31', 'op', 1),
    ],
)
def test_total_defense_review_cannot_ignore_native_encoding(stat, field, value):
    doc, context = setup_review()
    context['stat_specs'] = copy.deepcopy(context['stat_specs'])
    context['stat_specs'][stat][field] = value
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize(
    'scope', ['scalar_named_jewelry', 'scalar_colossal_jewel', 'scalar_named_charm', 'base_defense_set_boots']
)
def test_total_defense_requires_its_explicit_family_scope(scope):
    doc, context = setup_review()
    doc['rows'][0]['scope'] = scope
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted
