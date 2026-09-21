from dataclasses import replace
from unittest.mock import Mock

from inventory_tracking.models import Observation, PortalTome, State
from inventory_tracking.osd.presenter import Presenter
from inventory_tracking.reader import LiveReader


def test_reader_delivers_every_sample_before_render(tmp_path):
    presenter = Presenter()
    reader = LiveReader(tmp_path, observer=presenter.update)
    for count in (16, 18):
        reader.set_state(State(100, portal_tome=Observation(100, PortalTome(1, count, 20))))
    assert presenter.render(now=100) == ['tp: 2']


def test_widget_failure_is_isolated_and_recovers(caplog):
    broken, working = Mock(), Mock()
    broken.update.side_effect = ValueError('bad widget')
    working.render.return_value = ('working',)
    presenter = Presenter(widgets=[broken, working])
    presenter.update(State(100))
    presenter.update(State(101))
    assert presenter.render(now=101) == ['working']
    assert caplog.text.count('OSD widget') == 1
    broken.update.side_effect = None
    broken.render.return_value = ('recovered',)
    presenter.update(State(102))
    assert presenter.render(now=102) == ['recovered', 'working']


def test_stale_observation_and_out_of_order_snapshot_cannot_clear_latch():
    presenter = Presenter()
    state = State(100, portal_tome=Observation(100, PortalTome(1, 16, 20)))
    presenter.update(state)
    presenter.update(State(99, portal_tome=Observation(99, PortalTome(1, 20, 20))))
    presenter.update(State(103, portal_tome=Observation(100, PortalTome(1, 20, 20))))
    assert presenter.render(now=103) == []
    presenter.update(State(104, portal_tome=Observation(104, PortalTome(1, 18, 20))))
    assert presenter.render(now=104) == ['tp: 2']
    presenter.update(replace(state, sampled_at=105, session_ended=True))
    assert presenter.render(now=105) == []


def test_render_failures_are_logged_once_across_updates(caplog):
    widget = Mock()
    widget.render.side_effect = ValueError('bad render')
    presenter = Presenter(widgets=[widget])
    for timestamp in (100, 101, 102):
        presenter.update(State(timestamp))
        assert presenter.render(now=timestamp) == []
    assert caplog.text.count('OSD widget') == 1


def test_old_delivery_events_cannot_leak_into_new_session():
    from inventory_tracking.models import Actor, BeltCell, PotionRequest, PotionSent, PotionType

    event = PotionSent(PotionRequest(Actor.MERC, PotionType.HEALING, BeltCell(3, 5)), 100)
    presenter = Presenter()
    state = State(100, process_id=1, process_start='a', player_id=1, events=(event,))
    presenter.update(state)
    assert presenter.render(now=100)
    presenter.update(replace(state, player_id=2, sampled_at=100.1))
    assert presenter.render(now=100.1) == []
    presenter.update(replace(state, player_id=2, sampled_at=100.2))
    assert presenter.render(now=100.2) == []
