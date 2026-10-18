from inventory_tracking.routes.tz_leveling import (
    Capability,
    Config,
    Coordinator,
    FreshTerror,
    HuntTarget,
    Metrics,
    Progress,
    choose_hunt,
    next_area,
    route_inventory,
)
from inventory_tracking.terror.monsters import TerrorEntry
from inventory_tracking.terror.zones import GROUPS


def test_tz_read_must_belong_to_this_game_and_be_fresh():
    reads = FreshTerror(max_age=3)
    reads.observe('game-a', (TerrorEntry(35, 96, 18),), at=10)
    current = reads.current('game-a', 11)
    assert current is not None
    assert current.areas == frozenset({35})
    assert current.effects == ('Cold Enchanted',)
    assert reads.current('game-b', 11) is None
    assert reads.current('game-a', 14) is None
    reads.observe('game-b', None, at=15)
    assert reads.current('game-b', 15) is None
    reads.observe('game-b', (TerrorEntry(35, 96, 255),), at=16)
    current = reads.current('game-b', 16)
    assert current is not None
    assert current.effects == ('unknown (255)',)


def test_route_inventory_covers_every_herald_group_level_conservatively():
    inventory = route_inventory()
    herald_areas = {area for group in GROUPS for area in group.areas}
    assert set(inventory) - herald_areas == {20, 45, 50, 73, 132}
    assert all(capability.status != 'ready' for capability in inventory.values())
    assert all(capability.entry and capability.exit for capability in inventory.values())


def test_planner_requires_observed_area_and_skips_unreachable_entries():
    capabilities = {
        35: Capability(35, 'Andariel', 35, 'boss', 'ready'),
        36: Capability(36, 'Andariel', 35, 'boss', 'needs-played-check'),
        37: Capability(37, 'Andariel', 35, 'boss', 'unavailable', 'locked waypoint'),
    }
    config = Config(source='shard', shard_act=1, itinerary='all')
    evidence = FreshTerror()
    evidence.observe('g', (TerrorEntry(35, 96, 18), TerrorEntry(36, 96, 18), TerrorEntry(37, 96, 18)), at=2)
    choice = next_area(config, evidence.current('g', 2), Progress(), capabilities)
    assert choice.area == 35
    assert choice.skipped == ((36, 'needs-played-check'), (37, 'locked waypoint'))
    assert (
        next_area(config, evidence.current('g', 2), Progress(completed=frozenset({35})), capabilities).action == 'reset'
    )
    assert next_area(config, None, Progress(), capabilities).action == 'wait'


def test_designated_itinerary_order_and_active_rotation():
    capabilities = {35: Capability(35, 'A', 35, 'boss', 'ready'), 36: Capability(36, 'B', 35, 'chest', 'ready')}
    config = Config(source='active', itinerary=(36, 35))
    evidence = FreshTerror()
    evidence.observe('g', (TerrorEntry(35, 96, 18),), at=1)
    assert next_area(config, evidence.current('g', 1), Progress(), capabilities).area == 35
    assert next_area(config, evidence.current('g', 1), Progress(current=36), capabilities).action == 'finish-current'
    assert (
        next_area(config, evidence.current('g', 1), Progress(current=36), capabilities, finish_current=False).action
        == 'stop-current'
    )


def test_hunt_prefers_near_champion_to_distant_boss_and_ignores_stale_or_lost():
    targets = (
        HuntTarget('champion', 'c', 10, 1, 6, last_seen=9),
        HuntTarget('boss', 'b', 80, 1, 20, last_seen=9),
        HuntTarget('unique', 'stale', 2, 1, 3, last_seen=0),
        HuntTarget('herald', 'lost', 1, 1, 3, last_seen=9, reachable=False),
    )
    first = choose_hunt(targets, now=10)
    after_stale = choose_hunt(targets, now=20)
    after_cap = choose_hunt(targets[:2], now=10, hunt_seconds=120)
    assert first is not None
    assert first.name == 'c'
    assert after_stale is not None
    assert after_stale.name == 'b'
    assert after_cap is not None
    assert after_cap.name == 'b'


def test_metrics_count_only_observed_leader_deaths_once_over_total_elapsed_time():
    metrics = Metrics(started=0)
    metrics.phase('town', 10)
    metrics.phase('travel', 30)
    metrics.phase('combat', 50)
    metrics.seen('a', 'champion', 35)
    metrics.seen('b', 'herald', 35)
    metrics.died('a', 35)
    metrics.died('a', 35)
    metrics.lost('b')
    metrics.xp(100, 0)
    metrics.xp(150, 50)
    result = metrics.report(60)
    assert result['leaders'] == {'champion': 1, 'unique': 0, 'super': 0, 'herald': 0}
    assert result['elapsed_seconds'] == 60
    assert result['leaders_per_hour'] == 60
    assert result['xp_per_hour'] == 3000
    assert result['seconds'] == {'town': 20, 'travel': 20, 'combat': 10, 'other': 10}


def test_coordinator_is_inactive_by_default_and_shard_use_is_evidence_gated(tmp_path):
    idle = Coordinator(store=tmp_path / 'tz.json')
    assert not idle.request(1, 1)
    assert idle.hud_line == 'TZ loop: inactive'
    config = Config(source='shard', shard_act=1, itinerary=(35,))
    loop = Coordinator(config, store=tmp_path / 'tz.json', enabled=True)
    assert loop.request(1, 1)
    loop.observe('g', (TerrorEntry(35, 96, 18),), at=1)
    assert loop.decide('g', now=1, capabilities={35: Capability(35, 'A', 35, 'boss', 'ready')}).action == 'stop'
    assert 'shard use awaits played evidence' in loop.stop_reason
    assert loop.shard_spent == 0


