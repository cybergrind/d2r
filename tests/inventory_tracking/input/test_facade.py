from unittest.mock import Mock

import pytest

from inventory_tracking.input.facade import InputError, PotionInput, Refused, Target
from inventory_tracking.models import Actor, BeltCell, PotionRequest, PotionType, Refusal
from tests.inventory_tracking.conftest import SESSION
from tests.inventory_tracking.input.fakes import FakeFocus, FakeKeyboard


TARGET = Target(SESSION, 100, 1)


def request(actor=Actor.MERC):
    return PotionRequest(actor, PotionType.HEALING, BeltCell(3, 101))


def sender(keyboard, *, clock=lambda: 100, focus=None, sleep=None):
    return PotionInput(
        clock=clock,
        focus=focus or FakeFocus(),
        keyboard=keyboard,
        sleep=sleep or (lambda seconds: keyboard.events.append(('hold', None))),
    )


@pytest.mark.parametrize('actor', list(Actor))
def test_key_sequence_and_completion_timestamp(actor):
    keyboard = FakeKeyboard()
    clock = Mock(side_effect=[100, 100.1, 100.2])
    with sender(keyboard, clock=clock).attempt(TARGET, request(actor)) as attempt:
        assert attempt.refusal is None
        assert keyboard.events == []
        assert attempt.send() == pytest.approx(100.2)
    keys = [50, 12] if actor == Actor.MERC else [12]
    assert keyboard.events == (
        [('press', key) for key in keys]
        + [('sync', None), ('hold', None)]
        + [('release', key) for key in reversed(keys)]
        + [('sync', None)]
    )
    assert (keyboard.connections, keyboard.closed) == (1, 1)


@pytest.mark.parametrize('reason', list(Refusal))
def test_entry_refusal_closes_without_events(reason):
    keyboard = FakeKeyboard(display=reason != Refusal.NO_DISPLAY, held=reason == Refusal.KEY_HELD)
    if reason == Refusal.UNKNOWN_KEY:
        keyboard.keycodes = lambda names: None
    delivery = sender(
        keyboard,
        focus=FakeFocus([reason != Refusal.UNFOCUSED]),
        clock=lambda: 102 if reason == Refusal.STALE else 100,
    )
    with delivery.attempt(TARGET, request()) as attempt:
        assert attempt.refusal == reason
        with pytest.raises(InputError):
            attempt.send()
    assert keyboard.events == []
    assert keyboard.closed == 1


@pytest.mark.parametrize('reason', [Refusal.UNFOCUSED, Refusal.KEY_HELD, Refusal.STALE])
def test_late_refusal_emits_no_key_events(reason):
    keyboard = FakeKeyboard()
    clock = Mock(side_effect=[100, 102 if reason == Refusal.STALE else 100])
    with sender(keyboard, clock=clock, focus=FakeFocus([True, reason != Refusal.UNFOCUSED])).attempt(
        TARGET, request()
    ) as attempt:
        keyboard.held = reason == Refusal.KEY_HELD
        with pytest.raises(Refused) as caught:
            attempt.send()
        assert caught.value.refusal == reason
    assert keyboard.events == []
    assert keyboard.closed == 1


@pytest.mark.parametrize(
    'results',
    [
        [True, False],
        [True, OSError('press')],
        [True, True, False, True],
        [True, True, OSError('release'), True],
    ],
)
def test_event_failure_attempts_all_pressed_releases(results):
    keyboard = FakeKeyboard(results=results)
    with pytest.raises(InputError), sender(keyboard).attempt(TARGET, request()) as attempt:
        attempt.send()
    assert [event for event in keyboard.events if event[0] == 'release'] == [('release', 12), ('release', 50)]
    assert keyboard.closed == 1


def test_hold_failure_releases_and_syncs():
    keyboard = FakeKeyboard()
    with (
        pytest.raises(InputError),
        sender(keyboard, sleep=Mock(side_effect=OSError('hold'))).attempt(TARGET, request()) as attempt,
    ):
        attempt.send()
    assert keyboard.events[-3:] == [('release', 12), ('release', 50), ('sync', None)]


@pytest.mark.parametrize('stage', ['entry', 'exit', 'focus'])
def test_unexpected_backend_errors_are_input_errors(stage):
    keyboard = FakeKeyboard()
    if stage != 'focus':
        setattr(keyboard, f'{stage}_error', OSError(stage))
    with (
        pytest.raises(InputError),
        sender(keyboard, focus=FakeFocus([OSError('focus') if stage == 'focus' else True])).attempt(TARGET, request()),
    ):
        pass


def test_body_ledger_error_is_not_wrapped():
    keyboard = FakeKeyboard()
    error = OSError('reservation save failed')
    with pytest.raises(OSError, match='reservation save') as caught, sender(keyboard).attempt(TARGET, request()):
        raise error
    assert caught.value is error
    assert keyboard.events == []
    assert keyboard.closed == 1


def test_send_twice_or_after_exit_is_rejected():
    keyboard = FakeKeyboard()
    with sender(keyboard).attempt(TARGET, request()) as attempt:
        attempt.send()
        events = list(keyboard.events)
        with pytest.raises(InputError):
            attempt.send()
    with pytest.raises(InputError):
        attempt.send()
    assert keyboard.events == events


def test_configured_modifier_and_non_digit_column_reach_keyboard():
    from inventory_tracking.config import INPUT, with_overrides

    keyboard = FakeKeyboard()
    config = with_overrides(
        INPUT,
        bindings={Actor.PLAYER: (), Actor.MERC: ('Control_L',)},
        column_keys={1: '1', 2: '2', 3: 'F3', 4: '4'},
    )
    with PotionInput(config, clock=lambda: 100, sleep=lambda _: None, focus=FakeFocus(), keyboard=keyboard).attempt(
        TARGET, request()
    ) as attempt:
        attempt.send()
    assert keyboard.names == [b'Control_L', b'F3']
    assert [e for e in keyboard.events if e[0] == 'press'] == [('press', 37), ('press', 69)]


@pytest.mark.parametrize('late', [False, True])
def test_x11_owner_mismatch_refuses_even_with_compositor_game_focus(late):
    keyboard = FakeKeyboard()
    if not late:
        keyboard.owner_pid = 2
    with sender(keyboard).attempt(TARGET, request()) as attempt:
        if late:
            keyboard.owner_pid = 2
            with pytest.raises(Refused) as caught:
                attempt.send()
            assert caught.value.refusal == Refusal.UNFOCUSED
        else:
            assert attempt.refusal == Refusal.UNFOCUSED
    assert keyboard.events == []


def test_x11_owner_is_checked_even_when_compositor_is_unfocused():
    keyboard = FakeKeyboard()
    with sender(keyboard, focus=FakeFocus([False])).attempt(TARGET, request()) as attempt:
        assert attempt.refusal == Refusal.UNFOCUSED
    assert keyboard.owner_checks == 1
