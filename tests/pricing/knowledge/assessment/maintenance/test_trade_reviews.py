import pytest

from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions
from pricing.knowledge.assessment.policies.named_tiers import RULES, _policies
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.cases.fixed_jewelry_trade import CASES
from tests.pricing.knowledge.assessment.item_bank.trade_checks import trade_case


PATH = 'pricing/data/report-receipts/fixed-trade.json'
IDENTITY = ('unique', 'The Stone of Jordan')


def inputs():
    policies = _policies(RULES.read_bytes())
    definitions = {key: thaw(value) for key, value in catalog().named_variants.items()}
    cases = {c.id: c for c in CASES if c.item.name == IDENTITY[1]}
    review = {
        'quality': IDENTITY[0],
        'name': IDENTITY[1],
        'scope': 'fixed_named_jewelry',
        'policy_fingerprint': fingerprint(policies[IDENTITY]),
        'definition_fingerprint': fingerprint(definitions[IDENTITY]),
        'receipt': PATH,
        'review_date': '2026-10-01',
        'reason': 'Fixed identity and legal variants reviewed.',
        'cases': {key: fingerprint(trade_case(c)) for key, c in cases.items()},
    }
    receipt = {
        'schema_version': 1,
        'generation': 'selected',
        'exitstatus': 0,
        'sources_unchanged': True,
        'inputs': {'runtime.py': 'hash'},
        'finished_inputs': {'runtime.py': 'hash'},
        'cases': {
            key: {
                'trade_case': trade_case(c),
                'covers': list(c.covers),
                'phases': dict.fromkeys(('setup', 'call', 'teardown'), 'passed'),
            }
            for key, c in cases.items()
        },
    }
    return {'schema_version': 1, 'rows': [review]}, policies, definitions, {PATH: receipt}


def evaluate(data):
    return review_dimensions(*data, 'selected', {'runtime.py': 'hash'})


def test_review_requires_executed_trade_contracts_for_fixed_identity_only():
    rows, accepted = evaluate(inputs())
    assert rows[IDENTITY]['state'] == 'reviewed'
    assert accepted == {PATH}
    assert len(rows) == 1


@pytest.mark.parametrize(
    'corruption',
    ['missing', 'generation', 'sources', 'exit', 'phase', 'assertions', 'item', 'policy', 'definition', 'boundaries'],
)
def test_review_cannot_borrow_stale_partial_or_foreign_execution(corruption):
    doc, policies, definitions, receipts = inputs()
    receipt = receipts[PATH]
    case = next(iter(receipt['cases'].values()))
    if corruption == 'missing':
        receipts.clear()
    elif corruption == 'generation':
        receipt['generation'] = 'old'
    elif corruption == 'sources':
        receipt['finished_inputs'] = {}
    elif corruption == 'exit':
        receipt['exitstatus'] = 1
    elif corruption == 'phase':
        case['phases']['teardown'] = 'failed'
    elif corruption == 'assertions':
        case['trade_case']['checks'] = {}
    elif corruption == 'item':
        case['trade_case']['item']['name'] = 'Different item'
    elif corruption == 'policy':
        doc['rows'][0]['policy_fingerprint'] = 'old'
    elif corruption == 'definition':
        doc['rows'][0]['definition_fingerprint'] = 'old'
    else:
        key = next(k for k in doc['rows'][0]['cases'] if k.endswith('unknown-ethereal'))
        del doc['rows'][0]['cases'][key]
    rows, accepted = evaluate((doc, policies, definitions, receipts))
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


def test_fixed_identity_review_does_not_close_variable_roll_items():
    doc, policies, definitions, receipts = inputs()
    definitions = dict(definitions)
    definition = dict(definitions[IDENTITY][0])
    definition['roll_ranges'] = {'60': {'min': 3, 'max': 5}}
    definitions[IDENTITY] = (definition,)
    doc['rows'][0]['definition_fingerprint'] = fingerprint(definitions[IDENTITY])
    rows, accepted = evaluate((doc, policies, definitions, receipts))
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted


def test_identity_review_does_not_propagate_to_build_use_or_other_dimensions():
    from pricing.knowledge.assessment.maintenance.trade_reviews import apply_trade_reviews

    doc, policies, definitions, receipts = inputs()
    pending = {'state': 'pending'}
    rows = [
        {
            'id': 'identity:item',
            'kind': 'identity',
            'category': IDENTITY[0],
            'name': IDENTITY[1],
            'dimensions': {'trade_qualification': pending, 'market': pending},
        },
        {'id': 'use:item:unique', 'kind': 'use_quality', 'dimensions': {'trade_qualification': pending}},
    ]
    accepted = apply_trade_reviews(
        rows,
        doc,
        policies=policies,
        definitions=definitions,
        receipts=receipts,
        generation='selected',
        inputs={'runtime.py': 'hash'},
    )
    assert accepted == {PATH}
    assert rows[0]['dimensions']['trade_qualification']['state'] == 'reviewed'
    assert rows[0]['dimensions']['market'] == pending
    assert rows[1]['dimensions']['trade_qualification'] == pending


def test_completion_rechecks_receipts_instead_of_trusting_a_reviewed_dimension(monkeypatch, tmp_path):
    from pricing.knowledge.assessment.maintenance import trade_reviews

    doc, policies, definitions, receipts = inputs()
    context = {
        'policies': policies,
        'definitions': definitions,
        'receipts': receipts,
        'generation': 'selected',
        'inputs': {'runtime.py': 'hash'},
    }
    dimensions, _ = trade_reviews.review_dimensions(doc, **context)
    matrix = {
        'trade_receipts': [PATH],
        'rows': [
            {
                'kind': 'identity',
                'category': IDENTITY[0],
                'name': IDENTITY[1],
                'dimensions': {'trade_qualification': dimensions[IDENTITY]},
            }
        ],
    }
    monkeypatch.setattr(trade_reviews, 'load_context', lambda root, document: dict(context))
    documents = {'trade_reviews': doc, 'receipt:' + PATH: receipts[PATH]}
    trade_reviews.validate_published_reviews(matrix, documents, 'selected', context['inputs'], tmp_path)
    receipts[PATH]['generation'] = 'old'
    with pytest.raises(ValueError, match='Stale trade execution'):
        trade_reviews.validate_published_reviews(matrix, documents, 'selected', context['inputs'], tmp_path)


@pytest.mark.parametrize('document_present', [False, True])
def test_completion_rejects_reviewed_trade_rows_without_a_declared_execution_review(
    monkeypatch, tmp_path, document_present
):
    from pricing.knowledge.assessment.maintenance import trade_reviews

    _doc, policies, definitions, receipts = inputs()
    context = {
        'policies': policies,
        'definitions': definitions,
        'receipts': receipts,
        'generation': 'selected',
        'inputs': {'runtime.py': 'hash'},
    }
    monkeypatch.setattr(trade_reviews, 'load_context', lambda root, document: dict(context))
    matrix = {
        'trade_receipts': [],
        'rows': [
            {
                'kind': 'identity',
                'category': 'unique',
                'name': 'Raven Frost',
                'dimensions': {'trade_qualification': {'state': 'reviewed'}},
            }
        ],
    }
    documents = {'trade_reviews': {'schema_version': 1, 'rows': []}} if document_present else {}
    with pytest.raises(ValueError, match='Unattested trade qualification'):
        trade_reviews.validate_published_reviews(matrix, documents, 'selected', context['inputs'], tmp_path)
