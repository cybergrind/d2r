"""Domain identifiers shared by healing, belt tracking and presentation."""

import math
from dataclasses import dataclass, field
from enum import StrEnum
from typing import NamedTuple

from .mercenary import Mercenary


class Actor(StrEnum):
    PLAYER = 'player'
    MERC = 'merc'


class PotionType(StrEnum):
    HEALING = 'healing'
    REJUVENATION = 'rejuvenation'


class BeltCell(NamedTuple):
    column: int
    item_id: int


class ObservationStatus(StrEnum):
    AVAILABLE = 'available'
    UNAVAILABLE = 'unavailable'


@dataclass(frozen=True)
class Observation[T]:
    sampled_at: float
    value: T | None = None
    status: ObservationStatus = ObservationStatus.AVAILABLE
    reason: str = ''

    def __post_init__(self):
        object.__setattr__(self, 'status', ObservationStatus(self.status))
        if not math.isfinite(self.sampled_at):
            raise ValueError('Observation timestamp must be finite')
        if self.status == ObservationStatus.UNAVAILABLE and self.value is not None:
            raise ValueError('Unavailable observation cannot contain a value')

    @classmethod
    def unavailable(cls, sampled_at=0, reason='not sampled'):
        return cls(sampled_at, status=ObservationStatus.UNAVAILABLE, reason=reason)

    def fresh(self, now, max_age):
        return self.status == ObservationStatus.AVAILABLE and 0 <= now - self.sampled_at <= max_age


def validate_quantity(current, maximum):
    if type(current) is not int or type(maximum) is not int or not 0 <= current <= maximum or maximum <= 0:
        raise ValueError('Quantity must be an integer in 0..maximum with positive maximum')


@dataclass(frozen=True)
class TeleportCharges:
    item_id: int
    current: int
    maximum: int

    def __post_init__(self):
        validate_quantity(self.current, self.maximum)


@dataclass(frozen=True)
class PortalTome:
    item_id: int
    quantity: int
    capacity: int

    def __post_init__(self):
        validate_quantity(self.quantity, self.capacity)


@dataclass(frozen=True)
class Location:
    area_id: int
    in_town: bool


@dataclass(frozen=True)
class State:
    sampled_at: float
    current_raw: int | None = None
    maximum_raw: int | None = None
    reason: str = ''
    player_id: int | None = None
    merc: Mercenary | None = None
    process_id: int | None = None
    process_start: str | None = None
    belt_contents: tuple[int | None, ...] | None = None
    healing_cells: tuple[BeltCell, ...] = ()
    rejuvenation_cells: tuple[BeltCell, ...] = ()
    # Complete living-player sample with process identity; not a menu check.
    gameplay_ready: bool = False
    belt_ids: tuple[int, ...] = ()
    events: tuple[PotionSent, ...] = ()
    teleport: Observation[TeleportCharges] = field(default_factory=Observation.unavailable)
    portal_tome: Observation[PortalTome] = field(default_factory=Observation.unavailable)
    location: Observation[Location] = field(default_factory=Observation.unavailable)
    # Only set by a reader that can positively establish the game boundary.
    session_ended: bool = False


class Outcome(StrEnum):
    IDLE = 'idle'
    DISABLED = 'disabled'
    UNAVAILABLE = 'unavailable'
    NO_STOCK = 'no_stock'
    COOLDOWN = 'cooldown'
    PENDING = 'pending'
    SUSPENDED = 'suspended'
    STALE_BELT = 'stale_belt'
    BUSY = 'busy'
    REJECTED = 'rejected'
    SENT = 'sent'


@dataclass(frozen=True)
class PotionRequest:
    actor: Actor
    potion: PotionType
    item: BeltCell


@dataclass(frozen=True)
class PotionSent:
    request: PotionRequest
    sent_at: float


@dataclass(frozen=True)
class PotionResult:
    outcome: Outcome
    event: PotionSent | None = None
