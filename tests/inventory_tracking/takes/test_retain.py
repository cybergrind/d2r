"""How much of the takes is kept (takes/retain.py): packed when closed, the oldest removed past a size."""

import gzip
import json

from inventory_tracking.game.records import World
from inventory_tracking.takes.record import Recorder, Sample
from inventory_tracking.takes.retain import died, over, pack, recordings, size, tidy
from inventory_tracking.takes.takes import Take
from tests.inventory_tracking.macros.fakes import player


def take(root, name, *, lines=200, dead=False):
    directory = root / name
    directory.mkdir()
    (directory / 'manifest.json').write_text(json.dumps({'area': 39, 'schema': 2}))
    frames = [json.dumps({'t': n * 0.04, 'n': n, 'p': None, 'm': [], 'x': []}) for n in range(lines)]
    (directory / 'frames.jsonl').write_text('\n'.join(frames) + '\n')
    hurt = {'t': 1.0, 'event': 'hurt', 'lost': 300, 'life': 0 if dead else 900, 'dead': dead}
    (directory / 'events.jsonl').write_text(json.dumps(hurt) + '\n')
    for other in ('units', 'missiles', 'paths'):
        (directory / f'{other}.jsonl').write_text('')
    return directory


def test_a_take_is_packed_in_place_and_reads_as_before(tmp_path):
    directory = take(tmp_path, '20261012T010000Z-39')
    before, frames = size(directory), Take.load(directory).frames
    saved = pack(directory)
    assert saved > 0
    assert size(directory) == before - saved
    assert sorted(path.name for path in directory.iterdir()) == [
        'events.jsonl.gz', 'frames.jsonl.gz', 'manifest.json', 'missiles.jsonl.gz', 'paths.jsonl.gz', 'units.jsonl.gz',
    ]  # fmt: skip
    assert Take.load(directory).frames == frames
    assert pack(directory) == 0  # nothing left to pack


def test_past_the_size_the_oldest_go_and_a_take_with_a_death_last(tmp_path):
    old = take(tmp_path, '20261010T010000Z-39', dead=True)
    middle = take(tmp_path, '20261011T010000Z-25')
    new = take(tmp_path, '20261012T010000Z-39')
    (tmp_path / 'viz').mkdir()  # not a take: never looked at
    (tmp_path / 'scoreboard.json').write_text('{}')
    assert recordings(tmp_path) == [old, middle, new]
    assert (died(old), died(new)) == (True, False)
    one = size(new)

    assert over(tmp_path, 10 * one) == []
    assert over(tmp_path, 2 * one + 50) == [middle]  # the oldest without a death
    assert over(tmp_path, one + 50) == [middle, new]
    assert over(tmp_path, one + 50, spare=frozenset((new.name,))) == [middle, old]  # the open take stays
    assert over(tmp_path, 0) == [middle, new, old]


def test_a_death_is_found_in_a_packed_take_too(tmp_path):
    directory = take(tmp_path, '20261010T010000Z-39', dead=True)
    pack(directory)
    assert died(directory)


def test_tidying_packs_the_closed_take_and_holds_the_whole_to_the_size(tmp_path):
    old = take(tmp_path, '20261010T010000Z-39')
    closed = take(tmp_path, '20261012T010000Z-39')
    tidy(tmp_path, closed, keep=size(closed))  # room for one unpacked take
    assert not old.exists()
    assert (closed / 'frames.jsonl.gz').exists()
    assert not (closed / 'frames.jsonl').exists()
    with gzip.open(closed / 'frames.jsonl.gz', 'rt') as handle:
        assert sum(1 for _ in handle) == 200


def test_the_recorder_takes_every_level_but_a_town_and_packs_a_take_as_it_closes(tmp_path):
    def sample(area):
        return Sample(World(True, (), 'cyber1', (388, None), player=player(area)), [], None, None)

    samples = iter([sample(39), sample(39), sample(1), sample(1)])  # Moo Moo Farm, then the Rogue Encampment
    rec = Recorder(lambda: next(samples), output=tmp_path, areas=None, clock=lambda: 0.0, keep=10**9)
    for now in (0.0, 0.04, 0.08, 4.0):
        rec.step(now)
    assert rec.take is None
    assert rec.tidying is not None
    rec.tidying.join(5)
    (directory,) = tmp_path.iterdir()
    assert directory.name.endswith('-39')
    assert (directory / 'frames.jsonl.gz').exists()
    assert len(Take.load(directory).frames) == 3  # two in the level and the one within IDLE_SECONDS of it
