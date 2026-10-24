"""Real reads through the one assessment entry point (inventory_tracking/loot/assess.py): a recorded subset of the
identified items of 2026-10-21..23 (fixtures/assess_replay.json, frozen by
rca/2026-10-23/scripts/assess_replay_freeze.py from the study's replay, rca/2026-10-23/scripts/assess_replay.py: 1118
reads, 0 differ at the field and the town). Each
read holds its KB triage (offline, trimmed), the identify verdict and the owned copies as the collection held them at
its capture, and what the callers decided at the freeze (keep.py `decide_all`, api.py `town_kept`, `droppable`).

The coordinator, 2026-10-23: "Turn the replay into a regression test. Keep the fixtures small, or use a recorded
subset." A difference here is a change of the live rules (the callers' functions) or of the entry point: either says
which in its message.
"""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from inventory_tracking.game.records import Carried, Pack
from inventory_tracking.loot import api
from inventory_tracking.loot.api import droppable, town_kept
from inventory_tracking.loot.assess import (
    NEVER_TRASH,
    Assessor,
    BookAppraiser,
    FakeAppraiser,
    Outcome,
    Site,
    TableCopies,
)
from inventory_tracking.loot.facts import SET, UNIQUE, ItemFacts, Owner, Where, from_observation
from inventory_tracking.loot.keep import decide_all
from inventory_tracking.loot.shadow import Appraised, Book
from inventory_tracking.loot.value import Value, appraise_result


FIXTURE = Path(__file__).parent / 'fixtures' / 'assess_replay.json'
READS = json.loads(FIXTURE.read_text())['reads']


def judged(read: dict[str, Any]) -> tuple[ItemFacts, Value, list[ItemFacts] | None]:
    facts = from_observation(read['observation'], where=Where.INVENTORY, owner=Owner.LOOP, txt=read['txt'],
                             size=(read['size'][0], read['size'][1]))  # fmt: skip
    value = appraise_result(facts, read['result'], read['verdict'])
    owned = None if read['owned'] is None else [from_observation(copy, where=Where.STASH) for copy in read['owned']]
    return facts, value, owned


def reads() -> list:
    return [pytest.param(read, id=read['id']) for read in READS]


def test_the_sample_covers_the_rules_that_give_up_and_the_guards():
    rules = {(read['expect']['keep'].split()[0], read['expect']['keep'].split()[1]) for read in READS}
    assert {('drop', 'K4'), ('drop', 'K6'), ('drop', 'K7'), ('drop', 'K8'), ('keep', 'K4'), ('keep', 'K6')} <= rules
    guarded = [read for read in READS if read['expect']['keep'].startswith('drop')]
    assert any(read['expect']['town'] == 'keep' for read in guarded)  # D1: the town keeps a give-up
    assert any(read['expect']['field'] == 'keep' for read in guarded)  # D2: the field keeps a give-up
    assert len(READS) <= 60  # small: a recorded subset


@pytest.mark.parametrize('read', reads())
def test_the_callers_still_decide_as_they_did(read):
    """keep.py, api.py `town_kept` and `droppable` on the read as at the freeze."""
    facts, value, owned = judged(read)
    [(_, _, decision)] = decide_all([(facts, value)], lambda _facts: owned)
    expect = read['expect']
    assert decision.said().split()[:2] == expect['keep'].split()[:2], f'{read["title"]}: {decision.said()}'
    town = town_kept(facts, value, decision, owned)
    assert (town is None) == (expect['town'] == 'sell'), f'{read["title"]}: {town}'
    named = facts.quality in (SET, UNIQUE)
    field = droppable(facts, value, owned if named else None) if decision.gives_up else 'not given up'
    assert (field is None) == (expect['field'] == 'drop'), f'{read["title"]}: {field}'


@pytest.mark.parametrize('read', reads())
def test_the_entry_point_decides_as_the_callers(read):
    facts, value, owned = judged(read)
    assessor = Assessor(FakeAppraiser({facts.unit_id: value}), TableCopies({}, owned))
    expect = read['expect']
    field = assessor.assess(facts, Site.FIELD)
    assert (field.outcome == Outcome.DROP) == (expect['field'] == 'drop'), field.said()
    for site in (Site.TOWN, Site.CARD, Site.GAMBLE):
        found = assessor.assess(facts, site)
        assert (found.outcome == Outcome.VENDOR) == (expect['town'] == 'sell'), found.said()
        assert found.rule != NEVER_TRASH, found.said()
    assert field.rule != NEVER_TRASH, field.said()


