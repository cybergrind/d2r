import pytest

from inventory_tracking.items.metadata import decode_stats


def test_ias_max_damage_jewel_has_no_unreadable_throw_component():
    # Screenshot: +15% IAS / +9 maximum damage, copied to all three damage modes.
    stats = [{'id': stat, 'layer': 0, 'raw': value} for stat, value in [(22, 9), (24, 9), (93, 15), (160, 9)]]
    rows, facets, unresolved = decode_stats(stats)
    assert not unresolved
    assert [row['memory_stat'] for row in rows] == stats
    throw = rows[-1]
    assert throw['value'] == 9
    assert throw['presentation'] == 'internal'
    assert 'Maximum throw damage' in throw['text']
    assert all(facet['memory_stat']['id'] != 160 for facet in facets)


@pytest.mark.parametrize('stat_id', [159, 160])
@pytest.mark.parametrize(('layer', 'raw'), [(1, 9), (0, -1)])
def test_invalid_throw_damage_remains_unresolved(stat_id, layer, raw):
    stat = {'id': stat_id, 'layer': layer, 'raw': raw}
    assert decode_stats([stat])[2] == [stat]
