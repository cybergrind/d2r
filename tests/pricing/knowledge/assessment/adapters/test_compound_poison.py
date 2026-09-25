from inventory_tracking.items.poison import combine_poison
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.domain.facts import FactStatus, StatKey
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_combined_poison_keeps_native_semantic_values_and_units_without_guessing_market_duration():
    rows = [
        {'memory_stat': {'id': i, 'layer': 0, 'raw': raw}, 'status': 'unresolved'}
        for i, raw in [(57, 154), (58, 154), (59, 125), (326, 1)]
    ]
    decoded = combine_poison(rows)
    result = normalize(
        {'item': facts('Bill').to_dict(), 'source': {'stat_capture_complete': True}, 'decoded_stats': decoded}
    )
    for key, value, unit in [
        ('57:0', 154 / 256, 'damage_per_frame'),
        ('58:0', 154 / 256, 'damage_per_frame'),
        ('59:0', 5, 'seconds'),
        ('326:0', 1, 'count'),
    ]:
        fact = result.stat(StatKey(*map(int, key.split(':'))))
        assert fact.status == FactStatus.KNOWN
        assert fact.value == value
        assert result.stats[key]['unit'] == unit
        assert any(key in gap for gap in result.projection_gaps)
    assert result.properties == {}
    assert decoded[0]['text'] == '+75 Poison Damage over 5 Seconds'
