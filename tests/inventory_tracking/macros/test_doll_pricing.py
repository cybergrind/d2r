"""The safety and the goals among exploding dolls, on looks cut from take 20261021T103011Z-101 (Durance of Hate Level
2, Extra Fast; rca/2026-10-21/dolls-tz-findings.md §1.2):

- `dolls-firing-spot`, 13:32:03.37: "a group of 7: clearing the way", the hold barred (a doll 4.5 off), a firing spot
  hop taken that landed 12.2 from the nearest live doll; a doll died 2.2 off 0.9 s later (502 life);
- `dolls-ort-rune`, 13:31:02.33: "Ort Rune, on the way", a firing spot hop onto the rune that landed 11.7-12.6 from
  four full-life dolls; three died at 2.2-5.0 0.73 s later (1281 life).

Each switch of combat/threats/dolls.py on and off: DOLL_LAND (F2) in the safety's prices, DOLL_GUARD (F1) in the
goals. The looks are priced as test_herald_pricing.py prices its own (the production observation, the build's attack,
settings, shield and draw; a straight-line navigator).
"""

import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.combat import pack as herald_pack
from inventory_tracking.combat.policy import observe
from inventory_tracking.combat.survival import CALM
from inventory_tracking.combat.threats import dolls
from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.game.records import HEALING, VALUABLE, Drop, Loot, Monster
from inventory_tracking.macros import goals, pursuit as p, safety as module
from inventory_tracking.macros.build import Step
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import PRESSED
from tests.inventory_tracking.macros.fakes import player, world


FIXTURES = Path(__file__).parent / 'fixtures'
NOW = 10.0
FULL_BELT = (1,) * 16
FIRING_LANDED = (18043.5, 6771.5)  # where the hop of 13:32:03.48 landed
RUNE = (17908.0, 6900.0)  # the Ort Rune (the look's goal place)
RUNE_LANDED = (17904.5, 6906.5)


def snapshot(name: str) -> tuple[dict, list[Monster]]:
    snap = json.loads((FIXTURES / f'{name}.json').read_text(encoding='utf-8'))
    monsters = [
        Monster(
            m['unit'], m['txt'], m['mode'], m['x'], m['y'], m['owner'], flags=m['flags'], ally=m['ally'],
            life=m['life'], max_life=m['max_life'], modifiers=tuple(m['mods']), tier=m['tier'],
        )
        for m in snap['monsters']
    ]  # fmt: skip
    return snap, monsters


def scene(
    here: tuple[float, float], dolls_at: list[tuple[float, float]], life: int = 2894
) -> tuple[dict, list[Monster]]:
    """A look of the firing-spot cut's character (its stats) with Extra Fast Undead Stygian Dolls at `dolls_at`."""
    snap, _ = snapshot('dolls-firing-spot')
    snap = {**snap, 'player': {**snap['player'], 'x': here[0], 'y': here[1], 'life': life}}
    monsters = [
        Monster(100 + i, 216, 1, x, y, life=128, max_life=128, modifiers=(6,)) for i, (x, y) in enumerate(dolls_at)
    ]
    return snap, monsters


def priced(name, goal_of, step: Step | None, *, safety: module.Safety | None = None, now: float = NOW, attacking=True):
    """The act and decision record the safety and the arbiter make at the cut look `name` (or a `scene`) for the goal
    `goal_of(here)` asked by a level run's Move to `step` (None: no way: the goal is in reach)."""
    snap, monsters = snapshot(name) if isinstance(name, str) else name
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
    look = safety.look(alive, loot, 'battle', seen.blocked, build.shield, settings, now=now, draw=build.draw)
    goal = goal_of(seen.origin)
    in_reach = any(math.dist(seen.origin, f.at) <= attack.reach for f in seen.foes.values())
    way = (lambda: step) if step is not None else (lambda: p.NoWay('there', arrived=True))
    facts = replace(p.Facts(now, goal, False, in_reach, attacking, way, snap['area']), near=in_reach, quiet=0.2)
    posted = p.Pursuit('pickup', now - 5.0, advance=False, leash=p.FULL, area=snap['area'])
    found = safety.price(
        facts, posted, look, loot, CALM, settings, seen, attack, lambda point: Step(point, TELEPORT),
        options=lambda point: (Step(point, TELEPORT), Step(point)), teleport_hands='battle',
    )  # fmt: skip
    return p.decide(found, posted), safety.decision


