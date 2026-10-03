import json

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions
from pricing.knowledge.assessment.policies.named_tiers import RULES, _policies
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.cases.bk_trade import CASES
from tests.pricing.knowledge.assessment.item_bank.trade_checks import trade_case


IDENTITY = ('unique', "Bul-Kathos' Wedding Band")
PATH = 'pricing/data/report-receipts/scalar-jewelry-trade.json'


def data(identity=IDENTITY, case_set=CASES):
    policies = _policies(RULES.read_bytes())
    definitions = {key: thaw(value) for key, value in catalog().named_variants.items()}
    cases = {
        c.id: {
            'trade_case': trade_case(c),
            'covers': list(c.covers),
            'phases': dict.fromkeys(('setup', 'call', 'teardown'), 'passed'),
        }
        for c in case_set
    }
    review = {
        'quality': identity[0],
        'name': identity[1],
        'scope': 'scalar_named_jewelry',
        'policy_fingerprint': fingerprint(policies[identity]),
        'definition_fingerprint': fingerprint(definitions[identity]),
        'receipt': PATH,
        'review_date': '2026-10-01',
        'reason': 'All leech roll/variant boundaries reviewed.',
        'cases': {key: fingerprint(value['trade_case']) for key, value in cases.items()},
    }
    receipt = {
        'schema_version': 1,
        'generation': 'selected',
        'exitstatus': 0,
        'sources_unchanged': True,
        'inputs': {},
        'finished_inputs': {},
        'cases': cases,
    }
    return {'schema_version': 1, 'rows': [review]}, {
        'policies': policies,
        'definitions': definitions,
        'receipts': {PATH: receipt},
        'generation': 'selected',
        'inputs': {},
        'stat_specs': metadata()['stats'],
    }


def test_scalar_review_covers_legal_rolls_thresholds_missing_rolls_and_variants():
    doc, context = data()
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'reviewed'
    assert accepted == {PATH}


@pytest.mark.parametrize(
    'suffix', ['leech-3', 'leech-4', 'leech-5', 'leech-2', 'leech-6', 'missing-leech', 'unknown-ethereal']
)
def test_scalar_review_stays_open_if_a_required_boundary_was_not_executed(suffix):
    doc, context = data()
    key = next(key for key in doc['rows'][0]['cases'] if key.endswith('/' + suffix))
    del doc['rows'][0]['cases'][key]
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


def test_scalar_review_does_not_assume_raw_shifted_or_encoded_stats_are_plain_integers():
    doc, context = data()
    context['stat_specs'] = json.loads(json.dumps(context['stat_specs']))
    context['stat_specs']['60']['shift'] = 8
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize(
    'omit', [None, 'dex-20-ar-250', 'dex-20-ar-249', 'dex-19-ar-250', 'dex-15-ar-150', 'stat-2-None', 'stat-19-None']
)
def test_joint_raven_threshold_requires_executed_mixed_rolls_and_each_missing_component(omit):
    from tests.pricing.knowledge.assessment.item_bank.cases.raven_trade import CASES as RAVEN

    identity = ('unique', 'Raven Frost')
    doc, context = data(identity, RAVEN)
    if omit:
        del doc['rows'][0]['cases']['raven-trade/' + omit]
    rows, accepted = review_dimensions(doc, **context)
    assert rows[identity]['state'] == ('pending' if omit else 'reviewed')
    assert bool(accepted) is (omit is None)


def test_scalar_review_does_not_close_an_unresolved_legal_roll_branch():
    doc, context = data()
    context['policies'] = dict(context['policies'])
    policy = json.loads(json.dumps(context['policies'][IDENTITY]))
    policy['trade_qualification']['default_status'] = 'unresolved'
    context['policies'][IDENTITY] = policy
    doc['rows'][0]['policy_fingerprint'] = fingerprint(policy)
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


def test_joint_review_cannot_treat_correlated_native_rolls_as_independent():
    from tests.pricing.knowledge.assessment.item_bank.cases.raven_trade import CASES as RAVEN

    identity = ('unique', 'Raven Frost')
    doc, context = data(identity, RAVEN)
    context['definitions'] = dict(context['definitions'])
    variants = json.loads(json.dumps(context['definitions'][identity]))
    variants[0]['roll_ranges']['19']['property'] = variants[0]['roll_ranges']['2']['property']
    context['definitions'][identity] = variants
    doc['rows'][0]['definition_fingerprint'] = fingerprint(variants)
    rows, accepted = review_dimensions(doc, **context)
    assert rows[identity]['state'] == 'pending'
    assert not accepted


def test_sling_review_covers_plain_item_energy_despite_player_mana_operation():
    from tests.pricing.knowledge.assessment.item_bank.cases.sling_trade import CASES as SLING

    identity = ('unique', 'Sling')
    doc, context = data(identity, SLING)
    rows, accepted = review_dimensions(doc, **context)
    assert rows[identity]['state'] == 'reviewed'
    assert accepted == {PATH}


