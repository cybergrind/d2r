"""Free-space accounting from grid cells."""

import json

import pytest

from inventory_tracking.collection.capture import fits_counts, grid_space, item_sizes
from inventory_tracking.collection.export import export_payload
from inventory_tracking.collection.models import (
    CaptureRun,
    Character,
    ContainerKey,
    ContainerSpace,
    ItemRecord,
    Location,
    Sighting,
)
from inventory_tracking.collection.store import CollectionStore


def cells_from(rows, pointer_base=0x1000):
    """'#' cells get distinct pointers unless a letter marks one multi-cell item."""
    width = len(rows[0])
    cells = []
    letters = {}
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == '.':
                cells.append(0)
            elif ch == '#':
                cells.append(pointer_base + y * width + x + 1)
            else:
                cells.append(letters.setdefault(ch, 0x9000 + ord(ch)))
    return {'width': width, 'height': len(rows), 'cells': cells}


def test_fits_counts_is_a_greedy_lower_bound():
    rows = ['....', '....', '##..', '##..']
    fits = fits_counts(rows)
    assert fits['1x1'] == 12
    assert fits['2x2'] == 3
    assert fits['2x4'] == 1  # the right two columns
    assert fits['1x4'] == 2
    assert fits['2x3'] == 1
    assert fits_counts(['####', '####']) == dict.fromkeys(fits, 0)


def test_grid_space_reports_free_cells_and_layout():
    grid = cells_from(['AA..', 'AA..', '...#'])
    space = grid_space(grid, 'cube')
    assert (space['free'], space['occupied'], space['width'], space['height']) == (7, 5, 4, 3)
    assert space['rows'] == ['##..', '##..', '...#']
    assert space['fits']['2x2'] == 1


def test_item_sizes_come_from_the_cells_holding_each_pointer():
    grids = {2: cells_from(['AA.B', 'AA.B', '....']), 6: cells_from(['C.', 'C.', 'C.'])}
    sizes = item_sizes(grids)
    assert sizes[0x9000 + ord('A')] == (2, 2)
    assert sizes[0x9000 + ord('B')] == (1, 2)
    assert sizes[0x9000 + ord('C')] == (1, 3)


def test_store_keeps_the_latest_space_per_grid_and_finds_room(tmp_path, insight):
    space = ContainerSpace(
        owner='MuleOne',
        container='stash',
        width=4,
        height=2,
        free=4,
        occupied=4,
        rows=['##..', '##..'],
        fits=fits_counts(['##..', '##..']),
    )
    shared = ContainerSpace(
        owner='shared',
        container='shared_stash',
        tab=1,
        width=2,
        height=2,
        free=0,
        occupied=4,
        rows=['##', '##'],
        fits=fits_counts(['##', '##']),
    )
    containers: list[ContainerKey] = [('MuleOne', 'stash', None), ('shared', 'shared_stash', 1)]
    sighting = Sighting(
        item=ItemRecord.from_observation(insight), location=Location.from_source(insight['source'], 'MuleOne')
    )
    with CollectionStore(tmp_path / 'c.sqlite') as store:
        run = CaptureRun(id='c1', character=Character(name='MuleOne'), containers=containers, started_at='t1')
        store.record_capture(run, [sighting], [space, shared])
        assert [(s.owner, s.free) for s in store.spaces()] == [('MuleOne', 4), ('shared', 0)]
        assert [s.owner for s in store.spaces(fits='2x2')] == ['MuleOne']
        fuller = space.model_copy(
            update={'free': 2, 'occupied': 6, 'rows': ['###.', '###.'], 'fits': fits_counts(['###.', '###.'])}
        )
        run2 = CaptureRun(id='c2', character=Character(name='MuleOne'), containers=containers, started_at='t2')
        store.record_capture(run2, [sighting], [fuller])
        [mine, _] = store.spaces()
        assert (mine.free, mine.fits['2x2'], mine.fits['1x2']) == (2, 0, 1)
        payload = export_payload(store)
    assert [s['where'] for s in payload['spaces']] == ['Personal stash', 'Shared stash 1']
    assert payload['spaces'][0]['rows'] == ['###.', '###.']
    assert json.dumps(payload)  # serializable


def test_space_outside_captured_containers_is_rejected(tmp_path):
    space = ContainerSpace(
        owner='MuleOne', container='cube', width=3, height=4, free=12, occupied=0, rows=['...'] * 4, fits={}
    )
    with CollectionStore(tmp_path / 'c.sqlite') as store:
        run = CaptureRun(
            id='c1', character=Character(name='MuleOne'), containers=[('MuleOne', 'stash', None)], started_at='t'
        )
        with pytest.raises(ValueError, match='outside captured containers'):
            store.record_capture(run, [], [space])
        assert store.counts()['captures'] == 0
