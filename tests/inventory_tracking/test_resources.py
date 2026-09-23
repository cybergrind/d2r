import pytest

from inventory_tracking.config import RESOURCE_READER, ResourceReaderConfig, with_overrides
from inventory_tracking.models import Observation, ObservationStatus
from inventory_tracking.resources import resource_observations


def value[T](observation: Observation[T]) -> T:
    assert observation.value is not None
    return observation.value


CONFIG = with_overrides(
    RESOURCE_READER,
    portal_stats_offset=0x30,
    teleport_stats_offset=0xE8,
    weapon_slots_verified=True,
    location_verified=True,
)


def record(class_id, mode, *, page=0, slot=0, stats=(), item_id=9, owner=7):
    return {
        'unit_id': item_id,
        'txt_id': class_id,
        'mode': mode,
        'details': {'owner_id': owner, 'inventory_page': page, 'body_location': slot},
        'resource_stats': {
            'complete': True,
            'arrays': [{'header_offset': 0x30, 'stats': list(stats)}, {'header_offset': 0xE8, 'stats': list(stats)}],
        },
    }


def snapshot(items):
    return {
        'sample_monotonic': 100,
        'status': 'research',
        'resources': {
            'complete': True,
            'keys_sampled': True,
            'items': items,
            'locations': [{'unit_id': 7, 'area_id': 40}],
        },
    }


def test_resources_stay_unavailable_until_layout_is_verified():
    result = resource_observations(snapshot([]), 7, config=ResourceReaderConfig())
    assert all(observation.status == ObservationStatus.UNAVAILABLE for observation in result)


def test_select_inventory_tome_and_secondary_charged_staff():
    data = snapshot(
        [
            record(533, 0, stats=[{'id': 70, 'layer': 0, 'raw': 16}]),
            record(533, 0, page=1, stats=[], item_id=10),
            record(63, 1, slot=11, stats=[{'id': 204, 'layer': (54 << 6) | 1, 'raw': (20 << 8) | 3}], item_id=11),
            record(533, 0, owner=999, item_id=12),
        ]
    )
    result = resource_observations(data, 7, config=CONFIG)
    assert value(result.portal_tome).quantity == 16
    assert value(result.teleport).current == 3
    assert value(result.teleport).maximum == 20
    assert value(result.location).in_town


def test_absence_ambiguity_and_bad_quantity_are_distinct():
    assert resource_observations(snapshot([]), 7, config=CONFIG).teleport.value is None
    tome = record(533, 0, stats=[{'id': 70, 'layer': 0, 'raw': 21}])
    assert resource_observations(snapshot([tome]), 7, config=CONFIG).portal_tome.status == ObservationStatus.UNAVAILABLE
    tome['resource_stats']['arrays'][0]['stats'][0]['raw'] = 16  # pyrefly: ignore[bad-index]  # test fixture dict
    result = resource_observations(snapshot([tome, dict(tome, unit_id=10)]), 7, config=CONFIG)
    assert result.portal_tome.status == ObservationStatus.UNAVAILABLE
    assert value(result.location).in_town


def test_malformed_optional_data_cannot_break_health(snapshot):
    from inventory_tracking.state import from_research

    data = snapshot()
    data['resources'] = {'complete': True, 'items': [{'details': None}]}
    state = from_research(data, resource_config=CONFIG)
    assert state.health is not None
    assert state.portal_tome.status == ObservationStatus.UNAVAILABLE


@pytest.mark.parametrize('fixture', ['resources_baseline.json', 'resources_swapped.json'])
def test_captured_staff_and_tome_match_user_baseline(fixture):
    import json
    from pathlib import Path

    data = json.loads((Path(__file__).parent / 'fixtures' / fixture).read_text())
    result = resource_observations(data, data['player_id'], config=CONFIG)
    assert value(result.portal_tome).quantity == 18
    assert value(result.teleport).current == 32
    assert value(result.teleport).maximum == 33