@pytest.mark.parametrize(('field', 'value'), [('name', 'other'), ('op', 9), ('op_param', 1), ('shift', 8)])
def test_energy_exception_does_not_allow_unreviewed_encodings(field, value):
    from tests.pricing.knowledge.assessment.item_bank.cases.sling_trade import CASES as SLING

    identity = ('unique', 'Sling')
    doc, context = data(identity, SLING)
    context['stat_specs'] = json.loads(json.dumps(context['stat_specs']))
    context['stat_specs']['1'][field] = value
    rows, accepted = review_dimensions(doc, **context)
    assert rows[identity]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize('omit', [None, '5-5-25-10-8', '10-10-40-15-12', 'stat-357-None', 'stat-105-11', 'stat-77-16'])
def test_entropy_five_axis_review_requires_joint_limits_and_each_component(omit):
    from tests.pricing.knowledge.assessment.item_bank.cases.entropy_trade import CASES as ENTROPY

    identity = ('unique', 'Entropy Locket')
    doc, context = data(identity, ENTROPY)
    if omit:
        del doc['rows'][0]['cases']['entropy-trade/' + omit]
    rows, accepted = review_dimensions(doc, **context)
    assert rows[identity]['state'] == ('pending' if omit else 'reviewed')
    assert accepted == (set() if omit else {PATH})


@pytest.mark.parametrize(
    ('field', 'value'), [('name', 'other'), ('op', 13), ('op_param', 1), ('op_base', 'level'), ('shift', 8)]
)
def test_max_mana_exception_does_not_allow_other_operated_or_scaled_values(field, value):
    from tests.pricing.knowledge.assessment.item_bank.cases.entropy_trade import CASES as ENTROPY

    identity = ('unique', 'Entropy Locket')
    doc, context = data(identity, ENTROPY)
    context['stat_specs'] = json.loads(json.dumps(context['stat_specs']))
    context['stat_specs']['77'][field] = value
    rows, accepted = review_dimensions(doc, **context)
    assert rows[identity]['state'] == 'pending'
    assert not accepted


def test_scalar_partitions_keep_endpoints_and_both_sides_of_real_thresholds():
    from pricing.knowledge.assessment.maintenance.trade_scalar_jewelry import specification

    identity = ('unique', 'Sling')
    from tests.pricing.knowledge.assessment.item_bank.cases.sling_trade import CASES as SLING

    _, context = data(identity, SLING)
    spec = specification(context['policies'][identity], context['definitions'][identity], context['stat_specs'])
    assert spec[2] == {'358:0': {3, 4, 5}, '1:0': {10, 15}, '80:0': {10, 20}}


@pytest.mark.parametrize('omit', [None, '9-10-3-15-25', '10-9-3-15-25', '10-10-5-35-50', 'stat-85-None', 'stat-79-51'])
def test_colossal_scope_requires_joint_core_thresholds_and_secondary_boundaries(omit):
    from tests.pricing.knowledge.assessment.item_bank.cases.defender_fire_trade import CASES as DEFENDER

    identity = ('unique', "Defender's Fire")
    doc, context = data(identity, DEFENDER)
    doc['rows'][0]['scope'] = 'scalar_colossal_jewel'
    if omit:
        del doc['rows'][0]['cases']['defender-fire-trade/' + omit]
    rows, accepted = review_dimensions(doc, **context)
    assert rows[identity]['state'] == ('pending' if omit else 'reviewed')
    assert accepted == (set() if omit else {PATH})


@pytest.mark.parametrize('colossal', [False, True])
def test_jewelry_and_colossal_scopes_cannot_borrow_each_others_base_family(colossal):
    from tests.pricing.knowledge.assessment.item_bank.cases.defender_fire_trade import CASES as DEFENDER

    identity = ('unique', "Defender's Fire") if colossal else IDENTITY
    doc, context = data(identity, DEFENDER if colossal else CASES)
    doc['rows'][0]['scope'] = 'scalar_named_jewelry' if colossal else 'scalar_colossal_jewel'
    rows, accepted = review_dimensions(doc, **context)
    assert rows[identity]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize('name', ["Guardian's Light", "Guardian's Thunder"])
@pytest.mark.parametrize('omit_maximum', [False, True])
def test_guardian_colossal_reviews_require_perfect_case_even_without_a_premium(name, omit_maximum):
    from tests.pricing.knowledge.assessment.item_bank.cases.guardian_jewel_trade import CASES as GUARDIANS

    identity = ('unique', name)
    selected = tuple(c for c in GUARDIANS if c.item.name == name)
    doc, context = data(identity, selected)
    doc['rows'][0]['scope'] = 'scalar_colossal_jewel'
    if omit_maximum:
        key = next(k for k in doc['rows'][0]['cases'] if k.endswith('/10-10-5-35-50'))
        del doc['rows'][0]['cases'][key]
    rows, accepted = review_dimensions(doc, **context)
    assert rows[identity]['state'] == ('pending' if omit_maximum else 'reviewed')
    assert accepted == (set() if omit_maximum else {PATH})


