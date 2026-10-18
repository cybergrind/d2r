"""Pure, inactive planning and accounting for a Terror Zone leveling loop.

The caller must provide a game identity and a *current* client service read. The
tracker's remembered/monster-inferred terror state is useful on the HUD, but is
not sufficient evidence for automated travel or shard verification.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.links import WAYPOINTS
from inventory_tracking.routes.model import FIGHT, USE
from inventory_tracking.routes.tz_groups import ActiveZone, installed_active_zones, match_active_zone
from inventory_tracking.terror.monsters import TerrorEntry
from inventory_tracking.terror.tracker import MODIFIER_NAMES
from inventory_tracking.terror.zones import group_of


Source = Literal['active', 'shard']
Status = Literal['ready', 'needs-played-check', 'unavailable']
TOWER_GROUP_ITINERARY = (6, 11, 15, 20, 21, 22, 23, 24, 25)
TOWER_GROUP_CORE = frozenset((6, 11, 15, 21, 22, 23, 24, 25))


@dataclass(frozen=True)
class Config:
    source: Source
    itinerary: Literal['all'] | tuple[int, ...]
    shard_act: int | None = None
    finish_current_on_rotation: bool = True
    target_rule: Literal['required'] = 'required'
    objective: Literal['leaders-per-hour'] = 'leaders-per-hour'
    max_games: int = 1
    max_seconds: float = 3600
    min_supply: int = 3
    pickup_policy: Literal['sure', 'all'] = 'sure'
    character: str | None = None
    difficulty: str | None = None

    def __post_init__(self) -> None:
        if self.source == 'shard' and self.shard_act not in range(1, 6):
            raise ValueError('shard source requires an act from 1 to 5')
        if self.source == 'active' and self.shard_act is not None:
            raise ValueError('active source must not specify a shard act')
        if isinstance(self.itinerary, tuple) and (
            not self.itinerary or len(set(self.itinerary)) != len(self.itinerary)
        ):
            raise ValueError('designated itinerary must contain distinct areas')
        if self.max_games < 1 or self.max_seconds <= 0 or self.min_supply < 0:
            raise ValueError('invalid loop limits')


@dataclass(frozen=True)
class TerrorEvidence:
    game: str
    observed_at: float
    areas: frozenset[int]
    effects: tuple[str, ...]
    source: str = 'client-service'


class FreshTerror:
    def __init__(self, max_age: float = 3.0) -> None:
        self.max_age = max_age
        self.reading: TerrorEvidence | None = None

    def observe(self, game: str, entries: tuple[TerrorEntry, ...] | None, *, at: float) -> None:
        # An unread pass invalidates the prior pass, even in the same game.
        self.reading = None
        if entries is None or not game or not math.isfinite(at):
            return
        effects = tuple(
            dict.fromkeys(MODIFIER_NAMES.get(entry.modifier, f'unknown ({entry.modifier})') for entry in entries)
        )
        self.reading = TerrorEvidence(game, at, frozenset(entry.area for entry in entries), effects)

    def current(self, game: str, now: float) -> TerrorEvidence | None:
        read = self.reading
        if read is None or read.game != game or not 0 <= now - read.observed_at <= self.max_age:
            return None
        return read


@dataclass(frozen=True)
class Capability:
    area: int
    route: str
    waypoint: int | None
    target: Literal['boss', 'chest', 'object'] | None
    status: Status
    reason: str = ''
    entry: str = 'unmapped'
    exit: str = 'unmapped'


def route_inventory() -> dict[int, Capability]:
    """Conservative catalog audit of every installed TZ level, including no-Herald transit levels."""
    found: dict[int, Capability] = {}
    for zone in installed_active_zones():
        for area in zone.areas:
            if area in found:
                continue
            options = [(route, script) for route in ROUTES for script in route.scripts if script.area == area]
            if not options:
                found[area] = Capability(area, '', None, None, 'unavailable', 'no route script')
                continue
            route, script = options[0]
            waypoint = next((start for start in route.starts if start in WAYPOINTS), None)
            leading = next(
                (stage for prior in route.scripts for stage in prior.stages if stage.to == area or area in stage.tours),
                None,
            )
            entry = (
                leading.text()
                if leading is not None
                else (f'waypoint {area}' if area in WAYPOINTS else 'route entry needs played check')
            )
            leaving = next((stage for stage in script.stages if stage.to), None)
            exit_stage = leaving or next((stage for stage in script.stages if stage.kind == 'leave'), None)
            exit_text = exit_stage.text() if exit_stage is not None else 'route exit needs played check'
            target = (
                'boss'
                if any(stage.kind == FIGHT for stage in script.stages)
                else (
                    'chest'
                    if any(stage.kind == USE and 'chest' in stage.mark.lower() for stage in script.stages)
                    else ('object' if any(stage.kind == USE and not stage.to for stage in script.stages) else None)
                )
            )
            pending = next((stage.pending for stage in script.stages if stage.pending), '')
            if waypoint is None or pending:
                reason = pending or 'no entry waypoint'
                found[area] = Capability(area, route.name, waypoint, target, 'unavailable', reason, entry, exit_text)
            else:
                found[area] = Capability(
                    area, route.name, waypoint, target, 'needs-played-check', entry=entry, exit=exit_text
                )
    return found


@dataclass(frozen=True)
class ActiveZonePlan:
    """Identified active group and its route audit; the table's level order is not a travel plan."""

    zone: ActiveZone
    areas: tuple[int, ...]
    blockers: tuple[tuple[int, str], ...]

    @property
    def ready(self) -> bool:
        return not self.blockers


