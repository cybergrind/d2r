"""Editable runtime defaults. Healing triggers strictly below each threshold."""

from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Annotated, Literal, Self

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
    # Seconds. An unconsumed potion is retried after retry_backoff, doubling per miss up to retry_backoff_max;
    # max_consecutive_misses in a row pause the actor for suspend_seconds.
    retry_backoff: Positive
    retry_backoff_max: Positive
    max_consecutive_misses: Annotated[int, Field(gt=0)]
    suspend_seconds: Positive
    # Burst rule (user, 2026-10-12): losing this share of the most life within burst_window seconds asks for a
    # rejuvenation whatever life is left. 0: off for the actor.
    burst_share: Percent = 0.0
    burst_window: Positive = 1.0
    # No rejuvenation for the actor while the belt holds this many or fewer: they are kept for the other.
    rejuvenation_reserve: Annotated[int, Field(ge=0)] = 0

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
    burst_share=30.0,
    sample_max_age=1.0,
    consumption_timeout=2.0,
    retry_backoff=2.0,
    retry_backoff_max=30.0,
    max_consecutive_misses=8,
    suspend_seconds=120.0,
)
# Healing potions restore the merc slowly (about +13% over 8 s, 2026-09-26); rejuvenations are instant. Rejuvenation
# at 40%, never the belt's last two (the player, 2026-10-13: "keep at least 2 rev potions for user").
MERC_HEALING = HealingConfig(
    actor=Actor.MERC,
    enabled=True,
    thresholds={PotionType.HEALING: 75, PotionType.REJUVENATION: 40},
    rejuvenation_reserve=2,
    cooldowns={PotionType.HEALING: 3.0, PotionType.REJUVENATION: 0.5},
    sample_max_age=1.0,
    consumption_timeout=2.0,
    retry_backoff=2.0,
    retry_backoff_max=30.0,
    max_consecutive_misses=8,
    suspend_seconds=120.0,
)


class HealPriorityConfig(Config):
    """Whom the healer (`make osd`) feeds first, and the healing potions kept for the character
    (automation/priority.py). The player (2026-10-13): "healer should feed merc, then me. but if situation is
    critical - then feed player"; "something is wrong if we're empty" (rca/2026-10-13/potions-findings.md)."""

    # Off: the character first at every sample, no potion kept back.
    enabled: bool = True
    # Life %: where the macro's life budget ends (combat/harm.py `SafetySettings.floor`). The character is critical
    # when life, projected `horizon` seconds ahead at the fall of the last `window` seconds, is under it.
    floor: Percent = 65.0
    # Seconds: the burst rule's window (`HealingConfig.burst_window`) and harm.py's `horizon`.
    window: Positive = 1.0
    horizon: Positive = 1.5
    # Life points of a super healing potion (harm.py `healing_points`). The reserve brings the character from the
    # floor to full once: ceil((100 - floor)% of the most life / healing_points); 1818 life -> 2.
    healing_points: Positive = 480.0
    # One more kept while no rejuvenation is on the belt: a healing potion works over seconds.
    bare_extra: Annotated[int, Field(ge=0)] = 1
    # The last healing potion is never the mercenary's, whatever the life reads.
    least_reserve: Annotated[int, Field(ge=0)] = 1
    # Hold the reserve back from the mercenary. Off (the player, 2026-10-13: "we're trying to heal merc, but keep at
    # least 2 rev potions for user"): the character keeps 2 rejuvenations instead (`MERC_HEALING.rejuvenation_reserve`).
    # The reserve stays the `Potion stock:` low mark.
    keep_healing: bool = False


HEAL_PRIORITY = HealPriorityConfig()


class ShowItemsConfig(Config):
    """Turn the game's Show Items toggle on when a game starts (automation/show_items.py)."""

    enabled: bool = True
    # X11 key names to press; empty: the character's own Show Items binding (input/keybindings.py).
    key_names: tuple[str, ...] = ()
    saved_games: Path = Path(
        '/mnt/extra/1000/games/steam/steamapps/compatdata/2536520/pfx/drive_c/users/steamuser/Saved Games/'
        'Diablo II Resurrected'
    )
    settle_seconds: Positive = 1.5  # after entering a game, before the first press
    retry_seconds: Positive = 2.0  # between presses while the byte stays off
    max_attempts: Annotated[int, Field(gt=0)] = 3
    sample_max_age: Positive = 1.0


