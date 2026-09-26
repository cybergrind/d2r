import json

from inventory_tracking.shop.audit import audit


def test_audit_reports_unknown_payloads_and_input_errors_without_silently_skipping(tmp_path):
    capture = tmp_path / 'capture.json'
    capture.write_text(
        json.dumps(
            {
                'resource_stats': {
                    'arrays': [
                        {'header_offset': 232, 'stats': [{'id': 999, 'layer': 4, 'raw': 12}]},
                    ]
                },
                'txt_id': 535,
            }
        )
    )
    broken = tmp_path / 'broken.json'
    broken.write_text('{')
    result = audit([capture, broken])
    assert result['distinct_captured_lists'] == 1
    assert result['failures'] == [
        {
            'source': str(capture),
            'stats': [{'id': 999, 'layer': 4, 'raw': 12}],
        }
    ]
    assert result['input_errors'][0]['source'] == str(broken)
    assert result['distinct_catalog_endpoints'] >= 1800
    assert len(result['stats']) >= 367
