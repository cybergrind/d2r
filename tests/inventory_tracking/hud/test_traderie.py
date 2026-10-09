"""Traderie notifications card: unread ones from the browser reader's lines, on a desktop slot."""

import json
import os
import threading

from inventory_tracking.config import HUD, TRADERIE, with_overrides
from inventory_tracking.hud.layout import GameRect, Slot, desktop_rect, place
from inventory_tracking.hud.traderie import Notifications, follow, notification_lines, traderie_widgets, unread
from inventory_tracking.presentation import Tone


def notification(identifier, message, *, read=False, created_at='2026-10-07T00:00:00.000Z'):
    return {'id': identifier, 'type': 'offer-new', 'message': message, 'read': read, 'created_at': created_at}


def line(*notifications):
    return json.dumps({'notifications': list(notifications)})


def test_only_unread_notifications_count_newest_first():
    answer = {
        'notifications': [
            notification('a', 'old offer', created_at='2026-10-05T01:00:00.000Z'),
            notification('b', 'seen', read=True),
            notification('c', 'new offer', created_at='2026-10-07T05:00:00.000Z'),
        ]
    }

    assert [n['id'] for n in unread(answer)] == ['c', 'a']


def test_card_has_the_count_then_the_messages_and_folds_the_rest():
    found = [notification(str(i), f'buyer{i} made an  offer for Grand charm') for i in range(5)]

    lines = notification_lines(found, limit=2)

    assert [(entry.text, entry.tone) for entry in lines] == [
        ('Traderie: 5 new', Tone.VALUABLE),
        ('buyer0 made an offer for Grand charm', Tone.DEFAULT),  # Traderie's double space is collapsed
        ('buyer1 made an offer for Grand charm', Tone.DEFAULT),
        ('+3 more', Tone.METADATA),
    ]
    assert notification_lines([]) == []


def test_widget_sits_in_the_traderie_slot_which_is_shown_without_the_game():
    (widget,) = traderie_widgets(notification_lines([notification('a', 'an offer')]))

    assert (widget.id, widget.kind, widget.slot) == ('traderie', 'text', 'traderie')
    assert widget.slot in HUD.desktop_slots
    assert widget.slot in HUD.slots
    assert traderie_widgets([]) == []


def test_desktop_slots_are_laid_out_on_the_whole_canvas():
    rect = desktop_rect((2560, 1400))
    slot = HUD.slots['traderie']
    (widget,) = traderie_widgets(notification_lines([notification('a', 'an offer')]))

    ((_, box),) = place([widget], {'traderie': (400, 60)}, {'traderie': Slot(slot.x, slot.y, centered=True)}, rect)

    assert rect == GameRect(0, 0, 2560, 1400)
    assert box == (1080, 28, 400, 60)  # centred at the top


def test_unread_notifications_show_until_read_even_when_the_reader_goes_quiet():
    state = Notifications(with_overrides(TRADERIE, stale_seconds=300.0))
    assert state.lines(0.0) == []

    state.feed(line(notification('a', 'an offer')), 10.0)
    assert [entry.text for entry in state.lines(11.0)] == ['Traderie: 1 new', 'an offer']
    # Still shown without an answer for stale_seconds (user, 2026-10-09), with a note that it may be out of date.
    assert [entry.text for entry in state.lines(371.0)] == [
        'Traderie: 1 new',
        'an offer',
        'not checked for 6 min: no answer',
    ]

    state.feed(line(notification('a', 'an offer', read=True)), 320.0)
    assert state.lines(321.0) == []


def test_a_failed_check_keeps_the_last_unread_ones_and_bad_lines_are_ignored():
    state = Notifications()
    state.feed(line(notification('a', 'an offer')), 10.0)

    state.feed('not json', 11.0)
    assert state.lines(12.0)

    state.feed(json.dumps({'error': 'logged out of Traderie in this browser'}), 13.0)
    assert [entry.text for entry in state.lines(14.0)] == ['Traderie: 1 new', 'an offer']
    assert state.lines(400.0)[-1].text == 'not checked for 6 min: logged out of Traderie in this browser'


def test_follow_publishes_the_card_for_each_reader_line_and_clears_it_at_the_end():
    read_end, write_end = os.pipe()
    published = []
    with os.fdopen(read_end, 'rb') as stream:
        os.write(write_end, (line(notification('a', 'an offer')) + '\n').encode())
        os.close(write_end)  # the reader exits after one line

        follow(stream, Notifications(), published.append, threading.Event(), clock=lambda: 1.0, interval=0.01)

    assert [widget.id for widget in published[0]] == ['traderie']
    assert published[-1] == []
