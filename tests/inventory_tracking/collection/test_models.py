import pytest

from inventory_tracking.collection.models import CaptureRun, Character, ItemRecord, Location


def test_item_record_from_runeword_observation_keeps_sockets_and_stats(insight):
    item = ItemRecord.from_observation(insight)
    assert item.name == 'Insight'
    assert item.runeword == 'Insight'
    assert item.base_code == '9vo'
    assert item.sockets == 4
    assert item.socket_items == ['Ral Rune', 'Tir Rune', 'Tal Rune', 'Sol Rune']
    assert '+5 to Strength' in item.stat_lines
    assert item.unresolved == 0
    assert len(item.fingerprint) == 64


def test_item_record_keeps_unknown_flags_unknown(magic_ring):
    item = ItemRecord.from_observation(magic_ring)
    assert item.rarity == 'magic'
    assert item.identified is None
    assert item.ethereal is None


def test_search_text_covers_every_searchable_field(insight, set_helm):
    item = ItemRecord.from_observation(insight)
    text = item.search_text
    for needle in ('insight', 'bill', '9vo', 'ral rune', '+5 to strength'):
        assert needle in text
    helm = ItemRecord.from_observation(set_helm)
    assert "tal rasha's wrappings" in helm.search_text
    assert 'horadric crest' in helm.search_text


@pytest.mark.parametrize(
    ('page', 'name', 'owner_type', 'expected'),
    [
        (0, 'Main inventory', 0, ('Mule', 'inventory')),
        (3, 'Horadric Cube', 0, ('Mule', 'cube')),
        (255, 'Equipped items', 0, ('Mule', 'equipped')),
        (255, 'Mercenary equipment', 1, ('Mule', 'mercenary')),
        (4, 'Personal stash', 0, ('Mule', 'stash')),
        (4, 'Shared stash', 0, ('shared', 'shared_stash')),
    ],
)
def test_location_from_source_maps_verified_containers(page, name, owner_type, expected):
    source = {'container': {'page': page, 'name': name}, 'owner_type': owner_type, 'position': [1, 2]}
    location = Location.from_source(source, 'Mule', tab=1 if expected[1] == 'shared_stash' else None)
    assert (location.owner, location.container) == expected
    assert (location.x, location.y) == (1, 2)
    assert location.key == (location.owner, location.container, location.tab)


def test_location_rejects_tab_outside_shared_stash_and_unknown_pages():
    with pytest.raises(ValueError, match='carry a tab'):
        Location.from_source({'container': {'page': 0, 'name': 'Main inventory'}, 'position': [0, 0]}, 'Mule', tab=1)
    with pytest.raises(ValueError, match='Unsupported container page'):
        Location.from_source({'container': {'page': 9, 'name': 'Belt'}, 'position': [0, 0]}, 'Mule')


def test_location_label_names_tab_and_cell():
    assert Location(owner='shared', container='shared_stash', tab=2, x=4, y=5).label == 'shared · shared stash 2 (4,5)'
    assert Location(owner='Mule', container='stash', x=0, y=0).label == 'Mule · stash (0,0)'


def test_capture_run_requires_character_and_id():
    with pytest.raises(ValueError, match='at least 1 character'):
        CaptureRun(id='', character=Character(name='Mule'), containers=[], started_at='t')
    with pytest.raises(ValueError, match='at least 1 character'):
        Character(name='')