@pytest.mark.parametrize(
    'omit', [None, 'roll-20-80-10', 'roll-39-160-15', 'roll-40-160-15', 'component-79-None', 'unknown-contents']
)
def test_named_charm_scope_requires_mf_thresholds_and_both_secondary_rolls(omit):
    from tests.pricing.knowledge.assessment.item_bank.cases.gheed_trade import CASES as GHEED

    identity = ('unique', "Gheed's Fortune")
    doc, context = data(identity, GHEED)
    doc['rows'][0]['scope'] = 'scalar_named_charm'
    if omit:
        del doc['rows'][0]['cases']['gheed-trade/' + omit]
    rows, accepted = review_dimensions(doc, **context)
    assert rows[identity]['state'] == ('pending' if omit else 'reviewed')
    assert accepted == (set() if omit else {PATH})


@pytest.mark.parametrize(
    ('identity', 'bank', 'scope'),
    [
        (IDENTITY, 'bk', 'scalar_named_charm'),
        (('unique', "Gheed's Fortune"), 'gheed', 'scalar_named_jewelry'),
        (('unique', "Gheed's Fortune"), 'gheed', 'scalar_colossal_jewel'),
    ],
)
def test_charm_review_cannot_borrow_other_native_families(identity, bank, scope):
    from tests.pricing.knowledge.assessment.item_bank.cases.gheed_trade import CASES as GHEED

    doc, context = data(identity, GHEED if bank == 'gheed' else CASES)
    doc['rows'][0]['scope'] = scope
    rows, accepted = review_dimensions(doc, **context)
    assert rows[identity]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize(
    ('name', 'minimum', 'maximum'),
    [
        ('Flame Rift', -90, -70),
        ('Crack of the Heavens', -90, -70),
        ('Cold Rupture', -90, -70),
        ('Rotting Fissure', -90, -70),
        ('Black Cleft', -65, -45),
        ('Bone Break', -20, -10),
    ],
)
@pytest.mark.parametrize('omit', [None, 'minimum', 'maximum', 'missing', 'below', 'above', 'variant'])
def test_sunder_charm_review_requires_signed_limits_and_variant_boundaries(name, minimum, maximum, omit):
    from tests.pricing.knowledge.assessment.item_bank.cases.sunder_trade import CASES as SUNDERS

    omit = {
        None: None,
        'minimum': f'penalty-{minimum}',
        'maximum': f'penalty-{maximum}',
        'missing': 'penalty-None',
        'below': f'penalty-{minimum - 1}',
        'above': f'penalty-{maximum + 1}',
        'variant': 'unknown-ethereal',
    }[omit]
    identity = ('unique', name)
    selected = tuple(c for c in SUNDERS if c.item.name == name)
    doc, context = data(identity, selected)
    doc['rows'][0]['scope'] = 'scalar_named_charm'
    if omit:
        key = next(k for k in doc['rows'][0]['cases'] if k.endswith('/' + omit))
        del doc['rows'][0]['cases'][key]
    rows, accepted = review_dimensions(doc, **context)
    assert rows[identity]['state'] == ('pending' if omit else 'reviewed')
    assert accepted == (set() if omit else {PATH})


def test_scalar_review_cannot_certify_an_unknown_penalty_representation():
    from tests.pricing.knowledge.assessment.item_bank.cases.sunder_trade import CASES as SUNDERS

    identity = ('unique', 'Flame Rift')
    doc, context = data(identity, tuple(c for c in SUNDERS if c.item.name == identity[1]))
    doc['rows'][0]['scope'] = 'scalar_named_charm'
    context['policies'] = dict(context['policies'])
    policy = json.loads(json.dumps(context['policies'][identity]))
    policy['trade_qualification']['sunder_penalty'] = 'unknown'
    context['policies'][identity] = policy
    doc['rows'][0]['policy_fingerprint'] = fingerprint(policy)
    rows, accepted = review_dimensions(doc, **context)
    assert rows[identity]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize(('name', 'threshold'), [('Cold Rupture', -70), ('Black Cleft', -45), ('Bone Break', -10)])
def test_sunder_premium_review_requires_ordinary_roll_immediately_below_threshold(name, threshold):
    from tests.pricing.knowledge.assessment.item_bank.cases.sunder_trade import CASES as SUNDERS

    identity = ('unique', name)
    doc, context = data(identity, tuple(c for c in SUNDERS if c.item.name == name))
    doc['rows'][0]['scope'] = 'scalar_named_charm'
    key = next(k for k in doc['rows'][0]['cases'] if k.endswith(f'/penalty-{threshold - 1}'))
    del doc['rows'][0]['cases'][key]
    rows, accepted = review_dimensions(doc, **context)
    assert rows[identity]['state'] == 'pending'
    assert not accepted