def active_zone_plan(evidence: TerrorEvidence, capabilities: dict[int, Capability]) -> ActiveZonePlan | None:
    """Identify the current group and explain every level that cannot yet be dispatched."""
    zone = match_active_zone(evidence.areas)
    if zone is None:
        return None
    blockers = tuple(
        (area, capability.reason or capability.status) if capability is not None else (area, 'no route capability')
        for area in zone.areas
        if (capability := capabilities.get(area)) is None or capability.status != 'ready'
    )
    return ActiveZonePlan(zone, zone.areas, blockers)


@dataclass(frozen=True)
class Progress:
    completed: frozenset[int] = frozenset()
    skipped: frozenset[int] = frozenset()
    current: int | None = None


@dataclass(frozen=True)
class Choice:
    action: Literal['enter', 'wait', 'reset', 'continue-current', 'finish-current', 'stop-current', 'stop', 'pause']
    area: int | None = None
    reason: str = ''
    skipped: tuple[tuple[int, str], ...] = ()


def next_area(
    config: Config,
    evidence: TerrorEvidence | None,
    progress: Progress,
    capabilities: dict[int, Capability],
    *,
    finish_current: bool | None = None,
) -> Choice:
    """Choose only a service-confirmed, reachable area; group names never imply eligibility."""
    if evidence is None:
        return Choice('wait', reason='TZ list unread or stale')
    finish = config.finish_current_on_rotation if finish_current is None else finish_current
    if progress.current is not None and progress.current not in evidence.areas:
        return Choice('finish-current' if finish else 'stop-current', progress.current, 'active TZ rotated')
    if progress.current is not None and progress.current not in progress.completed:
        return Choice('continue-current', progress.current)
    order = sorted(evidence.areas) if config.itinerary == 'all' else config.itinerary
    skipped: list[tuple[int, str]] = []
    first: int | None = None
    for area in order:
        if area in progress.completed or area in progress.skipped:
            continue
        if area not in evidence.areas:
            skipped.append((area, 'not terrorized in current read'))
            continue
        group = group_of(area)
        if config.source == 'shard' and (group is None or group.act != config.shard_act):
            skipped.append((area, 'outside selected shard act'))
            continue
        capability = capabilities.get(area)
        if capability is None:
            skipped.append((area, 'no route capability'))
        elif capability.status != 'ready':
            skipped.append((area, capability.reason or capability.status))
        elif first is None:
            first = area
    if first is not None:
        return Choice('enter', first, skipped=tuple(skipped))
    return Choice('reset', reason='no eligible terrorized area remains', skipped=tuple(skipped))


