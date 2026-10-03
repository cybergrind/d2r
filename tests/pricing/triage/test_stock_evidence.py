import json

from pricing.triage.stock_evidence import restore


def test_old_stock_flag_recovers_from_its_own_cached_source(tmp_path):
    source = 'pricing/raw/example.json'
    path = tmp_path / source
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps([{'id': 'a', 'stock': True}, {'id': 'b', 'stock': False}]))
    base = {'source': source, 'category': 'runes', 'amount': 155, 'ask_ist': 0.02, 'unit_policy': 'stack_total'}
    rows = [base | {'listing_id': x} for x in ('a', 'b', 'missing')]
    result = restore(rows, tmp_path)
    assert result[0]['ask_ist'] is None
    assert result[0]['unit_policy'] == 'ambiguous'
    assert result[1]['ask_ist'] == 0.02
    assert result[2] == rows[2]
    assert rows[0]['ask_ist'] == 0.02
