from dataclasses import replace

import pytest

from inventory_tracking.config import OSD, with_overrides
from inventory_tracking.models import Location, Observation, State
from inventory_tracking.osd.presenter import Presenter
from inventory_tracking.tracking.resources import resource_observations
from tests.inventory_tracking.conftest import SESSION
from tests.inventory_tracking.tracking.test_resources import record, snapshot


@pytest.mark.parametrize('count', [0, 4, 5, 20])
@pytest.mark.parametrize('town', [True, False])
def test_identify_tome_count_only_when_low_in_town(count, town):
    data = snapshot([record(534, 0, stats=[{'id': 70, 'layer': 0, 'raw': count}])])
    data['resources']['locations'][0]['area_id'] = 40 if town else 111
    observations = resource_observations(data, 7)
    state = State(sampled_at=100, session=SESSION, **observations._asdict())
    presenter = Presenter(with_overrides(OSD, key_stock=with_overrides(OSD.key_stock, enabled=False)))
    presenter.update(state)
    assert presenter.render(now=100) == (['id: ' + str(count)] if town and count < 5 else [])
    assert presenter.render(now=103) == []
    for location in [Observation.unavailable(100), Observation(97, Location(40, True))]:
        presenter.update(replace(state, location=location))
        assert presenter.render(now=100) == []


@pytest.mark.parametrize(
    'items',
    [
        [],
        [record(534, 0, page=1)],
        [record(534, 0, owner=99)],
        [record(534, 0, stats=[{'id': 70, 'layer': 0, 'raw': 21}])],
    ],
)
def test_missing_or_invalid_identify_tome_is_hidden(items):
    observations = resource_observations(snapshot(items), 7)
    presenter = Presenter(with_overrides(OSD, key_stock=with_overrides(OSD.key_stock, enabled=False)))
    presenter.update(State(sampled_at=100, session=SESSION, **observations._asdict()))
    assert presenter.render(now=100) == []
