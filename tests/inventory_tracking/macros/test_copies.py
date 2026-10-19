"""The best copy of a unique or set item first (macros/copies.py). The player, 16:50 on 2026-10-18: "loop should keep
the best copy first": a set or unique item the appraisal calls `vendor` is sold only when a copy at least as good is
owned."""

import json
import logging

import pytest

from inventory_tracking.collection.models import CaptureRun, Character, ItemRecord, Location, Sighting
from inventory_tracking.collection.store import CollectionStore
from inventory_tracking.macros.copies import Appraisal, keep_copy, owned_copies, sold
from inventory_tracking.macros.game.records import Carried
from tests.inventory_tracking.appraisal.test_owned import unique


MAGIC, SET, RARE, UNIQUE = 4, 5, 6, 7
BELT = Carried(21, 391, 2, 0, (2, 1), UNIQUE)  # the loop's identified unique belt
RING = Carried(22, 522, 4, 0, (1, 1), MAGIC)


def read(unit: int, **rolls) -> dict:
    """An identify read of a Snowclash as unit `unit` (appraisal/owned.py's test item)."""
    observation = unique(**rolls)
    observation['source'] |= {'unit_id': unit}
    return observation


def test_the_first_copy_is_kept():
    assert keep_copy(BELT, Appraisal('vendor', read(21)), []) == 'the first copy'


def test_an_owned_copy_that_rolls_as_well_or_better_sells_it():
    assert keep_copy(BELT, Appraisal('vendor', read(21, defense=150)), [unique(defense=150)]) is None
    assert keep_copy(BELT, Appraisal('vendor', read(21, defense=140)), [unique(defense=160)]) is None
    # one copy rolls better, another worse: one at least as good is owned
    assert (
        keep_copy(BELT, Appraisal('vendor', read(21, defense=150)), [unique(defense=140), unique(defense=160)]) is None
    )


def test_a_copy_that_rolls_better_than_every_owned_one_is_kept():
    reason = keep_copy(BELT, Appraisal('vendor', read(21, defense=165)), [unique(defense=140), unique(defense=160)])
    assert reason is not None
    assert reason.startswith('rolls better than the 2 owned: +165% Enhanced Defense vs 1')


def test_better_on_some_stats_and_worse_on_others_than_the_only_copy_is_kept():
    reason = keep_copy(BELT, Appraisal('vendor', read(21, defense=150, cold=15)), [unique(defense=170, cold=10)])
    assert reason == 'none of the 1 owned rolls as well on every stat: CR +15% vs 10'


def test_what_is_owned_unknown_keeps_it():
    assert keep_copy(BELT, Appraisal('vendor'), [unique()]) is not None
    assert keep_copy(BELT, Appraisal('vendor', read(21)), None) is not None


def test_neither_magic_nor_rare_items_nor_kept_verdicts_are_its_concern():
    for quality in (MAGIC, RARE):
        item = Carried(21, 391, 2, 0, (2, 1), quality)
        assert keep_copy(item, Appraisal('vendor', read(21)), []) is None
    for verdict in ('self', 'check', 'slow', 'sell', 'keep'):
        assert keep_copy(BELT, Appraisal(verdict, read(21)), []) is None


@pytest.fixture
def collection(tmp_path):
    """A collection with `captures` recorded in order, each (character, observations): the last plays."""
    database = tmp_path / 'collection.sqlite'

    def record(*captures: tuple[str, list[dict]]):
        for index, (character, observations) in enumerate(captures):
            sightings = [
                Sighting(item=ItemRecord.from_observation(o), location=Location.from_source(o['source'], character))
                for o in observations
            ]
            keys = sorted({s.location.key for s in sightings}, key=str)
            run = CaptureRun(id=f'c{index}', character=Character(name=character), containers=keys,
                             started_at=f'2026-10-18T00:0{index}:00Z')  # fmt: skip
            with CollectionStore(database) as store:
                store.record_capture(run, sightings)
        return database

    return record


def placed(observation: dict, page: int, x: int = 0) -> dict:
    observation['source'] |= {'container': {'page': page, 'name': 'Personal stash' if page == 4 else 'Inventory'},
                              'position': [x, 0]}  # fmt: skip
    return observation


def test_owned_copies_are_the_collections_less_the_playing_characters_inventory_and_cube(collection):
    mule = placed(unique(defense=140), 4)
    in_transit = placed(unique(defense=160, x=4), 0, 4)  # junk the loop carried at the capture, sold since
    in_cube = placed(unique(defense=161, x=6), 3, 6)
    stashed = placed(unique(defense=150, x=2), 4, 2)
    database = collection(('Mule', [mule]), ('Loop', [in_transit, in_cube, stashed]))

    found = owned_copies(read(21, defense=155), database)

    assert found is not None
    assert sorted(o['decoded_stats'][0]['value'] for o in found) == [140, 150]


