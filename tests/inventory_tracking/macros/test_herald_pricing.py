"""The safety against a tier 5 Herald pack, priced on looks cut from take 20261021T063019Z-77
(rca/2026-10-21/herald-fight-findings.md): the look of 09:30:50.95 where the character fought out a pack that took 400
to 800 life a second (H-A), and two looks of the fight two minutes later that lost nothing (H-B), which stay fights.

Three pricing defects under the player's "fix it first" (2026-10-21 ~10:00), each behind its switch:
- combat/mechanics/life.py TIER_LIFE: a foe's life with its rank and Herald tier (the strikes were forecast to kill
  the T5 Herald and three minions in 0.36 s, so holding priced only 0.36 s of their blows);
- macros/safety.py DRAW_CASTABLE: holding is priced with the Death Mark draw only while the draw lands (its keys of the
  last seconds took on some monster); at 09:30:50.95 its three keys had taken on none and it was not cast again;
- macros/safety.py ESCAPE_SAME_SPAN: when nothing fits the budget, fighting out is weighed against the retreats over
  the same span (the escape horizon), not over its 0.72 s dwell against their whole way.

The looks are priced as the game prices them (hunting/judging.py `safety_priced`): the production observation, the
build's attack, settings, shield and draw, a Teleport in the battle hands; the navigator is a straight line.
"""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.combat import pack as herald_pack
from inventory_tracking.combat.mechanics import life
from inventory_tracking.combat.policy import observe
from inventory_tracking.combat.survival import CALM
from inventory_tracking.combat.threats import manaburn
from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.game.records import Loot, Monster
from inventory_tracking.macros import pursuit as p, safety as module
from inventory_tracking.macros.build import Step
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import STANDING
from tests.inventory_tracking.macros.fakes import player, world


FIXTURES = Path(__file__).parent / 'fixtures'
HERALD_A = 1966408054  # the tier 5 Herald of 09:30:41
NOW = 10.0
FULL_BELT = (1,) * 16  # a belt of potions: the price of life is the stocked one


def switches(monkeypatch, *, tier: bool, castable: bool, same_span: bool, tz: bool = True) -> None:
    """Stage A's switches; the Herald pack tactic (combat/pack.py, Stage B) off: these measure the pricing alone.
    `tz`: combat/mechanics/life.py TZ_LEVEL_LIFE (2026-10-21, after Stage A), off only to replay the game's decision."""
    monkeypatch.setattr(herald_pack, 'PACK_TACTIC', False)
    # Nor the packs kept at range (combat/threats/manaburn.py, 2026-10-21 ~16:30: H-A's Bramble Hulks are Extra Fast)
    monkeypatch.setattr(manaburn, 'FAST_RANGE', False)
    monkeypatch.setattr(manaburn, 'BURN_RANGE', False)
    monkeypatch.setattr(life, 'TIER_LIFE', tier)
    monkeypatch.setattr(life, 'TZ_LEVEL_LIFE', tz)
    monkeypatch.setattr(module, 'DRAW_CASTABLE', castable, raising=False)
    monkeypatch.setattr(module, 'ESCAPE_SAME_SPAN', same_span, raising=False)


def priced(name: str, safety: module.Safety | None = None) -> tuple[p.Act, dict]:
    """The act the safety (`safety`, a fresh one by default) and the arbiter choose at the cut look `name`, and the
    decision record."""
    snap = json.loads((FIXTURES / f'{name}.json').read_text(encoding='utf-8'))
    monsters = [
        Monster(
            m['unit'], m['txt'], m['mode'], m['x'], m['y'], m['owner'], flags=m['flags'], ally=m['ally'],
            life=m['life'], max_life=m['max_life'], modifiers=tuple(m['mods']), tier=m['tier'],
        )
        for m in snap['monsters']
    ]  # fmt: skip
    here = player(snap['area'], x=snap['player']['x'], y=snap['player']['y'])
    alive = world(snap['area'], player=here, monsters=tuple(monsters))
    foes = [m for m in monsters if not m.ally and m.owner == NO_OWNER]
    companions = [m for m in monsters if m.ally or m.owner != NO_OWNER]
    build = ECHOING_STRIKE_BUILD
    attack, settings = build.attack, build.settings.safety
    assert attack is not None
    seen = attack.sees(observe(here, foes, companions), companions)
    loot = Loot(
        life=snap['player']['life'],
        max_life=snap['player']['max_life'],
        stats=tuple((stat, value) for stat, value in snap['stats']),
        belt=FULL_BELT,
    )
    safety = safety if safety is not None else module.Safety()
    safety.draw_lands = snap['draw_lands']  # what the build's draw keys came to (macros/buffs.py `Buffs.lands`)
    look = safety.look(alive, loot, 'battle', seen.blocked, build.shield, settings, now=NOW, draw=build.draw)
    goal = Goal('the fight', seen.origin, 'fight', attack.reach, STANDING)
    facts = replace(
        p.Facts(NOW, goal, True, True, True, lambda: Step(goal.place), snap['area']), near=True, quiet=0.2, hurt=True
    )
    found = safety.price(
        facts, None, look, loot, CALM, settings, seen, attack, lambda point: Step(point),
        options=lambda point: (Step(point, TELEPORT), Step(point)), teleport_hands='battle',
    )  # fmt: skip
    return p.decide(found, None), safety.decision


def holds(decision: dict) -> list[dict]:
    return [c for c in decision['candidates'] if c['act'] == 'Hold']


def test_today_the_tanked_look_fights_out_as_the_game_did(monkeypatch) -> None:
    switches(monkeypatch, tier=False, castable=False, same_span=False, tz=False)
    monkeypatch.setattr(module, 'FLOOR_NO_CREDIT', False)  # the kill credit at the budget 0, as at 09:30 (2026-10-22)
    act, decision = priced('herald-t5-tanked')
    assert isinstance(act, p.Hold)
    assert act.reason == 'fighting out: less harm than any reachable retreat'
    assert decision['killed'][HERALD_A] == pytest.approx(0.36)  # the recorded decision's forecast
    assert holds(decision)[0]['H'] == pytest.approx(28.5, abs=1.0)  # and its price of holding


def test_with_the_three_fixes_the_tanked_look_teleports_out(monkeypatch) -> None:
    switches(monkeypatch, tier=True, castable=True, same_span=True)
    act, decision = priced('herald-t5-tanked')
    assert isinstance(act, p.Move), decision['candidates']
    assert act.reason.startswith('retreating')
    assert act.step.skill == TELEPORT


def test_the_tier_life_alone_forecasts_the_herald_alive_past_the_horizon(monkeypatch) -> None:
    switches(monkeypatch, tier=True, castable=False, same_span=False)
    _, decision = priced('herald-t5-tanked')
    assert HERALD_A not in decision['killed']
    assert all(at > 0.5 for at in decision['killed'].values())


def test_the_castable_draw_alone_prices_holding_without_a_draw_that_took_nowhere(monkeypatch) -> None:
    switches(monkeypatch, tier=False, castable=False, same_span=False)
    _, drawn = priced('herald-t5-tanked')
    switches(monkeypatch, tier=False, castable=True, same_span=False)
    _, undrawn = priced('herald-t5-tanked')
    assert holds(undrawn)[0]['H'] > 4 * holds(drawn)[0]['H']


def test_the_same_span_alone_weighs_fighting_out_over_the_escape_horizon(monkeypatch) -> None:
    switches(monkeypatch, tier=True, castable=True, same_span=False)
    _, short = priced('herald-t5-tanked')
    switches(monkeypatch, tier=True, castable=True, same_span=True)
    _, spanned = priced('herald-t5-tanked')
    fight_out = [c for c in spanned['candidates'] if c['act'] == 'Hold' and c['retreat']]
    before = [c for c in short['candidates'] if c['act'] == 'Hold' and c['retreat']]
    assert fight_out
    assert before
    assert fight_out[0]['H'] > 2 * before[0]['H']


@pytest.mark.parametrize('name', ['herald-t5-marking', 'herald-t5-held'])
def test_the_fight_that_lost_nothing_is_still_fought_with_the_three_fixes(monkeypatch, name: str) -> None:
    switches(monkeypatch, tier=True, castable=True, same_span=True)
    act, decision = priced(name)
    assert not (isinstance(act, p.Move) and act.reason.startswith('retreating')), decision['candidates']
    assert not (isinstance(act, p.Hold) and act.reason.startswith('fighting out')), act
