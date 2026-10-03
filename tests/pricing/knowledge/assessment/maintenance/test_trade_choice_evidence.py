import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance import trade_choice_evidence as evidence


def row():
    return {
        'id': 'row',
        'name': 'Opalvein',
        'rarity': 'unique',
        'scope_status': 'verified',
        'amount': 1,
        'unit_policy': 'single_item',
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'evidence_kind': 'ask',
        'seller_id': 'seller',
        'ask_ist': 1.0,
        'observed_at': '2026-09-18',
        'properties': {
            '799': 'softcore',
            '800': False,
            '798': 'PC',
            '1854': 'reign of the warlock',
            '743': 3,
            '441': 6,
            '721': 1,
            '511': 1,
        },
    }


def test_choice_census_counts_independent_sellers_and_preserves_unknown_choices():
    original = row()
    duplicate = {**original, 'id': 'duplicate'}
    other = {**original, 'id': 'other', 'seller_id': 'other'}
    result = evidence.audit_choices([original, duplicate, other])
    assert result['choices']['lightning']['priced_rows'] == ['duplicate', 'other', 'row']
    assert result['choices']['lightning']['priced_sellers'] == ['other', 'seller']
    assert result['choices']['fire']['priced_rows'] == []


@pytest.mark.parametrize(
    'mutation', ['ladder', 'hardcore', 'quantity', 'ethereal', 'mixed', 'bounds', 'date', 'ask', 'partial', 'identity']
)
def test_choice_census_excludes_incompatible_or_incomplete_evidence(mutation):
    r = row()
    if mutation == 'ladder':
        r['properties']['800'] = True
    elif mutation == 'hardcore':
        r['properties']['799'] = 'hardcore'
    elif mutation == 'quantity':
        r['amount'] = True
    elif mutation == 'ethereal':
        r['ethereal'] = None
    elif mutation == 'mixed':
        r['properties']['750'] = 3
    elif mutation == 'bounds':
        r['properties']['743'] = 6
    elif mutation == 'date':
        r['observed_at'] = None
    elif mutation == 'ask':
        r['ask_ist'] = float('inf')
    elif mutation == 'partial':
        del r['properties']['511']
    else:
        r['name'] = 'Another ring'
    assert evidence.audit_choices([r])['choices']['lightning']['priced_sellers'] == []


def test_equal_individual_resistance_selectors_count_but_conflicts_do_not():
    r = row()
    del r['properties']['441']
    r['properties'].update(dict.fromkeys(('427', '428', '426', '401'), 6))
    assert evidence.audit_choices([r])['choices']['lightning']['priced_sellers'] == ['seller']
    r['properties']['441'] = 7
    assert evidence.audit_choices([r])['choices']['lightning']['priced_sellers'] == []


def test_actual_cache_supports_only_fire_and_cold_independently():
    rows = [json.loads(line) for line in Path(evidence.MARKET).read_text().splitlines()]
    result = evidence.audit_choices(rows)
    assert {k: len(v['priced_sellers']) for k, v in result['choices'].items()} == {
        'magic': 2,
        'physical': 1,
        'fire': 4,
        'cold': 3,
        'lightning': 2,
        'poison': 1,
    }
    assert evidence.reviewed_choices(result, ('329:0', '331:0'))
    result['choices']['lightning']['priced_sellers'] = ['a', 'b', 'c']
    assert not evidence.reviewed_choices(result, ('329:0', '331:0'))


def test_rebound_unrelated_or_inconsistent_census_cannot_certify_unknowns():
    result = evidence.audit_choices([])
    for name in ('fire', 'cold'):
        result['choices'][name]['priced_sellers'] = ['a', 'b', 'c']
        result['choices'][name]['priced_rows'] = ['a', 'b', 'c']
    assert evidence.reviewed_choices(result, ('329:0', '331:0'))
    changed = deepcopy(result)
    changed['name'] = 'Other ring'
    assert not evidence.reviewed_choices(changed, ('329:0', '331:0'))
    changed = deepcopy(result)
    changed['choices']['poison']['property'] = '750'
    assert not evidence.reviewed_choices(changed, ('329:0', '331:0'))


def test_loader_binds_the_whole_market_snapshot_and_selected_identity(tmp_path):
    import hashlib

    source = tmp_path / evidence.MARKET
    source.parent.mkdir(parents=True)
    source.write_text(json.dumps(row()) + '\n')
    snapshot = {'path': evidence.MARKET, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    document = {'rows': [{'quality': 'unique', 'name': 'Opalvein', 'scope': 'choice_named_jewelry'}]}
    policies = {evidence.IDENTITY: {'trade_qualification': {'market_snapshot': snapshot}}}
    scopes = {'choice_named_jewelry'}
    result = evidence.load_evidence(tmp_path, document, policies, scopes)
    assert result[evidence.IDENTITY]['market_snapshot'] == snapshot
    assert result[evidence.IDENTITY]['choices']['lightning']['priced_sellers'] == ['seller']
    source.write_text(source.read_text() + json.dumps({**row(), 'id': 'second'}) + '\n')
    assert evidence.load_evidence(tmp_path, document, policies, scopes) == {}
    assert evidence.load_evidence(tmp_path, {'rows': []}, policies, scopes) == {}
