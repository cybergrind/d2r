"""The kill goals that made no move toward a kill on 2026-10-22 (rca/2026-10-22/walled-boss-findings.md):

- Tal Rasha's Tomb 67, 23:09:52-23:10:08 (game cyberg65, take 20261022T200931Z-67): the ledger's Ancient Kaa the
  Soulless, killed at 19:56:19 with his kill lost by the terror tracker's fresh state, gone for at his last place and
  stood at 15 units off with nothing to strike (terror/tracker.py BOOK_KILLS, macros/bossledger.py BOSS_ABSENT; their
  tests: tests/inventory_tracking/terror/test_tracker.py, test_bossledger.py, test_agenda.py);
- Sewers Level 3, 23:15:49-23:20:30 (take 20261022T201417Z-49): Radament priced by the harm model's conservative
  stand-in for an unread boss, every place within its radius near-lethal, 4.5 minutes of approaches and retreats with
  life 2943 of 2943 throughout, the goal going round the route's fight, the agenda's kill of the same unit and a super
  chest (hunting/choice.py ROUTE_BOSS_FIRST here)."""

from inventory_tracking.combat import harm as harm_model
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros import safety as safety_module
from inventory_tracking.macros.agenda import PLUS_WAY
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.hunting import choice
from inventory_tracking.macros.travel import PRESSED
from inventory_tracking.routes.model import FIGHT, fight
from tests.inventory_tracking.macros.test_hunt import foe
from tests.inventory_tracking.macros.test_tz_leveling import agenda_hunt


RADAMENT = 881231773
UNIQUE = 0x08


def radament_goal(place: tuple[float, float]) -> Goal:
    """The route's own fight goal with Radament in the read (goals.py `goal_of`: the boss's place and unit)."""
    return Goal('Radament', place, FIGHT, 20.0, PRESSED, unit=RADAMENT, route='Radament', stage=fight('Radament'))


def test_the_routes_boss_in_the_read_is_the_runs_goal_before_the_agendas_kill_of_it_and_its_chest(monkeypatch):
    play, hunt, run = agenda_hunt(PLUS_WAY)
    radament = foe(RADAMENT, 5030.0, 5000.0, flags=UNIQUE, txt_id=229)
    pack = [foe(unit, 5010.0 + unit, 5010.0, txt_id=3) for unit in range(50, 56)]
    found = radament_goal((radament.x, radament.y))
    goal = hunt.cleared(run, play.world, [radament, *pack], Ground(()), found)
    assert goal == found  # the boss's fight, not "full clear: the elite 229" nor a group of 6
    monkeypatch.setattr(choice, 'ROUTE_BOSS_FIRST', False)
    play, hunt, run = agenda_hunt(PLUS_WAY)
    goal = hunt.cleared(run, play.world, [radament, *pack], Ground(()), found)
    assert goal != found  # as played: the agenda's kill of the same unit or its group first


# --- STAND_IN_EVIDENCE (macros/safety.py) and STAND_IN_TEMPER (combat/harm.py) ---


def evidence_on(monkeypatch, prior: tuple[float, float] = (0.0, 0.0)) -> None:
    """STAND_IN_EVIDENCE is off until the arena shows it (walled-boss-findings.md §2); these tests switch it on, the
    takes' evidence (combat/stand_ins.py `prior`) set to `prior`."""
    monkeypatch.setattr(safety_module, 'STAND_IN_EVIDENCE', True)
    monkeypatch.setattr(safety_module.stand_ins, 'prior', lambda txt: prior)


# Radament as the take read him: monstats 229, unique and super unique flags (10), Extra Fast, Mana Burn, Extra Strong,
# questcomplete (6, 25, 5, 22), level 83, idle
SPOT = (7713.5, 8017.5)
HERE = (SPOT[0] - 20.0, SPOT[1])
LIFE = 2943.0


def radament(**changes) -> harm_model.Hostile:
    return harm_model.Hostile(RADAMENT, 229, SPOT, 10, (6, 25, 5, 22), 0, 83, mode=1, **changes)


def looked(
    guard: safety_module.Safety,
    seconds: float,
    *,
    life=lambda t: LIFE,
    here=HERE,
    step=0.25,
    start=0.0,
    his=lambda t: 1.0,
) -> harm_model.Look:
    """The ledger brought through `seconds` of looks every `step` s, Radament's life share `his(t)`; the last look's
    tempered Look."""
    t, out = start, harm_model.Look((radament(),), life=LIFE)
    while t < start + seconds:
        t += step
        seen = harm_model.Look((radament(life=his(t)),), life=LIFE)
        out = guard.tempered(seen, here, t, life(t), harm_model.SafetySettings())
    return out


