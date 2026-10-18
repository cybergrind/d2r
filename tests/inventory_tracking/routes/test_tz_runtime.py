from dataclasses import replace

from inventory_tracking.common import LOG
from inventory_tracking.levels.model import Location
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.model import Route, fight, leave, level, loot, use
from inventory_tracking.routes.progress import Progress
from inventory_tracking.routes.tz_execution import AreaWork
from inventory_tracking.routes.tz_leveling import Capability, Config, Coordinator
from inventory_tracking.routes.tz_runtime import TzRuntime
from inventory_tracking.terror.monsters import MonsterSnapshot, TerrorEntry


def snapshot(area=1, life=(100, 100), tz=(35,)):
    return MonsterSnapshot(
        Location(area, 0x500000, 5000, 5000),
        frozenset(),
        None,
        (),
        player_life=life,
        terror_entries=tuple(TerrorEntry(zone, 96, 18) for zone in tz),
    )


class FakeHunter:
    pursuit = None


class Macro:
    def __init__(self):
        dead = set()
        self.dead = dead
        self.progress = Progress(
            (Route('A', (35,), (level(35, fight('Boss'), loot(), leave()),)),), dead=lambda: frozenset(dead)
        )
        self.progress.note('g', 1)
        self.area_seen: int | None = 1
        self.unread = False
        self.working = False
        self.hunter = FakeHunter()
        self.tz_last_action = None
        self.tz_last_ok = False
        self.tz_loot_clear = False
        self.tz_hunt_over = None
        self.tz_target_over = None
        self.ground = None
        self.no_room = None
        self.actions = []
        self.cancelled = []

    def tz_start(self, action, area, now, *, game=None):
        self.actions.append((action, area, game))
        if action in ('prebuff', 'restock', 'travel', 'loot', 'create', 'leave', 'return-town'):
            self.tz_last_action, self.tz_last_ok = action, True
        return True

    def tz_cancel(self):
        self.cancelled.append(True)

    def valuable_left(self):
        return self.ground

    def tz_no_room(self):
        return self.no_room


def test_one_ready_active_waypoint_area_runs_to_observed_boss_and_loot_offline(caplog):
    caplog.set_level('INFO', logger=LOG.name)
    coordinator = Coordinator(Config('active', (35,)), enabled=True)
    coordinator.request(1, 1)
    macro = Macro()
    runtime = TzRuntime(coordinator, macro, {35: Capability(35, 'A', 35, 'boss', 'ready')}, lambda: 8)
    runtime.on_probe('g', snapshot(), [], 1)
    assert runtime.tick(1.1).action == 'prebuff'
    assert runtime.tick(1.2).action == 'restock'
    assert runtime.tick(1.3).action == 'travel'
    macro.area_seen = 35
    macro.progress.note('g', 35)
    runtime.on_probe('g', snapshot(35), [], 1.4)
    assert runtime.tick(1.5).action == 'hunt'
    macro.tz_hunt_over = 'nothing is left to go to on this level: no route stage, no boss known'
    assert runtime.tick(1.6).action == 'target'
    macro.dead.add('Boss')
    macro.tz_target_over = 'what is left of the route is loot, which takes a press'
    assert runtime.tick(1.7).action == 'loot'
    macro.tz_loot_clear = True
    assert runtime.tick(1.8).action == 'area-done'
    assert [action for action, _, _ in macro.actions] == ['prebuff', 'restock', 'travel', 'hunt', 'target', 'loot']
    assert coordinator.progress.completed == {35}
    assert coordinator.targets[35, 'boss'] == 'killed'
    assert 'TZ area 35: travel observed' in caplog.text
    assert 'TZ area 35: boss killed observed' in caplog.text
    assert 'TZ area 35: loot clear observed' in caplog.text


def test_runtime_never_dispatches_when_coordinator_or_route_is_not_enabled():
    macro = Macro()
    coordinator = Coordinator(Config('active', (35,)))
    runtime = TzRuntime(coordinator, macro, {35: Capability(35, 'A', 35, 'boss', 'ready')}, lambda: 8)
    runtime.on_probe('g', snapshot(), [], 1)
    assert runtime.tick(1).action == 'stop'
    assert macro.actions == []

    coordinator = Coordinator(Config('active', (35,)), enabled=True)
    coordinator.request(1, 1)
    runtime = TzRuntime(coordinator, macro, {35: Capability(35, 'A', 35, 'boss', 'needs-played-check')}, lambda: 8)
    runtime.on_probe('g', snapshot(), [], 1)
    assert runtime.tick(1.1).action == 'done'
    assert macro.actions == []