def test_a_mules_inventory_counts_and_other_items_do_not(collection):
    other = placed(unique(name='Nosferatu', table_id=301, x=2), 4, 2)
    database = collection(('Mule', [placed(unique(), 0), other]), ('Loop', [placed(unique(defense=170, x=6), 0, 6)]))
    found = owned_copies(read(21), database)
    assert found is not None
    assert len(found) == 1


def test_no_collection_is_unknown(tmp_path):
    assert owned_copies(read(21), tmp_path / 'absent.sqlite') is None


def keep(directory, *observations):
    (directory / 'identified').mkdir(exist_ok=True)
    for index, observation in enumerate(observations):
        path = directory / 'identified' / f'{observation["source"]["unit_id"]}-{index}.json'
        path.write_text(json.dumps({'id': 'x', 'observation': observation}))


def test_the_visit_keeps_a_first_copy_out_of_the_junk_and_says_why(tmp_path, caplog):
    keep(tmp_path, read(21))
    caplog.set_level(logging.INFO)

    assert sold([BELT, RING], tmp_path, lambda observation: []) == [RING]
    assert 'Macro: copies: keep Snowclash (Battle Belt): the first copy' in caplog.text


def test_an_owned_copy_as_good_leaves_it_junk(tmp_path):
    keep(tmp_path, read(21, defense=150))
    assert sold([BELT, RING], tmp_path, lambda observation: [unique(defense=170)]) == [BELT, RING]


def test_two_copies_in_one_visit_keep_the_better_and_sell_the_other(tmp_path):
    worse = Carried(23, 391, 4, 1, (2, 1), UNIQUE)
    keep(tmp_path, read(21, defense=140), read(23, defense=165, cold=15))
    assert sold([BELT, worse], tmp_path, lambda observation: []) == [BELT]


def test_two_identical_low_value_set_amulets_keep_one_and_sell_the_duplicate(tmp_path):
    first = Carried(31, 520, 4, 0, (1, 1), SET)
    duplicate = Carried(32, 520, 5, 0, (1, 1), SET)
    observations = []
    for unit in (31, 32):
        item = read(unit)
        item['item'] |= {'rarity': 'set', 'name': "Civerb's Icon", 'base_name': 'Amulet'}
        item['decoded_stats'] = []  # the item's base properties have fixed rolls
        observations.append(item)
    keep(tmp_path, *observations)

    assert sold([first, duplicate], tmp_path, lambda observation: []) == [duplicate]


def test_outside_the_service_or_with_no_read_or_on_a_failure(tmp_path):
    assert sold([BELT, RING], None, lambda observation: []) == [BELT, RING]
    assert sold([BELT, RING], tmp_path, lambda observation: []) == [RING]  # no identify read: kept

    def broken(observation):
        raise RuntimeError('boom')

    keep(tmp_path, read(21))
    assert sold([BELT, RING], tmp_path, broken) == [RING]


def test_the_visit_stashes_a_first_copy_instead_of_selling_it(monkeypatch, caplog, tmp_path):
    # 15:05:53 on 2026-10-18: the loop's Kelpie Snare (a unique Fuscina, unit 40) was junk and sold; none was owned
    import inventory_tracking.macros.visitlog as visitlog
    from inventory_tracking.macros.visit import visit
    from tests.inventory_tracking.macros.test_town import pack_1505, view_1505
    from tests.inventory_tracking.macros.test_visit import LK_NEEDS, Exit, Town, fortress

    monkeypatch.setattr(visitlog, 'session_directory', lambda: tmp_path)
    monkeypatch.setattr('inventory_tracking.macros.copies.owned_copies', lambda observation: [])
    fuscina = read(40)
    fuscina['item'] |= {'name': 'Kelpie Snare', 'base_name': 'Fuscina'}
    keep(tmp_path, fuscina)
    pack, own, junk = pack_1505()
    stash = view_1505()
    play = fortress(pack, [p.rows for p in stash.pages])
    play.stacks = dict(stash.stacks)
    town = Town(monkeypatch, play, junk)
    town.run = play.run()

    with caplog.at_level('INFO'):
        visit(town.run, town.hands(), LK_NEEDS, own, Exit.WAYPOINT)

    assert 'Macro: copies: keep Kelpie Snare (Fuscina): the first copy' in caplog.text
    assert 40 not in town.sold
    assert all(40 not in offered for offered in town.offered)
    assert play.pack is not None
    assert 40 not in {i.unit_id for i in (*play.pack.items, *play.pack.in_cube)}  # stashed
