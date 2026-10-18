from inventory_tracking.routes.tz_execution import Action, AreaWork, Observation, advance, next_work
from inventory_tracking.routes.tz_leveling import Capability, FreshTerror
from inventory_tracking.terror.monsters import TerrorEntry


def test_area_actions_wait_for_observed_results_in_the_required_order():
    capability = Capability(35, 'Andariel', 35, 'boss', 'ready')
    evidence = FreshTerror()
    evidence.observe('g', (TerrorEntry(35, 96, 18),), at=1)
    read = evidence.current('g', 1)
    assert read is not None
    work = AreaWork('g', 35, target='boss')
    expected = ('prebuff', 'restock', 'travel', 'hunt', 'target', 'loot', 'complete')
    for action in expected:
        assert next_work(work, capability, read, now=1).action == action
        assert advance(work, Observation(action, observed=False, game='g')) == work
        outcome = {'hunt': 'exhausted', 'target': 'killed', 'loot': 'clear'}.get(action, '')
        work = advance(work, Observation(action, observed=True, game='g', area=35, outcome=outcome))
    assert next_work(work, capability, read, now=1).action == 'done'


def test_travel_requires_current_confirmed_tz_and_work_never_consumes_a_shard():
    capability = Capability(35, 'Andariel', 35, 'boss', 'ready')
    work = AreaWork('g', 35, target='boss', prebuffed=True, restocked=True)
    assert next_work(work, capability, None, now=5).reason == 'TZ list unread or stale'
    evidence = FreshTerror()
    evidence.observe('g', (TerrorEntry(36, 96, 18),), at=5)
    read = evidence.current('g', 5)
    assert read is not None
    assert next_work(work, capability, read, now=5).reason == 'area not in current TZ list'
    evidence.observe('g', (TerrorEntry(35, 96, 18),), at=5)
    read = evidence.current('g', 5)
    assert read is not None
    assert next_work(work, capability, read, now=9).reason == 'TZ list unread or stale'
    assert next_work(work, capability, read, now=5).action == 'travel'


def test_target_and_loot_require_explicit_observations_before_completion():
    capability = Capability(35, 'Andariel', 35, 'boss', 'ready')
    work = AreaWork('g', 35, target='boss', prebuffed=True, restocked=True, arrived=True, hunted=True)
    assert next_work(work, capability, None, now=1).action == 'target'
    assert advance(work, Observation('loot', observed=True, game='g', area=35, outcome='clear')) == work
    assert advance(work, Observation('target', observed=True, game='g', area=35, outcome='')).target_outcome is None
    work = advance(work, Observation('target', observed=True, game='g', area=35, outcome='killed'))
    assert next_work(work, capability, None, now=1).action == 'loot'
    assert advance(work, Observation('loot', observed=False, game='g')).looted is False
    work = advance(work, Observation('loot', observed=True, game='g', area=35, outcome='clear'))
    assert next_work(work, capability, None, now=1).action == 'complete'


def test_manual_pause_and_cancellation_preempt_an_area_action():
    capability = Capability(35, 'Andariel', 35, 'boss', 'ready')
    work = AreaWork('g', 35, target='boss')
    assert next_work(work, capability, None, now=1, manual=True).action == 'pause'
    assert next_work(work, capability, None, now=1, cancelled=True).action == 'stop'


def test_observations_from_another_game_or_area_cannot_advance_work():
    work = AreaWork('g', 35, target='boss')
    assert advance(work, Observation('prebuff', observed=True, game='old')) == work
    work = advance(work, Observation('prebuff', observed=True, game='g'))
    work = advance(work, Observation('restock', observed=True, game='g'))
    assert advance(work, Observation('travel', observed=True, game='g', area=36)) == work


