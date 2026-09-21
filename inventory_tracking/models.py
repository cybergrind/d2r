"""Domain identifiers shared by healing, belt tracking and presentation."""

from dataclasses import dataclass
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