@dataclass(frozen=True)
class HuntTarget:
    kind: Literal['champion', 'unique', 'super', 'herald', 'room', 'boss', 'chest']
    name: str
    distance: float
    expected_kills: float
    fight_seconds: float
    last_seen: float
    reachable: bool = True
    failures: int = 0


def choose_hunt(
    targets: tuple[HuntTarget, ...],
    *,
    now: float,
    hunt_seconds: float = 0,
    stale_seconds: float = 8,
    max_hunt_seconds: float = 90,
    max_failures: int = 2,
    travel_units_per_second: float = 8,
) -> HuntTarget | None:
    """Rank leaders and promising rooms by expected kills per time, then finish the boss/chest."""
    available = [
        target
        for target in targets
        if target.reachable
        and target.failures < max_failures
        and (target.kind in ('boss', 'chest') or now - target.last_seen <= stale_seconds)
    ]
    route_targets = [target for target in available if target.kind in ('boss', 'chest')]
    hunt = [target for target in available if target.kind not in ('boss', 'chest')]
    if hunt_seconds >= max_hunt_seconds:
        hunt = []
    if hunt:
        return max(
            hunt,
            key=lambda target: (
                target.expected_kills / max(1, target.distance / travel_units_per_second + target.fight_seconds),
                -target.distance,
            ),
        )
    return min(route_targets, key=lambda target: target.distance) if route_targets else None


KINDS = ('champion', 'unique', 'super', 'herald')
PHASES = ('town', 'travel', 'combat', 'loot')


@dataclass
class Metrics:
    started: float
    active_phase: str = 'other'
    phase_at: float | None = None
    seconds: dict[str, float] = field(default_factory=dict)
    sightings: dict[str, tuple[str, int]] = field(default_factory=dict)
    deaths: set[str] = field(default_factory=set)
    kills: dict[str, int] = field(default_factory=lambda: dict.fromkeys(KINDS, 0))
    xp_first: int | None = None
    xp_last: int | None = None
    outcomes: dict[tuple[int, str], str] = field(default_factory=dict)
    shard_spent: int = 0
    player_deaths: int = 0
    potions: int = 0

    def phase(self, name: str, at: float) -> None:
        if name not in (*PHASES, 'other') or at < self.started:
            raise ValueError('invalid phase')
        prior = self.started if self.phase_at is None else self.phase_at
        self.seconds[self.active_phase] = self.seconds.get(self.active_phase, 0) + max(0, at - prior)
        self.active_phase, self.phase_at = name, at

    def seen(self, unit: str, kind: str, area: int) -> None:
        if kind in KINDS:
            self.sightings.setdefault(unit, (kind, area))

    def died(self, unit: str, area: int) -> None:
        sighting = self.sightings.get(unit)
        if unit not in self.deaths and sighting is not None and sighting[1] == area:
            self.deaths.add(unit)
            self.kills[sighting[0]] += 1

    def lost(self, unit: str) -> None:
        if unit not in self.deaths:
            self.sightings.pop(unit, None)

    def xp(self, value: int, at: float) -> None:
        if value < 0 or at < self.started:
            raise ValueError('invalid XP reading')
        if self.xp_first is None:
            self.xp_first = value
        self.xp_last = value

    def target(self, area: int, name: str, outcome: str) -> None:
        self.outcomes[area, name] = outcome

    def report(self, ended: float) -> dict[str, object]:
        elapsed = max(0, ended - self.started)
        seconds = dict(self.seconds)
        by_area: dict[int, dict[str, int]] = {}
        for unit in self.deaths:
            kind, area = self.sightings[unit]
            row = by_area.setdefault(area, dict.fromkeys(KINDS, 0))
            row[kind] += 1
        prior = self.started if self.phase_at is None else self.phase_at
        seconds[self.active_phase] = seconds.get(self.active_phase, 0) + max(0, ended - prior)
        return {
            'elapsed_seconds': elapsed,
            'leaders': dict(self.kills),
            'leaders_by_area': by_area,
            'leaders_per_hour': sum(self.kills.values()) * 3600 / elapsed if elapsed else 0,
            'xp_delta': (self.xp_last - self.xp_first)
            if self.xp_first is not None and self.xp_last is not None
            else None,
            'xp_per_hour': (self.xp_last - self.xp_first) * 3600 / elapsed
            if elapsed and self.xp_first is not None and self.xp_last is not None
            else None,
            'seconds': seconds,
            'targets': dict(self.outcomes),
            'shards_spent': self.shard_spent,
            'deaths': self.player_deaths,
            'potions': self.potions,
        }