def test_runtime_stops_on_low_life_before_dispatch():
    macro = Macro()
    coordinator = Coordinator(Config('active', (35,)), enabled=True)
    coordinator.request(1, 1)
    runtime = TzRuntime(coordinator, macro, {35: Capability(35, 'A', 35, 'boss', 'ready')}, lambda: 8)
    runtime.on_probe('g', snapshot(life=(20, 100)), [], 1)
    assert runtime.tick(1.1).reason == 'dangerous combat'
    assert macro.actions == []


def test_confirmed_probe_leader_kill_is_counted_once_from_first_game_read():
    macro = Macro()
    coordinator = Coordinator(Config('active', (35,)), enabled=True)
    coordinator.request(1, 1)
    runtime = TzRuntime(coordinator, macro, {35: Capability(35, 'A', 35, None, 'ready')}, lambda: 8)
    kill = {'event': 'elite_kill', 'unit_id': 7, 'area': 35, 'kind': 'champion'}
    runtime.on_probe('g', snapshot(), [kill, kill], 1)
    assert coordinator.metrics is not None
    assert coordinator.metrics.report(2)['leaders'] == {'champion': 1, 'unique': 0, 'super': 0, 'herald': 0}


def test_game_change_cancels_an_in_flight_area_before_a_new_probe_read():
    macro = Macro()
    coordinator = Coordinator(Config('active', (35,)), enabled=True)
    coordinator.request(1, 1)
    runtime = TzRuntime(coordinator, macro, {35: Capability(35, 'A', 35, 'boss', 'ready')}, lambda: 8)
    runtime.on_probe('g', snapshot(), [], 1)
    assert runtime.tick(1.1).action == 'prebuff'
    macro.progress.note('new-game', 1)
    assert runtime.tick(1.2).reason == 'game changed during TZ area'
    assert macro.cancelled


def test_unread_belt_prevents_the_first_action():
    macro = Macro()
    coordinator = Coordinator(Config('active', (35,)), enabled=True)
    coordinator.request(1, 1)
    runtime = TzRuntime(coordinator, macro, {35: Capability(35, 'A', 35, 'boss', 'ready')}, lambda: None)
    runtime.on_probe('g', snapshot(), [], 1)
    assert runtime.tick(1.1).reason == 'belt supplies unread'
    assert macro.actions == []


def test_tower_group_refuses_a_different_current_tz_read_in_town():
    macro = Macro()
    itinerary = (6, 11, 15, 20, 21, 22, 23, 24, 25)
    coordinator = Coordinator(Config('active', itinerary, max_games=1), enabled=True)
    coordinator.request(1, 1)
    caps = {area: Capability(area, 'Hole' if area in (11, 15) else 'Countess', 6, None, 'ready') for area in itinerary}
    runtime = TzRuntime(coordinator, macro, caps, lambda: 8)
    runtime.on_probe('g', snapshot(tz=(4, 38)), [], 1)

    result = runtime.tick(1.1)

    assert result.action == 'stop'
    assert 'current TZ' in result.reason
    assert macro.actions == []


def test_tower_group_selects_the_hole_branch_after_black_marsh():
    macro = Macro()
    macro.progress = Progress(ROUTES, wanted=lambda area: area in {11, 15, 21, 22, 23, 24, 25})
    macro.progress.note('g', 6)
    macro.area_seen = 6
    initial = macro.progress.step(6)
    assert initial is not None
    assert initial.stage.to == 20
    itinerary = (6, 11, 15, 20, 21, 22, 23, 24, 25)
    coordinator = Coordinator(Config('active', itinerary, max_games=1), enabled=True)
    coordinator.request(1, 1)
    caps = {area: Capability(area, 'Hole' if area in (11, 15) else 'Countess', 6, None, 'ready') for area in itinerary}
    runtime = TzRuntime(coordinator, macro, caps, lambda: 8)
    runtime.on_probe('g', snapshot(6, tz=itinerary), [], 1)
    coordinator.progress = coordinator.progress.__class__(frozenset({6}))
    runtime.after_area = True

    assert runtime.tick(1.1).reason == 'next active area is ready'
    chosen = macro.progress.step(6)
    assert chosen is not None
    assert chosen.stage.to == 11
    assert runtime._dispatch('travel', 11)
    assert macro.actions[-1] == ('travel', 11, 'g')


