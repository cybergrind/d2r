import sqlite3

import pytest

from inventory_tracking.collection.models import CaptureRun, Character, ItemRecord, Location, Sighting
from inventory_tracking.collection.store import CollectionStore


MULE = Character(name='MuleOne', class_name='Sorceress', level=12)
OTHER = Character(name='MuleTwo')
ALL_MULE_CONTAINERS = [
    ('MuleOne', 'inventory', None),
    ('MuleOne', 'cube', None),
    ('MuleOne', 'equipped', None),
    ('MuleOne', 'stash', None),
    ('shared', 'shared_stash', 1),
    ('shared', 'shared_stash', 2),
]


def sighting(observation, character='MuleOne', *, tab=None, at=None):
    item = ItemRecord.from_observation(observation)
    location = Location.from_source(observation['source'], character, tab=tab)
    if at is not None:
        location = location.model_copy(update={'x': at[0], 'y': at[1]})
    return Sighting(item=item, location=location)


def capture(run_id, character=MULE, containers=ALL_MULE_CONTAINERS, started_at='2026-09-25T10:00:00+00:00'):
    return CaptureRun(id=run_id, character=character, containers=list(containers), started_at=started_at)


@pytest.fixture
def store(tmp_path):
    with CollectionStore(tmp_path / 'collection.sqlite') as store:
        yield store


def test_first_capture_records_items_placements_and_character(store, insight, magic_ring, set_helm):
    sightings = [sighting(insight), sighting(magic_ring), sighting(set_helm, tab=1)]
    summary = store.record_capture(capture('c1'), sightings)
    assert (summary.total, summary.new, summary.moved, summary.unchanged, summary.gone) == (3, 3, 0, 0, 0)
    assert str(summary) == '3 items · 3 new · 0 moved · 0 gone'
    assert store.counts() == {'characters': 1, 'items': 3, 'placements': 3, 'gone': 0, 'captures': 1}
    [character] = store.characters()
    assert (character.name, character.class_name, character.level) == ('MuleOne', 'Sorceress', 12)
    item = store.item(sightings[0].item.fingerprint)
    assert item is not None
    assert item.socket_items == ['Ral Rune', 'Tir Rune', 'Tal Rune', 'Sol Rune']
    assert item.observation == insight
    [placement] = store.placements(item.fingerprint)
    assert placement.location == Location(owner='MuleOne', container='stash', x=0, y=6)
    assert placement.capture_id == 'c1'


def test_unchanged_recapture_adds_nothing(store, insight, magic_ring):
    sightings = [sighting(insight), sighting(magic_ring)]
    store.record_capture(capture('c1'), sightings)
    summary = store.record_capture(capture('c2', started_at='2026-09-25T11:00:00+00:00'), sightings)
    assert (summary.new, summary.moved, summary.unchanged, summary.gone) == (0, 0, 2, 0)
    assert store.counts()['placements'] == 2
    assert store.counts()['gone'] == 0
    item = store.item(sightings[0].item.fingerprint)
    assert item is not None
    row = store.db.execute(
        'SELECT first_seen, last_seen FROM items WHERE fingerprint = ?', (item.fingerprint,)
    ).fetchone()
    assert (row['first_seen'], row['last_seen']) == ('2026-09-25T10:00:00+00:00', '2026-09-25T11:00:00+00:00')


def test_moving_an_item_closes_the_old_placement_and_counts_a_move(store, insight):
    store.record_capture(capture('c1'), [sighting(insight)])
    summary = store.record_capture(capture('c2'), [sighting(insight, at=(4, 4))])
    assert (summary.new, summary.moved, summary.unchanged, summary.gone) == (0, 1, 0, 0)
    fingerprint = ItemRecord.from_observation(insight).fingerprint
    assert [p.location.x for p in store.placements(fingerprint)] == [4]
    history = store.placements(fingerprint, include_gone=True)
    assert [(p.location.x, p.gone_at is not None) for p in history] == [(0, True), (4, False)]


def test_item_missing_from_a_captured_container_is_marked_gone(store, insight, magic_ring):
    store.record_capture(capture('c1'), [sighting(insight), sighting(magic_ring)])
    summary = store.record_capture(capture('c2'), [sighting(magic_ring)])
    assert (summary.new, summary.moved, summary.unchanged, summary.gone) == (0, 0, 1, 1)
    assert store.counts() == {'characters': 1, 'items': 2, 'placements': 1, 'gone': 1, 'captures': 2}


