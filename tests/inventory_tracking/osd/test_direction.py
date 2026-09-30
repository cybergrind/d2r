import pytest

from inventory_tracking.levels.geometry import Pointer
from inventory_tracking.levels.guide import pointer_lines
from inventory_tracking.presentation import StyledLine


@pytest.mark.parametrize(('dx', 'dy', 'glyph'), [(1, -1, '→'), (-1, 1, '←'), (-1, -1, '↑'), (1, 1, '↓')])
def test_direction_survives_overlay_payload(dx, dy, glyph):
    line = pointer_lines([Pointer('Summoner', None, dx, dy)])[0]
    restored = StyledLine.from_payload(line.to_payload())
    assert restored.arrow == glyph
    assert restored.text == line.text


def test_invalid_arrow_payload_is_rejected():
    with pytest.raises(ValueError, match='arrow'):
        StyledLine.from_payload({'text': 'Target', 'arrow': 'invalid'})


@pytest.mark.parametrize(('glyph', 'tip'), [('→', (68.8, 40)), ('←', (11.2, 40)), ('↑', (40, 11.2)), ('↓', (40, 68.8))])
def test_vector_tip_points_in_screen_direction(glyph, tip):
    from inventory_tracking.osd.direction import arrow_polygon

    assert arrow_polygon(glyph, 80, 80)[3] == pytest.approx(tip)


def test_all_diagonals_fit_inside_the_indicator():
    from inventory_tracking.osd.direction import ARROWS, arrow_polygon

    for glyph in ARROWS:
        assert all(0 < x < 80 and 0 < y < 80 for x, y in arrow_polygon(glyph, 80, 80))
