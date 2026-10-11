"""Uber Diablo progress card: the regions of the player's mode that are close to the walk."""

import threading

from inventory_tracking.config import DCLONE, HUD, with_overrides
from inventory_tracking.hud.dclone import Progress, dclone_widgets, follow, progress
from inventory_tracking.presentation import Tone


def row(region, step, *, ver='2', ladder='2', hc='2', changed=1_000_000):
    # the tracker's own shape (diablo2.io/dclone_api.php, 2026-10-11): every value a string
    values = {'progress': str(step), 'region': str(region), 'ladder': ladder, 'hc': hc, 'timestamped': str(changed)}
    return values | {'reporter_id': '76181', 'ver': ver}


def test_only_rows_of_the_players_version_and_mode_count():
    answer = [
        row(1, 1),
        row(2, 5, changed=1_000_500),
        row(3, 5, ver='1'),  # LoD
        row(3, 6, ladder='1'),
        row(3, 6, hc='1'),
        row(9, 6),  # no such region
        'error code: 1015',
    ]

    assert progress(answer) == {'Americas': (1, 1_000_000), 'Europe': (5, 1_000_500)}
    assert progress({'error': 'banned'}) == {}


def test_the_card_lists_the_close_regions_nearest_the_walk_first_and_nothing_when_none_is_close():
    state = Progress(with_overrides(DCLONE, minimum_progress=4))
    assert state.lines(0.0, 1_000_000.0) == []

    state.feed([row(1, 3), row(2, 1), row(3, 2)], 10.0)
    assert state.lines(11.0, 1_000_000.0) == []

    state.feed([row(1, 4, changed=1_000_000 - 7200), row(2, 1), row(3, 5, changed=1_000_000 - 600)], 20.0)
    assert [(entry.text, entry.tone) for entry in state.lines(21.0, 1_000_000.0)] == [
        ('Uber Diablo 5/6 Asia', Tone.VALUABLE),
        ('Uber Diablo 4/6 Americas', Tone.DEMAND),
        ('Asia: changed 10 min ago', Tone.METADATA),
        ('Americas: changed 2 h ago', Tone.METADATA),
    ]

    state.feed([row(3, 6)], 30.0)
    assert state.lines(31.0, 1_000_000.0)[0].text == 'Uber Diablo 6/6 Asia - walking'


def test_a_failed_check_keeps_the_last_answer_and_a_long_silence_is_said():
    state = Progress(with_overrides(DCLONE, stale_seconds=1800.0))
    state.feed([row(2, 5)], 10.0)

    state.fail('HTTP Error 429: Too Many Requests')
    state.feed([row(2, 5, ver='1')], 400.0)  # the wrong version's rows are a failed check, never shown
    assert [entry.text for entry in state.lines(500.0, 1_000_000.0)][:1] == ['Uber Diablo 5/6 Europe']
    assert state.lines(2000.0, 1_000_000.0)[-1].text == (
        'not checked for 33 min: no row of this version and mode in the answer'
    )


def test_the_widget_stacks_in_the_traderie_slot_which_is_shown_without_the_game():
    state = Progress()
    state.feed([row(2, 5)], 0.0)
    (widget,) = dclone_widgets(state.lines(1.0, 1_000_000.0))

    assert (widget.id, widget.kind, widget.slot) == ('dclone', 'text', 'traderie')
    assert widget.slot in HUD.desktop_slots
    assert dclone_widgets([]) == []


def test_follow_asks_once_a_poll_publishes_in_between_and_clears_the_card_at_the_end():
    stop, asked, published = threading.Event(), [], []
    clock = iter(range(0, 10_000, 100))  # every look at the clock is 100 s later

    def ask(config):
        asked.append(config.version)
        if len(asked) == 2:
            raise OSError('HTTP Error 429: Too Many Requests')
        return [row(2, 5)]

    def publish(widgets):
        published.append(widgets)
        if len(published) == 8:
            stop.set()

    state = Progress(with_overrides(DCLONE, poll_seconds=300.0))
    follow(state, publish, stop, ask=ask, clock=lambda: next(clock), wall=lambda: 1_000_000.0, interval=0)

    assert 2 <= len(asked) < 8  # not on every publish
    assert all([widget.id for widget in widgets] == ['dclone'] for widgets in published[:8])  # kept through the 429
    assert published[-1] == []
