import pytest

from inventory_tracking.config import MercHealthWidgetConfig, PlayerHealthWidgetConfig
from inventory_tracking.models import Actor, Outcome, PotionResult, Refusal
from inventory_tracking.native.mercenary import Mercenary
from inventory_tracking.osd.widgets.health import MercHealthWidget, PlayerHealthWidget
from tests.inventory_tracking.conftest import make_state


FULL = Mercenary(99, 1000, 1000, 32768, True)
LOW = Mercenary(99, 300, 1000, 9830, True)


@pytest.mark.parametrize(
    ('result', 'line'),
    [
        (PotionResult(Outcome.SUSPENDED), 'merc heal: suspended'),
        (PotionResult(Outcome.BACKOFF), 'merc heal: backoff'),
        (PotionResult(Outcome.REJECTED, reason=Refusal.KEY_HELD), 'merc heal: rejected (key_held)'),
        (PotionResult(Outcome.NO_STOCK), 'merc heal: no_stock'),
    ],
)
def test_merc_widget_shows_healing_problems_even_at_full_health(result, line):
    widget = MercHealthWidget(MercHealthWidgetConfig(), max_age=1.0)
    widget.update(make_state(merc=FULL, outcomes={Actor.MERC: result}))
    assert widget.render(now=100.5) == (line,)


@pytest.mark.parametrize(
    'outcome', [Outcome.IDLE, Outcome.COOLDOWN, Outcome.SENT, Outcome.PENDING, Outcome.UNAVAILABLE]
)
def test_quiet_outcomes_add_no_status_line(outcome):
    widget = MercHealthWidget(MercHealthWidgetConfig(), max_age=1.0)
    widget.update(make_state(merc=FULL, outcomes={Actor.MERC: PotionResult(outcome)}))
    assert widget.render(now=100.5) == ()


def test_status_line_follows_the_health_line_and_ignores_the_other_actor():
    merc = MercHealthWidget(MercHealthWidgetConfig(), max_age=1.0)
    player = PlayerHealthWidget(PlayerHealthWidgetConfig(), max_age=1.0)
    state = make_state(
        current_raw=300,
        merc=LOW,
        outcomes={Actor.MERC: PotionResult(Outcome.SUSPENDED), Actor.PLAYER: PotionResult(Outcome.BACKOFF)},
    )
    merc.update(state)
    player.update(state)
    assert merc.render(now=100.5) == ('merc ~1/3', 'merc heal: suspended')
    assert player.render(now=100.5) == ('1/3', 'heal: backoff')


def test_stale_sample_hides_status():
    widget = MercHealthWidget(MercHealthWidgetConfig(), max_age=1.0)
    widget.update(make_state(merc=FULL, outcomes={Actor.MERC: PotionResult(Outcome.SUSPENDED)}))
    assert widget.render(now=102) == ()
