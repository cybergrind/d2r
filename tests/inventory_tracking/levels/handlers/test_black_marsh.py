"""Black Marsh: the Forgotten Tower entrance. Fixture black_marsh (evidence 2026-09-30); the user
confirmed the direction. Outdoor room lists hold 8x8 chunks named 'Wild Border N', feature presets
and 'preset 0' (generated terrain)."""

from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.registry import handler_for
from tests.inventory_tracking.levels.fixtures import replay


def test_tower_entrance_is_found_in_the_outdoor_room_list():
    snapshot = replay('black_marsh')
    handler = handler_for(6)

    guidance = handler.guide(snapshot)

    assert [(p.label, preset_name(p.room.preset)) for p in guidance.pois] == [('Forgotten Tower', 'Act 1 - Tower 1')]
    assert guidance.problems == ()
    assert handler.confirmed
