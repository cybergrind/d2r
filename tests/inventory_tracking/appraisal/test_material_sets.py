from inventory_tracking.collection.models import CaptureRun, Character, ItemRecord, Location, Sighting
from inventory_tracking.collection.store import CollectionStore
from inventory_tracking.items.metadata import metadata


def collection(tmp_path, quantities):
    path = tmp_path / 'collection.sqlite'
    bases = {b['code']: b for b in metadata()['bases'].values()}
    sightings = []
    for x, (code, quantity) in enumerate(quantities.items()):
        observation = {
            'item': {
                'base_code': code,
                'base_name': bases[code]['name'],
                'name': bases[code]['name'],
                'rarity': 'normal',
                'quantity': quantity,
            },
            'decoded_stats': [],
            'source': {'container': {'name': 'Materials stash', 'page': 4}, 'position': [x, 0]},
        }
        sightings.append(
            Sighting(
                item=ItemRecord.from_observation(observation),
                location=Location(owner='shared', container='materials', tab=None, x=x, y=0),
            )
        )
    capture = CaptureRun(
        id='materials',
        character=Character(name='Player'),
        containers=[('shared', 'materials', None)],
        started_at='2026-10-06T00:00:00Z',
    )
    with CollectionStore(path) as store:
        store.record_capture(capture, sightings)
    return path


def test_key_sets_count_units_and_only_name_shortages_for_one_more_set(tmp_path):
    from inventory_tracking.appraisal.material_sets import recorded_set

    path = collection(tmp_path, {'pk1': 5, 'pk2': 7, 'pk3': 4})
    result = recorded_set({'item': {'base_code': 'pk1', 'rarity': 'normal'}}, path)
    assert result['complete_sets'] == 1
    assert result['missing_next'] == {'Key of Terror': 1, 'Key of Destruction': 2}
    assert result['components'] == {'Key of Terror': 5, 'Key of Hate': 7, 'Key of Destruction': 4}
    assert result['observed_at'].startswith('2026-10-06')


def test_statue_sets_preserve_component_identity(tmp_path):
    from inventory_tracking.appraisal.material_sets import recorded_set

    path = collection(tmp_path, {'ua1': 20, 'ua2': 3, 'ua3': 2, 'ua4': 1, 'ua5': 2})
    result = recorded_set({'item': {'base_code': 'ua1', 'rarity': 'normal'}}, path)
    assert result['name'] == 'Statue Set'
    assert result['complete_sets'] == 1
    assert result['missing_next'] == {"Bul-Kathos' Nightmare": 1}


def test_unreadable_quantity_does_not_become_one_material(tmp_path):
    from inventory_tracking.appraisal.material_sets import recorded_set

    path = collection(tmp_path, {'pk1': 5, 'pk2': None, 'pk3': 4})
    result = recorded_set({'item': {'base_code': 'pk1', 'rarity': 'normal'}}, path)
    assert result['complete_sets'] is None
    assert result['missing_next'] == {}


def test_no_collection_or_unrelated_item_has_no_set_claim(tmp_path):
    from inventory_tracking.appraisal.material_sets import recorded_set

    assert recorded_set({'item': {'base_code': 'pk1', 'rarity': 'normal'}}, tmp_path / 'missing') is None
    path = collection(tmp_path, {'pk1': 5})
    assert recorded_set({'item': {'base_code': 'rin', 'rarity': 'unique'}}, path) is None


def test_material_report_shows_recorded_set_and_remaining_components():
    from inventory_tracking.appraisal.commodity import commodity_lines

    result = {
        'extraction': {'item': {'name': 'Key of Terror'}},
        'assessment': {'contract': {'policy': 'quest_material'}},
        'triage': {},
        'owned': {
            'material_set': {
                'name': '3x3 Key Set',
                'complete_sets': 1,
                'missing_next': {'Key of Terror': 1, 'Key of Destruction': 2},
                'observed_at': '2026-10-06T00:00:00Z',
            }
        },
    }
    lines = commodity_lines(result)
    assert 'Recorded sets: 1 x 3x3 Key Set (2026-10-06)' in lines
    assert 'For another set: 1 Key of Terror, 2 Key of Destruction' in lines


def test_closed_placements_are_not_available_for_a_set(tmp_path):
    import sqlite3

    from inventory_tracking.appraisal.material_sets import recorded_set

    path = collection(tmp_path, {'pk1': 5, 'pk2': 7, 'pk3': 4})
    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE placements SET gone_at='2026-10-06T01:00:00Z' WHERE fingerprint IN "
            "(SELECT fingerprint FROM items WHERE base_code='pk3')"
        )
    result = recorded_set({'item': {'base_code': 'pk1', 'rarity': 'normal'}}, path)
    assert result['complete_sets'] == 0
    assert result['missing_next'] == {'Key of Destruction': 3}


def test_service_attaches_material_set_evidence(tmp_path):
    from inventory_tracking.appraisal.service import owned_evidence

    path = collection(tmp_path, {'pk1': 5, 'pk2': 7, 'pk3': 4})
    result = owned_evidence(path)(
        {
            'item': {'base_code': 'pk1', 'base_name': 'Key of Terror', 'name': 'Key of Terror', 'rarity': 'normal'},
            'source': {},
        }
    )
    assert result['material_set']['complete_sets'] == 1


def test_stack_quantity_from_another_placement_is_not_reused(tmp_path):
    import sqlite3

    from inventory_tracking.appraisal.material_sets import recorded_set

    path = collection(tmp_path, {'pk1': 5, 'pk2': 7, 'pk3': 4})
    with sqlite3.connect(path) as db:
        db.execute("UPDATE items SET quantity=99, observation='{}' WHERE base_code='pk1'")
    result = recorded_set({'item': {'base_code': 'pk1', 'rarity': 'normal'}}, path)
    assert result['complete_sets'] is None
    assert result['components']['Key of Terror'] is None
