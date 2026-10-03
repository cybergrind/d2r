import json
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance import trade_equipment_evidence as evidence


def row():
    return {
        'id': 'row',
        'seller_id': 'seller',
        'name': 'Sandstorm Trek',
        'rarity': 'unique',
        'base_code': evidence.BASE,
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'amount': 1,
        'unit_policy': 'single_item',
        'sockets': 0,
        'socket_contents': 'empty',
        'ask_ist': 1,
        'observed_at': '2026-09-18',
        'ethereal': True,
        'properties': {
            '799': 'softcore',
            '800': False,
            '798': 'PC',
            '1854': 'reign of the warlock',
            '437': 15,
            '582': 15,
            '425': 140,
            '401': 40,
        },
    }


def test_unknown_ethereal_cannot_become_nonethereal_and_sellers_are_deduplicated():
    r = row()
    rows = [
        r,
        {**r, 'id': 'duplicate'},
        {**r, 'id': 'unknown', 'ethereal': None},
        {**r, 'id': 'noneth', 'ethereal': False},
    ]
    result = evidence.audit_trek(rows)['cohorts']
    assert result['ethereal_attributes']['priced_sellers'] == ['seller']
    assert result['nonethereal']['priced_rows'] == ['noneth']
    assert result['unknown_ethereal']['priced_rows'] == ['unknown']


@pytest.mark.parametrize(
    'mutation', ['ladder', 'hardcore', 'quantity', 'roll', 'partial', 'base', 'socket', 'date', 'ask']
)
def test_incompatible_incomplete_or_ambiguous_rows_do_not_establish_variant_evidence(mutation):
    r = row()
    if mutation == 'ladder':
        r['properties']['800'] = True
    elif mutation == 'hardcore':
        r['properties']['799'] = 'hardcore'
    elif mutation == 'quantity':
        r['amount'] = True
    elif mutation == 'roll':
        r['properties']['425'] = 139
    elif mutation == 'partial':
        del r['properties']['425']
    elif mutation == 'base':
        r['base_code'] = None
    elif mutation == 'socket':
        r['sockets'] = None
    elif mutation == 'date':
        r['observed_at'] = None
    else:
        r['ask_ist'] = float('nan')
    assert evidence.audit_trek([r])['cohorts']['ethereal_attributes']['priced_rows'] == []


def test_current_snapshot_supports_ethereal_segments_but_not_nonethereal_pricing():
    result = evidence.audit_trek(json.loads(line) for line in Path(evidence.MARKET).read_text().splitlines())
    assert {k: len(v['priced_sellers']) for k, v in result['cohorts'].items()} == {
        'ethereal_attributes': 3,
        'ethereal_ordinary': 4,
        'nonethereal': 0,
        'unknown_ethereal': 4,
    }
    assert evidence.reviewed_variants(result)
    result['cohorts']['nonethereal'] = {'priced_sellers': ['a', 'b', 'c'], 'priced_rows': ['a', 'b', 'c']}
    assert not evidence.reviewed_variants(result)


def test_equipment_evidence_loader_requires_the_selected_market_snapshot(tmp_path):
    import hashlib

    source = tmp_path / evidence.MARKET
    source.parent.mkdir(parents=True)
    source.write_text(json.dumps(row()) + '\n')
    snapshot = {'path': evidence.MARKET, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    doc = {'rows': [{'quality': 'unique', 'name': 'Sandstorm Trek', 'scope': 'ethereal_unique_boots'}]}
    policies = {evidence.IDENTITY: {'trade_qualification': {'market_snapshot': snapshot}}}
    scopes = {'ethereal_unique_boots'}
    assert evidence.load_evidence(tmp_path, doc, policies, scopes)[evidence.IDENTITY]['market_snapshot'] == snapshot
    source.write_text(source.read_text() + json.dumps({**row(), 'id': 'second'}) + '\n')
    assert evidence.load_evidence(tmp_path, doc, policies, scopes) == {}
    assert evidence.load_evidence(tmp_path, {'rows': []}, policies, scopes) == {}
