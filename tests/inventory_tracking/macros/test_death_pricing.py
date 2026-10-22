"""The death at 23:35:33.97 on 2026-10-21 (take 20261021T203514Z-95, Disused Fane, a terror zone;
rca/2026-10-21/death-findings.md), replayed on looks cut from the take:

- death-fane-life: the life of the last 14 s. One blow took 2014 -> 1578 of 2943 (22% within a second) and no
  rejuvenation was drunk to the end, 8 on the belt (combat/survival.py EMERGENCY_REJUVENATION);
- death-fane-walk, 23:35:32.35 (1.82 s before): life 1613, budget 0; the game chose a "retreat" walk of 16 onto three
  Flesh Hunters running in (macros/pursuit.py RETREAT_AWAY; macros/safety.py CLEAR_ESCAPES);
- death-fane-vetoed, 23:35:33.93 (0.24 s before): life 804 of 1896, every act vetoed; the game chose a walk of 16
  through a unique Flesh Hunter's pack (macros/pursuit.py VETOED_ESCAPE).

Each fixture carries the look's decision as the game recorded it: the arbiter replayed on those candidates chooses what
the game chose with the switches off. The player, 2026-10-21: "we must not die or we lose exp and our gear".
"""

import json
import math
from dataclasses import replace

import pytest

from inventory_tracking.combat import survival
from inventory_tracking.combat.harm import Harm
from inventory_tracking.combat.survival import DrinkSettings, Pressure, Reading, Supply, drink, pressure
from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.macros import pursuit as p, safety as module
from inventory_tracking.macros.build import Step
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.travel import STANDING
from inventory_tracking.models import PotionType
from tests.inventory_tracking.macros.test_herald_pricing import FIXTURES, NOW, priced


DEATH = 0.0  # the readings' clock: seconds from the frame the life read 0
DUE_BY = -1.3  # seconds: the rejuvenation is due by then (the frame Battle Orders ran out, 1079 life left after)
LOOK_EVERY = 0.2  # macros/drinking.py EVERY


def snap(name: str) -> dict:
    return json.loads((FIXTURES / f'{name}.json').read_text(encoding='utf-8'))


def hostiles(found: dict) -> list[tuple[float, float]]:
    return [
        (m['x'], m['y'])
        for m in found['monsters']
        if not m['ally'] and m['owner'] == NO_OWNER and m['mode'] not in (0, 12)
    ]


def off(monkeypatch) -> None:
    """The safety and the drinking as they were at 23:35."""
    monkeypatch.setattr(survival, 'EMERGENCY_REJUVENATION', False)
    monkeypatch.setattr(p, 'RETREAT_AWAY', False)
    monkeypatch.setattr(p, 'VETOED_ESCAPE', False)
    monkeypatch.setattr(module, 'CLEAR_ESCAPES', False)
    monkeypatch.setattr(module, 'FLOOR_NO_CREDIT', False)
    later(monkeypatch, False)


def later(monkeypatch, value: bool) -> None:
    """The fixes of 2026-10-22 (the Fane's arena) as `value` says."""
    monkeypatch.setattr(survival, 'READ_LAG', value)
    for name in ('CLEAR_FOOTING', 'DANGER_LOOK', 'AURA_FORECAST', 'ORDERS_PREDICT', 'REBUFF_RETREAT', 'REACH_BAR'):
        monkeypatch.setattr(module, name, value)
    monkeypatch.setattr(p, 'REBUFF_FIRST', value)


# The drinking


def drinks(settings: DrinkSettings | None = None) -> list[tuple[float, PotionType, float]]:
    """The potions the drinker's rule asks for at a look every LOOK_EVERY s over the take's life (open loop: the life
    is the take's, whatever is drunk): (seconds before the death, kind, life share)."""
    found = snap('death-fane-life')
    settings = settings or DrinkSettings()
    drunk = {PotionType.HEALING: found['healing_drunk'][0]}
    readings: list[Reading] = []
    asked = []
    looked = -math.inf
    for at, life, most in found['readings']:
        if life <= 0:
            break
        if at - looked < LOOK_EVERY:
            continue
        looked = at
        readings = [*(r for r in readings if at - r.at <= 6.0), Reading(at, life, most)]
        for when in found['healing_drunk']:
            if when <= at:
                drunk[PotionType.HEALING] = max(drunk[PotionType.HEALING], when)
        since = {kind: at - when for kind, when in drunk.items()}
        kind = drink(pressure(readings), Supply(4, found['rejuvenations']), since, settings)
        if kind is not None:
            asked.append((at, kind, life / most))
            drunk[kind] = at
    return asked


def test_today_no_rejuvenation_is_asked_for_to_the_death(monkeypatch) -> None:
    off(monkeypatch)
    asked = drinks()
    assert asked  # healing potions, as the game drank them
    assert all(kind == PotionType.HEALING for _, kind, _ in asked)