def group(here) -> Goal:
    return Goal('full clear: a group of 7: clearing the way (1 near)', FIRING_LANDED, 'fight', 20.0, PRESSED,
                unit=1, clearing=True)  # fmt: skip


def rune(here) -> Goal:
    return Goal('Ort Rune, on the way', RUNE, goals.PICK_UP, goals.PICK_REACH, PRESSED, unit=2)


def landings(decision: dict, near: tuple[float, float], within: float = 3.0) -> list[dict]:
    return [c for c in decision['candidates'] if c['act'] == 'Move' and math.dist(c['place'], near) <= within]


def switches(monkeypatch, *, land: bool, guard: bool = True) -> None:
    monkeypatch.setattr(herald_pack, 'PACK_TACTIC', False)
    monkeypatch.setattr(dolls, 'DOLL_LAND', land)
    monkeypatch.setattr(dolls, 'DOLL_GUARD', guard)


def test_the_cut_looks_hold_what_the_take_shows() -> None:
    snap, monsters = snapshot('dolls-ort-rune')
    here = (snap['player']['x'], snap['player']['y'])
    near = sorted(math.dist(RUNE_LANDED, (m.x, m.y)) for m in monsters if dolls.runner(m.txt_id))
    assert near[:4] == pytest.approx([12.0, 12.0, 12.5, 12.6], abs=0.1)
    assert all(6 in m.modifiers for m in monsters if dolls.runner(m.txt_id))  # Extra Fast, the zone's effect
    assert min(math.dist(here, (m.x, m.y)) for m in monsters if dolls.runner(m.txt_id)) > dolls.CLOSE_UNITS


@pytest.mark.parametrize('land', [False, True])
def test_f2_the_hop_onto_the_rune_beside_four_fresh_dolls(monkeypatch, land: bool) -> None:
    """The landing of 13:31:02.6 on the rune, 12.0-12.6 from five idle Extra Fast dolls: barred with DOLL_LAND (20
    under Extra Fast), priced as before without. The look holds what is in reach either way (a doll at 14.1)."""
    switches(monkeypatch, land=land, guard=False)
    act, decision = priced('dolls-ort-rune', group, Step(RUNE_LANDED, TELEPORT))
    hops = landings(decision, RUNE_LANDED, 0.5)
    assert hops
    assert bool(hops[0]['veto'] and hops[0]['veto'].startswith(dolls.LANDED)) is land
    assert not (isinstance(act, p.Move) and land and math.dist(act.step.spot, RUNE_LANDED) < 0.5)


@pytest.mark.parametrize('land', [False, True])
def test_f2_the_firing_spot_hop_12_from_dolls(monkeypatch, land: bool) -> None:
    """13:32:03.37: the hop the game made (12.2 from the nearest live doll at the landing) is barred with DOLL_LAND,
    and the character stands and strikes instead; without it the hop is made, as in the game."""
    switches(monkeypatch, land=land, guard=False)
    act, decision = priced('dolls-firing-spot', group, Step(FIRING_LANDED, TELEPORT))
    hop = landings(decision, FIRING_LANDED, 0.5)
    assert hop
    assert bool(hop[0]['veto'] and hop[0]['veto'].startswith(dolls.LANDED)) is land
    if land:
        assert isinstance(act, p.Hold)
    else:
        assert isinstance(act, p.Move)
        assert math.dist(act.step.spot, FIRING_LANDED) < 0.5


RING = [(5000.0 + 12 * math.cos(a), 5000.0 + 12 * math.sin(a)) for a in (k * math.tau / 8 for k in range(8))]


@pytest.mark.parametrize(('around', 'barred'), [(RING, False), (RING[:3], True)])
def test_f2_with_a_doll_on_the_character_the_escapes_stand_unless_one_lands_clear(monkeypatch, around, barred) -> None:
    """A doll 2 off (the hold barred by the corpse bar), others 12 off: the escapes landing near a doll stand while
    none lands clear of all (dolls all round: the existing escape logic wins), and are barred when one does."""
    switches(monkeypatch, land=True, guard=False)
    here = (5000.0, 5000.0)
    look = scene(here, [(5002.0, 5000.0), *around])
    _, decision = priced(look, group, Step((5000.0, 5030.0), TELEPORT))
    escapes = [c for c in decision['candidates'] if c['act'] == 'Move' and (c['retreat'] or c['dodge']) and c['skill']]
    assert escapes
    near = [c for c in escapes if (c['veto'] or '').startswith(dolls.LANDED)]
    assert bool(near) is barred
    if barred:
        assert any(not c['veto'] for c in escapes)  # one lands clear, and stands


