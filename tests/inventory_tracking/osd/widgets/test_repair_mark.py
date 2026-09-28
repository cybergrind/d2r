import pytest

from inventory_tracking.config import OSD, with_overrides
from inventory_tracking.models import Location, Observation, ShopPanel, State, TeleportCharges
from inventory_tracking.osd.presenter import Presenter
from tests.inventory_tracking.conftest import SESSION


CHARSI = ShopPanel(True, 'Charsi', True)


def state(*, charges=10, shop=CHARSI, sampled=100):
    return State(
        sampled_at=sampled,
        session=SESSION,
        teleport=Observation(sampled, TeleportCharges(1, charges, 20)),
        location=Observation(sampled, Location(1, True)),
        shop=Observation(sampled, shop) if shop is not None else Observation.unavailable(sampled, 'unreadable'),
    )


@pytest.mark.parametrize(
    ('charges', 'shop', 'marked'),
    [
        (10, ShopPanel(True, 'Charsi', True), True),
        (0, ShopPanel(True, 'Larzuk', True), True),
        (20, ShopPanel(True, 'Charsi', True), False),
        (10, ShopPanel(True, 'Akara', False), False),
        (10, ShopPanel(False), False),
        (10, None, False),
    ],
)
def test_mark_needs_missing_charges_and_an_open_smith_panel(charges, shop, marked):
    presenter = Presenter()
    presenter.update(state(charges=charges, shop=shop))
    marks = presenter.marks(now=100)
    assert [m.kind for m in marks] == (['repair'] if marked else [])
    # The mark never adds text; the Teleport widget keeps its own town reminder.
    assert 'repair mark' not in presenter.render(now=100)


def test_mark_carries_configured_geometry_and_expires_with_the_sample():
    config = with_overrides(OSD, repair_mark=with_overrides(OSD.repair_mark, center_x=0.5, center_y=0.25, size=0.1))
    presenter = Presenter(config)
    presenter.update(state())
    (mark,) = presenter.marks(now=100)
    assert (mark.center_x, mark.center_y, mark.size) == (0.5, 0.25, 0.1)
    assert presenter.marks(now=103) == []


def test_disabled_widget_and_missing_staff_draw_nothing():
    presenter = Presenter(with_overrides(OSD, repair_mark=with_overrides(OSD.repair_mark, enabled=False)))
    presenter.update(state())
    assert presenter.marks(now=100) == []
    presenter = Presenter()
    presenter.update(State(sampled_at=100, session=SESSION, shop=Observation(100, ShopPanel(True, 'Charsi', True))))
    assert presenter.marks(now=100) == []


def test_shop_panel_model_rejects_contradictions():
    with pytest.raises(ValueError, match='closed shop panel'):
        ShopPanel(False, 'Charsi')
    with pytest.raises(ValueError, match='names its vendor'):
        ShopPanel(True, None, True)
