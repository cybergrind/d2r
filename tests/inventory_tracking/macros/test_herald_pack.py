"""The safety's hop back from a tier 4-5 Herald pack (macros/safety.py `Safety.pack_back`, combat/pack.py; the player's
rulings of 2026-10-21 ~10:00: "a Teleport back when anything is within 10", "surrounded: out with the demon between,
up to 3 times a pack"). The looks are the fixtures of test_herald_pricing.py, cut from take 20261021T063019Z-77
(rca/2026-10-21/herald-fight-findings.md): H-A tanked at 09:30:50.95; H-B, the pack on the demons, lost nothing."""

import json
import math
from dataclasses import replace

import pytest

from inventory_tracking.combat import pack
from inventory_tracking.combat.harm import Harm, Hostile
from inventory_tracking.combat.threats import manaburn
from inventory_tracking.macros import pursuit as p, safety as module
from inventory_tracking.macros.build import Step
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.hunting.base import OMEN_STAND, omen_distance
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import STANDING
from tests.inventory_tracking.macros.test_herald_pricing import FIXTURES, priced


def the_pack(name: str) -> tuple[tuple[float, float], list[pack.Member], tuple[float, float]]:
    """The character's place, the pack and the Defiler's place of a fixture."""
    snap = json.loads((FIXTURES / f'{name}.json').read_text(encoding='utf-8'))
    here = (snap['player']['x'], snap['player']['y'])
    hostiles = [
        Hostile(m['unit'], m['txt'], (m['x'], m['y']), m['flags'], tier=m['tier'])
        for m in snap['monsters']
        if not m['ally'] and m['owner'] == 0xFFFFFFFF
    ]
    defiler = next((m['x'], m['y']) for m in snap['monsters'] if m['txt'] == 744)
    return here, pack.members(hostiles), defiler


def hops(decision: dict) -> list[dict]:
    return [c for c in decision['candidates'] if c['why'].startswith(pack.BACK_SAID)]


@pytest.fixture(autouse=True)
def herald_tactic_alone(monkeypatch) -> None:
    """The Herald pack tactic alone: H-A's Bramble Hulks are Extra Fast, which the Extra Fast range keeps at 18 since
    2026-10-21 ~16:30 (combat/threats/manaburn.py FAST_RANGE; its test is the last of this file)."""
    monkeypatch.setattr(manaburn, 'FAST_RANGE', False)


def test_the_tanked_look_teleports_back_into_range_with_the_defiler_between() -> None:
    act, decision = priced('herald-t5-tanked')
    assert isinstance(act, p.Move), decision['candidates']
    assert act.reason.startswith(f'{pack.BACK_SAID}: surrounded')
    assert act.step.skill == TELEPORT
    assert act.dodge  # out of the strike gap (I2)
    here, members, defiler = the_pack('herald-t5-tanked')
    landing = act.step.spot
    assert pack.PACK_RANGE[0] <= math.dist(landing, pack.centre(here, members)) <= pack.PACK_RANGE[1]
    assert all(math.dist(landing, m.at) >= pack.PACK_BACK for m in members)
    assert pack.between(landing, members, defiler, here)


def test_the_looks_with_the_pack_on_the_demons_price_no_hop_and_still_fight() -> None:
    for name in ('herald-t5-marking', 'herald-t5-held'):
        act, decision = priced(name)
        assert not hops(decision), name
        assert not (isinstance(act, p.Move) and act.reason.startswith('retreating')), name
        assert not (isinstance(act, p.Hold) and act.reason.startswith('fighting out')), name


def test_a_pack_is_hopped_out_of_three_times_then_the_plain_safety_decides() -> None:
    safety = module.Safety()
    for count in range(1, pack.PACK_HOPS + 1):
        act, _ = priced('herald-t5-tanked', safety)
        assert isinstance(act, p.Move)
        assert act.reason.startswith(pack.BACK_SAID)
        assert sum(safety.pack_hops.values()) == count
    act, decision = priced('herald-t5-tanked', safety)
    assert not hops(decision)
    assert isinstance(act, p.Move)
    assert act.reason.startswith('retreating')  # Stage A's retreat (rca/2026-10-21/herald-fight-findings.md §5)


def test_with_the_keep_range_off_the_tanked_look_retreats_as_in_stage_a(monkeypatch) -> None:
    monkeypatch.setattr(pack, 'PACK_KEEP_RANGE', False)
    act, decision = priced('herald-t5-tanked')
    assert not hops(decision)
    assert isinstance(act, p.Move)
    assert act.reason.startswith('retreating')


def candidate(act: p.Act, mean: float, barred: str | None = None) -> p.Candidate:
    return p.Candidate(act, 1.0, Harm(mean, mean, barred=barred), unstruck=0.3 if isinstance(act, p.Move) else 0.0)


def test_the_arbiter_takes_a_hop_back_over_a_cheaper_hold_unless_it_is_vetoed() -> None:
    goal = Goal('the fight', (0.0, 0.0), 'fight', 20.0, STANDING)
    hop = p.Move(Step((-16.0, 0.0), TELEPORT), goal, f'{pack.BACK_SAID}: surrounded', dodge=True)
    hold = p.Hold(goal)
    facts = p.Facts(0.0, goal, True, True, True, lambda: Step(goal.place), priced=True, budget=1000.0, life=2000.0)
    assert p.arbitrate(replace(facts, candidates=(candidate(hold, 1.0), candidate(hop, 50.0)))) is hop
    vetoed = (candidate(hold, 1.0), candidate(hop, 50.0, barred='lethal'))
    assert isinstance(p.arbitrate(replace(facts, candidates=vetoed)), p.Hold)


def test_the_omen_stand_is_24_with_the_pack_tactic_and_20_without(monkeypatch) -> None:
    assert omen_distance() == pack.PACK_OMEN_STAND == 24.0
    monkeypatch.setattr(pack, 'PACK_OMEN', False)
    assert omen_distance() == OMEN_STAND == 20.0


def test_with_the_extra_fast_range_the_tanked_look_teleports_out_of_18_from_every_hulk(monkeypatch) -> None:
    # The player, 2026-10-21 ~16:30: "Yes, 18 for Extra Fast" (H-A's Bramble Hulks: mods 28, 8, 6, no Mana Burn)
    monkeypatch.setattr(manaburn, 'FAST_RANGE', True)
    act, decision = priced('herald-t5-tanked')
    assert isinstance(act, p.Move), decision['candidates']
    assert act.reason.startswith(f'{pack.BACK_SAID}: {manaburn.FAST_SAID}: surrounded')
    assert act.step.skill == TELEPORT
    assert act.dodge
    _, members, _ = the_pack('herald-t5-tanked')
    assert all(math.dist(act.step.spot, m.at) >= manaburn.FAST_KEEP for m in members)
