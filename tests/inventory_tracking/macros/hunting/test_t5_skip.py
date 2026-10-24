"""T5_SKIP (macros/hunting/judging.py, 2026-10-23; the player ~20:35 of a tier 5 Herald pack the safety refuses every
spot near: "Skip it (Recommended)"): the first safety retreat with no spot kept in strike reach from a goal of a tier 5
Herald's pack gives the goal up, the whole pack passed; a tier 4 pack, a retreat that keeps a spot, a dodge or a kept
goal are no skip."""

from typing import TYPE_CHECKING, cast

import pytest

from inventory_tracking.macros.goals import PICK_UP, Goal
from inventory_tracking.macros.hunting import judging
from inventory_tracking.macros.pursuit import KEEPING, Move
from inventory_tracking.macros.travel import PRESSED, Step
from inventory_tracking.routes.model import FIGHT
from tests.inventory_tracking.macros.test_hunt import foe, game, hunter


if TYPE_CHECKING:
    from inventory_tracking.macros.engine import Run


HERALD = 3167950388  # the canyon's tier 5 Hell Slinger Herald (take 20261023T115109Z-46)
CANYON = (12652.0, 5328.0)
HERALD_FLAGS = 0x08  # a unique


def pack(tier: int):
    return (
        foe(HERALD, *CANYON, flags=HERALD_FLAGS, txt_id=376, life=120, max_life=128, tier=tier),
        *(foe(791979405 + n, CANYON[0] + 3.0 + n, CANYON[1] + 2.0, txt_id=376, tier=tier) for n in range(5)),
    )


def run_of(monkeypatch, tier: int = 5, *, switch: bool = True):
    monkeypatch.setattr(judging, 'T5_SKIP', switch)
    play = game(*pack(tier))
    return play, hunter(play)


def goal() -> Goal:
    return Goal('full clear: the elite 376 (3167950388): clearing the way (15 near)', CANYON, FIGHT, 22.0, PRESSED,
                unit=HERALD, clearing=True)  # fmt: skip


def retreat(reason: str = 'retreating: no progress act fits the life budget', *, dodge: bool = False) -> Move:
    return Move(Step((12630.0, 5345.0)), goal(), reason, dodge=dodge)


@pytest.mark.parametrize(('tier', 'switch', 'fires'), [(5, True, True), (4, True, False), (5, False, False)])
def test_the_first_refusal_by_a_tier_5_pack_skips_it(monkeypatch, tier, switch, fires) -> None:
    play, hunted = run_of(monkeypatch, tier, switch=switch)
    said = judging.t5_refused(hunted, play.world, goal(), retreat(), 9.0)
    assert (said is not None) is fires
    if said is not None:
        assert '(T5_SKIP)' in said
        assert 'pack of 6' in said


def test_a_retreat_that_keeps_a_spot_a_dodge_or_a_kept_goal_is_no_skip(monkeypatch) -> None:
    play, hunted = run_of(monkeypatch)
    assert judging.t5_refused(hunted, play.world, goal(), retreat(KEEPING), 9.0) is None
    assert judging.t5_refused(hunted, play.world, goal(), retreat('retreating: stepping out', dodge=True), 9.0) is None
    drop = Goal('Flawless Ruby', CANYON, PICK_UP, 2.0, PRESSED, unit=99)
    assert (
        judging.t5_refused(hunted, play.world, drop, Move(Step((12630.0, 5345.0)), drop, 'retreating: x'), 9.0) is None
    )


def test_no_skip_while_the_fight_kills(monkeypatch) -> None:
    """A member seen dead within T5_QUIET: the fight still kills, no skip; past it, the skip."""
    from dataclasses import replace

    play, hunted = run_of(monkeypatch)
    assert judging.t5_refused(hunted, play.world, goal(), retreat(), 9.0) is not None  # nothing died: skip
    first = play.world.monsters[1]
    dead = replace(play.world, monsters=(play.world.monsters[0], replace(first, mode=0), *play.world.monsters[2:]))
    assert judging.t5_refused(hunted, dead, goal(), retreat(), 10.0) is None  # a kill now
    assert judging.t5_refused(hunted, dead, goal(), retreat(), 10.0 + judging.T5_QUIET / 2) is None
    assert judging.t5_refused(hunted, dead, goal(), retreat(), 10.0 + judging.T5_QUIET + 0.1) is not None


def test_the_skipped_pack_is_passed_whole(monkeypatch, caplog) -> None:
    play, hunted = run_of(monkeypatch)
    caplog.set_level('INFO')
    run = cast('Run', None)  # read only on the KP_6 loop's rushed run
    assert judging.no_progress(hunted, run, play.world, goal(), retreat(), 9.0, None)
    assert 'skipping the tier 5 Herald pack of 6' in caplog.text
    members = {m.unit_id for m in play.world.monsters if m.tier == 5}
    assert members <= set(hunted.passed)
    assert all(hunted.passed[unit] >= 9.0 + judging.KNOT_AGAIN_SECONDS for unit in members)
