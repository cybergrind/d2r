import pytest

from inventory_tracking.models import Observation, PortalTome, TeleportCharges


@pytest.mark.parametrize(('current', 'maximum'), [(-1, 20), (21, 20), (0, 0), (1.5, 20), (True, 20)])
def test_resource_quantities_reject_invalid_values(current, maximum):
    for kind in (PortalTome, TeleportCharges):
        with pytest.raises(ValueError, match='Quantity'):
            kind(1, current, maximum)


def test_unavailable_is_not_absence_and_cannot_carry_stale_value():
    assert Observation(100).fresh(100, 2)
    assert not Observation.unavailable(100).fresh(100, 2)
    with pytest.raises(ValueError, match='Unavailable'):
        Observation(100, PortalTome(1, 16, 20), status='unavailable')
