"""ARRIVAL_REACH (builds/warlock/echoing_strike/attack.py, 2026-10-25; rca/2026-10-25/strike-range-findings.md): no
line is laid through a monster walking out of the blades' reach before they meet it. The looks are the BloodLord of
take 20261024T211233Z-102 at 00:13:29 (rca/auto/2026-10-25/nodamage-001329-3636923668.md): the character stood at
(17512.5, 8079.5), the BloodLord walked away at ~5 units a second, 21.8 away at the look and 26.4 at the blades'
furthest; four casts, no blade hit."""

import math

import pytest

from inventory_tracking.builds.warlock.echoing_strike import attack as module
from inventory_tracking.builds.warlock.echoing_strike.attack import REACH, EchoingStrike
from inventory_tracking.combat.policy import Foe, Observation


HERE = (17512.5, 8079.5)  # the character, still through the volley
BLOOD_LORD = 3636923668
VAMPIRE4 = 134  # monstats.txt: the BloodLord's class
# The BloodLord's places in the take's frames at -0.295, -0.135 and -0.015 s of the look (25 frames a second)
WALKED = ((0, (17518.73, 8060.27)), (4, (17519.44, 8059.56)), (7, (17519.96, 8059.04)))
FIRST = 100  # a simulator's frame (Observation.frame) for the first look: the motion's clock


def flat(txt: int) -> float:
    return 1000.0


def looked(attack: EchoingStrike, places, rivals=None, elite=False) -> Observation:
    """The looks at `places` ((frame, point) of the BloodLord) with `rivals` standing, the last one returned."""
    seen = None
    for frame, at in places:
        foes = {BLOOD_LORD: Foe(VAMPIRE4, at, 5000.0, elite), **(rivals or {})}
        seen = attack.sees(Observation(HERE, foes, frame=FIRST + frame), [])
    assert seen is not None
    return seen


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setattr(module, 'ARRIVAL_REACH', True)


def test_the_take_blood_lord_is_in_reach_at_the_look_and_met_far_past_it(on) -> None:
    attack = EchoingStrike(damage_of=flat)
    seen = looked(attack, WALKED)
    at = seen.foes[BLOOD_LORD].at
    assert math.dist(HERE, at) == pytest.approx(21.78, abs=0.01)
    assert math.dist(HERE, at) <= REACH
    assert attack.meets(HERE, BLOOD_LORD, at) > REACH + module.ARRIVAL_SLACK  # ~27: the casts' 26.4
    assert not attack.reaches(HERE, BLOOD_LORD, at)
    assert attack.outrun(seen) == {BLOOD_LORD}


def test_alone_it_gets_no_line_with_the_switch_on_and_one_with_it_off(monkeypatch) -> None:
    monkeypatch.setattr(module, 'ARRIVAL_REACH', True)
    attack = EchoingStrike(damage_of=flat)
    assert attack.aim(looked(attack, WALKED)) is None
    monkeypatch.setattr(module, 'ARRIVAL_REACH', False)
    attack = EchoingStrike(damage_of=flat)
    found = attack.aim(looked(attack, WALKED))
    assert found is not None
    assert found.unit == BLOOD_LORD
    assert attack.outrun(looked(attack, WALKED)) == frozenset()


def test_with_a_monster_standing_in_reach_that_one_is_struck(on) -> None:
    rival = {7: Foe(VAMPIRE4, (HERE[0] - 15.0, HERE[1]), 5000.0)}
    attack = EchoingStrike(damage_of=flat)
    found = attack.aim(looked(attack, WALKED, rival))
    assert found is not None
    assert found.unit == 7


def test_standing_at_the_same_place_or_coming_on_it_is_struck(on) -> None:
    attack = EchoingStrike(damage_of=flat)
    last = WALKED[-1][1]
    standing = [(frame, last) for frame, _ in WALKED]
    found = attack.aim(looked(attack, standing))
    assert found is not None
    assert found.unit == BLOOD_LORD
    attack = EchoingStrike(damage_of=flat)
    coming = [(frame, at) for (frame, _), (_, at) in zip(WALKED, reversed(WALKED), strict=True)]
    seen = looked(attack, coming)
    assert attack.meets(HERE, BLOOD_LORD, seen.foes[BLOOD_LORD].at) == pytest.approx(
        math.dist(HERE, seen.foes[BLOOD_LORD].at)
    )
    found = attack.aim(seen)
    assert found is not None
    assert found.unit == BLOOD_LORD


def test_a_held_leader_walking_out_stays_held_while_the_best_line_is_struck(on) -> None:
    attack = EchoingStrike(damage_of=flat, hold=True)
    attack.held.unit = BLOOD_LORD
    rival = {7: Foe(VAMPIRE4, (HERE[0] - 15.0, HERE[1]), 5000.0)}
    found = attack.aim(looked(attack, WALKED, rival, elite=True))
    assert found is not None
    assert found.unit == 7
    assert attack.held.unit == BLOOD_LORD


def test_one_look_has_no_speed_and_nothing_is_held_back(on) -> None:
    attack = EchoingStrike(damage_of=flat)
    found = attack.aim(looked(attack, WALKED[-1:]))
    assert found is not None
    assert found.unit == BLOOD_LORD