def test_coordinator_requires_target_outcome_and_restores_progress(tmp_path):
    store = tmp_path / 'tz.json'
    config = Config(source='active', itinerary=(35,), max_games=2)
    capabilities = {35: Capability(35, 'A', 35, 'boss', 'ready')}
    loop = Coordinator(config, store=store, enabled=True)
    loop.request(1, 1)
    loop.observe('g', (TerrorEntry(35, 96, 18),), at=2)
    assert loop.decide('g', now=2, capabilities=capabilities).area == 35
    assert loop.begin_area('g', 35, capabilities[35], now=2)
    assert loop.decide('g', now=2.1, capabilities=capabilities).action == 'continue-current'
    assert not loop.complete_area('g', 35, 'Andariel')
    loop.target_outcome('g', 35, 'Andariel', 'failed')
    assert not loop.complete_area('g', 35, 'Andariel')
    loop.target_outcome('g', 35, 'Andariel', 'killed')
    assert loop.complete_area('g', 35, 'Andariel')
    restored = Coordinator(config, store=store, enabled=True)
    assert restored.request(3, 3)
    restored.observe('g', (TerrorEntry(35, 96, 18),), at=3)
    assert restored.decide('g', now=3, capabilities=capabilities).action == 'reset'
    restored.observe('new-game', (TerrorEntry(35, 96, 18),), at=4)
    assert restored.decide('new-game', now=4, capabilities=capabilities).action == 'enter'


def test_unreachable_area_is_named_and_not_selected_twice_in_one_game():
    config = Config(source='active', itinerary=(35, 36))
    capabilities = {35: Capability(35, 'A', 35, 'boss', 'ready'), 36: Capability(36, 'B', 35, 'chest', 'ready')}
    loop = Coordinator(config, enabled=True)
    loop.request(1, 1)
    loop.observe('g', (TerrorEntry(35, 96, 18), TerrorEntry(36, 96, 18)), at=2)
    assert loop.decide('g', now=2, capabilities=capabilities).area == 35
    assert loop.skip_area('g', 35, 'door did not open')
    assert loop.decide('g', now=2.1, capabilities=capabilities).area == 36
    assert loop.skips == {35: 'door did not open'}


def test_begin_area_rechecks_fresh_terror_read_at_the_movement_boundary():
    config = Config(source='active', itinerary=(35,))
    capability = Capability(35, 'A', 35, 'boss', 'ready')
    loop = Coordinator(config, enabled=True)
    loop.request(1, 1)
    loop.observe('g', (TerrorEntry(35, 96, 18),), at=2)
    assert loop.decide('g', now=2, capabilities={35: capability}).area == 35
    assert not loop.begin_area('g', 35, capability, now=6)


def test_game_preflight_rejects_wrong_character_difficulty_and_time_limit():
    config = Config(source='active', itinerary=(35,), character='Warlock', difficulty='Hell', max_seconds=5)
    capabilities = {35: Capability(35, 'A', 35, 'boss', 'ready')}
    loop = Coordinator(config, enabled=True)
    loop.request(1, 1)
    loop.observe('g', (TerrorEntry(35, 96, 18),), at=2)
    assert loop.decide('g', now=2, capabilities=capabilities, character='Sorceress').reason == 'wrong character'
    loop.request(2, 2)
    assert (
        loop.decide('g', now=2, capabilities=capabilities, character='Warlock', difficulty='Normal').reason
        == 'wrong difficulty'
    )
    loop.request(2, 2)
    assert loop.decide('g', now=2, capabilities=capabilities, character='Warlock', difficulty='Hell').area == 35
    assert (
        loop.decide('g', now=7, capabilities=capabilities, character='Warlock', difficulty='Hell').reason
        == 'maximum time reached'
    )


def test_coordinator_stops_for_death_supplies_valuable_and_manual_pause(tmp_path):
    config = Config(source='active', itinerary=(35,))
    capabilities = {35: Capability(35, 'A', 35, 'boss', 'ready')}

    def reason(*, dead=False, dangerous=False, supplies=None, valuable_no_room=False):
        loop = Coordinator(config, store=tmp_path / 'stop.json', enabled=True)
        loop.request(1, 1)
        loop.observe('g', (TerrorEntry(35, 96, 18),), at=2)
        return loop.decide(
            'g',
            now=2,
            capabilities=capabilities,
            dead=dead,
            dangerous=dangerous,
            supplies=supplies,
            valuable_no_room=valuable_no_room,
        ).reason

    assert reason(dead=True) == 'dead'
    assert reason(dangerous=True) == 'dangerous combat'
    assert reason(supplies=1) == 'low supplies'
    assert reason(valuable_no_room=True) == 'valuable with no room'
    loop = Coordinator(config, enabled=True)
    loop.request(1, 1)
    loop.observe('g', (TerrorEntry(35, 96, 18),), at=2)
    assert loop.decide('g', now=2, capabilities=capabilities, manual=True).action == 'pause'
    assert loop.decide('g', now=3, capabilities=capabilities).action == 'enter'
    assert loop.request(3, 3)  # toggle off cancels immediately
    assert loop.hud_line == 'TZ loop: inactive'
