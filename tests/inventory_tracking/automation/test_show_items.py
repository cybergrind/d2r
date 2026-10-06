"""Turn the game's Show Items toggle on once per game (user, 2026-10-05): the OSD reads its byte."""

from dataclasses import replace

from inventory_tracking.automation.show_items import ShowItemsController
from inventory_tracking.config import ShowItemsConfig
from inventory_tracking.input import InputError
from inventory_tracking.models import Observation, Refusal, SessionIdentity
from tests.inventory_tracking.conftest import SESSION, make_state
from tests.inventory_tracking.input.fakes import FakeDelivery


CONFIG = ShowItemsConfig(enabled=True, key_names=('Alt_L',), settle_seconds=1.0, retry_seconds=2.0, max_attempts=3)
AUTO = ShowItemsConfig(enabled=True, settle_seconds=1.0, retry_seconds=2.0, max_attempts=3)


class Clock:
    def __init__(self, now=100.0):
        self.now = now

    def __call__(self):
        return self.now


class KeyDelivery(FakeDelivery):
    """FakeDelivery answering the named-key attempt the controller uses."""

    def attempt_keys(self, target, names):
        self.targets = [*getattr(self, 'targets', []), target]
        return self.attempt(target, names)


def state(now, shown, session=SESSION, name='CybergrindAA'):
    observed = Observation.unavailable(now) if shown is None else Observation(now, shown)
    return replace(make_state(now), session=session, show_items=observed, player_name=name)


def controller(delivery, clock, config=CONFIG, lookup=None):
    return ShowItemsController(config, delivery, clock=clock, lookup=lookup or (lambda name: None))


def test_without_a_configured_key_the_characters_own_binding_is_pressed():
    # The game keeps bindings per character (user, 2026-10-05: usually rebound to Z).
    clock, delivery = Clock(), KeyDelivery()
    looked_up = []
    shower = controller(delivery, clock, AUTO, lookup=lambda name: looked_up.append(name) or 'z')

    shower.step(state(100.0, False))
    clock.now = 101.0
    shower.step(state(101.0, False))
    clock.now = 103.0
    shower.step(state(103.0, False))

    assert delivery.requests == [('z',), ('z',)]
    assert looked_up == ['CybergrindAA']  # once per game


def test_no_known_binding_means_no_press():
    clock, delivery = Clock(), KeyDelivery()
    shower = controller(delivery, clock, AUTO)

    shower.step(state(100.0, False))
    clock.now = 101.0
    shower.step(state(101.0, False))

    assert delivery.requests == []


def test_labels_off_in_a_new_game_get_one_key_press_after_the_game_settles():
    clock, delivery = Clock(), KeyDelivery()
    shower = controller(delivery, clock)

    shower.step(state(100.0, False))  # just entered: the game may still be loading
    clock.now = 101.5
    shower.step(state(101.5, False))
    clock.now = 101.6
    shower.step(state(101.6, False))  # the press is not visible yet: wait for it

    assert delivery.requests == [('Alt_L',)]
    assert delivery.targets[0].session == SESSION


def test_labels_already_on_or_turned_on_leave_the_game_alone_for_the_rest_of_it():
    clock, delivery = Clock(), KeyDelivery()
    shower = controller(delivery, clock)

    shower.step(state(100.0, True))
    clock.now = 110.0
    shower.step(state(110.0, False))  # the player turned them off: their choice

    assert delivery.requests == []


def test_a_press_that_did_not_take_is_retried_then_given_up():
    clock, delivery = Clock(), KeyDelivery()
    shower = controller(delivery, clock)

    for now in (100.0, 101.0, 102.0, 103.0, 105.0, 107.0, 109.0, 120.0):
        clock.now = now
        shower.step(state(now, False))

    assert delivery.requests == [('Alt_L',)] * 3


def test_each_new_game_gets_its_own_press():
    clock, delivery = Clock(), KeyDelivery()
    shower = controller(delivery, clock)
    shower.step(state(100.0, True))

    next_game = SessionIdentity(1, '2', 8)
    shower.step(state(100.0, False, next_game))
    clock.now = 101.0
    shower.step(state(101.0, False, next_game))

    assert delivery.requests == [('Alt_L',)]


def test_unknown_state_outside_a_game_refusals_and_disabled_config_press_nothing():
    clock = Clock(110.0)
    unknown, refused, disabled = KeyDelivery(), KeyDelivery(refusal=Refusal.UNFOCUSED), KeyDelivery()

    controller(unknown, clock).step(state(110.0, None))
    controller(unknown, clock).step(replace(state(110.0, False), session=None))
    off = controller(disabled, clock, ShowItemsConfig(enabled=False))
    off.step(state(100.0, False))
    off.step(state(110.0, False))
    clock.now = 100.0
    clicks = controller(refused, clock)
    clicks.step(state(100.0, False))
    clock.now = 110.0
    clicks.step(state(110.0, False))
    refused.refusal = None
    clock.now = 110.1
    clicks.step(state(110.1, False))  # a refusal (game not focused) is no attempt: try on the next pass

    assert (unknown.requests, disabled.requests, refused.requests) == ([], [], [('Alt_L',)])


def test_an_input_error_stops_trying_in_that_game():
    clock, delivery = Clock(), KeyDelivery(error=InputError('boom'))
    shower = controller(delivery, clock)

    for now in (100.0, 101.0, 104.0, 108.0):
        clock.now = now
        shower.step(state(now, False))

    assert delivery.requests == [('Alt_L',)]
