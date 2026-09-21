from dataclasses import replace
from unittest.mock import Mock

import pytest

from inventory_tracking.config import (
    OSD,
    BeltWidgetConfig,
    NotificationsWidgetConfig,
    PlayerHealthWidgetConfig,
    with_overrides,
)
from inventory_tracking.models import BeltSnapshot, Observation, PlayerHealth, PortalTome, SessionIdentity, State
from inventory_tracking.osd.presenter import Presenter
from inventory_tracking.reader import LiveReader
from inventory_tracking.state import from_research
from tests.inventory_tracking.conftest import SESSION


def test_reader_delivers_every_sample_before_render(tmp_path):
    presenter = Presenter()
    reader = LiveReader(tmp_path, observer=presenter.update)
    for count in (16, 18):
        reader.set_state(State(session=SESSION, sampled_at=100, portal_tome=Observation(100, PortalTome(1, count, 20))))
    assert presenter.render(now=100) == ['tp: 2']


def test_widget_failure_is_isolated_and_recovers(caplog):
    broken, working = Mock(), Mock()
    broken.update.side_effect = ValueError('bad widget')
    working.render.return_value = ('working',)
    presenter = Presenter(widgets=[broken, working])
    presenter.update(State(sampled_at=100))
    presenter.update(State(sampled_at=101))
    assert presenter.render(now=101) == ['working']
    assert caplog.text.count('OSD widget') == 1
    broken.update.side_effect = None
    broken.render.return_value = ('recovered',)
    presenter.update(State(sampled_at=102))
    assert presenter.render(now=102) == ['recovered', 'working']


def test_stale_observation_and_out_of_order_snapshot_cannot_clear_latch():
    presenter = Presenter()
    state = State(session=SESSION, sampled_at=100, portal_tome=Observation(100, PortalTome(1, 16, 20)))
    presenter.update(state)
    presenter.update(State(session=SESSION, sampled_at=99, portal_tome=Observation(99, PortalTome(1, 20, 20))))
    presenter.update(State(session=SESSION, sampled_at=103, portal_tome=Observation(100, PortalTome(1, 20, 20))))
    assert presenter.render(now=103) == []
    presenter.update(State(session=SESSION, sampled_at=104, portal_tome=Observation(104, PortalTome(1, 18, 20))))
    assert presenter.render(now=104) == ['tp: 2']
    presenter.update(replace(state, sampled_at=105, session_ended=True))
    assert presenter.render(now=105) == []


def test_render_failures_are_logged_once_across_updates(caplog):
    widget = Mock()
    widget.render.side_effect = ValueError('bad render')
    presenter = Presenter(widgets=[widget])
    for timestamp in (100, 101, 102):
        presenter.update(State(sampled_at=timestamp))
        assert presenter.render(now=timestamp) == []
    assert caplog.text.count('OSD widget') == 1


def test_old_delivery_events_cannot_leak_into_new_session():
    from inventory_tracking.models import Actor, BeltCell, PotionRequest, PotionSent, PotionType

    event = PotionSent(PotionRequest(Actor.MERC, PotionType.HEALING, BeltCell(3, 5)), 100)
    presenter = Presenter()
    state = State(sampled_at=100, session=SessionIdentity(1, 'a', 1), events=(event,))
    presenter.update(state)
    assert presenter.render(now=100)
    presenter.update(replace(state, session=SessionIdentity(1, 'a', 2), sampled_at=100.1))
    assert presenter.render(now=100.1) == []
    presenter.update(replace(state, session=SessionIdentity(1, 'a', 2), sampled_at=100.2))
    assert presenter.render(now=100.2) == []


@pytest.fixture
def render():
    presenter = Presenter()

    def render_sample(state, *, now):
        presenter.update(state)
        return presenter.render(now=now)

    return render_sample


def test_health_and_missing_counts_not_remaining_stock(snapshot, render):
    state = from_research(snapshot())
    assert render(state, now=101) == ['juv 11']


def test_health_threshold_includes_exactly_seventy_percent(snapshot, render):
    state = replace(
        from_research(snapshot()), health=PlayerHealth(700 * 256, 1000 * 256), belt=BeltSnapshot((531,) * 16)
    )
    assert render(state, now=101) == ['700/1000']
    assert render(replace(state, health=PlayerHealth(700 * 256 + 1, 1000 * 256)), now=101) == []
    assert render(replace(state, health=PlayerHealth(699 * 256, 1000 * 256)), now=101) == ['699/1000']


def test_stale_and_future_samples_do_not_show_old_health_or_deficits(snapshot, render):
    state = from_research(snapshot())
    assert render(state, now=110) == []
    assert render(state, now=99) == []


