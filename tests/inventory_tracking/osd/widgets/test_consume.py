from dataclasses import replace

import pytest

from inventory_tracking.config import ConsumeWidgetConfig
from inventory_tracking.models import ConsumeBuff, Observation, PlayerHealth, SessionIdentity, State
from inventory_tracking.osd.presenter import Presenter
from inventory_tracking.osd.widgets.consume import ConsumeWidget


def sample(now, active, level=None, effect_id=1):
    return State(
        sampled_at=now,
        session=SessionIdentity(1, 'a', 2),
        consume=Observation(now, ConsumeBuff(active, level, effect_id if active else None)),
    )


@pytest.mark.parametrize(('level', 'duration'), [(7, 160), (9, 200)])
def test_applied_level_timer_and_bounded_removal_notice(level, duration):
    widget = ConsumeWidget(ConsumeWidgetConfig(), max_age=2)
    widget.update(sample(0, False))
    for now in range(1, duration + 2):
        widget.update(sample(now, True, level))
        lines = widget.render(now=now)
        if now < 1 + duration - 15:
            assert not lines
        elif now < 1 + duration:
            assert lines == (f'consume: ~{1 + duration - now}s left',)
        else:
            assert lines == ('consume: recast (estimated timer elapsed)',)
    end = duration + 2
    for now in range(end, end + 32):
        widget.update(sample(now, False))
        assert widget.render(now=now) == (('consume: no longer active',) if now < end + 30 else ())


@pytest.mark.parametrize('level', [None, 7])
def test_mid_buff_attach_never_invents_start_but_notifies_on_removal(level):
    widget = ConsumeWidget(ConsumeWidgetConfig(ended_notice_seconds=5), max_age=2)
    for now in range(20):
        widget.update(sample(now, True, level))
        assert not widget.render(now=now)
    for now in range(20, 26):
        widget.update(sample(now, False))
        assert bool(widget.render(now=now)) == (now < 25)
    widget.update(sample(26, True, 7))
    assert not widget.render(now=26)
    assert widget.deadline == 186


def test_uncertain_reads_discard_timer_without_claiming_expiration():
    widget = ConsumeWidget(ConsumeWidgetConfig(), max_age=2)
    widget.update(sample(0, False))
    widget.update(sample(1, True, 7))
    assert widget.deadline == 161
    widget.update(replace(sample(2, True, 7), consume=Observation.unavailable(2)))
    assert not widget.render(now=2)
    widget.update(sample(3, True, 7))
    assert widget.deadline is None
    widget.update(sample(4, False))
    assert widget.render(now=4) == ('consume: no longer active',)
    assert not widget.render(now=7)  # stale core/observation suppresses the notice


def test_gap_and_replacement_do_not_start_new_timers():
    widget = ConsumeWidget(ConsumeWidgetConfig(), max_age=2)
    widget.update(sample(0, False))
    widget.update(sample(5, True, 7))
    assert widget.deadline is None
    widget.update(sample(6, False))
    widget.update(sample(7, True, 7))
    assert widget.deadline == 167
    widget.update(sample(8, True, 9, effect_id=2))
    assert widget.deadline is None
    assert not widget.render(now=8)


def test_session_and_death_clear_tracking():
    widget = ConsumeWidget(ConsumeWidgetConfig(), max_age=2)
    presenter = Presenter(widgets=[widget])
    presenter.update(sample(0, False))
    presenter.update(sample(1, True, 7))
    presenter.update(replace(sample(2, True, 7), session=SessionIdentity(1, 'a', 3)))
    assert widget.deadline is None
    presenter.update(replace(sample(3, False), session=SessionIdentity(1, 'a', 3)))
    assert presenter.render(now=3) == ['consume: no longer active']
    presenter.update(replace(sample(4, False), session=SessionIdentity(1, 'a', 3), health=PlayerHealth(0, 100)))
    assert not presenter.render(now=4)


def test_unknown_level_and_disabled_widget():
    widget = ConsumeWidget(ConsumeWidgetConfig(enabled=False), max_age=2)
    widget.update(sample(0, False))
    widget.update(sample(1, True))
    assert widget.deadline is None
    widget.update(sample(2, False))
    assert not widget.render(now=2)


def test_configured_lead_and_recast_clear_old_notice():
    widget = ConsumeWidget(ConsumeWidgetConfig(warn_before_seconds=3), max_age=2)
    widget.update(sample(0, False))
    for now in range(1, 39):
        widget.update(sample(now, True, 1))
    assert widget.render(now=38) == ('consume: ~3s left',)
    widget.update(sample(39, False))
    assert widget.render(now=39) == ('consume: no longer active',)
    widget.update(sample(40, True, 7, effect_id=2))
    assert not widget.render(now=40)
    assert widget.deadline == 200