def test_f2_not_with_attack_mode_off(monkeypatch) -> None:
    """The KP_4 jump prices its hops with attack mode off: the press is the player's, the landing rule does not
    apply."""
    switches(monkeypatch, land=True, guard=False)
    _, decision = priced('dolls-ort-rune', group, Step(RUNE_LANDED, TELEPORT), attacking=False)
    assert not any((c['veto'] or '').startswith(dolls.LANDED) for c in decision['candidates'])


FAR = [(5040.0, 0.0 + 5000.0), (5042.0, 5004.0)]  # idle dolls out of reach, beyond the goal's landing


def test_f2_the_nearest_place_on_the_way_no_doll_bars(monkeypatch) -> None:
    switches(monkeypatch, land=True, guard=False)
    act, decision = priced(scene((5000.0, 5000.0), FAR), group, Step((5025.0, 5000.0), TELEPORT))
    assert landings(decision, (5025.0, 5000.0), 0.5)[0]['veto'].startswith(dolls.LANDED)
    safe = [c for c in decision['candidates'] if c['why'] == 'safe approach' and not c['veto']]
    assert safe
    assert all(min(math.dist(c['place'], at) for at in FAR) >= 20.0 for c in safe)
    assert 5000.0 < safe[0]['place'][0] < 5025.0  # on the way
    assert isinstance(act, p.Move)
    assert act.step.spot == tuple(safe[0]['place'])


def test_f2_the_asked_move_held_past_the_patience_is_made(monkeypatch, caplog) -> None:
    """Idle dolls with no way short of them (every place on the way barred) hold the run: past dolls.PATIENCE with
    nothing in reach, the asked move's bar is lifted (the corpse bar stays), said once."""
    switches(monkeypatch, land=True, guard=False)
    monkeypatch.setattr(module.Pricing, 'short_of_dolls', lambda self, step: None)
    safety = module.Safety()
    look = scene((5000.0, 5000.0), FAR)
    step = Step((5025.0, 5000.0), TELEPORT)
    first, _ = priced(look, group, step, safety=safety, now=NOW)
    assert not (isinstance(first, p.Move) and first.step.spot == step.spot)
    held, _ = priced(look, group, step, safety=safety, now=NOW + dolls.PATIENCE / 2)
    assert not (isinstance(held, p.Move) and held.step.spot == step.spot)
    with caplog.at_level('INFO'):
        later, _ = priced(look, group, step, safety=safety, now=NOW + dolls.PATIENCE + 0.1)
    assert isinstance(later, p.Move)
    assert later.step.spot == step.spot
    assert 'is no longer barred' in caplog.text


@pytest.mark.parametrize('guard', [False, True])
def test_f1_the_rune_beside_the_dolls_is_not_gone_to(monkeypatch, guard: bool) -> None:
    switches(monkeypatch, land=False, guard=guard)
    snap, monsters = snapshot('dolls-ort-rune')
    here = (snap['player']['x'], snap['player']['y'])
    foes = [m for m in monsters if not m.ally and m.owner == NO_OWNER]
    side = Drop(2, RUNE[0], RUNE[1], 'Ort Rune', VALUABLE)
    found = goals.goal_of(here, spend=PRESSED, reach=20.0, foes=foes, side=side)
    assert found is not None
    assert found.guarded is guard  # a rune is no potion: guarded by the dolls alone
    barring = goals.in_the_way(found, foes, here)
    assert bool([m for m in barring if dolls.runner(m.txt_id)]) is guard
    if guard:
        fight = goals.first_fight(found, here, barring, 20.0)
        nearest = min((m for m in barring if dolls.runner(m.txt_id)), key=lambda m: math.dist(here, (m.x, m.y)))
        assert fight.unit == nearest.unit_id  # a doll, the nearest
        assert fight.spend.short == pytest.approx(min(dolls.LAND_UNITS * dolls.FAST_FACTOR, 20.0 - 2.0))
        assert fight.guarded


