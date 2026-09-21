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