def test_radament_is_an_unread_boss_priced_whole_by_the_stand_in_from_5_or_30_units():
    seen = harm_model.Look((radament(),), life=LIFE)
    assert harm_model.stood_in(229)
    assert not harm_model.stood_in(3)  # a skeleton: the fit, not the stand-in
    near = harm_model.harm(seen, (SPOT[0] - 5, SPOT[1]), 1.5, 'battle')
    far = harm_model.harm(seen, (SPOT[0] - 30, SPOT[1]), 1.5, 'battle')
    assert near.mean == far.mean > LIFE / 2  # as played: every place in its radius near-lethal


def test_a_stalled_fight_in_its_reach_with_no_life_lost_tempers_the_stand_in_to_the_evidence(monkeypatch):
    evidence_on(monkeypatch)
    stall = safety_module.STALL_SECONDS
    guard = safety_module.Safety()
    early = looked(guard, stall - 1)
    assert early.hostiles[0].tempered == 1.0  # not stalled yet: whole
    guard = safety_module.Safety()
    out = looked(guard, stall + 2)
    share = out.hostiles[0].tempered
    assert safety_module.EVIDENCE_FLOOR <= share < 0.5
    whole = harm_model.harm(harm_model.Look((radament(),), life=LIFE), HERE, 1.0, 'battle')
    tempered = harm_model.harm(out, HERE, 1.0, 'battle')
    exposed = guard.evidence[RADAMENT].exposed
    blow = harm_model.most_blow(radament(), harm_model.Protection())[0]
    assert tempered.mean <= safety_module.EVIDENCE_MARGIN * blow / exposed * 1.2  # about the bound
    assert tempered.mean < whole.mean / 5
    assert tempered.worst < LIFE / 2  # one blow a little over the table's, seldom
    # Never under the floor, however long
    longer = looked(safety_module.Safety(), 600.0, step=0.5)
    assert longer.hostiles[0].tempered == safety_module.EVIDENCE_FLOOR


def test_a_fight_whose_boss_life_falls_keeps_the_stand_in_whole(monkeypatch):
    evidence_on(monkeypatch, prior=(145.0, 56.0))
    falling = looked(safety_module.Safety(), 30.0, his=lambda t: 1.0 - 0.02 * t)  # a tenth every 5 s
    assert falling.hostiles[0].tempered == 1.0
    # Its fall stops: STALL_SECONDS later the evidence prices it
    guard = safety_module.Safety()
    looked(guard, 10.0, his=lambda t: 1.0 - 0.02 * t)
    still = looked(guard, safety_module.STALL_SECONDS - 1, start=10.0, his=lambda t: 0.6)  # one fall more, then none
    assert still.hostiles[0].tempered == 1.0
    stalled = looked(guard, 2.0, start=10.0 + safety_module.STALL_SECONDS - 1, his=lambda t: 0.6)
    assert stalled.hostiles[0].tempered < 0.5


def test_the_takes_evidence_prices_a_stalled_boss_out_of_its_reach_and_so_lets_it_be_come_near(monkeypatch):
    far = (SPOT[0] - 60.0, SPOT[1])
    evidence_on(monkeypatch)
    alone = looked(safety_module.Safety(), 20.0, here=far)
    assert alone.hostiles[0].tempered == 1.0  # no evidence: whole
    evidence_on(monkeypatch, prior=(145.0, 56.0))  # Radament's, 2026-10-22 (combat/data/stand_ins.json)
    guard = safety_module.Safety()
    out = looked(guard, safety_module.STALL_SECONDS + 1, here=far)
    assert RADAMENT not in guard.evidence  # nothing seen in its radius here
    assert out.hostiles[0].tempered < 0.5
    near = harm_model.harm(out, HERE, 1.5, 'battle')
    assert harm_model.veto(near, LIFE) is None  # the place in his reach is no longer vetoed


def test_a_life_lost_puts_the_stand_in_back_whole_and_raises_its_bound(monkeypatch):
    evidence_on(monkeypatch)
    guard = safety_module.Safety()
    looked(guard, 12.0)
    hit = looked(guard, 1.0, life=lambda t: LIFE - 400.0, start=12.0)  # 400 lost
    assert hit.hostiles[0].tempered == 1.0  # survival first: whole while hurt
    calm = looked(guard, safety_module.EVIDENCE_HURT + 0.5, life=lambda t: LIFE - 400.0, start=13.0)
    share = calm.hostiles[0].tempered
    assert share < 1.0
    unhurt = looked(safety_module.Safety(), 16.5).hostiles[0].tempered
    assert share > unhurt  # the loss raised its bound


def test_the_switches_restore_the_stand_in(monkeypatch):
    evidence_on(monkeypatch, prior=(145.0, 56.0))
    monkeypatch.setattr(safety_module, 'STAND_IN_EVIDENCE', False)
    assert looked(safety_module.Safety(), 20.0).hostiles[0].tempered == 1.0
    monkeypatch.setattr(harm_model, 'STAND_IN_TEMPER', False)
    whole = harm_model.harm(harm_model.Look((radament(),), life=LIFE), HERE, 1.0, 'battle')
    assert harm_model.harm(harm_model.Look((radament(tempered=0.2),), life=LIFE), HERE, 1.0, 'battle') == whole
