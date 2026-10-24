"""The pointer on a cast's target before the key (macros/buffs.py `onto`), from the Death Mark keys that did not take
on 2026-10-24 18:49-19:43 (rca/2026-10-24/dm-latency-findings.md §9): ONTO_TWICE (the hover record flickering
between the target and nothing) and ONTO_PACK_MEMBER (the hover naming another member of the pack after the nudges)."""

import logging
from dataclasses import replace

import pytest

from inventory_tracking.combat import pack
from inventory_tracking.macros import buffs as executor
from tests.inventory_tracking.macros.test_buffs import (
    ASPECT,
    BESIDE,
    BOLT_ROW,
    NEAR,
    due_now,
    game,
    hovering,
    key_names,
    plan,
    said,
)


TARGET = (1, NEAR.unit_id)
OTHER = (1, BESIDE.unit_id)


def cast(monkeypatch, *answers, twice=False, member=False, tier=0, first=True):
    """A cast of BOLT_ROW on NEAR with the hover record naming `answers` in turn; NEAR and BESIDE of a tier `tier`
    pack; `first`: the row's skill one of combat/pack.py FIRST. The play, the buffs, the reads."""
    monkeypatch.setattr(executor, 'ONTO_TWICE', twice)
    monkeypatch.setattr(executor, 'ONTO_PACK_MEMBER', member)
    monkeypatch.setattr(pack, 'FIRST', {BOLT_ROW.skill} if first else set())
    near, beside = replace(NEAR, tier=tier), replace(BESIDE, tier=tier)
    play = game(near, beside)
    row = replace(BOLT_ROW, shows=lambda words: False, shows_within=1.0)  # watched as Death Mark's row is
    buffs, run = plan(row), play.run()
    reads = hovering(run, *answers)
    due = due_now(buffs, run, row, buffs.facts(run, play.world, foes=[near]))
    tried = buffs.cast(run, due, key_names, ASPECT)
    assert tried.cast
    return play, buffs, reads


@pytest.mark.parametrize('twice', [False, True])
def test_a_flickering_record_waits_for_the_target_twice(monkeypatch, twice) -> None:
    # 18:52:06.537 (unit 3058085133): "-341:O -261:T +20:- +60:T +100:-": the key went down on a frame naming nothing
    # and the mark showed on no monster. Off: the first read naming nothing ends the check; on: two reads in a row
    # naming the target
    _play, _buffs, reads = cast(monkeypatch, None, TARGET, None, TARGET, TARGET, twice=twice)
    assert len(reads) == (5 if twice else 1)


def test_twice_moves_up_the_body_on_nothing_named(monkeypatch) -> None:
    aimed: list[tuple[float, float]] = []
    monkeypatch.setattr(executor, 'ONTO_TWICE', True)
    monkeypatch.setattr(executor, 'ONTO_PACK_MEMBER', False)
    play = game(NEAR, BESIDE)
    buffs, run = plan(BOLT_ROW), play.run()
    hovering(run, None, TARGET, TARGET)
    aim = run.actuator.aim

    def noted(x: float, y: float, *, scatter: tuple[int, int] = (4, 3), near: int = 0, bind=None) -> None:
        aimed.append((x, y))
        aim(x, y, scatter=scatter, near=near, bind=bind)

    run.actuator.aim = noted
    due = due_now(buffs, run, BOLT_ROW, buffs.facts(run, play.world, foes=[NEAR]))
    assert buffs.cast(run, due, key_names, ASPECT).cast
    assert len(aimed) == 2
    assert aimed[1][1] == pytest.approx(aimed[0][1] - executor.NUDGE_UP)


def test_twice_is_bounded_and_presses_anyway(monkeypatch, caplog) -> None:
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        play, _buffs, reads = cast(monkeypatch, None, twice=True)
    assert len(reads) == executor.NUDGES + 2 + executor.ONTO_EXTRA
    assert play.pressed()[0] == 'F6'  # the key (and QUICK_CONFIRM's press again, the row being watched)
    assert said(caplog, 'never the target twice')


@pytest.mark.parametrize(('member', 'tier', 'first', 'on_beside'), [
    (True, 5, True, True),  # the case: the pack's member named, the key goes on it
    (False, 5, True, False),  # off: nudged, pressed anyway, counted on the target
    (True, 0, True, False),  # no Herald pack
    (True, 5, False, False),  # not a FIRST skill
])  # fmt: skip
def test_pack_member_named_takes_the_key(monkeypatch, member, tier, first, on_beside) -> None:
    # 18:56:12.413 (the elite 501 3025243841): "the pointer names the monster 501 (2468909469), ... after 2 moves (the
    # cast goes on the unit under it): pressed anyway", the mark showed on a member of the same tier 5 pack
    _play, buffs, reads = cast(monkeypatch, OTHER, member=member, tier=tier, first=first)
    skill = BOLT_ROW.skill
    if on_beside:
        assert len(reads) == 1
        assert (skill, BESIDE.unit_id) in buffs.cast_at
        assert (skill, NEAR.unit_id) not in buffs.cast_at
        assert buffs.watching[skill][0] == BESIDE.unit_id
    else:
        assert len(reads) == executor.NUDGES + 1
        assert (skill, NEAR.unit_id) in buffs.cast_at
        assert buffs.retarget is None


def test_twice_with_the_pack_member(monkeypatch) -> None:
    _play, buffs, reads = cast(monkeypatch, None, OTHER, twice=True, member=True, tier=5)
    assert len(reads) == 2
    assert buffs.watching[BOLT_ROW.skill][0] == BESIDE.unit_id