def test_slice_dispatches_once_and_requires_observed_completion():
    from inventory_tracking.routes.tz_execution import Slice
    from inventory_tracking.routes.tz_leveling import Config, Coordinator

    calls = []
    coordinator = Coordinator(Config('active', (35,)), enabled=True)
    assert coordinator.request(1, 1)
    capability = Capability(35, 'Andariel', 35, 'boss', 'ready')
    slice_run = Slice(coordinator, {35: capability}, lambda action, area: calls.append((action, area)) or True)
    entries = (TerrorEntry(35, 96, 18),)
    assert slice_run.tick('g', 1, entries=entries, area=1).action == 'prebuff'
    assert calls == [('prebuff', 35)]
    slice_run.tick('g', 1.1, entries=entries, area=1)
    assert calls == [('prebuff', 35)]
    assert (
        slice_run.tick('g', 1.2, entries=entries, area=1, completed=Observation('prebuff', True, 'g')).action
        == 'restock'
    )
    assert calls[-1] == ('restock', 35)
    assert (
        slice_run.tick('g', 1.3, entries=entries, area=1, completed=Observation('restock', True, 'g')).action
        == 'travel'
    )
    assert calls[-1] == ('travel', 35)
    # A completed input in the wrong area cannot advance travel.
    slice_run.tick('g', 1.4, entries=entries, area=1, completed=Observation('travel', True, 'g', 36))
    assert calls[-1] == ('travel', 35)
    assert (
        slice_run.tick('g', 1.5, entries=entries, area=35, completed=Observation('travel', True, 'g', 35)).action
        == 'hunt'
    )
    assert calls[-1] == ('hunt', 35)


def test_slice_does_not_dispatch_after_game_change_or_toggle_off():
    from inventory_tracking.routes.tz_execution import Slice
    from inventory_tracking.routes.tz_leveling import Config, Coordinator

    calls = []
    coordinator = Coordinator(Config('active', (35,)), enabled=True)
    coordinator.request(1, 1)
    slice_run = Slice(
        coordinator,
        {35: Capability(35, 'Andariel', 35, 'boss', 'ready')},
        lambda action, area: calls.append(action) or True,
    )
    entries = (TerrorEntry(35, 96, 18),)
    slice_run.tick('g', 1, entries=entries, area=1)
    assert slice_run.tick('other', 2, entries=entries, area=1).action == 'stop'
    assert coordinator.on is False
    assert calls == ['prebuff']


def test_slice_stops_on_failed_required_boss_before_loot_or_completion():
    from inventory_tracking.routes.tz_execution import Slice
    from inventory_tracking.routes.tz_leveling import Config, Coordinator

    coordinator = Coordinator(Config('active', (35,)), enabled=True)
    coordinator.request(1, 1)
    calls = []
    slice_run = Slice(
        coordinator, {35: Capability(35, 'A', 35, 'boss', 'ready')}, lambda action, area: calls.append(action) or True
    )
    entries = (TerrorEntry(35, 96, 18),)
    slice_run.tick('g', 1, entries=entries, area=1)
    steps: tuple[tuple[Action, int, str], ...] = (
        ('prebuff', 1, ''),
        ('restock', 1, ''),
        ('travel', 35, ''),
        ('hunt', 35, 'exhausted'),
    )
    for action, area, outcome in steps:
        slice_run.tick(
            'g', 1, entries=entries, area=area, completed=Observation(action, True, 'g', area=area, outcome=outcome)
        )
    result = slice_run.tick(
        'g', 1, entries=entries, area=35, completed=Observation('target', True, 'g', area=35, outcome='failed')
    )
    assert result.action == 'stop'
    assert calls == ['prebuff', 'restock', 'travel', 'hunt', 'target']
    assert not coordinator.progress.completed


