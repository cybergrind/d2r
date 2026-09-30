import copy

import pytest

from inventory_tracking.appraisal.owned import owned_copies, owned_lines, owned_summary
from inventory_tracking.collection.models import CaptureRun, Character, ItemRecord, Location, Sighting
from inventory_tracking.collection.store import CollectionStore


def stat(stat_id, name, value, label, low=None, high=None, better='higher'):
    row = {
        'memory_stat': {'id': stat_id, 'layer': 0, 'raw': value},
        'name': name,
        'status': 'decoded',
        'value': value,
        'label': label,
        'text': label.replace('{{value}}', str(value)),
    }
    if low is not None:
        row['roll_range'] = {'min': low, 'max': high, 'better': better}
    return row


def unique(name='Snowclash', table_id=300, *, defense=150, cold=12, x=0, y=0, ethereal=False):
    return {
        'item': {
            'base_code': 'ulc',
            'base_name': 'Battle Belt',
            'name': name,
            'rarity': 'unique',
            'identified': True,
            'ethereal': ethereal,
            'sockets': 0,
        },
        'decoded_stats': [
            stat(16, 'item_armor_percent', defense, '+{{value}}% Enhanced Defense', 130, 170),
            stat(43, 'coldresist', cold, 'Cold Resist +{{value}}%', 10, 15),
            stat(7, 'maxhp', 20, '+{{value}} to Life'),
        ],
        'unresolved_stats': [],
        'source': {
            'item_identity': {'table': 'unique', 'table_id': table_id},
            'container': {'page': 4, 'name': 'Personal stash'},
            'position': [x, y],
        },
    }


@pytest.fixture
def collection(tmp_path):
    database = tmp_path / 'collection.sqlite'

    def record(*observations):
        sightings = [
            Sighting(
                item=ItemRecord.from_observation(o),
                location=Location.from_source(o['source'], 'Mule'),
            )
            for o in observations
        ]
        capture = CaptureRun(
            id='c1',
            character=Character(name='Mule'),
            containers=[('Mule', 'stash', None)],
            started_at='2026-09-30T00:00:00Z',
        )
        with CollectionStore(database) as store:
            store.record_capture(capture, sightings)
        return database

    return record


def test_missing_collection_gives_no_evidence(tmp_path):
    assert owned_copies(unique(), tmp_path / 'absent.sqlite') is None


def test_better_rolls_than_every_owned_copy(collection):
    database = collection(unique(defense=140, x=0), unique(defense=160, cold=11, x=2))
    owned = owned_copies(unique(defense=165, cold=14), database)
    assert owned['count'] == 2
    assert owned['relation'] == 'better'
    assert owned_summary(owned) == 'owned 2: this one beats every copy'
    lines = owned_lines(owned)
    assert lines[0].startswith('Owned: 2 x unique Snowclash — this one beats every copy; rolls ')
    assert 'new better: +165% Enhanced Defense vs 160' in lines[1]


def test_one_better_owned_copy_makes_the_new_item_worse(collection):
    database = collection(unique(defense=140, cold=10, x=0), unique(defense=170, cold=15, x=2))
    assert owned_copies(unique(defense=150, cold=12), database)['relation'] == 'worse'


def test_mixed_rolls(collection):
    database = collection(unique(defense=170, cold=10))
    owned = owned_copies(unique(defense=150, cold=15), database)
    assert owned['relation'] == 'mixed'
    copy_ = owned['copies'][0]
    assert copy_['better'] == ['CR +15% vs 10']
    assert copy_['worse'] == ['+150% Enhanced Defense vs 170']


def test_other_uniques_and_ethereal_copies_do_not_count(collection):
    database = collection(unique(name='Nosferatu', table_id=301), unique(ethereal=True, x=2))
    owned = owned_copies(unique(), database)
    assert owned['count'] == 0
    assert owned_lines(owned) == ['Owned: none (unique Snowclash)']


def test_the_assessed_item_itself_is_not_a_copy(collection):
    item = unique(x=3, y=4)
    database = collection(item, copy.deepcopy(item) | {'source': unique(x=5)['source']})
    owned = owned_copies(item, database)
    assert owned['count'] == 1
    assert owned['relation'] == 'equal'
    assert owned['copies'][0]['identical']


def test_magic_items_match_on_the_same_kinds_of_stats(collection):
    def charm(life, x, *, skill=True):
        stats = [stat(7, 'maxhp', life, '+{{value}} to Life', 1, 45)]
        if skill:
            stats.append(stat(188, 'item_addskill_tab', 1, '+{{value}} to Lightning Skills'))
        observation = unique(x=x)
        observation['item'].update(base_code='cm3', base_name='Grand Charm', name='Grand Charm', rarity='magic')
        observation['decoded_stats'] = stats
        return observation

    database = collection(charm(30, 0), charm(44, 2, skill=False))
    owned = owned_copies(charm(40, 4), database)
    assert owned['count'] == 1
    assert owned['relation'] == 'better'
