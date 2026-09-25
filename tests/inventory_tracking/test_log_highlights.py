import logging
from io import StringIO

import pytest
from rich.console import Console

from inventory_tracking.common import HighlightHandler


@pytest.mark.parametrize('terminal', [True, False])
def test_unresolved_lines_are_yellow_only_in_color_console(terminal):
    record = logging.LogRecord(
        'inventory_tracking', logging.INFO, '', 0, 'Observed stats:\n  +35 to Life\n  unknown stat\nNext', (), None
    )
    record.highlight_lines = ('unknown stat',)
    output = StringIO()
    console = Console(file=output, force_terminal=terminal, no_color=False, width=100)
    handler = HighlightHandler(console=console, show_time=False, show_level=False, show_path=False)
    handler.emit(record)
    rendered = output.getvalue()
    assert '+35 to Life' in rendered
    assert 'unknown stat' in rendered
    assert ('\x1b[93m  unknown stat\x1b[0m' in rendered) == terminal
    if not terminal:
        assert '\x1b' not in rendered
    # File handlers format the same record after the console handler.
    assert '\x1b' not in logging.Formatter('%(message)s').format(record)


@pytest.mark.parametrize('terminal', [True, False])
def test_perfect_and_low_roll_colors_do_not_leak_into_plain_logs(terminal):
    record = logging.LogRecord('inventory_tracking', logging.INFO, '', 0, '  perfect roll\n  low roll', (), None)
    record.line_styles = {'perfect roll': 'bright_green', 'low roll': 'bright_red'}
    output = StringIO()
    handler = HighlightHandler(
        console=Console(file=output, force_terminal=terminal, no_color=False, width=100),
        show_time=False,
        show_level=False,
        show_path=False,
    )
    handler.emit(record)
    text = output.getvalue()
    assert ('\x1b[92m  perfect roll\x1b[0m' in text) == terminal
    assert ('\x1b[91m  low roll\x1b[0m' in text) == terminal
    assert '\x1b' not in logging.Formatter('%(message)s').format(record)


@pytest.mark.parametrize(('terminal', 'no_color'), [(True, False), (False, False), (True, True)])
def test_shared_assessment_styles_survive_console_without_coloring_saved_logs(terminal, no_color):
    from inventory_tracking.appraisal.presentation import ItemAssessment
    from tests.inventory_tracking.appraisal.test_text import saved_result

    assessment = ItemAssessment.from_record(saved_result())
    message = assessment.to_text()
    record = logging.LogRecord('inventory_tracking', logging.INFO, '', 0, '%s', (message,), None)
    styled = assessment.to_rich()
    record.styled_message = styled
    output = StringIO()
    handler = HighlightHandler(
        console=Console(file=output, force_terminal=terminal, no_color=no_color, width=200),
        show_time=False,
        show_level=False,
        show_path=False,
    )
    rendered = handler.render_message(record, message)
    assert rendered.plain == message
    assert rendered.spans == styled.spans
    assert rendered is not styled
    handler.emit(record)
    assert 'Magic Ring' in output.getvalue()
    if not terminal:
        assert '\x1b' not in output.getvalue()
    if no_color:
        assert '\x1b[38;' not in output.getvalue()
    assert logging.Formatter('%(message)s').format(record) == message