SHOW_ITEMS = ShowItemsConfig()


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
    # Shown outside town at or below this many charges left (user, 2026-10-10: at 20, not at 13 of 69).
    low_charges: Annotated[int, Field(ge=0)] = 20
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
    # Button centre and highlight size as fractions of the game window height; x from the window's left edge, y from
    # its bottom edge. Measured 2026-09-28 on a 2560x1418 window (Charsi): 768 px from the left, 414 px up, ~96 px.
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


class BeltConfig(Config):
    """What the belt's columns are for: the pickup rules (macros/pickup.py) and the OSD belt widget."""

    # The kind of each column 1-4 when it is empty (tracking/belt.py `column_shortages`). None: learned from the game
    # (the kind a column last held), which resets each game while the belt carries over. Set to the player's belt
    # (the player, 2026-10-13: "yes, use this layout").
    layout: tuple[PotionType, PotionType, PotionType, PotionType] | None = (
        PotionType.REJUVENATION,
        PotionType.REJUVENATION,
        PotionType.HEALING,
        PotionType.HEALING,
    )


OSD = OSDConfig()
READER = ReaderConfig()
INPUT = InputConfig()
BELT = BeltConfig()


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
    # sys.setswitchinterval for the service process (Python's default 0.005): each memory pread gives up the GIL and,
    # with another thread busy, waits up to the interval to take it back (rca/2026-10-13/latency-findings.md, Fix 1).
    switch_interval: Annotated[float, Field(gt=0, le=0.005)] = 0.0005
    reconnect_delay: Positive = 2.0
    shop_auto: bool = True  # watch loaded vendor stock and scan when its first gear item changes
    shop_poll_interval: Positive = 1.0  # seconds between stock probes in town; 5x outside town
    stash_auto: bool = True  # collect (as Win+S) every time the stash panel is closed
    stash_poll_interval: Positive = 0.5  # seconds between open-panel flag reads
    identify_auto: bool = True  # assess inventory/cube items the moment they become identified (Cain, scrolls)
    identify_poll_interval: Positive = 1.0  # seconds between identified-flag reads; 5x in the field, all identified
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
    # The pickup step takes every rune (user, 2026-10-10 night); the marks above stay at `rune_minimum`.
    pickup_rune_minimum: Annotated[str, Field(pattern=r'^r(0[1-9]|[12][0-9]|3[0-3])$')] = 'r01'
    rune_poll_interval: Positive = 0.5
    shrine_marks: tuple[int, ...] = (18,)  # shrine types to point at (d2data shrines.json; 18 = Gem)
    unique_marks: bool = True  # also point at unique drops whose base has an expensive unique (loot/uniques.py)
    # Ist: the good-roll ask (highest bucket median, loot/data/uniques.json) of the base's dearest unique.
    # 2.5 takes in Harlequin Crest and The Stone of Jordan (user, 2026-10-06).
    unique_minimum: Annotated[float, Field(ge=0)] = 2.5
    super_chest_marks: bool = True  # point at closed glowing chests (object class 397)
    # Other drops to point at, by group (loot/materials.py): Worldstone Shards, flawless and perfect gems, the
    # Colossal Ancients' statues, the Pandemonium keys (user, 2026-10-07), charms and the bosses' essences (user,
    # 2026-10-10), Wirt's Leg (user, 2026-10-12).
    material_marks: tuple[Literal['shards', 'gems', 'statues', 'keys', 'charms', 'essences', 'leg'], ...] = (
        'shards',
        'gems',
        'statues',
        'keys',
        'charms',
        'essences',
        'leg',
    )
    # Groups the pickup step takes besides the marked ones: every ring, jewel and amulet (user, 2026-10-10 night).
    pickup_also: tuple[Literal['rings', 'jewels', 'amulets'], ...] = ('rings', 'jewels', 'amulets')
    # The pickup step also takes the equipment the loot filter shows (loot/shown.py; user, 2026-10-11): uniques and
    # sets of any size; rare, magic and white bases of at most `pickup_shown_cells` inventory cells ("prefer smaller
    # types"). 6 takes the 2x3 bases and leaves the 2x4 ones (polearms, Colossus Blades, Zakarum Shields, Amazon
    # bows and spears).
    pickup_filter_shown: bool = True
    pickup_shown_cells: Annotated[int, Field(ge=1, le=8)] = 6
    # A gold pile of at least this much is gone to by the pickup step (user, 2026-10-11: "gold >5k"); None: none is.
    pickup_gold_minimum: int | None = 5000
    terror_probe: bool = True  # record monster sightings/kills to terror-probe.jsonl (terror/probe.py research)
    terror_probe_interval: Positive = 0.25  # seconds between monster-table reads
    terror_summary_seconds: Positive = 10.0  # seconds between per-area summary events
    # Seconds between `around` events: the monsters within a screen with the player's life (danger-plan.md R4;
    # its statistics script, terror/exposure.py, is in git history).
    terror_around_seconds: Positive = 1.0
    elite_line: bool = True  # the level's elite groups killed, alive and expected on the Terror card (terror/elites.py)
    danger_marks: bool = True  # deadly packs: own map dots, ground marks and a warning row (terror/danger.py)
    terror_card: bool = True  # HUD card: next Herald tier, group kills, breakpoint and spawn odds
    boss_stats: bool = True  # Terror card slot: kills, average time between kills and time since the last, per boss
    combat_record: bool = True  # record takes of play in combat_areas for combat/plan.md (takes/record.py)
    # Levels recorded when `combat_everywhere` is off (levels.txt ids): Chaos Sanctuary, Catacombs 1-4, Worldstone
    # Keep 1-3 and the Throne, Tower Cellar 1-5, Black Marsh, Far Oasis, Frigid Highlands, Durance of Hate 1-3,
    # Halls of Anguish, Death's Calling and Vaught, Arcane Sanctuary.
    combat_areas: tuple[int, ...] = (
        108,
        35,
        36,
        37,
        38,
        128,
        129,
        130,
        131,
        21,
        22,
        23,
        24,
        25,
        6,
        43,
        111,
        100,
        101,
        102,
        122,
        123,
        124,
        74,
    )
    # Record every level that is no town (user, 2026-10-12: "can we record combat logs for all levels?").
    combat_everywhere: bool = True
    # The towns too (2026-10-13): takes follow one another with no gap but the loading screens, so what is carried
    # into a level (buffs, the belt, the staff's charges) is on record.
    combat_town: bool = True
    # The pursuit loop for the builds `make serve` plays (BuildSettings.pursuit, macros/pursuit.py;
    # rca/2026-10-13/pursuit-v1.md): a teleport-key press posts a goal and cancels nothing. Off: the keys as before.
    macro_pursuit: bool = True
    # Keypad 5 taps this button of a virtual Xbox pad, made at the first press (input/gamepad.py;
    # rca/2026-10-13/pickup-cube.md). 'x': bindings record 1, where Loot to Cube is written below. None: no such key.
    gamepad_button: str | None = 'x'
    # Controller bindings `make serve` writes at its start, record -> skill (skills.txt) (gamepad.py `bind_table`;
    # rca/2026-10-13/controller-mode.md §3; user 2026-10-13: "bind everything we need"). Records 0-5 are
    # A X B Y RB RT, 6-11 the same with LT held; 12-15 have no pad button and are cast by keyboard slot n's key
    # (macros/pad.py `KeyRoute`). A record holding another skill is the player's, left alone unless named in
    # `gamepad_overwrite`; a skill already on a record is not written twice; the file is copied to runs/gamepad
    # first. Written only while no D2R.exe runs: the client reads the file at launch and writes it back on leaving
    # a game. Kept as they are: 0 Attack (A), 7 Town Portal (LT+X). Record 2: Summon Defiler over Miasma Bolt (the
    # player, 2026-10-13: "we don't use miasma bolt at all"), so Consume's upkeep works in controller mode too.
    # Bind Demon on 12 (key `6`), Engorge on 13 (key `7`): `7` is Echoing Strike's keyboard key, and a strike held
    # on it after a flip to controller mode recasts record 13 - harmless for Engorge, not for Bind Demon.
    gamepad_bindings: dict[int, int] = {
        1: 370,  # X: Loot to Cube
        2: 377,  # B: Summon Defiler
        3: 388,  # Y: Echoing Strike
        4: 390,  # RB: Blade Warp
        5: 54,  # RT: Teleport (the staff's charges)
        6: 387,  # LT+A: Psychic Ward
        8: 389,  # LT+B: Hex: Purge
        9: 375,  # LT+Y: Death Mark
        10: 393,  # LT+RB: Sigil: Lethargy
        11: 381,  # LT+RT: Consume
        12: 382,  # key `6`: Bind Demon, the player's own (the macros never cast it)
        13: 379,  # key `7`: Engorge
    }
    gamepad_overwrite: tuple[int, ...] = (2,)  # records whose skill the table may replace (the file copied first)
    gamepad_bind: bool = True  # False: the bindings files are never written
    # The macros play in either input mode (macros/pad.py; the player 2026-10-13: "thus, we could do full automated
    # runs in controller's mode"). False: a run in controller mode is refused with "click once".
    controller_play: bool = True
    # Records 12-15 by keyboard key in controller mode (macros/pad.py `KeyRoute`): once a game is in controller mode,
    # with no hostile within 20 units, a Hex: Purge cast by its key probes the route (`Pad key:`); records 12-15 are
    # cast by key in this session only after a probe worked. False: no probe, no key route.
    controller_key_route: bool = True
    # Reads per second of the game's input mode (tracking/input_mode.py InputModeWatch).
    input_mode_rate: Positive = 100.0
    # Takes are gzipped as they close (about 1/15 of the size); past this many GB in all the oldest are removed, one
    # the character died in last (takes/retain.py).
    combat_keep_gb: float = 20.0
    combat_rate: Positive = 25.0  # frames per second sampled; the engine's rate
    # Also write each monster's path record to the take's paths.jsonl when it changes (~1 KB per monster per change).
    combat_paths: bool = True
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
    upward: bool = False  # y is the bottom of the slot's widget stack, which grows up


