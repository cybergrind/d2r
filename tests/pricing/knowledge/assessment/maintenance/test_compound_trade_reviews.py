import copy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions
from tests.pricing.knowledge.assessment.item_bank.cases.protector_trade import CASES
from tests.pricing.knowledge.assessment.maintenance.test_scalar_trade_reviews import PATH, data


IDENTITY = ('unique', "Protector's Stone")


def compound_data():
    doc, context = data(IDENTITY, CASES)
    doc['rows'][0]['scope'] = 'compound_colossal_jewel'
    return doc, context


@pytest.mark.parametrize(
    'omit',
    [
        None,
        '30-5-3-15-25',
        '50-10-5-35-50',
        'stat-17-30',
        'stat-18-30',
        'stat-17-None',
        'stat-18-None',
        'stat-366-11',
        'unknown-sockets',
    ],
)
def test_compound_review_requires_equal_ed_endpoints_and_each_missing_mismatched_component(omit):
    doc, context = compound_data()
    if omit:
        del doc['rows'][0]['cases']['protector-trade/' + omit]
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == ('pending' if omit else 'reviewed')
    assert accepted == (set() if omit else {PATH})


@pytest.mark.parametrize('scope', ['scalar_colossal_jewel', 'scalar_named_jewelry'])
def test_compound_roll_cannot_use_an_independent_scalar_review(scope):
    doc, context = compound_data()
    doc['rows'][0]['scope'] = scope
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize('mutation', ['base', 'property', 'range', 'missing', 'group', 'duplicate'])
def test_compound_review_requires_native_paired_definition(mutation):
    doc, context = compound_data()
    context['definitions'] = dict(context['definitions'])
    definition = copy.deepcopy(context['definitions'][IDENTITY])
    row = definition[0]
    if mutation == 'base':
        row['base_name'] = 'Ring'
    if mutation == 'property':
        row['roll_ranges']['18']['property'] = 'other'
    if mutation == 'range':
        row['roll_ranges']['18']['max'] = 49
    if mutation == 'missing':
        del row['roll_ranges']['18']
    if mutation == 'group':
        row['property_groups'] = [{'unreviewed': True}]
    if mutation == 'duplicate':
        row['roll_ranges']['extra'] = copy.deepcopy(row['roll_ranges']['18'])
    context['definitions'][IDENTITY] = definition
    doc['rows'][0]['definition_fingerprint'] = fingerprint(definition)
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('name', 'other'),
        ('op', 8),
        ('op_param', 1),
        ('op_base', 'level'),
        ('shift', 8),
        ('encode', 1),
        ('parameter_bits', 2),
    ],
)
def test_compound_does_not_allow_unreviewed_ed_representation(field, value):
    doc, context = compound_data()
    context['stat_specs'] = copy.deepcopy(context['stat_specs'])
    context['stat_specs']['18'][field] = value
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


def test_compound_scope_cannot_ignore_missing_compound_policy_guard():
    doc, context = compound_data()
    context['policies'] = dict(context['policies'])
    policy = copy.deepcopy(context['policies'][IDENTITY])
    policy['trade_qualification']['compound_stats'] = []
    context['policies'][IDENTITY] = policy
    doc['rows'][0]['policy_fingerprint'] = fingerprint(policy)
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


def test_compound_partitions_include_thresholds_on_either_native_component():
    from pricing.knowledge.assessment.maintenance.trade_compound_rolls import legal_vectors
    from pricing.knowledge.assessment.maintenance.trade_scalar_jewelry import specification

    _, context = compound_data()
    policy = copy.deepcopy(context['policies'][IDENTITY])
    policy['trade_qualification']['bands'] = [
        {
            'status': 'premium',
            'reason': 'Test partition',
            'when': {
                'all': [
                    {'op': 'stat_at_least', 'key': '17:0', 'value': 40},
                    {'op': 'stat_at_least', 'key': '18:0', 'value': 45},
                ]
            },
        }
    ]
    spec = specification(
        policy,
        context['definitions'][IDENTITY],
        context['stat_specs'],
        allowed_bases=('Colossal Jewel',),
        compounds=('enhanced_damage',),
    )
    keys = tuple(sorted(spec[1]))
    vectors = tuple(legal_vectors(keys, spec[2], ('enhanced_damage',)))
    assert {v[keys.index('17:0')] for v in vectors} == {30, 39, 40, 44, 45, 50}
    assert all(v[keys.index('17:0')] == v[keys.index('18:0')] for v in vectors)


def test_compound_review_rejects_duplicate_native_material_field_even_with_updated_case_hash():
    doc, context = compound_data()
    key = 'protector-trade/50-10-5-35-50'
    case = context['receipts'][PATH]['cases'][key]['trade_case']
    case['item']['raw_stats'] = (*case['item']['raw_stats'], (17, 0, 50))
    doc['rows'][0]['cases'][key] = fingerprint(case)
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted
