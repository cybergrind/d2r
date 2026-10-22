"""The Lower Kurast dance of game cyberg64 (2026-10-22 18:09:26-18:10:35, take 20261022T150918Z-79;
rca/2026-10-22/lk-dance-findings.md): a Hell Buzzard champion pack (monstats 112, vulture3) with Extra Fast, Mana Burn
and Spectral Hit held the loop 18 off its chests for 69 s with life 2930 of 2930 and mana 723-745 of 745. The looks
are the take's own (fixtures/lk_dance_cyberg64.json: those where the 2026-10-21 rules brought a hop).

- MANA_BUDGET (combat/threats/manaburn.py): an Extra Fast drainer outside a Herald's pack is priced, not kept by its
  Extra Fast alone;
- LOOP_IGNORES_IDLE (macros/safety.py): on the loop's run off a Terror Zone, unhurt, only the striking are kept;
- DANCE_BUDGET (macros/hunting/judging.py): DANCE_SECONDS of retreats and hops with no progress give the goal up."""

import json
import math
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from inventory_tracking.combat import harm as harm_model
from inventory_tracking.combat.survival import Pressure
from inventory_tracking.combat.threats import manaburn
from inventory_tracking.macros import safety as safety_module
from inventory_tracking.macros.hunting import judging
from inventory_tracking.macros.pursuit import Move


FIXTURE = Path(__file__).parents[1] / 'combat' / 'fixtures' / 'lk_dance_cyberg64.json'
LOOKS = json.loads(FIXTURE.read_text(encoding='utf-8'))['looks']
UNHURT = Pressure(1.0, 0.0, 0.0, 0.0)


def hostiles(look: dict) -> list[harm_model.Hostile]:
    return [
        harm_model.Hostile(unit, txt, (x, y), flags, tuple(mods), tier, level, life=share / 128, mode=mode)
        for unit, txt, x, y, flags, mods, tier, level, share, mode in look['hostiles']
    ]


def kept(look: dict, hs: list[harm_model.Hostile] | None = None, **kwargs) -> list[manaburn.Burner]:
    """The keep range's burners at a look as the safety's `kept_at_range` gets them, the take's mana safe."""
    hs = hs if hs is not None else hostiles(look)
    here, (life, most), (mana, pool) = tuple(look['here']), look['life'], look['mana']
    seen = harm_model.Look(tuple(hs), life=float(life))

    def priced(sel: list, place: tuple[float, float]) -> float:
        return harm_model.harm(replace(seen, hostiles=tuple(sel)), place, manaburn.THREAT_SECONDS, 'battle').mean

    found = manaburn.burners(hs)
    safe = mana >= manaburn.MANA_SAFE * pool
    return manaburn.threatening(
        here, hs, found, priced, life, life / most, 0.0, safe, mana - manaburn.RESERVE, **kwargs
    )


def test_the_pack_is_the_extra_fast_mana_burn_buzzards_and_every_look_kept_them_at_18(monkeypatch) -> None:
    monkeypatch.setattr(manaburn, 'MANA_BUDGET', False)
    assert len(LOOKS) == 6
    for look in LOOKS:
        found = kept(look)
        assert found  # as played
        assert all(b.keep == manaburn.FAST_KEEP for b in found)
        assert all(b.drains for b in found)
        assert manaburn.why_back(tuple(look['here']), found, []) is not None


def test_mana_budget_lets_the_harmless_buzzards_go_and_keeps_the_switch(monkeypatch) -> None:
    for look in LOOKS:
        assert kept(look) == [], look['at']  # priced: their 2 s forecast under 10% of 2930 and the mana's spare
    monkeypatch.setattr(manaburn, 'MANA_BUDGET', False)
    assert all(kept(look) for look in LOOKS)


def test_mana_budget_still_keeps_a_herald_pack_a_burn_and_a_forecast_past_the_spare() -> None:
    look = LOOKS[0]
    herald = [replace(h, tier=5) for h in hostiles(look)]
    assert kept(look, herald)  # a tier 5 Herald's drainers: kept whatever the forecast (DRAIN_GATE)
    hs = hostiles(look)
    here = tuple(look['here'])
    found = manaburn.burners(hs)
    assert manaburn.threatening(here, hs, found, lambda s, p: 0.0, 2930.0, 1.0, 0.0, False) == found  # a burn seen
    dear = manaburn.threatening(here, hs, found, lambda s, p: 200.0, 2930.0, 1.0, 0.0, True, 150.0)
    assert dear == found  # 200 burnt in 2 s against a spare of 150: kept
    assert manaburn.threatening(here, hs, found, lambda s, p: 400.0, 2930.0, 1.0, 0.0, True) == found  # life threat


def safety_kept(look: dict, rush: bool = True, felt: Pressure = UNHURT, hs=None) -> tuple:
    safety = safety_module.Safety()
    safety.mana_safe = True
    seen = harm_model.Look(tuple(hs if hs is not None else hostiles(look)), life=float(look['life'][0]))
    loot = SimpleNamespace(life=look['life'][0], max_life=look['life'][1])
    facts = SimpleNamespace(rush=rush, area=79)
    settings = harm_model.SafetySettings()
    here, mana = tuple(look['here']), look['mana'][0]
    return safety.kept_at_range(seen, here, settings, loot, felt, mana, facts)  # type: ignore[arg-type]


def test_the_loop_off_a_terror_zone_keeps_only_the_striking_while_unhurt(monkeypatch) -> None:
    monkeypatch.setattr(manaburn, 'MANA_BUDGET', False)  # the keep range as played, LOOP_IGNORES_IDLE alone
    monkeypatch.setattr(safety_module, 'terrorized', lambda area, hs=(): False)
    idle = LOOKS[0]
    calm = [replace(h, mode=1) for h in hostiles(idle)]
    assert safety_kept(idle, hs=calm) == ()  # none strikes: ignored
    near = min(calm, key=lambda h: math.dist(tuple(idle['here']), h.at))
    striking = [replace(h, mode=4) if h.unit == near.unit else h for h in calm]
    assert [b.unit for b in safety_kept(idle, hs=striking)] == [near.unit]  # the one that strikes: kept
    assert safety_kept(idle, hs=calm, felt=Pressure(0.98, 0.02, 0.0, 0.0))  # anything hurt: all kept
    assert safety_kept(idle, rush=False, hs=calm)  # not the loop's run (KP_1): kept
    monkeypatch.setattr(safety_module, 'terrorized', lambda area, hs=(): True)
    assert safety_kept(idle, hs=calm)  # a Terror Zone: kept
    monkeypatch.setattr(safety_module, 'terrorized', lambda area, hs=(): False)
    monkeypatch.setattr(safety_module, 'LOOP_IGNORES_IDLE', False)
    assert safety_kept(idle, hs=calm)


def hunter(**extra) -> SimpleNamespace:
    passed: list = []
    found = SimpleNamespace(
        dance=None,
        bearings=SimpleNamespace(progress=None, marks=None),
        known_level=lambda player: None,
        pass_by=lambda goal, why, now, rooms=(): passed.append((goal.label, why)),
        passed=passed,
    )
    for key, value in extra.items():
        setattr(found, key, value)
    return found


def goal(**fields) -> SimpleNamespace:
    base = {
        'label': 'Super chests',
        'place': (4900.0, 2492.0),
        'do': 'use',
        'unit': None,
        'stage': None,
        'mark': object(),
        'clearing': False,
    }
    base.update(fields)
    return SimpleNamespace(**base)


RETREAT = Move(None, None, "retreating: every progress act is vetoed (kept at range: a move into the pack's reach)")  # type: ignore[arg-type]
HOP = Move(None, None, 'pack: keeping range: mana burn: 1 of the pack on the character within 18')  # type: ignore[arg-type]


def test_the_dance_budget_skips_the_loops_chest_after_five_seconds_with_no_progress(monkeypatch) -> None:
    skipped: list = []
    monkeypatch.setattr(
        judging.route, 'note_empty', lambda run, mark, progress, marks, why='': skipped.append(why) or True
    )
    h, g = hunter(), goal()
    world = SimpleNamespace(monsters=[], player=None)
    posted = SimpleNamespace(rush=True)
    times = [0.0, 1.0, 2.5, 4.0, 4.9]  # 18:09:26.98 on: retreats and hops, nothing dies, the chest not opened
    for i, now in enumerate(times):
        assert not judging.no_progress(h, None, world, g, RETREAT if i % 2 else HOP, now, posted)  # type: ignore[arg-type]
    assert judging.no_progress(h, None, world, g, RETREAT, 5.1, posted)  # type: ignore[arg-type]
    assert skipped
    assert 'DANCE_BUDGET' in skipped[0]
    assert h.dance is None


def test_a_kill_or_a_new_goal_restarts_the_budget_and_bosses_and_drops_are_never_given_up(monkeypatch) -> None:
    monkeypatch.setattr(judging.route, 'note_empty', lambda *a, **k: True)
    posted = SimpleNamespace(rush=True)
    world = SimpleNamespace(monsters=[], player=None)
    h, g = hunter(), goal()
    judging.no_progress(h, None, world, g, HOP, 0.0, posted)  # type: ignore[arg-type]
    died = SimpleNamespace(monsters=[SimpleNamespace(unit_id=7, mode=12, ally=False)], player=None)
    assert not judging.no_progress(h, None, died, g, HOP, 4.0, posted)  # type: ignore[arg-type]  # a kill: restarts
    assert not judging.no_progress(h, None, died, g, HOP, 8.5, posted)  # type: ignore[arg-type]  # 4.5 s since
    assert judging.no_progress(h, None, died, g, HOP, 9.5, posted)  # type: ignore[arg-type]
    hit = [SimpleNamespace(unit_id=8, mode=1, ally=False, life=900)]
    judging.no_progress(h, None, SimpleNamespace(monsters=hit, player=None), g, HOP, 10.0, posted)  # type: ignore[arg-type]
    hit = [SimpleNamespace(unit_id=8, mode=1, ally=False, life=700)]  # damage dealt: restarts
    assert not judging.no_progress(h, None, SimpleNamespace(monsters=hit, player=None), g, HOP, 16.0, posted)  # type: ignore[arg-type]
    other = goal(place=(4867.0, 2532.0))  # the next chest: progress
    assert not judging.no_progress(h, None, world, other, HOP, 10.0, posted)  # type: ignore[arg-type]
    for kept_goal in (goal(do='pick up'), goal(do='fight', stage=SimpleNamespace(kind='fight'))):
        h = hunter()
        judging.no_progress(h, None, world, kept_goal, HOP, 0.0, posted)  # type: ignore[arg-type]
        assert not judging.no_progress(h, None, world, kept_goal, HOP, 30.0, posted)  # type: ignore[arg-type]


def test_a_tz_clearing_goal_is_passed_to_come_back_later_and_the_switch_turns_it_off(monkeypatch) -> None:
    world = SimpleNamespace(monsters=[], player=None)
    h, g = hunter(), goal(label='the elite 112', do='fight', unit=5, clearing=True, mark=None)
    judging.no_progress(h, None, world, g, HOP, 0.0, None)  # type: ignore[arg-type]
    assert judging.no_progress(h, None, world, g, RETREAT, 6.0, None)  # type: ignore[arg-type]
    assert h.passed
    assert h.passed[0][0] == 'the elite 112'
    monkeypatch.setattr(judging, 'DANCE_BUDGET', False)
    h = hunter()
    judging.no_progress(h, None, world, g, HOP, 0.0, None)  # type: ignore[arg-type]
    assert not judging.no_progress(h, None, world, g, HOP, 60.0, None)  # type: ignore[arg-type]


@pytest.mark.parametrize('reason', ['', 'toward Super chests', 'mana: leaving: mana 10 of 745'])
def test_other_moves_are_no_dance(reason: str) -> None:
    assert not judging.dancing(Move(None, None, reason))  # type: ignore[arg-type]
