import copy
import json

import pytest

from pricing.knowledge.assessment.maintenance.trade_torch_evidence import audit, reviewed_classes
from pricing.knowledge.assessment.policies.named_tiers import RULES


def rows():
    policy = next(p for p in json.loads(RULES.read_bytes())['policies'] if p['name'] == 'Hellfire Torch')
    return copy.deepcopy(policy['trade_qualification']['market_evidence'])


def test_three_amazon_sellers_do_not_establish_other_class_demand():
    evidence = audit(rows())
    assert [len(row['priced_sellers']) for row in evidence['classes']] == [3, 0, 0, 0, 0, 0, 0, 0]
    assert reviewed_classes(evidence, {0})
    assert not reviewed_classes(evidence, {0, 1})


def test_new_independent_class_evidence_invalidates_old_unknown_class_review():
    data = rows()
    for row in copy.deepcopy(data):
        row['id'] = 'sorceress-' + row['id']
        row['properties'].pop('453')
        row['properties']['514'] = 3
        data.append(row)
    evidence = audit(data)
    assert not reviewed_classes(evidence, {0})
    assert reviewed_classes(evidence, {0, 1})


@pytest.mark.parametrize(
    'bad',
    [
        'mode',
        'season',
        'game',
        'date',
        'unit',
        'ethereal',
        'sockets',
        'contents',
        'class',
        'mixed_class',
        'roll',
        'compound',
        'unpriced',
        'seller',
    ],
)
def test_invalid_rows_cannot_fill_the_three_seller_requirement(bad):
    data = rows()
    row = data[0]
    if bad == 'mode':
        row['properties']['799'] = 'hardcore'
    elif bad == 'season':
        row['properties']['800'] = True
    elif bad == 'game':
        row['properties'].pop('1854')
    elif bad == 'date':
        row['observed_at'] = None
    elif bad == 'unit':
        row['amount'] = 2
    elif bad == 'ethereal':
        row['ethereal'] = None
    elif bad == 'sockets':
        row['sockets'] = None
    elif bad == 'contents':
        row['socket_contents'] = 'unknown'
    elif bad == 'class':
        row['properties'].pop('453')
    elif bad == 'mixed_class':
        row['properties']['514'] = 3
    elif bad == 'roll':
        row['properties']['727'] = 21
    elif bad == 'compound':
        row['properties']['437'] = 10
    elif bad == 'unpriced':
        row['ask_ist'] = None
    else:
        row['seller_id'] = data[1]['seller_id']
    assert not reviewed_classes(audit(data), {0})