def test_empty_belt_counts_all_missing_but_other_owners_are_not_counted(snapshot, render):
    data = snapshot()
    for item in data['groups']['items']['units']:
        item['details']['owner_id'] = 9
    assert render(from_research(data), now=101) == [
        'juv 16',
    ]


def test_incomplete_read_and_startup_are_quiet(render):
    assert render(State(sampled_at=100, reason='incomplete read'), now=101) == []
    assert render(State(sampled_at=100, reason='connecting'), now=101) == []


def test_refill_clears_previous_shortage(snapshot, render):
    state = replace(from_research(snapshot()), belt=BeltSnapshot((531, 531, 606, 606) * 3 + (531, 531, 606, None)))
    assert render(state, now=101) == ['hp 1']
    assert render(replace(state, belt=BeltSnapshot((531, 531, 606, 606) * 4)), now=101) == []


@pytest.mark.parametrize(
    ('contents', 'expected'),
    [
        ([None] * 16, ['juv 16']),
        ([531] * 16, []),
        ([530] * 12 + [None] * 4, ['juv 4']),
        ([602, 531, 606, 531] * 3 + [None] * 4, ['juv 2', 'hp 2']),
        ([None, 531, 531, 531] + [606, 531, 531, 531] * 3, ['hp 1']),
        ([531, None, None, None] + [606, None, None, None] * 3, ['juv 15']),
    ],
)
def test_dynamic_shortages_follow_column_bottom_or_empty_default(contents, expected, snapshot, render):
    data = snapshot()
    data['groups']['items']['units'] = [
        {'unit_id': i + 100, 'txt_id': item, 'mode': 2, 'details': {'owner_id': 7, 'x': i, 'y': 0}}
        for i, item in enumerate(contents)
        if item is not None
    ]
    assert render(from_research(data), now=101) == expected


@pytest.mark.parametrize(('fraction', 'visible'), [(32768, False), (21300, False), (21299, True)])
def test_merc_health_display_is_strictly_below_65_percent(fraction, visible, render):
    from inventory_tracking.mercenary import Mercenary

    state = State(
        session=SESSION,
        sampled_at=100,
        health=PlayerHealth(1000, 1000),
        merc=Mercenary(42, 256000 * fraction // 32768, 256000, fraction, True),
    )
    lines = render(state, now=100)
    assert bool(lines) == visible
    if visible:
        assert lines[0].startswith('merc ~')


def test_explicit_targets_count_all_potion_tiers(snapshot):
    data = snapshot()
    for item in data['groups']['items']['units']:
        item['txt_id'] = 530 if item['txt_id'] == 531 else 602
    presenter = Presenter(with_overrides(OSD, belt=BeltWidgetConfig(rejuvenation_target=5, healing_target=7)))
    presenter.update(from_research(data))
    assert presenter.render(now=100) == []


def test_injected_osd_visibility_and_notification_duration():
    from inventory_tracking.models import Actor, BeltCell, PotionRequest, PotionSent, PotionType

    event = PotionSent(PotionRequest(Actor.PLAYER, PotionType.HEALING, BeltCell(3, 101)), 100)
    config = with_overrides(
        OSD, player_health=PlayerHealthWidgetConfig(percent=90), notifications=NotificationsWidgetConfig(seconds=0.5)
    )
    state = State(
        session=SESSION,
        sampled_at=100,
        health=PlayerHealth(800 * 256, 1000 * 256),
        events=(event,),
        belt=BeltSnapshot((531,) * 16),
    )
    presenter = Presenter(config)
    presenter.update(state)
    assert presenter.render(now=100.4) == ['player potion sent (3)', '800/1000']
    assert presenter.render(now=100.5) == ['800/1000']


def test_factory_order_and_max_age_reach_every_widget():
    from inventory_tracking.osd.presenter import default_widgets

    widgets = default_widgets(with_overrides(OSD, max_age=4))
    assert [type(widget).__name__ for widget in widgets] == [
        'NotificationsWidget',
        'PlayerHealthWidget',
        'MercHealthWidget',
        'BeltWidget',
        'TeleportWidget',
        'PortalWidget',
        'LootWidget',
        'KeysWidget',
    ]
    assert {widget.max_age for widget in widgets} == {4}
    presenter = Presenter(with_overrides(OSD, max_age=4), widgets=widgets)
    presenter.update(State(session=SESSION, sampled_at=100, belt=BeltSnapshot((None,) * 16)))
    assert presenter.render(now=104) == ['juv 16']
    assert presenter.render(now=104.1) == []
