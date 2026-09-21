"""Editable runtime defaults. Healing triggers strictly below each threshold."""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .models import Actor, PotionType


def positive(value, name):
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be finite and positive')


def potion_map(values, name, *, percent=False):
    if set(values) != set(PotionType):
        raise ValueError(f'{name} must configure every potion type')
    for value in values.values():
        if percent:
            if not math.isfinite(value) or not 0 <= value <= 100:
                raise ValueError(f'{name} must be percentages in 0..100')
        else:
            positive(value, name)
    return MappingProxyType(dict(values))


@dataclass(frozen=True)
class HealingConfig:
    actor: Actor
    enabled: bool
    thresholds: Mapping[PotionType, float]
    cooldowns: Mapping[PotionType, float]
    sample_max_age: float
    consumption_timeout: float

    def __post_init__(self):
        object.__setattr__(self, 'actor', Actor(self.actor))
        object.__setattr__(self, 'thresholds', potion_map(self.thresholds, 'thresholds', percent=True))
        object.__setattr__(self, 'cooldowns', potion_map(self.cooldowns, 'cooldowns'))
        if self.thresholds[PotionType.REJUVENATION] > self.thresholds[PotionType.HEALING]:
            raise ValueError('Rejuvenation threshold must not exceed healing threshold')
        positive(self.sample_max_age, 'sample_max_age')
        positive(self.consumption_timeout, 'consumption_timeout')


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


@dataclass(frozen=True)
class OSDConfig:
    player_health_percent: float = 70
    merc_health_percent: float = 65
    notification_seconds: float = 1.0
    max_age: float = 2.0
    font_size: float = 16
    font_family: str = 'monospace'
    font_weight: str = 'bold'
    color: str = '#ffffff'
    x: int = 0
    y: int = -130
    monitor: int | None = None
    refresh_interval: float = 0.1
    rejuvenation_target: int | None = None
    healing_target: int | None = None

    def __post_init__(self):
        for name in ('notification_seconds', 'max_age', 'font_size', 'refresh_interval'):
            positive(getattr(self, name), name)
        for name in ('player_health_percent', 'merc_health_percent'):
            if not 0 <= getattr(self, name) <= 100:
                raise ValueError(f'{name} must be in 0..100')
        if self.monitor is not None and self.monitor < 0:
            raise ValueError('monitor must be nonnegative')
        targets = (self.rejuvenation_target, self.healing_target)
        if any(x is not None and (type(x) is not int or not 0 <= x <= 16) for x in targets):
            raise ValueError('Potion targets must be integers in 0..16')
        if sum(x or 0 for x in targets) > 16:
            raise ValueError('Potion targets must fit 16 belt slots')


@dataclass(frozen=True)
class ReaderConfig:
    interval: float = 0.1
    reconnect_delay: float = 2.0
    shutdown_timeout: float = 3.0

    def __post_init__(self):
        for name in ('interval', 'reconnect_delay', 'shutdown_timeout'):
            positive(getattr(self, name), name)


@dataclass(frozen=True)
class InputConfig:
    game_app_id: str = 'steam_app_2536520'
    focus_timeout: float = 0.3
    key_hold_seconds: float = 0.025
    # Preserve conservative protection while migrating the old shared timestamp.
    legacy_cooldown: float = 3.0

    def __post_init__(self):
        for name in ('focus_timeout', 'key_hold_seconds', 'legacy_cooldown'):
            positive(getattr(self, name), name)


OSD = OSDConfig()
READER = ReaderConfig()
INPUT = InputConfig()