def test_f1_a_potion_keeps_its_old_guards_and_adds_the_dolls(monkeypatch) -> None:
    switches(monkeypatch, land=False, guard=True)
    here = (0.0, 0.0)
    doll = Monster(1, 216, 1, 30.0, 0.0)  # 18 from the potion, 30 from the character
    brute = Monster(2, 133, 1, 12.0, 5.0)  # 5 from the potion
    side = Drop(3, 12.0, 0.0, 'Super Healing Potion', HEALING)
    found = goals.goal_of(here, spend=PRESSED, reach=20.0, foes=[doll, brute], side=side)
    assert found is not None
    assert found.guarded
    assert {m.unit_id for m in goals.in_the_way(found, [doll, brute], here)} == {1, 2}
    fight = goals.first_fight(found, here, goals.in_the_way(found, [doll, brute], here), 20.0)
    assert fight.unit == 1  # the doll is fought first, from range
    monkeypatch.setattr(dolls, 'DOLL_GUARD', False)
    assert {m.unit_id for m in goals.in_the_way(found, [doll, brute], here)} == {2}
    assert goals.first_fight(found, here, [brute], 20.0).spend.short == 0.0


def test_f1_once_the_dolls_are_dead_the_valuable_is_taken(monkeypatch) -> None:
    switches(monkeypatch, land=False, guard=True)
    here = (0.0, 0.0)
    dead = Monster(1, 216, 12, 25.0, 0.0)
    side = Drop(3, 12.0, 0.0, 'Ort Rune', VALUABLE)
    found = goals.goal_of(here, spend=PRESSED, reach=20.0, foes=[dead], side=side)
    assert found is not None
    assert found.do == goals.PICK_UP
    assert not found.guarded
    assert goals.in_the_way(found, [dead], here) == []


@pytest.mark.parametrize('first', [False, True])
def test_f3_the_doll_running_in_is_struck_before_a_richer_line(monkeypatch, first: bool) -> None:
    """Hunter.choose (DOLL_FIRST): a doll 12 off before five Death Lords on a richer line (the threat scene
    `dolls_running_in`); a doll already 3 off is no longer "first"."""
    from inventory_tracking.game.view import Viewport
    from inventory_tracking.levels.model import Ground
    from tests.inventory_tracking.macros.test_hunt import ASPECT, foe, game, hunter

    monkeypatch.setattr(dolls, 'DOLL_FIRST', first)
    lords = [foe(n, 5000.0, 4991.0 - 3.0 * n, txt_id=131) for n in range(1, 6)]
    doll = foe(10, 5012.0, 5000.0, txt_id=216)
    play = game(*lords, doll)
    hunt = hunter(play)
    ground = Ground(())
    chosen = hunt.choose(play.world, [*lords, doll], [*lords, doll], ground, Viewport(ASPECT))
    assert (chosen.unit == 10) is first
    beside = foe(10, 5003.0, 5000.0, txt_id=216)
    play = game(*lords, beside)
    chosen = hunter(play).choose(play.world, [*lords, beside], [*lords, beside], ground, Viewport(ASPECT))
    assert chosen.unit != 10


@pytest.mark.parametrize('bait', [False, True])
def test_bait_the_way_in_to_dolls_the_demon_holds(monkeypatch, bait: bool) -> None:
    """DOLL_BAIT: dolls on a demon 30 off: the way in to BAIT_STAND from them is priced and taken first; off, not
    offered."""
    switches(monkeypatch, land=False, guard=False)
    monkeypatch.setattr(dolls, 'DOLL_BAIT', bait)
    snap, monsters = scene((5000.0, 5000.0), [(5031.0, 5001.0), (5032.0, 4999.0), (5030.0, 5002.0)])
    demon = Monster(200, 744, 1, 5029.0, 5000.0, owner=snap['player']['unit'], ally=True)
    act, decision = priced((snap, [*monsters, demon]), group, None)  # the draw sends the demon (safety.py `look`)
    ways = [c for c in decision.get('candidates', ()) if c['why'].startswith(dolls.BAIT_SAID)]
    assert bool(ways) is bait
    if bait:
        assert isinstance(act, p.Move)
        assert act.reason.startswith(dolls.BAIT_SAID)