def test_containers_outside_the_capture_are_left_untouched(store, insight, magic_ring):
    store.record_capture(capture('c1'), [sighting(insight), sighting(magic_ring)])
    inventory_only = capture('c2', containers=[('MuleOne', 'inventory', None)])
    summary = store.record_capture(inventory_only, [sighting(magic_ring)])
    assert (summary.unchanged, summary.gone) == (1, 0)
    assert store.counts()['placements'] == 2


def test_sighting_outside_captured_containers_is_rejected_without_writes(store, insight, magic_ring):
    inventory_only = capture('c1', containers=[('MuleOne', 'inventory', None)])
    with pytest.raises(ValueError, match='outside captured containers'):
        store.record_capture(inventory_only, [sighting(insight)])
    assert store.counts() == {'characters': 0, 'items': 0, 'placements': 0, 'gone': 0, 'captures': 0}


def test_shared_stash_is_refreshed_by_whichever_character_captured_it_last(store, set_helm, magic_ring):
    shared = [('shared', 'shared_stash', 1)]
    store.record_capture(capture('c1', containers=shared), [sighting(set_helm, tab=1)])
    summary = store.record_capture(capture('c2', character=OTHER, containers=shared), [])
    assert summary.gone == 1
    assert store.counts()['placements'] == 0
    assert [c.name for c in store.characters()] == ['MuleOne', 'MuleTwo']


def test_identical_items_in_two_cells_are_two_placements_of_one_item(store, magic_ring):
    twins = [sighting(magic_ring), sighting(magic_ring, at=(5, 1))]
    summary = store.record_capture(capture('c1'), twins)
    assert (summary.total, summary.new) == (2, 2)
    assert store.counts()['items'] == 1
    assert len(store.placements(twins[0].item.fingerprint)) == 2


def test_query_matches_words_across_name_set_runeword_sockets_and_stats(store, insight, magic_ring, set_helm):
    store.record_capture(capture('c1'), [sighting(insight), sighting(magic_ring), sighting(set_helm, tab=1)])

    def names(rows):
        return [item.name for item, _ in rows]

    assert names(store.query('insight')) == ['Insight']
    assert names(store.query("tal rasha's")) == ["Tal Rasha's Horadric Crest"]
    assert names(store.query('wrappings')) == ["Tal Rasha's Horadric Crest"]
    assert names(store.query('sol rune')) == ['Insight']
    assert names(store.query('maximum stamina')) == ['Ring']
    assert names(store.query('+5 strength')) == ['Insight']
    assert names(store.query('life')) == ["Tal Rasha's Horadric Crest"]
    assert names(store.query('%')) == ['Insight', 'Ring']  # literal percent, not a wildcard
    assert names(store.query(sockets=4)) == ['Insight']
    assert names(store.query(sockets='empty')) == []
    assert names(store.query(owner='shared')) == ["Tal Rasha's Horadric Crest"]
    assert names(store.query(container='inventory')) == ['Ring']
    assert len(store.query()) == 3


def test_reopening_keeps_data_and_rejects_foreign_schema_versions(tmp_path, insight):
    path = tmp_path / 'collection.sqlite'
    with CollectionStore(path) as store:
        store.record_capture(capture('c1'), [sighting(insight)])
    with CollectionStore(path) as store:
        assert store.counts()['items'] == 1
    with sqlite3.connect(path) as raw:
        raw.execute('PRAGMA user_version = 99')
    with pytest.raises(ValueError, match='schema version'):
        CollectionStore(path).open()


def test_older_databases_gain_the_added_columns_and_tables(tmp_path, insight):
    path = tmp_path / 'old.sqlite'
    with CollectionStore(path) as store:
        store.record_capture(capture('c1'), [sighting(insight)])
    with sqlite3.connect(path) as raw:
        for column in ('quantity', 'width', 'height'):
            raw.execute(f'ALTER TABLE items DROP COLUMN {column}')
        raw.execute('DROP TABLE spaces')
        raw.execute('PRAGMA user_version = 1')
    with CollectionStore(path) as store:
        assert store.db.execute('PRAGMA user_version').fetchone()[0] == 3
        item = store.item(ItemRecord.from_observation(insight).fingerprint)
        assert item is not None
        assert item.quantity is None
        assert item.width is None
        assert store.spaces() == []
