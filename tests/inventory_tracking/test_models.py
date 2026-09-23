import pytest

from inventory_tracking.models import (
    Actor,
    Observation,
    ObservationStatus,
    PlayerHealth,
    PortalTome,
    PotionType,
    State,
    TeleportCharges,
)
from inventory_tracking.native.mercenary import Mercenary


@pytest.mark.parametrize(('current', 'maximum'), [(-1, 20), (21, 20), (0, 0), (1.5, 20), (True, 20)])
def test_resource_quantities_reject_invalid_values(current, maximum):
    for kind in (PortalTome, TeleportCharges):
        with pytest.raises(ValueError, match='Quantity'):
            kind(1, current, maximum)


def test_unavailable_is_not_absence_and_cannot_carry_stale_value():
    assert Observation(100).fresh(100, 2)
    assert not Observation.unavailable(100).fresh(100, 2)
    with pytest.raises(ValueError, match='Unavailable'):
        Observation(100, PortalTome(1, 16, 20), status=ObservationStatus.UNAVAILABLE)


def test_state_is_keyword_only():
    with pytest.raises(TypeError):
        State(0, 1)  # pyrefly: ignore[bad-argument-count, unexpected-positional-argument]
    assert State(sampled_at=0).sampled_at == 0


@pytest.mark.parametrize(
    ('merc', 'expected'),
    [
        (None, None),
        (Mercenary(9, 0, 1000, 0, False), None),
        (Mercenary(9, 500, 1000, 16384, False), None),
        (Mercenary(9, 500, 1000, 16384, True), (16384, 32768)),
    ],
)
def test_health_for_each_actor(merc, expected):
    state = State(sampled_at=0, health=PlayerHealth(300, 1200), merc=merc)
    assert state.health_for(Actor.MERC) == expected
    assert state.health_for(Actor.PLAYER) == (300, 1200)
    assert State(sampled_at=0).health_for(Actor.PLAYER) is None
    assert State(sampled_at=0).usable_cells(PotionType.HEALING) == ()