def test_removal_and_missing_charged_skill_hide_staff_without_claiming_zero():
    staff = record(63, 0, stats=[{'id': 204, 'layer': 54 << 6, 'raw': (33 << 8) | 32}])
    result = resource_observations(snapshot([staff]), 7, config=CONFIG)
    assert result.teleport.status == ObservationStatus.AVAILABLE
    assert result.teleport.value is None
    staff = record(63, 1, slot=11, stats=[{'id': 107, 'layer': 54, 'raw': 1}])
    assert resource_observations(snapshot([staff]), 7, config=CONFIG).teleport.value is None


def test_live_defaults_decode_captured_consumption_and_town_transition():
    import json
    from pathlib import Path

    from inventory_tracking.models import State
    from inventory_tracking.osd.presenter import Presenter
    from tests.inventory_tracking.conftest import SESSION

    presenter = Presenter()
    for fixture, charges, quantity, town, expected in [
        ('resources_baseline.json', 32, 18, True, ['tele 32/33 repair']),
        ('resources_swapped.json', 32, 18, True, ['tele 32/33 repair']),
        ('resources_consumed.json', 31, 16, False, []),
    ]:
        data = json.loads((Path(__file__).parent / 'fixtures' / fixture).read_text())
        observations = resource_observations(data, data['player_id'])
        assert value(observations.teleport).current == charges
        assert value(observations.portal_tome).quantity == quantity
        assert value(observations.location).in_town == town
        presenter.update(State(sampled_at=data['sample_monotonic'], session=SESSION, **observations._asdict()))
        assert presenter.render(now=data['sample_monotonic']) == expected


def test_keys_sum_only_owned_inventory_stacks():
    config = with_overrides(CONFIG, key_stats_offset=0x30)

    def keys(quantity, **kwargs):
        return record(558, 0, stats=[{'id': 70, 'layer': 0, 'raw': quantity}], **kwargs)

    data = snapshot(
        [
            keys(2),
            keys(3, item_id=10),
            keys(12, page=1, item_id=11),
            keys(12, page=5, item_id=12),
            keys(12, owner=999, item_id=13),
        ]
    )
    assert value(resource_observations(data, 7, config=config).keys) == 5
    assert value(resource_observations(snapshot([]), 7, config=config).keys) == 0
    data['resources']['items'][0]['resource_stats']['complete'] = False
    assert resource_observations(data, 7, config=config).keys.status == ObservationStatus.UNAVAILABLE


@pytest.mark.parametrize('quantity', [-1, 13, True])
def test_invalid_key_stack_does_not_claim_zero(quantity):
    config = with_overrides(CONFIG, key_stats_offset=0x30)
    item = record(558, 0, stats=[{'id': 70, 'layer': 0, 'raw': quantity}])
    assert resource_observations(snapshot([item]), 7, config=config).keys.status == ObservationStatus.UNAVAILABLE


def test_missing_key_capture_and_duplicate_stacks_are_unavailable():
    config = with_overrides(CONFIG, key_stats_offset=0x30)
    data = snapshot([])
    del data['resources']['keys_sampled']
    assert resource_observations(data, 7, config=config).keys.status == ObservationStatus.UNAVAILABLE
    item = record(558, 0, stats=[{'id': 70, 'layer': 0, 'raw': 2}])
    assert resource_observations(snapshot([item, item]), 7, config=config).keys.status == ObservationStatus.UNAVAILABLE
    ground = dict(item, mode=3)
    assert value(resource_observations(snapshot([ground]), 7, config=config).keys) == 0


def test_live_key_baseline_excludes_other_inventory_pages():
    import json
    from pathlib import Path

    from inventory_tracking.models import State
    from inventory_tracking.osd.presenter import Presenter
    from tests.inventory_tracking.conftest import SESSION

    data = json.loads((Path(__file__).parent / 'fixtures' / 'keys_baseline.json').read_text())
    observation = resource_observations(data, data['player_id']).keys
    assert value(observation) == 12
    presenter = Presenter()
    presenter.update(State(sampled_at=data['sample_monotonic'], session=SESSION, keys=observation))
    assert presenter.render(now=data['sample_monotonic']) == []
