import pytest

from inventory_tracking.models import Location, Observation, State, TeleportCharges
from inventory_tracking.osd.presenter import Presenter
from tests.inventory_tracking.conftest import SESSION


@pytest.mark.parametrize(
    ('current', 'town', 'expected'),
    [
        (69, True, []),
        (68, True, ['tele 68/69 repair']),
        (21, False, []),
        (20, False, ['tele 20/69']),
        (0, None, ['tele 0/69']),
        (30, None, []),
        (3, True, ['tele 3/69 repair']),
    ],
)
def test_teleport_visibility_independent_of_health(current, town, expected):
    presenter = Presenter()
    location = Observation.unavailable(100, 'unknown') if town is None else Observation(100, Location(1, town))
    presenter.update(
        State(
            sampled_at=100,
            session=SESSION,
            teleport=Observation(100, TeleportCharges(1, current, 69)),
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


@pytest.mark.parametrize(('charges', 'expected'), [(20, ['tele 20/33']), (21, []), (33, [])])
def test_threshold_is_a_count_of_charges_whatever_the_staff_holds(charges, expected):
    presenter = Presenter()
    presenter.update(State(sampled_at=100, session=SESSION, teleport=Observation(100, TeleportCharges(1, charges, 33))))
    assert presenter.render(now=100) == expected
