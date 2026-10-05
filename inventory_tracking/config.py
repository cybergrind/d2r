"""Editable runtime defaults. Healing triggers strictly below each threshold."""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_serializer, field_validator, model_validator

from inventory_tracking.models import Actor, PotionType
from inventory_tracking.native.layout import BELT_SIZE


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
    # An unconsumed potion is retried after retry_backoff, doubling per consecutive miss up to retry_backoff_max;
    # max_consecutive_misses in a row pause the actor for suspend_seconds, after which it resumes on its own.
    retry_backoff: Positive
    retry_backoff_max: Positive
    max_consecutive_misses: Annotated[int, Field(gt=0)]
    suspend_seconds: Positive

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
        if self.retry_backoff > self.retry_backoff_max:
            raise ValueError('retry_backoff must not exceed retry_backoff_max')
        return self


PLAYER_HEALING = HealingConfig(
    actor=Actor.PLAYER,
    enabled=True,
    thresholds={PotionType.HEALING: 65, PotionType.REJUVENATION: 40},
    cooldowns={PotionType.HEALING: 3.0, PotionType.REJUVENATION: 1.0},
    sample_max_age=1.0,
    consumption_timeout=2.0,
    retry_backoff=2.0,
    retry_backoff_max=30.0,
    max_consecutive_misses=8,
    suspend_seconds=120.0,
)
# Healing potions restore this merc slowly (about +13% over 8 s measured 2026-09-26); rejuvenations are instant,
# so they take over well before the merc is in danger.
MERC_HEALING = HealingConfig(
    actor=Actor.MERC,
    enabled=True,
    thresholds={PotionType.HEALING: 75, PotionType.REJUVENATION: 65},
    cooldowns={PotionType.HEALING: 3.0, PotionType.REJUVENATION: 0.5},
    sample_max_age=1.0,
    consumption_timeout=2.0,
    retry_backoff=2.0,
    retry_backoff_max=30.0,
    max_consecutive_misses=8,
    suspend_seconds=120.0,
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


class IdentifyWidgetConfig(Config):
    enabled: bool = True
    low_count: Annotated[int, Field(ge=0)] = 5


class PortalWidgetConfig(Config):
    enabled: bool = True
    # Shown in town at or below this many scrolls left in the tome.
    trigger_remaining: Annotated[int, Field(ge=0)] = 3
    capacity: Annotated[int, Field(gt=0)] = 20

    @model_validator(mode='after')
    def _trigger_below_capacity(self) -> Self:
        if self.trigger_remaining >= self.capacity:
            raise ValueError('Portal trigger must be an integer in 0..capacity-1')
        return self


class RepairMarkWidgetConfig(Config):
    """Highlight around a smith's Repair All button while equipped Teleport charges are missing."""

    enabled: bool = True
    # Button centre and highlight size as fractions of the game window height; x from the
    # window's left edge, y from its bottom edge. Measured 2026-09-28 on a 2560x1418 window
    # (Charsi): centre 768 px from the left, 414 px above the bottom, button about 96 px
    # (2026-09-28 screenshot check: 426 px sat ~12 px too high).
    center_x: Positive = 0.542
    center_y: Positive = 0.292
    size: Positive = 0.085
    color: str = '#ff3b3b'
    pulse_seconds: Positive = 1.2


class ConsumeWidgetConfig(Config):
    enabled: bool = True
    warn_before_seconds: Positive = 15
    ended_notice_seconds: Positive = 30


class OSDConfig(Config):
    """Window and display settings; each widget owns its own nested config."""

    notifications: NotificationsWidgetConfig = NotificationsWidgetConfig()
    player_health: PlayerHealthWidgetConfig = PlayerHealthWidgetConfig()
    merc_health: MercHealthWidgetConfig = MercHealthWidgetConfig()
    belt: BeltWidgetConfig = BeltWidgetConfig()
    teleport: TeleportWidgetConfig = TeleportWidgetConfig()
    portal: PortalWidgetConfig = PortalWidgetConfig()
    identify: IdentifyWidgetConfig = IdentifyWidgetConfig()
    loot: LootWidgetConfig = LootWidgetConfig()
    key_stock: KeysWidgetConfig = KeysWidgetConfig()
    consume: ConsumeWidgetConfig = ConsumeWidgetConfig()
    repair_mark: RepairMarkWidgetConfig = RepairMarkWidgetConfig()
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


class AppraisalConfig(Config):
    osd: bool = True
    display_seconds: Positive = 30
    display_recheck_interval: Positive = 0.5  # seconds between hover re-reads while an Alt+D card shows
    cache_seconds: Positive = 300
    poll_interval: Positive = 0.2
    publication_poll_interval: Positive = 2.0  # seconds between checks for a newly published KB generation
    focus_cache_seconds: Positive = 0.15  # watchers reuse a D2R focus answer this long
    slow_loop_seconds: Positive = 0.5  # log a per-step breakdown when one service-loop pass takes longer
    reconnect_delay: Positive = 2.0
    shop_auto: bool = True  # watch loaded vendor stock and scan when its first gear item changes
    shop_poll_interval: Positive = 1.0  # seconds between stock probes in town; 5x outside town
    stash_auto: bool = True  # collect (as Win+S) every time the stash panel is closed
    stash_poll_interval: Positive = 0.5  # seconds between open-panel flag reads
    identify_auto: bool = True  # assess inventory/cube items the moment they become identified (Cain, scrolls)
    identify_poll_interval: Positive = 1.0  # seconds between identified-flag reads in town; 5x outside town
    identify_lookup_processes: Annotated[int, Field(ge=1, le=8)] = 3  # KB lookups of one identify pass run in parallel
    retrieval_keep_warm_interval: Positive = 15.0  # idle seconds before a retrieval process reruns a recent lookup
    level_guide: bool = True  # on entering a guided level (levels/handlers/), point at its target
    level_guide_poll_interval: Positive = 0.5  # seconds between current-area reads
    level_guide_seconds: Positive = 5.0  # how long the arrow stays on the OSD
    # The map starts pinned: shown in every level until a double Win+C unpins it (user, 2026-10-05).
    level_guide_pinned: bool = True
    level_walls: bool = True  # draw walkable tiles of loaded rooms on the level map
    rune_marks: bool = True  # HUD arrows to valuable runes on the ground (streamed, often off-screen)
    rune_minimum: Annotated[str, Field(pattern=r'^r(0[1-9]|[12][0-9]|3[0-3])$')] = 'r16'  # Io and up (user, 2026-09-30)
    rune_poll_interval: Positive = 0.5
    shrine_marks: tuple[int, ...] = (18,)  # shrine types to point at (d2data shrines.json; 18 = Gem)
    super_chest_marks: bool = True  # point at closed glowing chests (object class 397)
    terror_probe: bool = True  # record monster sightings/kills to terror-probe.jsonl (terror/probe.py research)
    terror_probe_interval: Positive = 0.25  # seconds between monster-table reads
    terror_summary_seconds: Positive = 10.0  # seconds between per-area summary events
    terror_card: bool = True  # HUD card: next Herald tier, group kills, breakpoint and spawn odds
    terror_card_unconfirmed: bool = (
        False  # also show it before any monster says terrorized or not (marked "unconfirmed")
    )


APPRAISAL = AppraisalConfig()


class HudSlot(Config):
    """Top-left of a slot's widget stack as fractions of the game window (x from left, y from top)."""

    x: Annotated[float, Field(ge=0, le=1)]
    y: Annotated[float, Field(ge=0, le=1)]
    max_width: Annotated[float, Field(gt=0, le=1)] = 1.0  # widest widget, fraction of the game window width
    centered: bool = False  # x is the middle of the slot's widgets, not their left edge


class HudGroundConfig(Config):
    """Marks on the game view at map positions (hud/ground.py); shown while the level map is."""

    enabled: bool = True
    # Map dot kinds (osd/level_map.KIND_TONES) that also get a ground mark: unique/champion
    # monsters, Heralds, the next level, exits and waypoints (user, 2026-10-05).
    kinds: tuple[str, ...] = ('leader', 'herald', 'stairs', 'exit', 'waypoint')
    alpha: Annotated[float, Field(gt=0, le=1)] = 0.5  # outline; the fill is fainter still
    # Where the player stands in the game window, and one tile's floor-diamond height, as window
    # fractions. Classic 800x600 view values (a tile is 160x80 px there); not calibrated in D2R yet.
    player_x: Annotated[float, Field(ge=0, le=1)] = 0.5
    player_y: Annotated[float, Field(ge=0, le=1)] = 0.46
    tile_height: Positive = 80 / 600
    # Marks beyond the view are drawn this far inside the window edge (fraction of its height).
    edge_inset: Annotated[float, Field(ge=0, lt=0.4)] = 0.04


class HudConfig(Config):
    """HUD canvas (inventory_tracking/hud/plan.md): one click-through overlay with widget slots."""

    # Widget sizes are logical pixels at this game-window height; other heights scale (0.6-2.0).
    reference_height: Positive = 1422
    refresh_interval: Positive = 0.1
    gap: Annotated[int, Field(ge=0)] = 8
    slots: dict[str, HudSlot] = {
        'guide': HudSlot(x=0.03, y=0.08),
        # Level map (the guide's MapCard): centred at the top of the window (user, 2026-10-04).
        'map': HudSlot(x=0.5, y=0.15, centered=True),
        # Alt+D / shop / identify card: right of the guide card, at most 45% of the window wide.
        'assessment': HudSlot(x=0.2, y=0.12, max_width=0.45),
        # Valuable runes on the ground: under the guide card.
        'loot': HudSlot(x=0.03, y=0.34),
        # Terror Zone card (terror/tracker.py): right of the widest Alt+D card, at the top (user, 2026-10-04).
        'terror': HudSlot(x=0.78, y=0.02, max_width=0.2),
        # Ground marks (hud/ground.py): the whole game window.
        'ground': HudSlot(x=0, y=0),
    }
    ground: HudGroundConfig = HudGroundConfig()


HUD = HudConfig()
