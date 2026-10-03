import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.trade_partial_evidence import audit_region
from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions
from tests.pricing.knowledge.assessment.item_bank.cases.partial_jewelry_trade import MARA_CASES, NAGEL_CASES
from tests.pricing.knowledge.assessment.maintenance.test_scalar_trade_reviews import data


MARA = ('unique', "Mara's Kaleidoscope")
NAGEL = ('unique', 'Nagelring')


def review_inputs(identity=MARA):
    doc, context = data(identity, MARA_CASES if identity == MARA else NAGEL_CASES)
    row = doc['rows'][0]
    row['scope'] = 'partial_compound_named_jewelry' if identity == MARA else 'partial_scalar_named_jewelry'
    evidence = audit_region([], identity)
    evidence['market_snapshot'] = context['policies'][identity]['trade_qualification']['market_snapshot']
    row['unresolved_evidence_fingerprint'] = fingerprint(evidence)
    context['partial_evidence'] = {identity: evidence}
    return doc, context


@pytest.mark.parametrize('identity', [MARA, NAGEL])
def test_partial_review_preserves_explicitly_audited_unknown_lower_rolls(identity):
    doc, context = review_inputs(identity)
    rows, accepted = review_dimensions(doc, **context)
    assert rows[identity]['state'] == 'reviewed'
    assert accepted


@pytest.mark.parametrize('corruption', ['absent', 'fingerprint', 'market', 'bounds', 'enough-sellers', 'identity'])
def test_unknown_disposition_requires_current_exact_thin_evidence(corruption):
    doc, context = review_inputs()
    evidence = context['partial_evidence'][MARA]
    if corruption == 'absent':
        context['partial_evidence'] = {}
    elif corruption == 'fingerprint':
        doc['rows'][0]['unresolved_evidence_fingerprint'] = 'stale'
    elif corruption == 'market':
        evidence['market_snapshot'] = {'path': 'changed', 'sha256': 'changed'}
    elif corruption == 'bounds':
        evidence['maximum'] = 30
    elif corruption == 'enough-sellers':
        evidence['priced_sellers'] = ['a', 'b', 'c']
    else:
        evidence['name'] = 'Nagelring'
    if corruption not in ('absent', 'fingerprint'):
        doc['rows'][0]['unresolved_evidence_fingerprint'] = fingerprint(evidence)
    rows, accepted = review_dimensions(doc, **context)
    assert rows[MARA]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize(
    ('identity', 'missing'),
    [
        (MARA, 'mara-partial-trade/res-20'),
        (MARA, 'mara-partial-trade/res-26'),
        (MARA, 'mara-partial-trade/res-27'),
        (MARA, 'mara-partial-trade/res-29'),
        (MARA, 'mara-partial-trade/res-30'),
        (MARA, 'mara-partial-trade/component-39-None'),
        (MARA, 'mara-partial-trade/component-45-20'),
        (MARA, 'mara-partial-trade/unknown-ethereal'),
        (NAGEL, 'nagel-partial-trade/mf-15-ar-50'),
        (NAGEL, 'nagel-partial-trade/mf-29-ar-75'),
        (NAGEL, 'nagel-partial-trade/mf-30-ar-50'),
        (NAGEL, 'nagel-partial-trade/mf-30-ar-75'),
        (NAGEL, 'nagel-partial-trade/component-19-None'),
        (NAGEL, 'nagel-partial-trade/component-80-31'),
    ],
)
def test_partial_evidence_does_not_waive_native_roll_or_variant_execution(identity, missing):
    doc, context = review_inputs(identity)
    del doc['rows'][0]['cases'][missing]
    rows, accepted = review_dimensions(doc, **context)
    assert rows[identity]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize(('identity', 'scope'), [(MARA, 'compound_named_jewelry'), (NAGEL, 'scalar_named_jewelry')])
def test_existing_full_disposition_scopes_remain_strict(identity, scope):
    doc, context = review_inputs(identity)
    doc['rows'][0]['scope'] = scope
    rows, accepted = review_dimensions(doc, **context)
    assert rows[identity]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize('key', ['mara-partial-trade/res-20', 'mara-partial-trade/res-31'])
def test_unknown_or_impossible_roll_cannot_be_asserted_sellable_with_rebound_hash(key):
    doc, context = review_inputs()
    case = next(iter(context['receipts'].values()))['cases'][key]['trade_case']
    case['checks']['qualification']['status'] = 'candidate'
    doc['rows'][0]['cases'][key] = fingerprint(case)
    rows, accepted = review_dimensions(doc, **context)
    assert rows[MARA]['state'] == 'pending'
    assert not accepted
