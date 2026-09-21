from dataclasses import replace

from inventory_tracking.models import Observation, SessionIdentity, State
from inventory_tracking.osd.presenter import Presenter


def test_key_warning_threshold_refill_and_staleness():
    presenter = Presenter()
    state = State(sampled_at=100, session=SessionIdentity(1, 'a', 2))
    for count, expected in [(12, []), (5, []), (4, ['keys: 4']), (0, ['keys: 0']), (5, [])]:
        presenter.update(replace(state, keys=Observation(100, count)))
        assert presenter.render(now=100) == expected
    presenter.update(replace(state, keys=Observation(100, 3)))
    assert presenter.render(now=103) == []
    presenter.update(replace(state, keys=Observation.unavailable(100, 'failed')))
    assert presenter.render(now=100) == []
    presenter.update(replace(state, session=None, keys=Observation(100, 0)))
    assert presenter.render(now=100) == []
