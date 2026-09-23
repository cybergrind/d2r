"""Domain identifiers shared by healing, belt tracking and presentation."""

import math
from dataclasses import dataclass, field
from enum import StrEnum
from typing import NamedTuple

from .layout import LIFE_FRACTION_MAX
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


class SessionIdentity(NamedTuple):
    """Which game we are looking at: process, player and, for the merc actor's ledger record, the hireling."""

    process_id: int
    process_start: str
    player_id: int
    merc_id: int | None = None

    @property
    def core(self) -> tuple[int, str, int]:
        """Process and player only; hiring or losing a merc is not a new game."""
        return self.process_id, self.process_start, self.player_id


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
class PlayerHealth:
    current_raw: int
    maximum_raw: int


@dataclass(frozen=True)
class BeltSnapshot:
    """Sixteen belt slots by index plus the bottom-row potions usable by hotkey column."""

    contents: tuple[int | None, ...]
    healing_cells: tuple[BeltCell, ...] = ()
    rejuvenation_cells: tuple[BeltCell, ...] = ()
    item_ids: tuple[int, ...] = ()

    def cells(self, kind: PotionType) -> tuple[BeltCell, ...]:
        return self.rejuvenation_cells if kind == PotionType.REJUVENATION else self.healing_cells


@dataclass(frozen=True)
class ConsumeBuff:
    active: bool
    level: int | None = None
    effect_id: int | None = None


@dataclass(frozen=True, kw_only=True)
class State:
    """Published snapshot: either a complete in-game sample (`session` set) or a placeholder with a `reason`."""

    sampled_at: float
    reason: str = ''
    session: SessionIdentity | None = None
    health: PlayerHealth | None = None
    merc: Mercenary | None = None
    belt: BeltSnapshot | None = None
    events: tuple[PotionSent, ...] = ()
    teleport: Observation[TeleportCharges] = field(default_factory=Observation.unavailable)
    portal_tome: Observation[PortalTome] = field(default_factory=Observation.unavailable)
    location: Observation[Location] = field(default_factory=Observation.unavailable)
    show_items: Observation[bool] = field(default_factory=Observation.unavailable)
    consume: Observation[ConsumeBuff] = field(default_factory=Observation.unavailable)
    keys: Observation[int] = field(default_factory=Observation.unavailable)
    # Only set by a reader that can positively establish the game boundary.
    session_ended: bool = False

    def fresh(self, now: float, max_age: float) -> bool:
        """A complete sample taken at most `max_age` ago and not from the future."""
        return self.session is not None and 0 <= now - self.sampled_at <= max_age

    def health_for(self, actor: Actor) -> tuple[int, int] | None:
        """(current, maximum) on a common scale per actor; None when unknown, missing or dead."""
        if actor == Actor.PLAYER:
            return (self.health.current_raw, self.health.maximum_raw) if self.health else None
        merc = self.merc
        return (merc.life_fraction_raw, LIFE_FRACTION_MAX) if merc and merc.alive else None

    def usable_cells(self, kind: PotionType) -> tuple[BeltCell, ...]:
        return self.belt.cells(kind) if self.belt else ()


class Refusal(StrEnum):
    UNFOCUSED = 'unfocused'
    NO_DISPLAY = 'no_display'
    UNKNOWN_KEY = 'unknown_key'
    KEY_HELD = 'key_held'
    STALE = 'stale'


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
    reason: Refusal | None = None
