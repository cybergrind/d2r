import json
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance import trade_titan_evidence as evidence


def row():
    return {
        'id': 'row',
        'seller_id': 'seller',
        'name': "Titan's Revenge",
        'rarity': 'unique',
        'base_code': evidence.BASE_CODES['Ceremonial Javelin'],
        'ethereal': True,
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'amount': 1,
        'unit_policy': 'single_item',
        'sockets': 0,
        'socket_contents': 'empty',
        'ask_ist': 1,
        'observed_at': '2026-09-18',
        'properties': {
            '799': 'softcore',
            '800': False,
            '798': 'PC',
            '1854': 'reign of the warlock',
            '510': 199,
            '462': 9,
        },
    }


def test_original_and_upgraded_rolls_stay_in_independent_cohorts():
    r = row()
    result = evidence.audit_titan(
        [
            r,
            {**r, 'id': 'duplicate'},
            {**r, 'id': 'upgraded', 'base_code': evidence.BASE_CODES['Matriarchal Javelin']},
            {**r, 'id': 'unknown', 'base_code': None},
        ]
    )
    assert result['cohorts']['ama/premium']['priced_rows'] == ['duplicate', 'row']
    assert result['cohorts']['ama/premium']['priced_sellers'] == ['seller']
    assert result['cohorts']['amf/lower']['priced_rows'] == ['upgraded']
    assert result['cohorts']['unknown_base']['priced_rows'] == ['unknown']


@pytest.mark.parametrize(
    'mutation', ['ladder', 'hardcore', 'quantity', 'ed', 'leech', 'missing', 'ask', 'date', 'socket']
)
def test_unusable_titan_rows_cannot_establish_trade_evidence(mutation):
    r = row()
    if mutation == 'ladder':
        r['properties']['800'] = True
    elif mutation == 'hardcore':
        r['properties']['799'] = 'hardcore'
    elif mutation == 'quantity':
        r['amount'] = True
    elif mutation == 'ed':
        r['properties']['510'] = 201
    elif mutation == 'leech':
        r['properties']['462'] = 4
    elif mutation == 'missing':
        del r['properties']['510']
    elif mutation == 'ask':
        r['ask_ist'] = float('inf')
    elif mutation == 'date':
        r['observed_at'] = None
    else:
        r['sockets'] = 1
    assert all(not v['priced_sellers'] for v in evidence.audit_titan([r])['cohorts'].values())


def test_current_cohorts_support_each_premium_but_leave_explicit_lower_variants_thin():
    result = evidence.audit_titan(json.loads(line) for line in Path(evidence.MARKET).read_text().splitlines())
    assert evidence.reviewed_variants(result)
    for code in ('ama', 'amf'):
        assert len(result['cohorts'][code + '/premium']['priced_sellers']) == 4
        assert result['cohorts'][code + '/lower']['priced_sellers'] == []
        assert result['cohorts'][code + '/nonethereal']['priced_sellers'] == []
    result['cohorts']['amf/lower'].update(priced_rows=['a', 'b', 'c'], priced_sellers=['a', 'b', 'c'])
    assert not evidence.reviewed_variants(result)


def test_new_cache_bytes_invalidate_selected_snapshot_census(tmp_path):
    import hashlib

    source = tmp_path / evidence.MARKET
    source.parent.mkdir(parents=True)
    source.write_text(json.dumps(row()) + '\n')
    snapshot = {'path': evidence.MARKET, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    doc = {'rows': [{'quality': 'unique', 'name': "Titan's Revenge", 'scope': 'ethereal_unique_javelin'}]}
    policies = {evidence.IDENTITY: {'trade_qualification': {'market_snapshot': snapshot}}}
    scopes = {'ethereal_unique_javelin'}
    assert evidence.load_evidence(tmp_path, doc, policies, scopes)[evidence.IDENTITY]['market_snapshot'] == snapshot
    source.write_text(source.read_text() + json.dumps({**row(), 'id': 'second'}) + '\n')
    assert evidence.load_evidence(tmp_path, doc, policies, scopes) == {}
