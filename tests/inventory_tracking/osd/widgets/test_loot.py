from dataclasses import replace

from inventory_tracking.models import Observation, SessionIdentity, State
from inventory_tracking.osd.presenter import Presenter


def test_loot_warning_tracks_state_and_expires():
    presenter = Presenter()
    state = State(sampled_at=100, session=SessionIdentity(1, 'a', 2))
    for enabled, expected in [(False, ['loot is not enabled']), (True, []), (False, ['loot is not enabled'])]:
        presenter.update(replace(state, show_items=Observation(100, enabled)))
        assert presenter.render(now=100) == expected
    assert presenter.render(now=103) == []
    presenter.update(replace(state, show_items=Observation.unavailable(100, 'read failed')))
    assert presenter.render(now=100) == []
    presenter.update(replace(state, session=None, show_items=Observation(100, False)))
    assert presenter.render(now=100) == []


def test_new_session_uses_current_loot_state():
    presenter = Presenter()
    presenter.update(State(sampled_at=100, session=SessionIdentity(1, 'a', 2), show_items=Observation(100, True)))
    presenter.update(State(sampled_at=101, session=SessionIdentity(1, 'a', 3), show_items=Observation(101, False)))
    assert presenter.render(now=101) == ['loot is not enabled']
    presenter.update(State(sampled_at=102, session_ended=True))
    assert presenter.render(now=102) == []
