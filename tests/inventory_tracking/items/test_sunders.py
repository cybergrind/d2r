import pytest

from inventory_tracking.items.metadata import decode_stats


@pytest.mark.parametrize(
    ('stat', 'element', 'prop'),
    [
        (187, 'Cold', '1871'),
        (189, 'Fire', '1872'),
        (190, 'Lightning', '1873'),
        (191, 'Poison', '1874'),
        (192, 'Physical', '1875'),
        (193, 'Magic', '1876'),
    ],
)
def test_sunder_effect_retains_native_magnitude(stat, element, prop):
    decoded, facets, unresolved = decode_stats([{'id': stat, 'layer': 0, 'raw': 300}])
    assert not unresolved
    assert decoded[0]['text'] == f'Monster {element} Immunity is Sundered'
    assert decoded[0]['value'] == 300
    assert [(f['property_id'], f['value']) for f in facets] == [(prop, 300)]


@pytest.mark.parametrize(('raw', 'layer'), [(1, 0), (0, 0), (-300, 0), (301, 0), (300, 1)])
def test_unverified_sunder_payload_stays_unresolved(raw, layer):
    stat = {'id': 189, 'layer': layer, 'raw': raw}
    _, facets, unresolved = decode_stats([stat])
    assert unresolved == [stat]
    assert not facets
