import pytest

from inventory_tracking.input.facade import InputError, PotionInput, Refused
from inventory_tracking.models import Refusal
from tests.inventory_tracking.input.fakes import FakeDelivery, FakeFocus, FakeKeyboard
from tests.inventory_tracking.input.test_facade import TARGET, request


@pytest.mark.parametrize('backend', ['real', 'fake'])
@pytest.mark.parametrize('scenario', ['ready', 'entry_refusal', 'late_refusal', 'error'])
def test_delivery_contract(backend, scenario):
    events = []
    keyboard = FakeKeyboard(results=[False] if scenario == 'error' else [])
    if backend == 'fake':
        delivery = FakeDelivery(
            clock=lambda: 100,
            refusal=Refusal.UNFOCUSED if scenario == 'entry_refusal' else None,
            late_refusal=Refusal.UNFOCUSED if scenario == 'late_refusal' else None,
            error=InputError('uncertain') if scenario == 'error' else None,
            on_send=events.append,
        )
    else:
        delivery = PotionInput(
            clock=lambda: 100,
            sleep=lambda _: None,
            keyboard=keyboard,
            focus=FakeFocus([scenario != 'entry_refusal', scenario != 'late_refusal']),
        )
    with delivery.attempt(TARGET, request()) as attempt:
        assert not events
        assert not keyboard.events
        if scenario == 'entry_refusal':
            assert attempt.refusal == Refusal.UNFOCUSED
            with pytest.raises(InputError):
                attempt.send()
        elif scenario == 'late_refusal':
            with pytest.raises(Refused) as caught:
                attempt.send()
            assert caught.value.refusal == Refusal.UNFOCUSED
        elif scenario == 'error':
            with pytest.raises(InputError):
                attempt.send()
        else:
            assert attempt.refusal is None
            assert attempt.send() == 100
        with pytest.raises(InputError):
            attempt.send()
    if scenario in ('entry_refusal', 'late_refusal'):
        assert not events
        assert not keyboard.events
    with pytest.raises(InputError):
        attempt.send()
