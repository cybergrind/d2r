"""Deterministic optional-resource preview, without game access or input."""

from ..models import Location, Observation, PortalTome, State, TeleportCharges


def resource_frame(*, now, elapsed):
    # Full, small deficit, latch trigger, partial refill, nearly full, repaired.
    quantity, charges, town = (
        (20, 20, True),
        (17, 18, True),
        (16, 3, False),
        (18, 0, False),
        (19, 10, True),
        (20, 20, True),
    )[int(elapsed // 3) % 6]
    return State(
        now,
        1000,
        1000,
        belt_contents=(531,) * 16,
        teleport=Observation(now, TeleportCharges(1, charges, 20)),
        portal_tome=Observation(now, PortalTome(2, quantity, 20)),
        location=Observation(now, Location(40 if town else 41, town)),
    )
