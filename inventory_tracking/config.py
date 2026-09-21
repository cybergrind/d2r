"""Editable runtime defaults. Healing triggers strictly below each threshold."""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_serializer, field_validator, model_validator

from .layout import BELT_SIZE
from .models import Actor, PotionType


# Field types carry the range checks so models only spell out cross-field rules.
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Percent = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
BeltTarget = Annotated[int, Field(ge=0, le=BELT_SIZE)]


class Config(BaseModel):
    """Immutable, strictly typed settings. Change them with `with_overrides`, never `model_copy`."""

    model_config = ConfigDict(frozen=True, strict=True, extra='forbid')


def with_overrides[M: BaseModel](model: M, **changes: object) -> M:
    """Return a re-validated copy; `model_copy(update=...)` would skip validation of the new values."""
    return model.__class__.model_validate({**dict(model), **changes})


class HealingConfig(Config):
    actor: Actor
    enabled: bool
    thresholds: Mapping[PotionType, Percent]
    cooldowns: Mapping[PotionType, Positive]
    sample_max_age: Positive
    consumption_timeout: Positive

    @field_validator('thresholds', 'cooldowns', mode='after')
    @classmethod
    def _complete_and_frozen(
        cls, values: Mapping[PotionType, float], info: ValidationInfo
    ) -> Mapping[PotionType, float]:
        if set(values) != set(PotionType):
            raise ValueError(f'{info.field_name} must configure every potion type')
        return MappingProxyType(dict(values))

    @field_serializer('thresholds', 'cooldowns')
    def _plain_mapping(self, values: Mapping[PotionType, float]) -> dict[PotionType, float]:
        return dict(values)

    @model_validator(mode='after')
    def _rejuvenation_below_healing(self) -> Self:
        if self.thresholds[PotionType.REJUVENATION] > self.thresholds[PotionType.HEALING]:
            raise ValueError('Rejuvenation threshold must not exceed healing threshold')
        return self


PLAYER_HEALING = HealingConfig(
    actor=Actor.PLAYER,
    enabled=True,
    thresholds={PotionType.HEALING: 65, PotionType.REJUVENATION: 40},
    cooldowns={PotionType.HEALING: 3.0, PotionType.REJUVENATION: 1.0},
    sample_max_age=1.0,
    consumption_timeout=2.0,
)
MERC_HEALING = HealingConfig(
    actor=Actor.MERC,
    enabled=True,
    thresholds={PotionType.HEALING: 55, PotionType.REJUVENATION: 20},
    cooldowns={PotionType.HEALING: 3.0, PotionType.REJUVENATION: 3.0},
    sample_max_age=1.0,
    consumption_timeout=2.0,
)


class NotificationsWidgetConfig(Config):
    enabled: bool = True
    seconds: Positive = 1.0


class PlayerHealthWidgetConfig(Config):
    enabled: bool = True
    # Shown at or below this percentage of maximum life.
    percent: Percent = 70


class MercHealthWidgetConfig(Config):
    enabled: bool = True
    # Shown strictly below this percentage of the client life fraction.
    percent: Percent = 65


class BeltWidgetConfig(Config):
    enabled: bool = True
    # Explicit column targets override the bottom-row detection; None keeps it automatic.
    rejuvenation_target: BeltTarget | None = None
    healing_target: BeltTarget | None = None

    @model_validator(mode='after')
    def _targets_fit_belt(self) -> Self:
        if (self.rejuvenation_target or 0) + (self.healing_target or 0) > BELT_SIZE:
            raise ValueError(f'Potion targets must fit {BELT_SIZE} belt slots')
        return self


class TeleportWidgetConfig(Config):
    enabled: bool = True
    low_percent: Percent = 20
    show_repair_in_town: bool = True


class LootWidgetConfig(Config):
    enabled: bool = True


class KeysWidgetConfig(Config):
    enabled: bool = True
    low_count: Annotated[int, Field(ge=0)] = 5


class PortalWidgetConfig(Config):
    enabled: bool = True
    trigger_remaining: Annotated[int, Field(ge=0)] = 19
    capacity: Annotated[int, Field(gt=0)] = 20

    @model_validator(mode='after')
    def _trigger_below_capacity(self) -> Self:
        if self.trigger_remaining >= self.capacity:
            raise ValueError('Portal trigger must be an integer in 0..capacity-1')
        return self


