import pytest

from inventory_tracking.items.metadata import decode_stats


def native(stat_id, raw, layer=0):
    return {'id': stat_id, 'layer': layer, 'raw': raw}


@pytest.mark.parametrize(
    ('stat', 'text', 'internal'),
    [
        # Reproduced from the Dimoak's Hew, Tomb Reaver and Wirt's Leg captures.
        (native(31, -8), 'Defense: -8', False),
        (native(155, 10, 1), '10% Reanimate as: Returned', False),
        (native(356, 2), 'Quest item difficulty: Hell', True),
    ],
)
def test_captured_decoder_gaps_preserve_native_values(stat, text, internal):
    rows, facets, unresolved = decode_stats([stat])
    assert not unresolved
    assert not facets
    assert rows[0]['memory_stat'] == stat
    assert rows[0]['value'] == stat['raw']
    assert rows[0]['text'] == text
    assert (rows[0].get('presentation') == 'internal') == internal


@pytest.mark.parametrize(('level', 'value'), [(1, 2), (91, 227), (99, 247)])
def test_messerschmidt_maximum_damage_percentage_scales_with_viewer(level, value):
    rows, facets, unresolved = decode_stats([native(219, 20)], viewer_level=level)
    assert not unresolved
    assert not facets
    assert rows[0]['value'] == value
    assert rows[0]['text'] == f'+{value}% Enhanced Maximum Damage (Based on Character Level)'
    assert rows[0]['per_level'] == {'numerator': 20, 'denominator': 8}
    assert rows[0]['origin'] == 'level_formula'


@pytest.mark.parametrize('level', [None, 0, 100, True])
def test_maximum_damage_percentage_requires_valid_viewer(level):
    stat = native(219, 20)
    assert decode_stats([stat], viewer_level=level)[2] == [stat]


@pytest.mark.parametrize(
    ('raw', 'text'), [(20, '-20% to Enemy Magic Resistance'), (-5, '+5% to Enemy Magic Resistance')]
)
def test_magic_pierce_uses_resistance_sign_and_retains_native_magnitude(raw, text):
    rows, facets, unresolved = decode_stats([native(358, raw)])
    assert not unresolved
    assert not facets
    assert rows[0]['text'] == text
    assert rows[0]['value'] == raw


@pytest.mark.parametrize(
    ('stat', 'text'),
    [
        (native(140, 3), 'Extra blood visual effect: 3'),
        (native(181, 1), 'Fade visual effect: 1'),
        (native(98, 1, 175), 'Set state: fullsetgeneric'),
        (native(98, 1, 176), 'Set state: monsterset'),
    ],
)
def test_cosmetic_and_set_effects_are_internal_diagnostics(stat, text):
    rows, facets, unresolved = decode_stats([stat])
    assert not unresolved
    assert not facets
    assert rows[0]['text'] == text
    assert rows[0]['presentation'] == 'internal'
    assert rows[0]['memory_stat'] == stat


@pytest.mark.parametrize(
    'stat',
    [
        native(31, -8, 1),
        native(72, -8),
        native(155, 10, 999),
        native(155, 101, 1),
        native(155, -1, 1),
        native(356, 3),
        native(356, -1),
        native(356, 2, 1),
        native(219, 20, 1),
        native(219, -1),
        native(358, 20, 1),
        native(140, -1),
        native(140, 1, 1),
        native(181, -1),
        native(181, 1, 1),
        native(98, 2, 175),
        native(98, 1, 999),
    ],
)
def test_invalid_or_unreviewed_effects_remain_unresolved(stat):
    assert decode_stats([stat], viewer_level=91)[2] == [stat]