class Coordinator:
    """Inactive-by-default TZ request and decision state.

    It returns declarative choices only. A future guarded executor may act on
    them after route and game evidence is played and reviewed. Shard consumption
    is intentionally unavailable until the plan's manual observations exist.
    """

    def __init__(self, config: Config | None = None, *, store: Path | None = None, enabled: bool = False) -> None:
        self.config, self.store = config, store
        self.enabled = enabled and config is not None
        self.on = False
        self.stop_reason = ''
        self.reads = FreshTerror()
        self.game: str | None = None
        self.games = 0
        self.progress = Progress()
        self.targets: dict[tuple[int, str], str] = {}
        self.shard_spent = 0
        self.started_at: float | None = None
        self.skips: dict[int, str] = {}
        self.metrics: Metrics | None = None
        if store is not None and store.exists():
            self._restore()

    def _restore(self) -> None:
        assert self.store is not None
        try:
            saved = json.loads(self.store.read_text(encoding='utf-8'))
            if saved.get('source') != (self.config.source if self.config else None):
                return
            self.game = str(saved['game']) if saved.get('game') else None
            self.games = int(saved.get('games', 0))
            self.progress = Progress(
                frozenset(int(x) for x in saved.get('completed', ())),
                frozenset(int(x) for x in saved.get('skips', {})),
                int(saved['current']) if saved.get('current') is not None else None,
            )
            self.skips = {int(area): str(why) for area, why in saved.get('skips', {}).items()}
            self.started_at = float(saved['started_at']) if saved.get('started_at') is not None else None
            self.targets = {(int(area), name): outcome for area, name, outcome in saved.get('targets', ())}
            # Deliberately do not restore `on` or TZ evidence after a service restart.
        except OSError, ValueError, TypeError, KeyError:
            self.stop_reason = 'saved TZ progress unreadable'

    def _save(self) -> None:
        if self.store is None or self.config is None:
            return
        saved = {
            'source': self.config.source,
            'game': self.game,
            'games': self.games,
            'completed': sorted(self.progress.completed),
            'current': self.progress.current,
            'skips': self.skips,
            'started_at': self.started_at,
            'targets': [[area, name, outcome] for (area, name), outcome in sorted(self.targets.items())],
        }
        self.store.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.store.with_suffix(self.store.suffix + '.tmp')
        temporary.write_text(json.dumps(saved, sort_keys=True), encoding='utf-8')
        temporary.replace(self.store)

    def request(self, requested: float, now: float) -> bool:
        """Toggle the separate request; disabled installs reject it without starting work."""
        if not self.enabled or not math.isfinite(requested) or not 0 <= now - requested <= 1:
            return False
        self.on = not self.on
        self.stop_reason = ''
        if self.on and self.started_at is None:
            self.started_at = now
            self._save()
        if self.on and self.metrics is None:
            self.metrics = Metrics(now)
        return True

    @property
    def hud_line(self) -> str:
        if not self.on:
            return f'TZ loop: stopped: {self.stop_reason}' if self.stop_reason else 'TZ loop: inactive'
        reading = self.reads.reading
        if reading is None:
            return 'TZ loop: waiting for current client TZ read'
        effect = ', '.join(reading.effects) or 'unknown'
        mode = self.config.source if self.config else 'unknown'
        return f'TZ loop: {mode}; areas {len(reading.areas)}; effect {effect}; {reading.source}'

    def observe(self, game: str, entries: tuple[TerrorEntry, ...] | None, *, at: float) -> None:
        self.reads.observe(game, entries, at=at)

    def observe_events(self, game: str, events: list[dict[str, object]]) -> None:
        """Count only confirmed probe leader deaths, once per game and unit."""
        metrics = self.metrics
        if not self.on or metrics is None or game != self.game:
            return
        for event in events:
            if event.get('event') != 'elite_kill':
                continue
            kind, area, unit = event.get('kind'), event.get('area'), event.get('unit_id')
            if kind not in KINDS or not isinstance(area, int) or not isinstance(unit, int):
                continue
            key = f'{game}:{unit}'
            metrics.seen(key, kind, area)
            metrics.died(key, area)

    def _game(self, game: str) -> None:
        if game != self.game:
            self.game = game
            self.games += 1
            self.progress = Progress()
            self.targets = {}
            self.skips = {}
            self._save()

    def _stop(self, why: str) -> Choice:
        self.on = False
        self.stop_reason = why
        return Choice('stop', reason=why)

    def decide(
        self,
        game: str,
        *,
        now: float,
        capabilities: dict[int, Capability],
        dead: bool = False,
        dangerous: bool = False,
        supplies: int | None = None,
        valuable_no_room: bool = False,
        manual: bool = False,
        character: str | None = None,
        difficulty: str | None = None,
    ) -> Choice:
        if not self.on or self.config is None:
            return Choice('stop', reason=self.stop_reason or 'inactive')
        if dead:
            return self._stop('dead')
        if dangerous:
            return self._stop('dangerous combat')
        if supplies is not None and supplies < self.config.min_supply:
            return self._stop('low supplies')
        if valuable_no_room:
            return self._stop('valuable with no room')
        if manual:
            return Choice('pause', reason='manual intervention')
        if self.config.character is not None:
            if character is None:
                return Choice('wait', reason='character unread')
            if character != self.config.character:
                return self._stop('wrong character')
        if self.config.difficulty is not None:
            if difficulty is None:
                return Choice('wait', reason='difficulty unread')
            if difficulty != self.config.difficulty:
                return self._stop('wrong difficulty')
        if self.started_at is not None and now - self.started_at >= self.config.max_seconds:
            return self._stop('maximum time reached')
        if self.config.source == 'shard':
            return self._stop('shard use awaits played evidence')
        evidence = self.reads.current(game, now)
        if evidence is None:
            return Choice('wait', reason='TZ list unread or stale')
        self._game(game)
        if self.games > self.config.max_games:
            return self._stop('maximum games reached')
        return next_area(self.config, evidence, self.progress, capabilities)

    def begin_area(self, game: str, area: int, capability: Capability, *, now: float) -> bool:
        if game != self.game or not self.on or capability.area != area or capability.status != 'ready':
            return False
        read = self.reads.current(game, now)
        if read is None or area not in read.areas:
            return False
        if area in self.progress.completed or area in self.progress.skipped:
            return False
        self.progress = Progress(self.progress.completed, self.progress.skipped, area)
        self._save()
        return True

    def skip_area(self, game: str, area: int, why: str) -> bool:
        if game != self.game or not why or area in self.progress.completed:
            return False
        self.skips[area] = why
        self.progress = Progress(self.progress.completed, self.progress.skipped | {area})
        self._save()
        return True

    def target_outcome(self, game: str, area: int, name: str, outcome: str) -> None:
        if game != self.game or outcome not in ('killed', 'opened', 'failed', 'unreachable'):
            return
        self.targets[area, name] = outcome
        self._save()

    def complete_area(self, game: str, area: int, target: str | None) -> bool:
        if game != self.game or (target is not None and self.targets.get((area, target)) not in ('killed', 'opened')):
            return False
        self.progress = Progress(self.progress.completed | {area}, self.progress.skipped)
        self._save()
        return True