class ReplayHands:
    """The field routine's hands over one replayed read: the item carried identified, its appraisal, its owned copies,
    the drop at the feet recorded (api.py `FieldHands`, the parts `Field._judge` asks)."""

    def __init__(self, read: dict[str, Any]) -> None:
        self.read, self.dropped = read, []
        unit = read['observation']['source'].get('unit_id') or 7
        self.unit = int(unit)
        quality = from_observation(read['observation'], where=Where.INVENTORY, owner=Owner.LOOP).quality
        size = (read['size'][0], read['size'][1])
        self.item = Carried(self.unit, read['txt'], 0, 0, size, quality, identified=True)
        self.owned = None if read['owned'] is None else [from_observation(c, where=Where.STASH) for c in read['owned']]

    def carried(self) -> Pack:
        return Pack(items=(self.item,))

    def loops(self, pack: Pack) -> list[Carried]:
        return list(pack.items)

    def appraise(self, units) -> dict[int, Appraised]:
        read = self.read
        return {self.unit: Appraised(read['observation'], read['result'], read['verdict'])}

    def copies(self, facts: ItemFacts) -> list[ItemFacts] | None:
        return self.owned

    def drop(self, item: Carried, why: str) -> bool:
        self.dropped.append((item.unit_id, why))
        return True

    def reject(self, item: Carried, why: str) -> None:
        del item, why


@pytest.mark.parametrize('read', reads())
def test_the_field_routine_decides_the_same_through_the_entry_point(read, monkeypatch):
    """api.py `Field._judge` with ASSESS_FIELD on and off on each real read: the same decision, the same drop, the same
    words at the feet (the gate of the switch, 2026-10-23)."""
    found = {}
    for assessed in (True, False):
        monkeypatch.setattr(api, 'ASSESS_FIELD', assessed)
        hands = ReplayHands(read)
        field = api.Field(log=lambda *args: None)
        judged = field._judge(hands, [hands.unit], 'game-1')  # pyrefly: ignore[bad-argument-type]  a partial fake
        found[assessed] = ([(j.decision, j.dropped) for j in judged], hands.dropped, dict(field.judged))
    assert found[True] == found[False], read['title']
    assert bool(found[True][1]) == (read['expect']['field'] == 'drop'), read['title']


def visit_of(selected: list[dict[str, Any]]) -> tuple[list[Carried], Book, TableCopies]:
    """The reads carried together in one town visit (units 1..n), the identify worker's book of them and their owned
    copies by unit."""
    book, carried, owned = Book(), [], {}
    for unit, read in enumerate(selected, 1):
        hands = ReplayHands(read)
        carried.append(replace(hands.item, unit_id=unit))
        book.put(unit, Appraised(read['observation'], read['result'], read['verdict']))
        owned[unit] = hands.owned
    return carried, book, TableCopies(owned)


def town_both(selected: list[dict[str, Any]]) -> tuple[tuple, tuple]:
    from inventory_tracking.macros.visit import town_assessed

    carried, book, copies = visit_of(selected)
    old_kept: dict[int, tuple[str, str]] = {}
    old = api.town_sold(carried, frozenset(), book, copies, old_kept)
    new_kept: dict[int, tuple[str, str]] = {}
    new = town_assessed(carried, new_kept, Assessor(BookAppraiser(book), copies))
    return (new, new_kept), (old, old_kept)


@pytest.mark.parametrize('read', reads())
def test_the_town_visit_sells_the_same_through_the_entry_point(read):
    """macros/visit.py `town_assessed` (ASSESS_TOWN) against api.py `town_sold` on each real read: the same sales, the
    same words, the same give-ups kept by a town guard (the gate of the switch, 2026-10-23)."""
    new, old = town_both([read])
    assert new == old, read['title']
    assert bool(new[0]) == (read['expect']['town'] == 'sell'), read['title']


def test_the_town_visit_sells_the_same_when_the_reads_are_carried_together():
    """All the reads in one visit (the best rolled first: a copy kept counts as owned for the next), and in reverse."""
    for selected in (READS, list(reversed(READS))):
        new, old = town_both(selected)
        assert new == old
