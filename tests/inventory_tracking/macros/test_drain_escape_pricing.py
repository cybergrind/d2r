"""The safety among mana-draining Dark Shapes (combat/threats/drain_escape.py MANA_ESCAPE; rca/2026-10-23/
death-manaburn-findings.md), priced on looks cut from take 20261023T155650Z-88 (Flayer Dungeon Level 1), the death of
18:57:45: a tier 5 Herald pack of Dark Shapes (monstats wraith5) with plain ones about, whose own blows burn mana.

- burnt, 18:57:37.65: a plain Dark Shape 2.0 off had just taken 468 of 745 mana; the plain ones were kept at no range;
- held, 18:57:39.0: 1.6 s after the burn, mana 283: the look held (Psychic Ward, a strike) with a Dark Shape on the
  character; the burn to 0 came 0.8 s later;
- no mana, 18:57:41.39: mana 0 after a Rejuvenation's 0.34 s of mana went unused.
The player: "we must not die or we lose exp and our gear" (2026-10-23).
"""

import json
import math

import pytest

from inventory_tracking.combat.threats import drain_escape, manaburn
from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.macros import pursuit as p, safety as module
from inventory_tracking.macros.skills import TELEPORT
from tests.inventory_tracking.macros.test_herald_pricing import FIXTURES, NOW, priced


DARK_SHAPE = 42  # monstats wraith5
BURNT = 468.0  # the blow of 18:57:37.4 (46.72 s of the take)


def drainers(name: str) -> tuple[tuple[float, float], list[tuple[float, float]]]:
    """The character's place and the live Dark Shapes' of a fixture."""
    snap = json.loads((FIXTURES / f'{name}.json').read_text(encoding='utf-8'))
    here = (snap['player']['x'], snap['player']['y'])
    found = [
        (m['x'], m['y'])
        for m in snap['monsters']
        if m['txt'] == DARK_SHAPE and m['life'] > 0 and not m['ally'] and m['owner'] == NO_OWNER
    ]
    return here, found


def remembering(seconds: float) -> module.Safety:
    """A safety that saw the take's burn `seconds` before the look."""
    safety = module.Safety()
    safety.burn_watch.burnt_at, safety.burn_watch.points = NOW - seconds, BURNT
    return safety


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setattr(drain_escape, 'MANA_ESCAPE', True)


def test_the_plain_dark_shape_on_the_character_is_hopped_from_only_with_the_switch(monkeypatch) -> None:
    monkeypatch.setattr(drain_escape, 'MANA_ESCAPE', False)
    act, _ = priced('darkshape-burnt-leave')
    assert isinstance(act, p.Hold)  # no burner: the plain ones carry no Mana Burn
    monkeypatch.setattr(drain_escape, 'MANA_ESCAPE', True)
    act, decision = priced('darkshape-burnt-leave')
    assert isinstance(act, p.Move), decision['candidates']
    assert act.step.skill == TELEPORT
    here, found = drainers('darkshape-burnt-leave')
    assert min(math.dist(here, d) for d in found) == pytest.approx(2.0, abs=0.1)
    assert min(math.dist(act.step.spot, d) for d in found) >= manaburn.keep_of(DARK_SHAPE, ())


def test_after_the_burn_the_leave_comes_first_and_lands_out_of_reach(on) -> None:
    act, decision = priced('darkshape-burnt-held', remembering(1.6))
    assert isinstance(act, p.Move), decision['candidates']
    assert act.reason.startswith(f'{manaburn.MANA_SAID}: ')
    assert drain_escape.BURN_SAID in act.reason
    assert act.step.skill == TELEPORT
    assert act.dodge
    here, found = drainers('darkshape-burnt-held')
    assert math.dist(here, act.step.spot) >= min(drain_escape.FAR_LENGTHS) - 1e-6
    assert min(math.dist(act.step.spot, d) for d in found) >= manaburn.keep_of(DARK_SHAPE, ()) + 6.0


def test_switched_off_the_held_look_holds_as_the_game_did(monkeypatch) -> None:
    monkeypatch.setattr(drain_escape, 'MANA_ESCAPE', False)
    act, _ = priced('darkshape-burnt-held', remembering(1.6))
    assert isinstance(act, p.Hold)


def test_with_no_mana_the_leave_walks_and_keeps_the_teleport_for_the_refill(on) -> None:
    safety = remembering(3.0)
    act, decision = priced('darkshape-no-mana', safety)
    assert isinstance(act, p.Move), decision['candidates']
    assert act.step.skill is None  # a walk: no mana for Teleport
    refill = safety.refill
    assert refill is not None
    assert getattr(refill.step, 'skill', None) == TELEPORT
    assert refill.fresh(NOW)
    assert not refill.fresh(NOW + drain_escape.REFILL_FRESH + 0.1)