def test_now_the_blow_that_left_54_percent_is_a_rejuvenation_by_the_battle_orders_frame() -> None:
    asked = drinks()
    rejuvenations = [(at, share) for at, kind, share in asked if kind == PotionType.REJUVENATION]
    assert rejuvenations
    at, share = rejuvenations[0]
    assert at <= DUE_BY
    assert share == pytest.approx(1578 / 2943, abs=0.001)  # the look after the 436 blow, 23:35:28.4


@pytest.mark.parametrize(
    ('share', 'burst', 'kind'),
    [
        (0.536, 0.215, PotionType.REJUVENATION),  # 23:35:28.4: 22% within a second at 54%
        (0.424, 0.171, PotionType.REJUVENATION),  # 23:35:33.93: 804 of 1896
        (0.70, 0.30, PotionType.HEALING),  # over EMERGENCY_BELOW: a healing potion
        (0.55, 0.10, PotionType.HEALING),  # 40% after the worst second again: not scary
    ],
)
def test_the_worst_second_played_ahead_under_danger_is_severe(share: float, burst: float, kind: PotionType) -> None:
    felt = Pressure(share, burst, 0.05, burst)
    assert drink(felt, Supply(4, 8), {}, DrinkSettings()) == kind


def test_the_emergency_needs_a_rejuvenation_on_the_belt() -> None:
    felt = Pressure(0.536, 0.3, 0.09, 0.215)
    assert drink(felt, Supply(4, 0), {}, DrinkSettings()) == PotionType.HEALING
    assert drink(felt, Supply(4, 8), {PotionType.REJUVENATION: 0.5}, DrinkSettings()) == PotionType.HEALING


# The arbiter on the candidates the game priced


def recorded(name: str) -> tuple[p.Facts, dict]:
    """The look's facts with the candidates as the game recorded them. Their rollouts are not kept: a lethal veto is
    one rollout in eight lethal, and one in sixteen for the act the game chose, which its choice says was the least
    lethal (the walk of 23:35:33.94 over a hold of less mean harm)."""
    found = snap(name)
    decision = found['decision']
    here = (found['player']['x'], found['player']['y'])
    about = hostiles(found)
    goal = Goal('full clear: the elite 47 (4193434304)', here, 'fight', 22.0, STANDING, 4193434304, clearing=True)
    life = float(decision['life'])
    candidates = []
    for c in decision['candidates']:
        place = tuple(c['place'])
        if c['act'] == 'Hold':
            act: p.Act = p.Hold(goal)
        else:
            act = p.Move(Step(place, c['skill']), goal, c['why'])
        lethal = 4 if place == tuple(decision['chosen_place']) else 8
        losses = (
            (life,) * lethal + (0.0,) * (64 - lethal) if c['veto'] == 'lethal exposure in the short rollouts' else ()
        )
        barred = c['veto'] if c['veto'] and not losses else None
        harm = Harm(c['H'], c['worst'], losses=losses, barred=barred)
        clear = None
        if c['act'] == 'Move':
            clear = module.clearance(here, place, about, c['skill'] is None)
        candidates.append(p.Candidate(act, c['T'], harm, c['retreat'], 0.0, False, c['keeps'], clear))
    facts = p.Facts(NOW, goal, False, True, True, lambda: Step(here), found['area'])
    facts = replace(
        facts,
        candidates=tuple(candidates),
        priced=True,
        budget=decision['budget'],
        life=life,
        kappa=0.01,
        near=True,
        hurt=True,
        clear=min(math.dist(here, at) for at in about),
    )
    return facts, decision


def test_today_the_arbiter_on_the_recorded_candidates_walks_onto_the_runners(monkeypatch) -> None:
    off(monkeypatch)
    facts, decision = recorded('death-fane-walk')
    act = p.arbitrate(facts)
    assert isinstance(act, p.Move)
    assert act.step.skill is None
    assert act.step.spot == pytest.approx(tuple(decision['chosen_place']))
    assert act.reason == decision['reason']


def test_now_no_retreat_walks_toward_the_pack_and_the_fight_is_fought_out() -> None:
    facts, _ = recorded('death-fane-walk')
    act = p.arbitrate(facts)
    assert isinstance(act, p.Hold)  # the one move left came within 1.5 of a Flesh Hunter
    assert act.reason == 'fighting out: less harm than any reachable retreat'


def test_today_every_act_vetoed_walks_through_the_pack(monkeypatch) -> None:
    off(monkeypatch)
    facts, decision = recorded('death-fane-vetoed')
    act = p.arbitrate(facts)
    assert isinstance(act, p.Move)
    assert act.step.skill is None
    assert act.step.spot == pytest.approx(tuple(decision['chosen_place']))
    assert act.reason == decision['reason']


