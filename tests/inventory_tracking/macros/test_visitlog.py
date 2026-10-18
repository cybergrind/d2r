"""The town visit's snapshots and their codec (macros/visitlog.py; rca/2026-10-18/arch-town-planning.md step M0)."""

import json
import logging
from datetime import datetime
from pathlib import Path

from inventory_tracking.common import LOG, log_to_file
from inventory_tracking.macros.portal import FROM_SLING
from inventory_tracking.macros.town import Exit, Needs
from inventory_tracking.macros.visitlog import (
    Recorder,
    Snapshot,
    carried_from,
    carried_json,
    load,
    pack_from,
    pack_json,
    session_directory,
    snapshot_from,
    snapshot_json,
    view_from,
    view_json,
)
from inventory_tracking.macros.world import Carried, Pack, Page, StashView


RING = Carried(10, 537, 6, 0, (1, 1), quality=5, identified=False, unique=0)
FORTUNE = Carried(11, 603, 0, 0, (1, 1), quality=7, identified=True, unique=359)
PLATE = Carried(31, 352, 0, 0, (2, 3), quality=7)
PACK = Pack(
    (RING, Carried(1, 564, 0, 0, (2, 2))),
    ('##.', '##.', '##.', '...'),
    frozenset({31}),
    (PLATE,),
    keys=19,
    portals=None,
    key_room=False,
    pointer=None,
    identifies=20,
    stashed=(FORTUNE,),
    stash=('#' + '.' * 9,) + ('.' * 10,) * 9,
)
VIEW = StashView(
    (
        Page(0, ('#' + '.' * 9,) + ('.' * 10,) * 9, owner=7, units=frozenset({11}), items=(FORTUNE,)),
        Page(1, ('#' * 10,) * 10, owner=8),
    ),
    ((575, 10), (631, 99)),
)
START = Snapshot(
    'start',
    PACK,
    frozenset({(564, 0, 0)}),
    Needs(keys=12, portals=FROM_SLING),
    Exit.PORTAL,
    VIEW,
    frozenset({10}),
    frozenset({12}),
    frozenset({631}),
    gold=438_140,
    cap=940_000,
    at='15:20:18',
    misses=('junk left 1',),
    predicted=('cube 1 items (unique Embossed Plate at (0, 0))',),
)


def through_json(raw):
    return json.loads(json.dumps(raw))


def test_every_type_comes_back_the_same_through_json():
    assert carried_from(through_json(carried_json(FORTUNE))) == FORTUNE
    assert pack_from(through_json(pack_json(PACK))) == PACK
    assert pack_from(through_json(pack_json(Pack()))) == Pack()
    assert view_from(through_json(view_json(VIEW))) == VIEW
    assert snapshot_from(through_json(snapshot_json(START))) == START
    assert snapshot_from(through_json(snapshot_json(Snapshot('end', Pack(), frozenset(), Needs(), Exit.LEAVE)))) == (
        Snapshot('end', Pack(), frozenset(), Needs(), Exit.LEAVE)
    )


def test_the_needs_portals_come_back_as_the_known_source():
    back = snapshot_from(through_json(snapshot_json(START)))

    assert back.needs.portals is FROM_SLING


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 18, 15, 20, 18)

    def __call__(self) -> datetime:
        return self.now


def test_a_visit_writes_one_file_its_stops_added_and_the_gold_told_to_each(tmp_path: Path):
    record = Recorder(tmp_path, Clock())
    start = Snapshot('start', PACK, START.own, Needs(), Exit.WAYPOINT, VIEW)

    record.note(start)
    record.gold(438_140, 940_000)
    record.note(Snapshot('end', Pack(), START.own, Needs(), Exit.WAYPOINT, misses=('junk left 1',)))

    [path] = (tmp_path / 'visits').iterdir()
    assert path.name == '152018.json'
    doc = json.loads(path.read_text())
    assert (doc['version'], doc['visit']) == (1, '152018')
    stops = load(path)
    assert [s.stop for s in stops] == ['start', 'end']
    assert stops[0].pack == PACK
    assert stops[0].view == VIEW
    assert all((s.gold, s.cap, s.at) == (438_140, 940_000, '15:20:18') for s in stops)
    assert stops[1].misses == ('junk left 1',)

    Recorder(tmp_path, Clock()).note(start)  # a second visit in the same second
    assert sorted(p.name for p in (tmp_path / 'visits').iterdir()) == ['152018-2.json', '152018.json']


def test_with_no_run_directory_nothing_is_written():
    record = Recorder(None)

    record.note(START)

    assert not record.active
    assert record.path is None


def test_a_file_that_cannot_be_written_is_logged_once_and_never_raises(tmp_path: Path, caplog):
    (tmp_path / 'visits').write_text('a file where the folder goes')
    record = Recorder(tmp_path, Clock())

    with caplog.at_level(logging.INFO):
        record.note(START)
        record.note(START)

    assert not record.active
    assert caplog.text.count('Macro: visit snapshot: not written') == 1


def test_the_run_directory_is_where_probe_log_is_written(tmp_path: Path):
    assert all(Path(getattr(h, 'baseFilename', '')).name != 'probe.log' for h in LOG.handlers)
    assert session_directory() is None
    with log_to_file(tmp_path / 'probe.log'):
        assert session_directory() == tmp_path
