"""Empty alerts must unmap the entire surface, not just fade the text."""

from unittest.mock import Mock, call

import pytest

from inventory_tracking.osd.window import apply_display


def test_shortage_then_refill_unmaps_window_and_clears_text():
    window, label = Mock(), Mock()
    apply_display(window, label, ['hp 1'])
    apply_display(window, label, [])
    assert window.set_visible.call_args_list == [call(True), call(False)]
    assert label.set_text.call_args_list == [call('hp 1'), call('')]


def test_empty_startup_can_show_a_later_alert():
    window, label = Mock(), Mock()
    apply_display(window, label, [])
    apply_display(window, label, ['700/1000', 'juv 2'])
    assert window.set_visible.call_args_list == [call(False), call(True)]
    label.set_text.assert_called_with('700/1000 · juv 2')


def test_assessment_lines_are_multiline_and_unmap_when_cleared():
    window, label = Mock(), Mock()
    apply_display(window, label, ['Ring', 'Price: unknown'], multiline=True)
    label.set_text.assert_called_with('Ring\nPrice: unknown')
    apply_display(window, label, [], multiline=True)
    window.set_visible.assert_called_with(False)


def test_styled_osd_uses_escaped_markup_and_clears_it_on_hide():
    from inventory_tracking.presentation import StyledLine, Tone

    window, label = Mock(), Mock()
    apply_display(window, label, [StyledLine('<Ring>', Tone.MAGIC)], multiline=True)
    markup = label.set_markup.call_args.args[0]
    assert '&lt;Ring&gt;' in markup
    assert 'foreground=' in markup
    apply_display(window, label, [], multiline=True)
    label.set_text.assert_called_with('')
    window.set_visible.assert_called_with(False)


def test_mark_drawing_pulses_and_rejects_bad_colors():
    from inventory_tracking.osd.widgets.repair_mark import Mark
    from inventory_tracking.osd.window import draw_mark, parse_color, pulse

    assert parse_color('#ff0080') == (1.0, 0.0, 128 / 255)
    assert pulse(0.0, 1.2) == pytest.approx(0.5)
    assert pulse(1.2, 1.2) == pytest.approx(0.5)
    cr = Mock()
    draw_mark(cr, 120, Mark('repair', 0.5, 0.3, 0.085, '#ff3b3b', 1.2), now=0.3)
    assert cr.arc.call_count == 4
    assert cr.stroke_preserve.call_count == 1
    assert cr.stroke.call_count == 1
    widths = [c.args[0] for c in cr.set_line_width.call_args_list]
    assert widths[1] == pytest.approx(120 * 0.06)
    assert widths[0] > widths[1]
    with pytest.raises(ValueError, match='#rrggbb'):
        draw_mark(cr, 120, Mark('repair', 0.5, 0.3, 0.085, 'red', 1.2), now=0)
