from dataclasses import replace

from inventory_tracking.models import Observation, PortalTome, SessionIdentity, State
from inventory_tracking.osd.presenter import Presenter


def sample(quantity, *, at=100, item=1, player=2):
    tome = None if quantity is None else PortalTome(item, quantity, 20)
    return State(sampled_at=at, portal_tome=Observation(at, tome), session=SessionIdentity(1, 'a', player))


def test_latch_sequence_and_render_is_pure():
    presenter = Presenter()
    for quantity, expected in [(20, []), (17, []), (16, ['tp: 4']), (18, ['tp: 2']), (19, ['tp: 1']), (20, [])]:
        presenter.update(sample(quantity))
        assert presenter.render(now=100) == expected
        assert presenter.render(now=100) == expected


def test_unavailable_hides_but_preserves_latch_absence_resets():
    presenter = Presenter()
    presenter.update(sample(15))
    presenter.update(replace(sample(18), portal_tome=Observation.unavailable(100, 'failed')))
    assert presenter.render(now=100) == []
    presenter.update(sample(18))
    assert presenter.render(now=100) == ['tp: 2']
    assert presenter.render(now=103) == []
    presenter.update(sample(None))
    presenter.update(sample(18))
    assert presenter.render(now=100) == []


def test_item_and_session_changes_reset_latch():
    presenter = Presenter()
    presenter.update(sample(16))
    presenter.update(sample(18, item=3))
    assert presenter.render(now=100) == []
    presenter.update(sample(16, item=3))
    presenter.update(sample(18, item=3, player=8))
    assert presenter.render(now=100) == []


def test_future_observation_cannot_show_zero_deficit_after_time_catches_up():
    presenter = Presenter()
    presenter.update(sample(16))
    presenter.update(replace(sample(20), portal_tome=Observation(101, PortalTome(1, 20, 20))))
    assert presenter.render(now=101) == []