class HudGroundConfig(Config):
    """Marks on the game view at map positions (hud/ground.py); shown while the level map is."""

    enabled: bool = True
    # Map dot kinds (levels/map_card.py KIND_TONES) that also get a ground mark (user, 2026-10-05). 'danger': every
    # monster of a deadly pack, 'elite': its leader, 'pack': the arrow to such a pack out of view.
    kinds: tuple[str, ...] = ('leader', 'danger', 'elite', 'pack', 'herald', 'stairs', 'exit', 'waypoint')
    alpha: Annotated[float, Field(gt=0, le=1)] = 0.5  # outline; the fill is fainter still
    # Where the player stands in the game window, and one tile's floor-diamond height, as window fractions.
    # Classic 800x600 values (a tile is 160x80 px there); not calibrated in D2R yet.
    player_x: Annotated[float, Field(ge=0, le=1)] = 0.5
    player_y: Annotated[float, Field(ge=0, le=1)] = 0.46
    tile_height: Positive = 80 / 600
    # Marks beyond the view are drawn this far inside the window edge (fraction of its height).
    edge_inset: Annotated[float, Field(ge=0, lt=0.4)] = 0.04
    # A mark beyond the view is an arrow on a ring around the player (user, 2026-10-05). Ring radius as a fraction of
    # the window height: `arrow_near` for `arrow_hold` seconds after entering a level, growing to `arrow_rest` by
    # `arrow_seconds`.
    arrow_near: Annotated[float, Field(gt=0, lt=0.5)] = 0.09
    arrow_rest: Annotated[float, Field(gt=0, lt=0.5)] = 0.24
    arrow_hold: Annotated[float, Field(ge=0)] = 1.0
    arrow_seconds: Positive = 2.5
    arrow_alpha: Annotated[float, Field(gt=0, le=1)] = 0.9
    # Kinds that get an arrow only within this many tiles of the player (a screen is ~15 across; user, 2026-10-05:
    # not an arrow for every pack); other kinds always do. A deadly pack gets one arrow, to its centre; its members
    # none.
    arrow_range: dict[str, float] = {'leader': 15, 'elite': 15, 'danger': 0, 'pack': 40}