def test_tower_group_travels_from_town_via_black_marsh_and_untargeted_tower():
    macro = Macro()
    macro.progress = Progress(ROUTES, wanted=lambda area: area in {6, 11, 15, 21, 22, 23, 24, 25})
    macro.progress.note('g', 1)
    itinerary = (6, 11, 15, 20, 21, 22, 23, 24, 25)
    active = (6, 11, 15, 21, 22, 23, 24, 25)  # area 20 may have no TZ entry; it remains required transit
    coordinator = Coordinator(Config('active', itinerary, max_games=1), enabled=True)
    coordinator.request(1, 1)
    caps = {area: Capability(area, 'Countess', 6, None, 'ready') for area in itinerary}
    runtime = TzRuntime(coordinator, macro, caps, lambda: 8)
    runtime.on_probe('g', snapshot(tz=active), [], 1)
    coordinator.progress = coordinator.progress.__class__(frozenset({6, 11, 15}))

    assert runtime.tick(1.1).action == 'prebuff'
    assert runtime.tick(1.2).action == 'restock'
    assert runtime.tick(1.3).action == 'travel'
    assert macro.actions[-1] == ('travel', 6, 'g')

    macro.progress.note('g', 6)
    macro.area_seen = 6
    runtime.on_probe('g', snapshot(6, tz=active), [], 1.4)
    runtime.tick(1.5)
    chosen = macro.progress.step(6)
    assert chosen is not None
    assert chosen.stage.to == 20
    assert macro.actions[-1] == ('travel', 20, 'g')

    macro.progress.note('g', 20)
    macro.area_seen = 20
    runtime.on_probe('g', snapshot(20, tz=active), [], 1.6)
    runtime.tick(1.7)
    assert macro.actions[-1] == ('travel', 21, 'g')

    macro.progress.note('g', 21)
    macro.area_seen = 21
    runtime.on_probe('g', snapshot(21, tz=active), [], 1.8)
    assert runtime.tick(1.9).action == 'hunt'


def test_a_new_valuable_during_hunt_waits_for_pickup_instead_of_stopping():
    macro = Macro()
    coordinator = Coordinator(Config('active', (35,)), enabled=True)
    coordinator.request(1, 1)
    runtime = TzRuntime(coordinator, macro, {35: Capability(35, 'A', 35, None, 'ready')}, lambda: 8)
    runtime.on_probe('g', snapshot(), [], 1)
    assert runtime.tick(1.1).action == 'prebuff'
    assert runtime.tick(1.2).action == 'restock'
    assert runtime.tick(1.3).action == 'travel'
    macro.area_seen = 35
    macro.progress.note('g', 35)
    runtime.on_probe('g', snapshot(35), [], 1.4)
    assert runtime.tick(1.5).action == 'hunt'
    macro.ground = 'Deep Worldstone Shard'
    macro.working = True
    assert runtime.tick(1.6).action == 'hunt'
    assert coordinator.on
    macro.working = False
    macro.tz_hunt_over = 'nothing is left to go to on this level'
    assert runtime.tick(1.7).action == 'loot'
    macro.ground = None  # observed pickup removed the shard before the loot action finished
    macro.tz_loot_clear = True
    assert runtime.tick(1.8).action == 'area-done'


def test_inventory_full_with_valuable_stops_hunt_at_the_ground_location_without_exiting():
    macro = Macro()
    coordinator = Coordinator(Config('active', (35,)), enabled=True)
    coordinator.request(1, 1)
    runtime = TzRuntime(coordinator, macro, {35: Capability(35, 'A', 35, None, 'ready')}, lambda: 8)
    runtime.on_probe('g', snapshot(), [], 1)
    runtime.tick(1.1)
    runtime.tick(1.2)
    runtime.tick(1.3)
    macro.area_seen = 35
    macro.progress.note('g', 35)
    runtime.on_probe('g', snapshot(35), [], 1.4)
    assert runtime.tick(1.5).action == 'hunt'
    macro.working = True
    macro.ground = 'Tal Rune'
    macro.no_room = 'Tal Rune at (7809, 6667)'
    result = runtime.tick(1.6)
    assert result.action == 'stop'
    assert result.reason == 'TZ inventory full: Tal Rune at (7809, 6667); recover ground loot in this game'
    assert all(action != 'leave' for action, _, _ in macro.actions)


