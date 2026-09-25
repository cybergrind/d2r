import json
from datetime import UTC, datetime

from inventory_tracking.appraisal.text import format_appraisal
from pricing.knowledge.index import build_index
from pricing.knowledge.pipeline import retrieve_draft
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_full_report_prices_only_complete_exact_variants(tmp_path):
    rows = [
        {
            'kind': 'market',
            'name': 'Cinquedeas',
            'base_code': facts('Cinquedeas').base_code,
            'rarity': 'normal',
            'ethereal': False,
            'sockets': 3,
            'socket_contents': 'empty',
            'properties': {},
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'seller_id': str(i),
            'listing_id': str(i),
            'ask_ist': i,
            'unit_policy': 'single_item',
            'observed_at': datetime.now(UTC).date().isoformat(),
        }
        for i in (1, 2, 3)
    ]
    rows.append({**rows[0], 'seller_id': 'expensive', 'listing_id': 'expensive', 'ethereal': True, 'ask_ist': 100})
    data = tmp_path / 'rows.json'
    data.write_text(json.dumps({'schema_version': 1, 'rows': rows}))
    database = tmp_path / 'kb.sqlite3'
    build_index([data], database)
    extraction = {
        'item': {
            'name': 'Cinquedeas',
            'base_name': 'Cinquedeas',
            'base_code': '9kr',
            'rarity': 'normal',
            'identified': True,
            'ethereal': False,
            'sockets': 3,
            'socket_contents': 'empty',
            'affixes': [],
        },
        'decoded_stats': [],
        'source': {'stat_capture_complete': True},
    }
    result = retrieve_draft(extraction, database)
    assert result['assessment']['comparison_requests'][0]['request_id'] == 'current'
    request_result = result['assessment']['comparison_results'][0]
    assert request_result['segment_id'] == 'exact_current_variant'
    assert request_result['price_estimate'] == result['price_estimate']
    assert request_result['comparisons'] == result['assessment']['comparisons']
    assert result['price_estimate']['estimate_ist'] == 2
    assert result['price_estimate']['sellers'] == 3
    assert len(result['assessment']['comparisons']['rejected']) == 1
    text = format_appraisal({'state': 'complete', 'request_id': 1, 'result': result})
    assert 'Assessment:' not in text
    assert '100 Ist' not in text
    assert '3 sellers' in text
