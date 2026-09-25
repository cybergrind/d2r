from inventory_tracking.items.metadata import decode_stats


def test_leaf_defense_uses_wielder_level_and_preserves_coefficient():
    decoded, _, unresolved = decode_stats([{'id': 214, 'layer': 0, 'raw': 16}], viewer_level=91)
    assert not unresolved
    assert decoded[0]['value'] == 182
    assert decoded[0]['per_level'] == {'numerator': 16, 'denominator': 8}
    assert decoded[0]['viewer_level'] == 91