def test_loot_cannot_complete_while_valuable_remains_on_ground():
    macro = Macro()
    coordinator = Coordinator(Config('active', (35,)), enabled=True)
    coordinator.request(1, 1)
    runtime = TzRuntime(coordinator, macro, {35: Capability(35, 'A', 35, None, 'ready')}, lambda: 8)
    runtime.on_probe('g', snapshot(), [], 1)
    runtime.tick(1.1)
    runtime.tick(1.2)
    runtime.tick(1.3)
    macro.area_seen = 35
    macro.progress.note('g', 35)
    runtime.on_probe('g', snapshot(35), [], 1.4)
    runtime.tick(1.5)
    macro.tz_hunt_over = 'nothing is left to go to on this level'
    assert runtime.tick(1.6).action == 'loot'
    macro.tz_loot_clear = True  # a pickup plan can be empty even when there is no inventory room
    macro.ground = 'Deep Worldstone Shard'
    result = runtime.tick(1.7)
    assert result.action == 'stop'
    assert result.reason == 'TZ loot left on ground: Deep Worldstone Shard'
    assert not coordinator.progress.completed


def test_confirmed_leader_kills_keep_a_long_hunt_alive_until_it_reaches_loot():
    macro = Macro()
    coordinator = Coordinator(Config('active', (35,)), enabled=True)
    coordinator.request(1, 1)
    runtime = TzRuntime(coordinator, macro, {35: Capability(35, 'A', 35, None, 'ready')}, lambda: 8)
    runtime.on_probe('g', snapshot(), [], 1)
    runtime.tick(1.1)
    runtime.tick(1.2)
    runtime.tick(1.3)
    macro.area_seen = 35
    macro.progress.note('g', 35)
    runtime.on_probe('g', snapshot(35), [], 1.4)
    assert runtime.tick(1.5).action == 'hunt'
    macro.working = True
    kill = {'event': 'elite_kill', 'unit_id': 7, 'area': 35, 'kind': 'champion'}
    runtime.on_probe('g', snapshot(35), [kill], 80)
    assert runtime.tick(80.1).action == 'hunt'
    runtime.on_probe('g', snapshot(35), [], 95)
    assert runtime.tick(95.1).action == 'hunt'  # more than 90 s since hunt start
    macro.working = False
    macro.tz_hunt_over = 'nothing is left to go to on this level'
    assert runtime.tick(95.2).action == 'loot'
    macro.tz_loot_clear = True
    assert runtime.tick(95.3).action == 'area-done'


def test_repeated_leader_event_does_not_keep_a_stalled_hunt_alive():
    macro = Macro()
    coordinator = Coordinator(Config('active', (35,)), enabled=True)
    coordinator.request(1, 1)
    runtime = TzRuntime(coordinator, macro, {35: Capability(35, 'A', 35, None, 'ready')}, lambda: 8)
    runtime.on_probe('g', snapshot(), [], 1)
    runtime.tick(1.1)
    runtime.tick(1.2)
    runtime.tick(1.3)
    macro.area_seen = 35
    macro.progress.note('g', 35)
    runtime.on_probe('g', snapshot(35), [], 1.4)
    assert runtime.tick(1.5).action == 'hunt'
    macro.working = True
    kill = {'event': 'elite_kill', 'unit_id': 7, 'area': 35, 'kind': 'champion'}
    runtime.on_probe('g', snapshot(35), [kill], 80)
    assert runtime.tick(80.1).action == 'hunt'
    runtime.on_probe('g', snapshot(35), [kill], 180)
    assert runtime.tick(180.1).reason == 'TZ area action timed out'