def test_cached_probe_read_does_not_become_fresh_again_on_a_later_tick():
    from inventory_tracking.routes.tz_execution import Slice
    from inventory_tracking.routes.tz_leveling import Config, Coordinator

    calls = []
    coordinator = Coordinator(Config('active', (35,)), enabled=True)
    coordinator.request(1, 1)
    slice_run = Slice(
        coordinator, {35: Capability(35, 'A', 35, None, 'ready')}, lambda action, area: calls.append(action) or True
    )
    step = slice_run.tick('g', 5, entries=(TerrorEntry(35, 96, 18),), observed_at=1, area=1)
    assert step.action == 'wait'
    assert calls == []


def test_pending_action_times_out_and_cancels_even_when_tz_read_goes_stale():
    from inventory_tracking.routes.tz_execution import Slice
    from inventory_tracking.routes.tz_leveling import Config, Coordinator

    cancelled = []
    coordinator = Coordinator(Config('active', (35,)), enabled=True)
    coordinator.request(1, 1)
    slice_run = Slice(
        coordinator,
        {35: Capability(35, 'A', 35, None, 'ready')},
        lambda action, area: True,
        cancel=lambda: cancelled.append(True),
        action_timeout=2,
    )
    entries = (TerrorEntry(35, 96, 18),)
    assert slice_run.tick('g', 1, entries=entries, area=1).action == 'prebuff'
    assert slice_run.tick('g', 3, entries=None, area=1).action == 'stop'
    assert cancelled == [True]


def test_slice_completes_one_area_then_reuses_game_town_work_for_another():
    from inventory_tracking.routes.tz_execution import Slice
    from inventory_tracking.routes.tz_leveling import Config, Coordinator

    calls = []
    coordinator = Coordinator(Config('active', (35, 36)), enabled=True)
    coordinator.request(1, 1)
    caps = {area: Capability(area, str(area), area, None, 'ready') for area in (35, 36)}
    slice_run = Slice(coordinator, caps, lambda action, area: calls.append((action, area)) or True)
    entries = (TerrorEntry(35, 96, 18), TerrorEntry(36, 96, 18))

    def observed(action, at, area, outcome=''):
        return slice_run.tick(
            'g',
            at,
            entries=entries,
            area=area,
            completed=Observation(action, True, 'g', area, outcome),
        ).action

    assert slice_run.tick('g', 1, entries=entries, area=1).action == 'prebuff'
    assert observed('prebuff', 1.1, 1) == 'restock'
    assert observed('restock', 1.2, 1) == 'travel'
    assert observed('travel', 1.3, 35) == 'hunt'
    assert observed('hunt', 1.4, 35, 'exhausted') == 'loot'
    assert observed('loot', 1.5, 35, 'clear') == 'area-done'
    assert coordinator.on
    assert coordinator.progress.completed == {35}
    assert slice_run.tick('g', 1.6, entries=entries, area=1).action == 'travel'
    assert calls[-1] == ('travel', 36)
    assert calls.count(('prebuff', 35)) == calls.count(('restock', 35)) == 1


def test_slice_reports_reset_after_last_active_area_without_stopping_coordinator():
    from inventory_tracking.routes.tz_execution import Slice
    from inventory_tracking.routes.tz_leveling import Config, Coordinator

    coordinator = Coordinator(Config('active', (35,), max_games=2), enabled=True)
    coordinator.request(1, 1)
    slice_run = Slice(coordinator, {35: Capability(35, 'A', 35, None, 'ready')}, lambda _a, _n: True)
    entries = (TerrorEntry(35, 96, 18),)
    step = slice_run.tick('g', 1, entries=entries, area=1)
    observations = (
        ('prebuff', 1, ''),
        ('restock', 1, ''),
        ('travel', 35, ''),
        ('hunt', 35, 'exhausted'),
        ('loot', 35, 'clear'),
    )
    for action, area, outcome in observations:
        step = slice_run.tick(
            'g',
            1,
            entries=entries,
            area=area,
            completed=Observation(action, True, 'g', area, outcome),
        )
    assert step.action == 'area-done'
    assert slice_run.tick('g', 1.1, entries=entries, area=35).action == 'reset'
    assert coordinator.on