class OSDConfig(Config):
    """Window and display settings; each widget owns its own nested config."""

    notifications: NotificationsWidgetConfig = NotificationsWidgetConfig()
    player_health: PlayerHealthWidgetConfig = PlayerHealthWidgetConfig()
    merc_health: MercHealthWidgetConfig = MercHealthWidgetConfig()
    belt: BeltWidgetConfig = BeltWidgetConfig()
    teleport: TeleportWidgetConfig = TeleportWidgetConfig()
    portal: PortalWidgetConfig = PortalWidgetConfig()
    loot: LootWidgetConfig = LootWidgetConfig()
    key_stock: KeysWidgetConfig = KeysWidgetConfig()
    # Seconds before any reading displays as stale; handed to every widget by the factory.
    max_age: Positive = 2.0
    font_size: Positive = 16
    font_family: str = 'monospace'
    font_weight: str = 'bold'
    color: str = '#ffffff'
    x: int = 0
    y: int = -130
    monitor: Annotated[int, Field(ge=0)] | None = None
    refresh_interval: Positive = 0.1


class ReaderConfig(Config):
    interval: Positive = 0.1
    reconnect_delay: Positive = 2.0
    shutdown_timeout: Positive = 3.0


class InputConfig(Config):
    game_app_id: str = 'steam_app_2536520'
    focus_timeout: Positive = 0.3
    key_hold_seconds: Positive = 0.025
    bindings: Mapping[Actor, tuple[str, ...]] = Field(
        default_factory=lambda: {Actor.PLAYER: (), Actor.MERC: ('Shift_L',)}, validate_default=True
    )
    column_keys: Mapping[int, str] = Field(
        default_factory=lambda: {1: '1', 2: '2', 3: '3', 4: '4'}, validate_default=True
    )

    @field_validator('bindings', mode='after')
    @classmethod
    def _actor_bindings(cls, values: Mapping[Actor, tuple[str, ...]]) -> Mapping[Actor, tuple[str, ...]]:
        if set(values) != set(Actor):
            raise ValueError('bindings must configure every actor')
        if any(not name.strip() for names in values.values() for name in names):
            raise ValueError('Binding names must be non-empty')
        return MappingProxyType(dict(values))

    @field_validator('column_keys', mode='after')
    @classmethod
    def _column_bindings(cls, values: Mapping[int, str]) -> Mapping[int, str]:
        if set(values) != {1, 2, 3, 4}:
            raise ValueError('column_keys must configure exactly columns 1-4')
        if any(not name.strip() for name in values.values()):
            raise ValueError('Column key names must be non-empty')
        return MappingProxyType(dict(values))

    @field_serializer('bindings')
    def _plain_bindings(self, values: Mapping[Actor, tuple[str, ...]]) -> dict[Actor, tuple[str, ...]]:
        return dict(values)

    @field_serializer('column_keys')
    def _plain_columns(self, values: Mapping[int, str]) -> dict[int, str]:
        return dict(values)


OSD = OSDConfig()
READER = ReaderConfig()
INPUT = InputConfig()


class ResourceReaderConfig(Config):
    # Promote each candidate only after controlled host validation on this build.
    portal_stats_offset: int | None = None
    key_stats_offset: int | None = None
    teleport_stats_offset: int | None = None
    weapon_slots_verified: bool = False
    location_verified: bool = False

    @field_validator('portal_stats_offset', 'teleport_stats_offset', 'key_stats_offset', mode='after')
    @classmethod
    def _aligned_within_header(cls, offset: int | None) -> int | None:
        if offset is not None and (not 0 <= offset <= 0x1F0 or offset % 8):
            raise ValueError('Resource stat descriptor must be aligned within the research header')
        return offset

    @property
    def enabled(self) -> bool:
        return (
            self.portal_stats_offset is not None
            or self.teleport_stats_offset is not None
            or self.key_stats_offset is not None
            or self.location_verified
        )


# Controlled 2026-09-21 probes: 32/33 -> 31/33 charges, 18 -> 16 portals,
# staff slot 4 -> 11 on swap, and Harrogath 109 -> field 111.
RESOURCE_READER = ResourceReaderConfig(
    portal_stats_offset=0x30,
    key_stats_offset=0x30,
    teleport_stats_offset=0xE8,
    weapon_slots_verified=True,
    location_verified=True,
)
