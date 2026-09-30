import pytest

from pricing.knowledge.assessment.maintenance.guide_spans import audit_spans
from pricing.knowledge.builds import guide_mentions


def test_table_slot_does_not_leak_into_later_prose_mentions():
    html = """<h2>Gear</h2><table><tr><th>Weapon</th><td>
    <span class="d2planner-item" data-d2planner-id="12" data-d2planner-profile="n8010616">Death Cleaver</span>
    </td></tr></table><p><span class="d2planner-item" data-d2planner-id="4">Enigma</span></p>
    <table><tr><td>Helmet</td><td>
    <span class="d2planner-item" data-d2planner-id="2">Guillaume's Face</span></td></tr></table>"""
    rows = guide_mentions(html)
    assert [r['slot'] for r in rows] == ['Weapon', 'unspecified', 'Helmet']
    assert [r['item_id'] for r in rows] == ['12', '4', '2']
    assert rows[0]['profile_id'] == 'n8010616'
    assert all(r['side'] == 'player' for r in rows)


@pytest.mark.parametrize('field', ['slot', 'side', 'profile_id'])
def test_span_reconciliation_rejects_changed_equipment_context(field):
    mention = {'label': 'Insight', 'item_id': '42', 'slot': 'Weapon', 'side': 'merc', 'profile_id': '12345678'}
    row = {
        'id': 'candidate',
        'source_id': 'source',
        'source_locator': '/item-spans/0',
        'slot': 'Weapon',
        'side': 'merc',
        'details': {'original_label': 'Insight', 'raw_item_id': '42', 'profile_id': '12345678'},
    }
    assert audit_spans([mention], 'source', [row], {})['spans'][0]['status'] == 'represented'
    changed = {**mention, field: 'different'}
    result = audit_spans([changed], 'source', [row], {})
    assert result['spans'][0]['status'] == 'conflict'
    assert result['unaccounted_occurrence_ids'] == ['candidate']
