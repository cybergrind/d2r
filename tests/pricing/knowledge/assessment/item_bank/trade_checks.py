"""Explicit trade output contracts retained with executed item-bank evidence."""

from dataclasses import asdict

from inventory_tracking.appraisal.presentation import ItemAssessment


def trade_case(case):
    return {'item': asdict(case.item), 'context': case.context, 'checks': case.trade_checks}


def assert_trade_checks(result, checks):
    assert checks['schema_version'] == 1
    actual = result.get('assessment', {}).get('trade_qualification', {})
    assert {key: actual.get(key) for key in checks['qualification']} == checks['qualification']
    document = ItemAssessment.from_record({'state': 'complete', 'request_id': 'trade-contract', 'result': result})
    lines = [{'text': line.text, 'tone': line.tone} for line in document.lines if line.text.startswith('Trade:')]
    assert lines == checks['lines']
