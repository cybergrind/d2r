"""Deterministic optional-resource preview, without game access or input."""

from inventory_tracking.models import (
    BeltSnapshot,
    Location,
    Observation,
    PlayerHealth,
    PortalTome,
    SessionIdentity,
    ShopPanel,
    State,
    TeleportCharges,
)


DEMO_SESSION = SessionIdentity(0, 'demo', 0)


def resource_frame(*, now, elapsed):
    # Full; at the portal threshold in town; low stock and empty outside town
    # (portal reminder hidden there); partial refill in town; repaired.
    quantity, charges, town = (
        (20, 20, True),
        (3, 18, True),
        (2, 3, False),
        (0, 0, False),
        (3, 10, True),
        (20, 20, True),
    )[int(elapsed // 3) % 6]
    return State(
        sampled_at=now,
        session=DEMO_SESSION,
        health=PlayerHealth(1000, 1000),
        belt=BeltSnapshot((531,) * 16),
        teleport=Observation(now, TeleportCharges(1, charges, 20)),
        portal_tome=Observation(now, PortalTome(2, quantity, 20)),
        location=Observation(now, Location(40 if town else 41, town)),
    )


def repair_frame(*, now):
    """In town at Charsi's Trade panel with a half-charged staff: the repair mark and its text reminder."""
    return State(
        sampled_at=now,
        session=DEMO_SESSION,
        health=PlayerHealth(1000, 1000),
        belt=BeltSnapshot((531,) * 16),
        teleport=Observation(now, TeleportCharges(1, 10, 20)),
        location=Observation(now, Location(1, True)),
        shop=Observation(now, ShopPanel(True, 'Charsi', True)),
    )
