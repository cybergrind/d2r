"""Uber Diablo progress card: the regions of the player's mode that are close to the walk."""

import itertools
import json
import threading

from inventory_tracking.config import DCLONE, HUD, with_overrides
from inventory_tracking.hud.dclone import CREDIT, Progress, Refused, dclone_widgets, follow, progress, retry_after
from inventory_tracking.presentation import Tone


NOW = 1_000_000.0  # epoch seconds, as the tracker's own times


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
    assert state.lines(NOW) == []

    state.feed([row(1, 3), row(2, 1), row(3, 2)], NOW)
    assert state.lines(NOW) == []

    state.feed([row(1, 4, changed=1_000_000 - 7200), row(2, 1), row(3, 5, changed=1_000_000 - 600)], NOW)
    assert [(entry.text, entry.tone) for entry in state.lines(NOW + 1)] == [
        ('Uber Diablo 5/6 Asia', Tone.VALUABLE),
        ('Uber Diablo 4/6 Americas', Tone.DEMAND),
        ('Asia: changed 10 min ago', Tone.METADATA),
        ('Americas: changed 2 h ago', Tone.METADATA),
        (CREDIT, Tone.METADATA),  # the API's condition of use
    ]

    state.feed([row(3, 6)], NOW)
    assert state.lines(NOW)[0].text == 'Uber Diablo 6/6 Asia - walking'


def test_a_failed_check_keeps_the_last_answer_and_a_long_silence_is_said():
    state = Progress(with_overrides(DCLONE, stale_seconds=1800.0))
    state.feed([row(2, 5)], NOW)

    state.fail('HTTP 429 Too Many Requests')
    state.feed([row(2, 5, ver='1')], NOW + 400)  # the wrong version's rows are a failed check, never shown
    assert [entry.text for entry in state.lines(NOW + 500)][:1] == ['Uber Diablo 5/6 Europe']
    assert state.lines(NOW + 2000)[-1].text == 'not checked for 33 min: no row of this version and mode in the answer'


def test_the_widget_stacks_in_the_traderie_slot_which_is_shown_without_the_game():
    state = Progress()
    state.feed([row(2, 5)], NOW)
    (widget,) = dclone_widgets(state.lines(NOW))

    assert (widget.id, widget.kind, widget.slot) == ('dclone', 'text', 'traderie')
    assert widget.slot in HUD.desktop_slots
    assert dclone_widgets([]) == []


def test_retry_after_is_seconds_or_a_date():
    assert retry_after('120', NOW) == 120.0
    assert retry_after('Thu, 01 Jan 1970 00:10:00 GMT', 0.0) == 600.0
    assert retry_after('Thu, 01 Jan 1970 00:10:00 GMT', 900.0) == 0.0
    assert retry_after(None, NOW) is None
    assert retry_after('soon', NOW) is None


def run(config, answers, *, start=NOW, step=100.0, publishes=20):
    """`follow` with a clock that moves `step` seconds a look; -> (the times asked at, the cards)."""
    stop, asked, published, clock = threading.Event(), [], [], [start - step]

    def wall():
        clock[0] += step
        return clock[0]

    def ask(_):
        asked.append(clock[0])
        answer = answers[min(len(asked), len(answers)) - 1]
        if isinstance(answer, Exception):
            raise answer
        return answer

    def publish(widgets):
        published.append(widgets)
        if len(published) == publishes:
            stop.set()

    follow(Progress(config), publish, stop, ask=ask, wall=wall, interval=0)
    return asked, published


def settings(tmp_path, **changes):
    return with_overrides(DCLONE, cache=tmp_path / 'dclone' / 'cache.json', poll_seconds=300.0, **changes)


def test_the_tracker_is_asked_once_a_poll_and_the_card_is_cleared_at_the_end(tmp_path):
    asked, published = run(settings(tmp_path), [[row(2, 5)]])

    assert [when - NOW for when in asked] == [0.0, 300.0, 600.0, 900.0, 1200.0, 1500.0, 1800.0]
    assert all([widget.id for widget in widgets] == ['dclone'] for widgets in published[:20])
    assert published[-1] == []


def test_a_restart_shows_the_stored_answer_and_does_not_ask_before_the_poll_is_over(tmp_path):
    # 2026-10-11, 20:07: every restart of `serve` asked at once and the tracker answered 429
    config = settings(tmp_path)
    run(config, [[row(2, 5)]], publishes=1)
    assert json.loads(config.cache.read_text())['fetched_at'] == NOW

    asked, published = run(config, [[row(2, 6)]], start=NOW + 100, publishes=4)

    assert [when - NOW for when in asked] == [300.0]
    assert [widget.id for widget in published[0]] == ['dclone']  # from the file, before any request


def test_a_refusal_waits_for_its_retry_after_and_without_one_twice_as_long_each_time(tmp_path):
    refused = Refused('HTTP 429 Too Many Requests')
    config = settings(tmp_path, backoff_seconds=2000.0)
    asked, published = run(config, [[row(2, 5)], refused, refused, refused, [row(2, 5)]], step=50.0, publishes=140)

    waits = [later - earlier for earlier, later in itertools.pairwise(asked)]
    assert waits[:5] == [300.0, 600.0, 1200.0, 2000.0, 300.0]  # doubled, capped, and back to the poll
    assert all(published[:140])  # the last answer stays on the card throughout

    asked, _ = run(settings(tmp_path / 'named'), [Refused('HTTP 429', 1000.0), [row(2, 5)]], publishes=14)
    assert [when - NOW for when in asked[:2]] == [0.0, 1000.0]


def test_a_restart_does_not_ask_before_a_refusal_is_waited_out(tmp_path):
    config = settings(tmp_path)
    run(config, [Refused('HTTP 429', 1000.0)], publishes=1)

    asked, _ = run(config, [[row(2, 5)]], start=NOW + 100, publishes=12)

    assert [when - NOW for when in asked[:1]] == [1000.0]
