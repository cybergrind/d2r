"""Every route, and the levels that have none with the reason."""

from inventory_tracking.routes.catalog import act1, act2, act3, act4, act5
from inventory_tracking.routes.links import TOWNS
from inventory_tracking.routes.model import Route


ROUTES: tuple[Route, ...] = (*act1.ROUTES, *act2.ROUTES, *act3.ROUTES, *act4.ROUTES, *act5.ROUTES)

# Level -> why it has no script.
EXEMPT: dict[int, str] = {
    **dict.fromkeys(TOWNS, 'a town'),
    # (with act2.DURIEL on, the tombs' route has its script: routes/catalog/act2.py `tombs`)
    **({} if act2.DURIEL else {73: "Duriel's Lair: entered only with the Horadric Staff, and in no Herald group"}),
    **dict.fromkeys((133, 134, 135, 136), 'the Pandemonium event: not farmed by route'),
    137: 'the Colossal Summit: not farmed by route',
}
