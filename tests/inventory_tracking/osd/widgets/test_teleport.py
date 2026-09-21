import pytest

from inventory_tracking.models import Location, Observation, State, TeleportCharges
from inventory_tracking.osd.presenter import Presenter
from tests.inventory_tracking.conftest import SESSION


@pytest.mark.parametrize(
    ('current', 'town', 'expected'),
    [
        (20, True, []),
        (19, True, ['tele 19/20 repair']),
        (4, False, []),
        (3, False, ['tele 3/20']),
        (0, None, ['tele 0/20']),
        (10, None, []),
        (3, True, ['tele 3/20 repair']),
    ],
)
def test_teleport_visibility_independent_of_health(current, town, expected):
    presenter = Presenter()
    location = Observation.unavailable(100, 'unknown') if town is None else Observation(100, Location(1, town))
    presenter.update(
        State(
            sampled_at=100,
            session=SESSION,
            teleport=Observation(100, TeleportCharges(1, current, 20)),
            location=location,
        )
    )
    assert presenter.render(now=100) == expected
    assert presenter.render(now=103) == []


def test_absent_and_unavailable_staff_clear_display():
    presenter = Presenter()
    for value, expected in [(TeleportCharges(1, 0, 20), ['tele 0/20']), (None, [])]:
        presenter.update(State(sampled_at=100, session=SESSION, teleport=Observation(100, value)))
        assert presenter.render(now=100) == expected
    presenter.update(State(sampled_at=100, session=SESSION))
    assert presenter.render(now=100) == []


@pytest.mark.parametrize(('charges', 'expected'), [(6, ['tele 6/33']), (7, [])])
def test_threshold_uses_actual_staff_capacity(charges, expected):
    presenter = Presenter()
    presenter.update(State(sampled_at=100, session=SESSION, teleport=Observation(100, TeleportCharges(1, charges, 33))))
    assert presenter.render(now=100) == expected
