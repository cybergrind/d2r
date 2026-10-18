"""Inactive-by-default bridge from a fresh TZ probe to one guarded macro area run.

Only a coordinator that was explicitly enabled and a route promoted to ``ready``
can dispatch. The service's default coordinator has neither. No shard action exists.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Protocol

from inventory_tracking.common import LOG
from inventory_tracking.macros.pursuit import Pursuit
from inventory_tracking.native.layout import TOWN_IDS
from inventory_tracking.routes.model import FIGHT, USE
from inventory_tracking.routes.progress import Progress, done
from inventory_tracking.routes.tz_execution import Observation, Slice, WorkStep
from inventory_tracking.routes.tz_leveling import (
    TOWER_GROUP_CORE,
    TOWER_GROUP_ITINERARY,
    Capability,
    Coordinator,
)
from inventory_tracking.terror.monsters import MonsterSnapshot


TOWER_ROUTE_PATHS = {'Hole': (6, 11, 15), 'Countess': (6, 20, 21, 22, 23, 24, 25)}


class TzHunter(Protocol):
    @property
    def pursuit(self) -> Pursuit | None: ...


class TzMacro(Protocol):
    """The guarded runner seam; offline fakes implement the same contract."""

    @property
    def progress(self) -> Progress | None: ...

    @property
    def area_seen(self) -> int | None: ...

    @property
    def unread(self) -> bool: ...

    @property
    def working(self) -> bool: ...

    @property
    def hunter(self) -> TzHunter | None: ...

    @property
    def tz_last_action(self) -> str | None: ...

    @property
    def tz_last_ok(self) -> bool: ...

    @property
    def tz_loot_clear(self) -> bool: ...

    @property
    def tz_hunt_over(self) -> str | None: ...

    @property
    def tz_target_over(self) -> str | None: ...

    @property
    def valuable_left(self) -> Callable[[], str | None]: ...

    def tz_no_room(self) -> str | None: ...

    def tz_start(self, action: str, area: int, now: float, *, game: str | None = None) -> bool: ...

    def tz_cancel(self) -> None: ...


@dataclass(frozen=True)
class ProbeRead:
    game: str
    snapshot: MonsterSnapshot
    at: float


class TzRuntime:
    """Run confirmed active areas and guarded game transitions through the macro runner."""

    def __init__(
        self,
        coordinator: Coordinator,
        macro: TzMacro,
        capabilities: dict[int, Capability],
        supplies: Callable[[], int | None],
        *,
        start_game: str | None = None,
    ) -> None:
        self.coordinator, self.macro, self.capabilities, self.supplies = coordinator, macro, capabilities, supplies
        self.slice = Slice(coordinator, capabilities, self._dispatch, cancel=macro.tz_cancel)
        self.read: ProbeRead | None = None
        self.now = 0.0
        self.game = ''
        self.reported = False
        self.start_game = start_game
        self.after_area = False
        self.session_action: str | None = None
        self.session_at: float | None = None
        self.town_checked_game: str | None = None
        self.travel_hop: int | None = None

    def on_probe(self, game: str, snapshot: MonsterSnapshot, events: list[dict], now: float) -> None:
        """Called only after the probe bracketed its read with the same game and area."""
        self.read = ProbeRead(game, snapshot, now)
        self.coordinator.observe(game, snapshot.terror_entries, at=now)
        if self.coordinator.on and self.coordinator.game != game:
            self.coordinator._game(game)
        metrics = self.coordinator.metrics
        prior_deaths = set(metrics.deaths) if metrics is not None else set()
        self.coordinator.observe_events(game, events)
        work = self.slice.work
        pending_at = self.slice.pending_at
        if (
            work is not None
            and work.game == game
            and self.slice.pending == 'hunt'
            and pending_at is not None
            and 0 <= now - pending_at < self.slice.action_timeout
            and metrics is not None
            and any(metrics.sightings[key][1] == work.area for key in metrics.deaths - prior_deaths)
        ):
            self.slice.pending_at = now
            LOG.info('TZ area %d: hunt watchdog refreshed by confirmed leader kill', work.area)

    def _dispatch(self, action: str, area: int) -> bool:
        capability = self.capabilities[area]
        if action == 'travel' and self._tower_group:
            source = self.macro.area_seen
            hop = self._route_hop(area, source) if source is not None else None
            if hop is None or not self.macro.tz_start(action, hop, self.now, game=self.game):
                return False
            self.travel_hop = hop
            return True
        if action == 'travel' and capability.waypoint != area:
            source = self.macro.area_seen
            progress = self.macro.progress
            step = progress.step(source) if progress is not None and source is not None else None
            if step is None or step.stage.to != area:
                return False
        return self.macro.tz_start(action, area, self.now, game=self.game)

    @property
    def _tower_group(self) -> bool:
        config = self.coordinator.config
        return config is not None and config.itinerary == TOWER_GROUP_ITINERARY

    def _route_hop(self, destination: int, source: int) -> int | None:
        """One observed route edge toward a Tower-group area, including the town waypoint and area 20 transit."""
        capability = self.capabilities[destination]
        if source in TOWN_IDS:
            return capability.waypoint
        progress = self.macro.progress
        if progress is None:
            return None
        path = TOWER_ROUTE_PATHS.get(capability.route)
        if path is None or source not in path or destination not in path:
            return None
        index = path.index(source)
        if index >= path.index(destination):
            return None
        if source == 6 and not progress.select_route(self.game, 6, capability.route):
            return None
        step = progress.step(source)
        if step is None or step.route != capability.route or step.stage.to != path[index + 1]:
            return None
        return step.stage.to

    def _target_outcome(self, area: int, target: str) -> str:
        progress = self.macro.progress
        if progress is None or (chosen := progress.chosen(area)) is None:
            return 'failed'
        _, script = chosen
        stages = [
            stage
            for stage in script.stages
            if (target == 'boss' and stage.kind == FIGHT)
            or (target == 'chest' and stage.kind == USE and 'chest' in stage.mark.lower())
            or (target == 'object' and stage.kind == USE and not stage.to)
        ]
        if not stages:
            return 'failed'
        facts = progress.facts if progress.dead is None else replace(progress.facts, dead=progress.dead())
        if all(done(area, stage, facts) is True for stage in stages):
            return 'killed' if target == 'boss' else 'opened'
        return 'failed'

    def _stop(self, reason: str) -> WorkStep:
        self.macro.tz_cancel()
        self.coordinator._stop(reason)
        self._report(self.now)
        return WorkStep('stop', reason)

    def _report(self, now: float) -> None:
        if not self.reported and self.coordinator.metrics is not None:
            LOG.info('TZ slice: %s; report %s', self.coordinator.stop_reason, self.coordinator.metrics.report(now))
            self.reported = True

    def _completion(self, game: str, area: int | None, supply: int | None) -> Observation | WorkStep | None:
        pending = self.slice.pending
        work = self.slice.work
        if pending is None or work is None:
            return None
        if pending == 'restock':
            minimum = self.coordinator.config.min_supply if self.coordinator.config is not None else 0
            if self.macro.working:
                return None
            if self.macro.tz_last_action != pending or not self.macro.tz_last_ok:
                return self._stop('TZ town supply stopped; check macro card')
            if supply is None or supply < minimum:
                return self._stop('low supplies after town check')
            return Observation('restock', True, game)
        if self.macro.working:
            return None
        if pending in ('prebuff', 'travel', 'loot'):
            if self.macro.tz_last_action != pending or not self.macro.tz_last_ok:
                return self._stop(f'TZ {pending} stopped; check macro card')
            if pending == 'prebuff':
                return Observation('prebuff', True, game)
            if pending == 'travel':
                if self._tower_group:
                    if area is None or area != self.travel_hop:
                        return self._stop(f'TZ travel did not reach route hop {self.travel_hop}')
                    if area != work.area:
                        hop = self._route_hop(work.area, area)
                        if hop is None or not self.macro.tz_start('travel', hop, self.now, game=game):
                            return self._stop(f'TZ onward route to area {work.area} unavailable')
                        self.travel_hop = hop
                        return None
                    self.travel_hop = None
                return Observation('travel', True, game, area=area) if area == work.area else None
            if pending == 'loot' and self.macro.tz_loot_clear and area == work.area:
                # `valuable_left` reports a valuable on the ground, not whether
                # inventory has room. A full inventory can leave choose_pickup empty.
                if left := self.macro.valuable_left():
                    return self._stop(f'TZ loot left on ground: {left}')
                if progress := self.macro.progress:
                    progress.looted(work.area)
                return Observation('loot', True, game, area=area, outcome='clear')
            return self._stop('TZ loot was not clear')
        if pending == 'hunt':
            reason = self.macro.tz_hunt_over
            if reason is None:
                return self._stop('TZ elite hunt stopped without an outcome')
            if reason.startswith('nothing is left to go to'):
                return Observation('hunt', True, game, area=area, outcome='exhausted')
            return self._stop(f'TZ elite hunt stopped: {reason}')
        if pending == 'target':
            reason = self.macro.tz_target_over
            if reason is None:
                return self._stop('TZ route target stopped without an outcome')
            outcome = self._target_outcome(work.area, work.target or '')
            return Observation('target', True, game, area=area, outcome=outcome)
        return None

    def tick(self, now: float) -> WorkStep:
        self.now = now
        if not self.coordinator.on:
            self.macro.tz_cancel()
            self._report(now)
            return WorkStep('stop', self.coordinator.stop_reason or 'inactive')
        progress = self.macro.progress
        game = progress.game if progress is not None else None
        area = self.macro.area_seen
        if self.session_action is not None:
            return self._session_completion(game, area)
        if game is None and self.coordinator.game is None and self.start_game is not None:
            return self._start_session('create', 0, self.start_game)
        work = self.slice.work
        if work is not None and game is not None and game != work.game:
            return self._stop('game changed during TZ area')
        if (
            self.slice.pending is not None
            and self.slice.pending_at is not None
            and now - self.slice.pending_at >= self.slice.action_timeout
        ):
            return self._stop('TZ area action timed out')
        if self.macro.unread or game is None or area is None:
            return WorkStep('wait', 'game or area unread')
        if self.slice.pending == 'hunt' and (blocked := self.macro.tz_no_room()):
            left = self.macro.valuable_left()
            if left is not None and left != 'unread':
                return self._stop(f'TZ inventory full: {blocked}; recover ground loot in this game')
        self.game = game
        read = self.read if self.read is not None and self.read.game == game else None
        entries = read.snapshot.terror_entries if read is not None else None
        if (
            self.coordinator.config is not None
            and self.coordinator.config.itinerary == TOWER_GROUP_ITINERARY
            and area in TOWN_IDS
            and self.town_checked_game != game
        ):
            current = self.coordinator.reads.current(game, now)
            if current is None:
                return WorkStep('wait', 'current TZ town memory unread')
            LOG.info('TZ town memory: areas %s; effect %s', sorted(current.areas), ', '.join(current.effects))
            if not TOWER_GROUP_CORE.issubset(current.areas):
                return self._stop('current TZ is not Black Marsh, Hole and Forgotten Tower')
            self.town_checked_game = game
        supply = self.supplies()
        if supply is None:
            return WorkStep('wait', 'belt supplies unread')
        completed = self._completion(game, area, supply)
        if isinstance(completed, WorkStep):
            return completed
        life = read.snapshot.player_life if read is not None else None
        if life is None:
            return WorkStep('wait', 'player life unread')
        hunter = self.macro.hunter
        pursuit = hunter.pursuit if hunter is not None else None
        manual = bool(pursuit is not None and pursuit.paused)
        if self.after_area:
            return self._after_area(game, area, supply, now, manual, life)
        step = self.slice.tick(
            game,
            now,
            entries=entries,
            observed_at=read.at if read is not None else None,
            area=area,
            completed=completed,
            manual=manual,
            dead=life[0] <= 0,
            dangerous=life[1] > 0 and life[0] / life[1] < 0.25,
            supplies=supply,
            valuable_no_room=False,
        )
        if step.action == 'stop':
            self.macro.tz_cancel()
            self._report(now)
        elif step.action == 'area-done':
            self.after_area = True
        elif step.action == 'reset':
            return self._after_area(game, area, supply, now, manual, life)
        elif step.action == 'done':
            self._report(now)
        return step

    def _start_session(self, action: str, area: int, game: str) -> WorkStep:
        if not self.macro.tz_start(action, area, self.now, game=game):
            return self._stop(f'TZ {action} could not start')
        self.session_action, self.session_at = action, self.now
        if self.coordinator.metrics is not None:
            self.coordinator.metrics.phase('town' if action != 'return-town' else 'travel', self.now)
        return WorkStep('wait', f'TZ {action} started')

    def _session_completion(self, game: str | None, area: int | None) -> WorkStep:
        action = self.session_action
        assert action is not None
        if self.session_at is not None and self.now - self.session_at >= self.slice.action_timeout:
            return self._stop(f'TZ {action} timed out')
        if self.macro.working:
            return WorkStep('wait', f'TZ {action} running')
        if self.macro.tz_last_action != action or not self.macro.tz_last_ok:
            return self._stop(f'TZ {action} stopped; check macro card')
        if action == 'return-town':
            if game != self.game or area not in TOWN_IDS:
                return WorkStep('wait', 'TZ return to town not yet observed')
            self.after_area = False
        elif action == 'leave':
            if game is not None or area is not None:
                return WorkStep('wait', 'TZ game exit not yet observed')
            self.session_action = None
            return self._start_session('create', 0, self.game)
        elif action == 'create':
            if game is None or game == (self.game or self.start_game) or area not in TOWN_IDS:
                return WorkStep('wait', 'TZ next game not yet observed in town')
            self.game = game
            self.start_game = None
            self.after_area = False
            self.read = None
        self.session_action = self.session_at = None
        return WorkStep('wait', f'TZ {action} observed')

    def _after_area(
        self,
        game: str,
        area: int,
        supply: int,
        now: float,
        manual: bool,
        life: tuple[int, int],
    ) -> WorkStep:
        choice = self.coordinator.decide(
            game,
            now=now,
            capabilities=self.capabilities,
            manual=manual,
            dead=life[0] <= 0,
            dangerous=life[1] > 0 and life[0] / life[1] < 0.25,
            supplies=supply,
            valuable_no_room=False,
        )
        if choice.action in ('enter', 'reset') and (left := self.macro.valuable_left()):
            return self._stop(f'TZ exit blocked by ground loot: {left}')
        if choice.action == 'stop':
            return self._stop(choice.reason)
        if choice.action in ('wait', 'pause'):
            return WorkStep(choice.action, choice.reason)
        if choice.action == 'enter' and choice.area is not None:
            progress = self.macro.progress
            step = progress.step(area) if progress is not None else None
            if self._tower_group and area not in TOWN_IDS:
                hop = self._route_hop(choice.area, area)
                if hop is not None:
                    self.after_area = False
                    return WorkStep('wait', 'next active area is ready')
                if area == 6 and choice.area in TOWER_GROUP_ITINERARY:
                    return self._stop(f'TZ branch from Black Marsh to area {choice.area} unavailable')
            if area in TOWN_IDS or (step is not None and step.stage.to == choice.area):
                self.after_area = False
                return WorkStep('wait', 'next active area is ready')
            return self._start_session('return-town', area, game)
        if choice.action == 'reset':
            config = self.coordinator.config
            if config is None or self.coordinator.games >= config.max_games:
                self.coordinator._stop('maximum games reached')
                self._report(now)
                return WorkStep('done', 'maximum games reached')
            return self._start_session('leave', area, game)
        return WorkStep('wait', choice.reason)
