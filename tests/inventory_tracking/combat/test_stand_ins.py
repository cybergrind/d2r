"""combat/stand_ins.py: the takes' evidence on the stand-in hostiles (rca/2026-10-22/walled-boss-findings.md §2)."""

import gzip
import json

from inventory_tracking.combat import stand_ins


TABLE = {
    'types': {
        '229': {'seconds': 145.3, 'lost': 56.0, 'biggest': 33.0, 'takes': 3},
        '211': {'seconds': 20.4, 'lost': 15.0, 'biggest': 7.0, 'takes': 2},
    },
    'pooled': {'seconds': 6967.4, 'lost': 29787.0, 'biggest': 1034.0, 'takes': 1680},
}


def test_a_type_with_enough_seconds_of_its_own_is_priced_by_its_row_else_by_the_pool(monkeypatch):
    monkeypatch.setattr(stand_ins, 'table', lambda: TABLE)
    assert stand_ins.prior(229) == (145.3, 56.0)
    assert stand_ins.prior(211) == (6967.4, 29787.0)  # 20 s: under POOL_SECONDS
    assert stand_ins.prior(243) == (6967.4, 29787.0)  # none of its own


def test_the_built_file_holds_radament(monkeypatch):
    found = stand_ins.table()
    assert set(found) >= {'types', 'pooled'}
    seconds, lost = stand_ins.prior(229)
    assert seconds >= stand_ins.POOL_SECONDS  # 2026-10-22: 145 s, 56 lost
    assert lost < seconds


def frame(t: float, life: float, monsters: list) -> dict:
    return {'t': t, 'game': True, 'p': [1, 3, 49, 100.0, 100.0, 0, 0, life, 3000, 700, 745], 'm': monsters}


def test_a_take_counts_the_seconds_within_its_radius_of_a_live_one_and_the_life_lost_then(tmp_path):
    take = tmp_path / '20261022T201417Z-49'
    take.mkdir()
    near = [7, 229, 1, 110.0, 100.0, 128, 128]
    far = [7, 229, 1, 160.0, 100.0, 128, 128]
    dead = [7, 229, 12, 110.0, 100.0, 0, 128]
    rows = [
        frame(0.0, 3000, [near]),
        frame(0.4, 2990, [near]),  # 0.4 s, 10 lost
        frame(1.4, 2980, [near]),  # a gap: FRAME_MOST, 10 lost
        frame(1.8, 2900, [far]),  # out of its radius: nothing
        frame(2.2, 2900, [dead]),  # dead: nothing
    ]
    with gzip.open(take / 'frames.jsonl.gz', 'wt') as out:
        out.write(''.join(json.dumps(row) + '\n' for row in rows))
    with gzip.open(take / 'units.jsonl.gz', 'wt') as out:
        out.write(json.dumps({'t': 0.0, 'unit': 7, 'txt': 229}) + '\n')
    found = stand_ins.build(tmp_path)
    assert found['types']['229'] == {'seconds': 0.9, 'lost': 20.0, 'biggest': 10.0, 'takes': 1}
    assert found['pooled']['seconds'] == 0.9