def test_now_every_act_vetoed_teleports_to_the_landing_clearest_of_the_hostiles() -> None:
    facts, decision = recorded('death-fane-vetoed')
    act = p.arbitrate(facts)
    assert isinstance(act, p.Move)
    assert act.step.skill is not None
    assert act.reason == f'retreating: {p.VETOED_AWAY}'
    about = hostiles(snap('death-fane-vetoed'))
    landings = [tuple(c['place']) for c in decision['candidates'] if c['act'] == 'Move' and c['skill'] is not None]
    clearest = max(min(math.dist(at, h) for h in about) for at in landings)
    assert min(math.dist(act.step.spot, h) for h in about) == pytest.approx(clearest)


# The safety pricing the cut looks again, late as the game's looks were (81-99 ms against 80)


def late():
    """A look's timer past its deadline from the first lap on: the cuts of a look over its time."""
    calls = [0]

    def timer() -> float:
        calls[0] += 1
        return 0.0 if calls[0] == 1 else 1.0

    return timer


@pytest.mark.parametrize('name', ['death-fane-walk', 'death-fane-vetoed'])
def test_now_a_late_look_jumps_clear_of_every_hostile(name: str) -> None:
    act, decision = priced(name, module.Safety(timer=late()))
    assert decision['late']
    assert isinstance(act, p.Move), decision['candidates']
    assert act.step.skill is not None
    assert min(math.dist(act.step.spot, at) for at in hostiles(snap(name))) >= p.AWAY_UNITS


def test_today_the_late_vetoed_look_hops_into_the_packs(monkeypatch) -> None:
    off(monkeypatch)
    act, decision = priced('death-fane-vetoed', module.Safety(timer=late()))
    assert isinstance(act, p.Move), decision['candidates']
    assert act.reason == 'retreating: safety: every act is vetoed; the least lethal is this move'
    assert min(math.dist(act.step.spot, at) for at in hostiles(snap('death-fane-vetoed'))) < p.AWAY_UNITS


def test_the_clearest_places_are_farther_from_every_hostile_than_the_character() -> None:
    here = (15066.5, 5648.5)
    about = hostiles(snap('death-fane-vetoed'))
    places = module.clearest(here, about)
    assert len(places) == module.CLEAR_ASKED
    now = min(math.dist(here, at) for at in about)
    assert all(min(math.dist(point, at) for at in about) > now for point in places)
    assert module.clearest(here, []) == []


def test_a_walk_is_as_clear_as_its_nearest_pass_and_a_jump_as_its_landing() -> None:
    here, spot, foe = (0.0, 0.0), (16.0, 0.0), (8.0, 1.0)
    assert module.clearance(here, spot, [foe], walk=True) == pytest.approx(1.0)
    assert module.clearance(here, spot, [foe], walk=False) == pytest.approx(math.dist(spot, foe))
    assert module.clearance(here, spot, [], walk=True) is None


# The kill credit under the life's floor (macros/safety.py FLOOR_NO_CREDIT)


def test_with_the_life_budget_0_no_kill_is_credited_to_the_strikes(monkeypatch) -> None:
    _, credited = priced('death-fane-walk')
    assert credited['budget'] == 0.0
    assert not credited['killed']  # 23:35:32.35: the game's look had the Night Lord dead in 1.8 s; it never died
    monkeypatch.setattr(module, 'FLOOR_NO_CREDIT', False)
    _, before = priced('death-fane-walk')
    assert before['killed']


def test_over_the_life_budget_the_kills_are_still_credited() -> None:
    _, decision = priced('herald-witches-low-mana')
    assert decision['budget'] > 0
    assert decision['killed']


def test_without_the_credit_fighting_out_by_the_pack_is_priced_dearer(monkeypatch) -> None:
    def fought(decision: dict) -> float:
        return next(c['H'] for c in decision['candidates'] if c['act'] == 'Hold' and c['retreat'])

    # The hold in reach of blows that take the life is barred since (REACH_BAR, test_rebuff.py): the credit alone here
    monkeypatch.setattr(module, 'REACH_BAR', False)
    _, now = priced('death-fane-walk')
    monkeypatch.setattr(module, 'FLOOR_NO_CREDIT', False)
    _, before = priced('death-fane-walk')
    assert fought(now) > fought(before)


def test_the_vetoed_look_without_the_credit_still_jumps_clear_of_every_hostile(monkeypatch) -> None:
    for credit in (True, False):
        monkeypatch.setattr(module, 'FLOOR_NO_CREDIT', not credit)
        act, decision = priced('death-fane-vetoed', module.Safety(timer=late()))
        assert isinstance(act, p.Move), decision['candidates']
        assert act.step.skill is not None
        assert min(math.dist(act.step.spot, at) for at in hostiles(snap('death-fane-vetoed'))) >= p.AWAY_UNITS
    monkeypatch.setattr(module, 'FLOOR_NO_CREDIT', False)
    _, decision = priced('death-fane-vetoed')
    assert decision['killed']
    monkeypatch.setattr(module, 'FLOOR_NO_CREDIT', True)
    _, decision = priced('death-fane-vetoed')
    assert not decision['killed']