class HudConfig(Config):
    """HUD canvas (inventory_tracking/hud/plan.md): one click-through overlay with widget slots."""

    # Widget sizes are logical pixels at this game-window height; other heights scale (0.6-2.0).
    reference_height: Positive = 1422
    refresh_interval: Positive = 0.1
    gap: Annotated[int, Field(ge=0)] = 8
    slots: dict[str, HudSlot] = {
        # Level guide rows: bottom left, growing up (user, 2026-10-06: at the top left they covered stash tooltips).
        'guide': HudSlot(x=0.01, y=0.99, upward=True),
        # Level map (the guide's MapCard): top centre (user, 2026-10-04).
        'map': HudSlot(x=0.5, y=0.15, centered=True),
        # Alt+D / shop / identify card: at most 45% of the window wide.
        'assessment': HudSlot(x=0.2, y=0.12, max_width=0.45),
        # Valuable drops on the ground (user, 2026-10-07).
        'loot': HudSlot(x=0.33, y=0.34),
        # Terror Zone card (terror/tracker.py): right of the widest Alt+D card, left of the game's corner text (user,
        # 2026-10-04 and 2026-10-06).
        'terror': HudSlot(x=0.68, y=0.02, max_width=0.2),
        # Ground marks (hud/ground.py): the whole game window.
        'ground': HudSlot(x=0, y=0),
        # Unread Traderie notifications (hud/traderie.py): top centre, between the portraits and the Terror card.
        'traderie': HudSlot(x=0.5, y=0.02, max_width=0.3, centered=True),
        # Macro attack mode (hud/process.py ModeBeacon), above the skill bar; never dimmed: read at a glance in a fight.
        'mode': HudSlot(x=0.5, y=0.8, max_width=0.2, centered=True),
    }
    # Slot places in controller mode (hud/live.py InputModeByte; rca/2026-10-13/controller-mode.md §5): the bottom bar
    # tops at about 0.89 of the window height and the life globe begins at x 0.165. Unnamed slots keep their places.
    controller_slots: dict[str, HudSlot] = {
        # Left of the life globe.
        'guide': HudSlot(x=0.01, y=0.99, max_width=0.155, upward=True),
        # The mode line and the pad legend under it, growing up from just above the bar.
        'mode': HudSlot(x=0.5, y=0.88, max_width=0.3, centered=True, upward=True),
    }
    # Slots also shown while the game is not focused or not running, laid out on the focused output's working area.
    desktop_slots: tuple[str, ...] = ('traderie',)
    # The niri output the desktop slots are drawn on, on their own surface (user, 2026-10-09: Traderie on the laptop
    # panel, the game's HUD on DP-5). None, or not connected: they share the game's canvas.
    desktop_output: str | None = 'eDP-1'
    ground: HudGroundConfig = HudGroundConfig()
    # While one of these panels is open the `dim_slots` widgets are drawn at `dim_alpha` of their opacity (user,
    # 2026-10-07); 'assessment' is about those items and stays as it is.
    dim_panels: tuple[str, ...] = ('inventory', 'stash', 'cube', 'npc_shop', 'mercenary')
    dim_slots: tuple[str, ...] = ('guide', 'map', 'ground', 'terror', 'loot')
    dim_alpha: Annotated[float, Field(ge=0, le=1)] = 0.15


