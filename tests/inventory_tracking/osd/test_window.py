"""Empty alerts must unmap the entire surface, not just fade the text."""

from unittest.mock import Mock, call

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
