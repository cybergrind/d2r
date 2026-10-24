"""The gambled rings are judged by the one assessment entry point at GAMBLE (macros/gamble.py ASSESSED; loot/assess.py,
design.md §10.4 step 3). The player, 2026-10-23: "I want to have one place that decides pickups/value".

Gate: the same sell/keep per ring as the old call (loot/api.py `town_verdicts` over BOOK). Recorded: the 6 rings of
loot/fixtures/assess_replay.json here; 681 identified ring reads of 2026-10-20..23 by
rca/2026-10-23/scripts/assess_2b_gamble.py (673 sell, 8 keep, 0 differ). engine.py `protected` still refuses a sale
(D3: the action's guard, below any decision).
"""

import json
import logging
from pathlib import Path

import pytest

from inventory_tracking.game.records import Carried
from inventory_tracking.loot import assess, shadow as loot_shadow
from inventory_tracking.loot.assess import Assessor, BookAppraiser, TableCopies
from inventory_tracking.loot.facts import Where, base_of_code, from_observation
from inventory_tracking.loot.shadow import Appraised, Book
from inventory_tracking.macros import gamble
from inventory_tracking.macros.gamble import Judged, keep_rules
from tests.inventory_tracking.macros.test_gamble import MAGIC, GambleGame


REPLAY = Path(__file__).parents[1] / 'loot' / 'fixtures' / 'assess_replay.json'
RINGS = [read for read in json.loads(REPLAY.read_text())['reads'] if read['observation']['item']['base_code'] == 'rin']
QUALITIES = {'magic': 4, 'set': 5, 'rare': 6, 'unique': 7}


@pytest.fixture
def book(monkeypatch):
    found = Book()
    monkeypatch.setattr(loot_shadow, 'BOOK', found)  # the old call reads it at call time
    monkeypatch.setattr(assess, 'SHADOW_SAID', set())
    return found


def judged(book, read, on: bool, monkeypatch) -> Judged:
    unit = int(read['observation']['source']['unit_id'])
    book.put(unit, Appraised(read['observation'], read['result'], read['verdict']))
    owned = None if read['owned'] is None else [from_observation(copy, where=Where.STASH) for copy in read['owned']]
    monkeypatch.setattr(gamble, 'ASSESSED', on)
    known = base_of_code('rin')
    ring = Carried(
        unit, known[0] if known else 0, 0, 0, (1, 1), quality=QUALITIES[read['observation']['item']['rarity']]
    )
    judge = keep_rules(None, lambda: Assessor(BookAppraiser(book), TableCopies({}, owned)))
    return judge([ring])[unit]


def test_the_sample_holds_a_sold_ring_and_one_the_towns_guard_keeps():
    assert len(RINGS) == 6
    assert {read['expect']['town'] for read in RINGS} == {'sell', 'keep'}  # Nagelring: kept by `town_kept` (D1)


@pytest.mark.parametrize('read', [pytest.param(read, id=f'{n}-{read["title"]}') for n, read in enumerate(RINGS)])
def test_each_ring_is_sold_or_kept_as_the_old_call_did(read, book, monkeypatch):
    new, old = judged(book, read, True, monkeypatch), judged(book, read, False, monkeypatch)
    assert new.sell == old.sell == (read['expect']['town'] == 'sell'), (new.why, old.why)
    assert new.title == old.title
    assert new.why.startswith('sell: ' if new.sell else 'keep: ')
    assert new.stats == old.stats


def test_a_ring_with_no_read_is_kept_either_way(book, monkeypatch):
    ring = Carried(4242, gamble.RING, 3, 1, (1, 1), quality=MAGIC)
    for on in (True, False):
        monkeypatch.setattr(gamble, 'ASSESSED', on)
        verdict = keep_rules(None, lambda: Assessor(BookAppraiser(book), TableCopies({})))([ring])[4242]
        assert not verdict.sell, verdict.why


def test_a_difference_logs_one_shadow_line(book, monkeypatch, caplog):
    read = next(read for read in RINGS if read['expect']['town'] == 'keep')

    def sold(rings, copies):
        del copies
        return {ring.unit_id: Judged(ring.unit_id, True, 'x', 'sell') for ring in rings}

    monkeypatch.setattr(gamble, '_town_judged', sold)
    with caplog.at_level(logging.INFO):
        verdict = judged(book, read, True, monkeypatch)
    assert not verdict.sell  # the entry point decides
    [line] = [r.message for r in caplog.records if 'assess: gamble' in r.message]
    assert line.endswith('new keep / old sell (new decides)')


def test_protected_still_refuses_a_ring_the_rules_sell(monkeypatch):
    # D3: engine.py `protected` guards the sale below any decision (the player's item by its print)
    monkeypatch.setattr(gamble, 'RINGS_MOST', 2)
    play = GambleGame(carried=950_000, bank=2_500_000, free=8)
    run = play.run()
    first: list[int] = []

    def players(item: Carried) -> bool:
        first.append(item.unit_id) if not first else None
        return item.unit_id == first[0]

    run.players_item = players

    def sell_all(rings):
        return {r.unit_id: Judged(r.unit_id, True, 'magic Ring', 'sell: K8 worthless') for r in rings}

    done = gamble.gamble(run, sell_all)
    assert done.bought == 2
    assert done.sold == 1
    assert [r.unit_id for r in play.rings()] == [first[0]]
