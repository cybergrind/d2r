from contextlib import contextmanager
from unittest.mock import Mock

import pytest

from inventory_tracking.models import Actor, BeltCell, PotionRequest, PotionType
from inventory_tracking.potion_input import PotionInput


def request(actor=Actor.MERC):
    return PotionRequest(actor, PotionType.HEALING, BeltCell(3, 101))


class FakeKeyboard:
    """Records the key sequence; `results` scripts press/release return values in call order."""

    def __init__(self, *, results=(), held=False, display=True):
        self.results = list(results)
        self.held = held
        self.display = display
        self.events = []
        self.connections = 0
        self.closed = 0

    def keycodes(self, names):
        return [50 if name == b'Shift_L' else int(name) + 9 for name in names]

    def any_key_held(self):
        return self.held

    def _event(self, kind, key):
        self.events.append((kind, key))
        return self.results.pop(0) if self.results else True

    def press(self, key):
        return self._event('press', key)

    def release(self, key):
        return self._event('release', key)

    def sync(self):
        self.events.append(('sync', None))

    @contextmanager
    def connect(self):
        self.connections += 1
        try:
            yield self if self.display else None
        finally:
            self.closed += 1


def sender(keyboard, *, clock=lambda: 100, focused=None):
    return PotionInput(clock=clock, focused=focused or (lambda session: True), keyboard=keyboard)


@pytest.mark.parametrize('actor', [Actor.PLAYER, Actor.MERC])
def test_key_sequence_and_reservation_before_delivery(actor, sample, monkeypatch):
    keyboard = FakeKeyboard()
    reserved = []
    monkeypatch.setattr(
        'inventory_tracking.potion_input.time.sleep', lambda seconds: keyboard.events.append(('hold', None))
    )
    assert sender(keyboard)(
        sample(), request(actor), max_age=1, before_send=lambda: reserved.append(len(keyboard.events))
    )
    keys = [50, 12] if actor == Actor.MERC else [12]
    assert reserved == [0]
    assert keyboard.events == (
        [('press', key) for key in keys]
        + [('sync', None), ('hold', None)]
        + [('release', key) for key in reversed(keys)]
        + [('sync', None)]
    )
    assert (keyboard.connections, keyboard.closed) == (1, 1)


def test_failed_press_releases_both_keys_and_closes_display(sample):
    keyboard = FakeKeyboard(results=[True, False])
    with pytest.raises(RuntimeError, match='Potion key press failed'):
        sender(keyboard)(sample(), request(), max_age=1, before_send=Mock())
    assert [event for event in keyboard.events if event[0] != 'sync'] == [
        ('press', 50),
        ('press', 12),
        ('release', 12),
        ('release', 50),
    ]
    assert keyboard.closed == 1


@pytest.mark.parametrize('max_age', [0.01, 0.1])
def test_injected_freshness_prevents_input(sample, max_age):
    keyboard = FakeKeyboard()
    assert not sender(keyboard, clock=lambda: 101)(sample(), request(), max_age=max_age, before_send=Mock())
    assert keyboard.connections == 0


def test_failed_release_attempts_remaining_keys_and_reports_uncertain_delivery(sample, monkeypatch):
    keyboard = FakeKeyboard(results=[True, True, False, True])
    monkeypatch.setattr('inventory_tracking.potion_input.time.sleep', lambda seconds: None)
    with pytest.raises(RuntimeError, match='release'):
        sender(keyboard)(sample(), request(), max_age=1, before_send=Mock())
    assert keyboard.events[-2] == ('release', 50)
    assert keyboard.closed == 1


@pytest.mark.parametrize('reason', ['held_key', 'focus_changed', 'sample_aged', 'no_display'])
def test_last_moment_checks_prevent_reservation_and_input(reason, sample):
    keyboard = FakeKeyboard(held=reason == 'held_key', display=reason != 'no_display')
    clock = Mock(side_effect=[100, 102] if reason == 'sample_aged' else [100, 100])
    focused = Mock(side_effect=[True, reason != 'focus_changed'])
    reserve = Mock()
    assert not sender(keyboard, clock=clock, focused=focused)(sample(), request(), max_age=1, before_send=reserve)
    reserve.assert_not_called()
    assert not [event for event in keyboard.events if event[0] == 'press']


@pytest.mark.parametrize(
    'changes',
    [
        {'session': None},
        {'current_raw': 0},
        {'healing_cells': ()},
        {'healing_cells': (BeltCell(5, 101),)},
    ],
)
def test_guards_refuse_without_focus_query_or_display(changes, sample):
    keyboard = FakeKeyboard()
    focused = Mock(return_value=True)
    assert not sender(keyboard, focused=focused)(sample(**changes), request(), max_age=1, before_send=Mock())
    focused.assert_not_called()
    assert keyboard.connections == 0


def test_unfocused_game_never_opens_a_display(sample):
    keyboard = FakeKeyboard()
    assert not sender(keyboard, focused=lambda session: False)(sample(), request(), max_age=1, before_send=Mock())
    assert keyboard.connections == 0
