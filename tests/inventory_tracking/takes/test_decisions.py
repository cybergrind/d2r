"""Each look's decision told to the take (takes/decisions.py DECISION_EVENTS, 2026-10-23, realtime-3-findings.md)."""

import json

import pytest

from inventory_tracking.game.records import World
from inventory_tracking.takes import decisions
from inventory_tracking.takes.record import Recorder, Sample
from tests.inventory_tracking.macros.fakes import player


@pytest.fixture
def heard():
    found: list[dict] = []
    before = decisions.listen(found.append)
    yield found
    decisions.listen(before)


def test_with_the_switch_off_nothing_is_told(monkeypatch, heard):
    monkeypatch.setattr(decisions, 'DECISION_EVENTS', False)
    decisions.tell({'looked_at': 1.0, 'chosen': 'Move'})
    assert heard == []


def test_with_the_switch_on_each_decision_is_told_once(monkeypatch, heard):
    monkeypatch.setattr(decisions, 'DECISION_EVENTS', True)
    decisions.tell({'looked_at': 1.0, 'chosen': 'Move'})
    decisions.tell({'looked_at': 1.2, 'chosen': 'Strike', 'look': 'fight'})
    assert [d['chosen'] for d in heard] == ['Move', 'Strike']


def test_a_listener_that_raises_never_fails_the_look(monkeypatch):
    monkeypatch.setattr(decisions, 'DECISION_EVENTS', True)

    def broken(decision):
        raise RuntimeError('full')

    before = decisions.listen(broken)
    try:
        decisions.tell({'looked_at': 1.0})
    finally:
        decisions.listen(before)


def sample(state=None) -> Sample:
    world = World(True, (), 'game', (), player=player(area=108))
    return Sample(world, macro_state=state)


def recorded(tmp_path, monkeypatch, on: bool) -> list[dict]:
    monkeypatch.setattr(decisions, 'DECISION_EVENTS', on)
    clock = [10.0]
    shown = iter([sample({'decision': {'looked_at': 9.9, 'chosen': 'Hold'}}), sample(), sample()])
    recorder = Recorder(lambda: next(shown), output=tmp_path, areas=frozenset({108}), clock=lambda: clock[0])
    recorder.step(10.0)
    clock[0] = 10.05
    recorder.decided({'looked_at': 10.01, 'chosen': 'Move'})
    clock[0] = 10.08
    recorder.decided({'looked_at': 10.06, 'chosen': 'Strike', 'look': 'fight'})
    recorder.step(10.1)
    recorder.step(10.2)
    recorder.close('done')
    take = next(tmp_path.iterdir())
    rows = [json.loads(line) for line in (take / 'events.jsonl').read_text().splitlines()]
    return [row for row in rows if row['event'] == 'decision']


def test_on_the_take_has_each_told_decision_at_its_time_and_not_the_polled_one(tmp_path, monkeypatch):
    found = recorded(tmp_path, monkeypatch, True)
    assert [(row['t'], row['chosen']) for row in found] == [(10.05, 'Move'), (10.08, 'Strike')]


def test_off_the_take_has_the_polled_decision_as_before(tmp_path, monkeypatch):
    found = recorded(tmp_path, monkeypatch, False)
    assert [row['chosen'] for row in found] == ['Hold', 'Move', 'Strike']  # the told ones still noted when called


def test_a_fight_choice_is_told_as_a_strike_with_its_time_from_the_look(monkeypatch, heard):
    monkeypatch.setattr(decisions, 'DECISION_EVENTS', True)
    decisions.fight(20.0, 20.0123, 77, (5001.04, 4999.96))
    assert heard == [
        {'looked_at': 20.0, 'ms': 12.3, 'chosen': 'Strike', 'target': 77, 'focal': [5001.0, 5000.0], 'look': 'fight'}
    ]


def test_a_fight_choice_with_the_switch_off_is_not_told(monkeypatch, heard):
    monkeypatch.setattr(decisions, 'DECISION_EVENTS', False)
    decisions.fight(20.0, 20.01, 77, (5001.0, 5000.0))
    assert heard == []