HUD = HudConfig()


class TraderieConfig(Config):
    """Traderie notifications card (hud/traderie.py), read through the player's own browser."""

    enabled: bool = True
    port: Annotated[int, Field(gt=0, lt=65536)] = 8333  # the browser's DevTools (remote debugging) port
    poll_seconds: Positive = 60  # between reloads of the reader's hidden tab
    stale_seconds: Positive = 300  # no successful check for this long is said on the card
    max_lines: Annotated[int, Field(gt=0)] = 3  # messages listed under the count


TRADERIE = TraderieConfig()


class DCloneConfig(Config):
    """Uber Diablo progress card (hud/dclone.py), from diablo2.io's Diablo Clone tracker."""

    enabled: bool = True
    url: str = 'https://diablo2.io/dclone_api.php'
    # The player's economy in the tracker's codes: ver 2 = RotW (1 = LoD), ladder 2 = Non-Ladder, hc 2 = Softcore.
    version: str = '2'
    ladder: str = '2'
    hardcore: str = '2'
    poll_seconds: Positive = 300  # between requests; the tracker bans an address that asks a few times a minute
    # After a failed request the wait doubles per failure in a row up to this, unless the tracker names its own
    # (Retry-After).
    backoff_seconds: Positive = 3600
    # The last answer and the time of the next request, kept across restarts of `serve`.
    cache: Path = Path(__file__).resolve().parent / 'runs' / 'dclone' / 'cache.json'
    stale_seconds: Positive = 1800  # no successful check for this long is said on the card
    minimum_progress: Annotated[int, Field(ge=1, le=6)] = 4  # of 6 steps: a region this close is shown


DCLONE = DCloneConfig()