def test_explicit_lobby_start_and_stony_to_tristram_onward_are_observed_offline():
    macro = Macro()
    macro.progress = Progress(
        (Route('Tristram', (4,), (level(4, use('Tristram', 38)), level(38, use("Wirt's body"), loot(), leave()))),)
    )
    macro.progress.note(None, None)
    macro.area_seen = None
    coordinator = Coordinator(Config('active', (4, 38), max_games=1), enabled=True)
    coordinator.request(1, 1)
    caps = {
        4: Capability(4, 'Tristram', 4, None, 'ready'),
        38: Capability(38, 'Tristram', 4, 'object', 'ready'),
    }
    runtime = TzRuntime(coordinator, macro, caps, lambda: 8, start_game='cyber1')
    assert runtime.tick(1.1).reason == 'TZ create started'
    assert macro.actions == [('create', 0, 'cyber1')]
    macro.progress.note('cyber2', 1)
    macro.area_seen = 1
    assert runtime.tick(1.2).reason == 'TZ create observed'
    runtime.on_probe('cyber2', snapshot(tz=(4, 38)), [], 1.3)
    assert runtime.tick(1.4).action == 'prebuff'
    assert runtime.tick(1.5).action == 'restock'
    assert runtime.tick(1.6).action == 'travel'
    macro.progress.note('cyber2', 4)
    macro.area_seen = 4
    runtime.on_probe('cyber2', snapshot(4, tz=(4, 38)), [], 1.7)
    assert runtime.tick(1.8).action == 'hunt'
    macro.tz_hunt_over = 'nothing is left to go to on this level'
    assert runtime.tick(1.9).action == 'loot'
    macro.tz_loot_clear = True
    assert runtime.tick(2).action == 'area-done'
    assert runtime.tick(2.1).reason == 'next active area is ready'
    assert runtime.tick(2.2).action == 'travel'
    assert macro.actions[-1] == ('travel', 38, 'cyber2')
    assert coordinator.progress.completed == {4}
    macro.progress.note('cyber2', 38)
    macro.area_seen = 38
    runtime.on_probe('cyber2', snapshot(38, tz=(4, 38)), [], 2.3)
    assert runtime.tick(2.4).action == 'hunt'
    macro.tz_hunt_over = 'nothing is left to go to on this level'
    assert runtime.tick(2.5).action == 'target'
    macro.progress.facts = replace(macro.progress.facts, finished=frozenset({(38, "Wirt's body")}))
    macro.tz_target_over = 'what is left of the route is loot, which takes a press'
    assert runtime.tick(2.6).action == 'loot'
    macro.tz_loot_clear = True
    assert runtime.tick(2.7).action == 'area-done'
    assert runtime.tick(2.8).action == 'done'
    assert coordinator.progress.completed == {4, 38}
    assert coordinator.targets[38, 'object'] == 'opened'
    assert coordinator.on is False


def test_cave_second_onward_edge_stays_in_area_and_dispatches_to_level_two():
    macro = Macro()
    macro.progress = Progress(
        (Route('Cave', (3,), (level(3, use('Cave', 9)), level(9, loot(), use('Next level', 13)), level(13, loot()))),)
    )
    macro.progress.note('g', 9)
    macro.area_seen = 9
    coordinator = Coordinator(Config('active', (3, 9, 13), max_games=1), enabled=True)
    coordinator.request(1, 1)
    caps = {area: Capability(area, 'Cave', 3, None, 'ready') for area in (3, 9, 13)}
    runtime = TzRuntime(coordinator, macro, caps, lambda: 8)
    runtime.on_probe('g', snapshot(9, tz=(3, 9, 13)), [], 1)
    coordinator.progress = coordinator.progress.__class__(frozenset({3}), current=9)
    runtime.slice.work = AreaWork('g', 9, None, prebuffed=True, restocked=True, arrived=True, hunted=True)
    runtime.slice.pending = 'loot'
    macro.tz_last_action, macro.tz_last_ok, macro.tz_loot_clear = 'loot', True, True
    assert runtime.tick(1.05).action == 'area-done'
    step = macro.progress.step(9)
    assert step is not None
    assert step.stage.to == 13
    assert runtime.tick(1.1).reason == 'next active area is ready'
    assert runtime._dispatch('travel', 13)
    assert macro.actions[-1] == ('travel', 13, 'g')


def test_session_reset_waits_for_observed_lobby_and_new_town():
    macro = Macro()
    coordinator = Coordinator(Config('active', (35,), max_games=2), enabled=True)
    coordinator.request(1, 1)
    runtime = TzRuntime(coordinator, macro, {35: Capability(35, 'A', 35, None, 'ready')}, lambda: 8)
    macro.progress.note('cyber1', 1)
    runtime.on_probe('cyber1', snapshot(), [], 1)
    coordinator.progress = coordinator.progress.__class__(frozenset({35}))
    runtime.after_area = True
    assert runtime.tick(1.1).reason == 'TZ leave started'
    assert runtime.tick(1.2).reason == 'TZ game exit not yet observed'
    macro.progress.note(None, None)
    macro.area_seen = None
    assert runtime.tick(1.3).reason == 'TZ create started'
    assert macro.actions[-1] == ('create', 0, 'cyber1')
    assert runtime.tick(1.4).reason == 'TZ next game not yet observed in town'
    macro.progress.note('cyber2', 1)
    macro.area_seen = 1
    assert runtime.tick(1.5).reason == 'TZ create observed'
