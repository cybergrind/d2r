"""The safety against a Mana Burn pack and under the mana floor (combat/threats/manaburn.py BURN_RANGE, MANA_FLOOR;
rca/2026-10-21/mana-burn-findings.md), priced on looks cut from take 20261021T124558Z-25 (Tower Cellar Level 5): a tier
5 Ghost Herald with Cold Enchanted, Extra Fast and Mana Burn and its 14 minions, which ran in at 18.7 units a second
and burnt the mana 730 -> 0 in 0.66 s.

- arriving, 15:46:12.10: the pack 15.7-30 away, mana 740: the look held (H 0); now a hop back out of its reach;
- surrounded, 15:46:13.64: 6 within 5, mana 660: the look hopped 10 units, inside the pack; now out of its reach;
- burnt, 15:46:14.32: mana 10: the look chose a Teleport the mana could not pay; now the leave walks.
The player, 2026-10-21 ~15:50: "another super-sketchy battle against bird that burned all mana, we were tanking most
of T5 herald damage without being able to hit (=low mana)".
"""

import json
import math
from dataclasses import replace
from types import SimpleNamespace

from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.combat import pack as herald_pack
from inventory_tracking.combat.harm import Harm, Hostile
from inventory_tracking.combat.policy import observe
from inventory_tracking.combat.survival import CALM
from inventory_tracking.combat.threats import manaburn
from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.game.records import Loot, Monster
from inventory_tracking.macros import pursuit as p, safety as module
from inventory_tracking.macros.build import Step
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.hunting import moves
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import STANDING
from inventory_tracking.models import PotionType
from tests.inventory_tracking.macros.fakes import player, world
from tests.inventory_tracking.macros.test_herald_pricing import FIXTURES, FULL_BELT, NOW, priced


HERALD = 3599738168
# The take's "a better place in the fight ... a jump by Teleport of 22 ... worth 322366" at 15:46:12.23: into the pack
# (not offered to the safety: it lies within stance KEEP_AWAY of a Ghost; asked as the run's way here)
INTO_THE_PACK = (12607.5, 11076.5)


def burning(name: str) -> tuple[tuple[float, float], list[manaburn.Burner]]:
    """The character's place and the draining hostiles of a fixture."""
    snap = json.loads((FIXTURES / f'{name}.json').read_text(encoding='utf-8'))
    here = (snap['player']['x'], snap['player']['y'])
    hostiles = [
        Hostile(m['unit'], m['txt'], (m['x'], m['y']), m['flags'], tuple(m['mods']), m['tier'])
        for m in snap['monsters']
        if not m['ally'] and m['owner'] == NO_OWNER
    ]
    return here, manaburn.burners(hostiles)


def hops(decision: dict) -> list[dict]:
    return [c for c in decision['candidates'] if c['why'].startswith(herald_pack.BACK_SAID)]


def off(monkeypatch) -> None:
    """Items 1 and 3 off, and the Extra Fast range (the Ghosts are Extra Fast): the safety as it was at 15:46."""
    monkeypatch.setattr(manaburn, 'BURN_RANGE', False)
    monkeypatch.setattr(manaburn, 'FAST_RANGE', False)
    monkeypatch.setattr(manaburn, 'MANA_FLOOR', False)


def test_today_the_arriving_pack_is_waited_for_and_now_it_is_hopped_away_from(monkeypatch) -> None:
    off(monkeypatch)
    act, _ = priced('herald-manaburn-arriving')
    assert isinstance(act, p.Hold)
    monkeypatch.undo()
    act, decision = priced('herald-manaburn-arriving')
    assert isinstance(act, p.Move), decision['candidates']
    assert act.reason.startswith(f'{herald_pack.BACK_SAID}: {manaburn.BURN_SAID}')
    assert act.step.skill == TELEPORT
    assert act.dodge
    here, burners = burning('herald-manaburn-arriving')
    assert manaburn.clear_of(act.step.spot, burners, manaburn.HOP_CLEAR)
    assert math.dist(here, act.step.spot) >= min(manaburn.HOP_LENGTHS) - 1e-6


def test_today_the_surrounded_hop_lands_inside_the_pack_and_now_out_of_its_reach(monkeypatch) -> None:
    here, burners = burning('herald-manaburn-surrounded')
    off(monkeypatch)
    act, _ = priced('herald-manaburn-surrounded')
    assert isinstance(act, p.Move)
    assert act.reason.startswith(f'{herald_pack.BACK_SAID}: surrounded')  # the Herald pack's hop of 15:46:13.64
    assert math.dist(here, act.step.spot) < 12.0
    assert not manaburn.clear_of(act.step.spot, burners)
    monkeypatch.undo()
    act, _ = priced('herald-manaburn-surrounded')
    assert isinstance(act, p.Move)
    assert act.reason.startswith(f'{herald_pack.BACK_SAID}: {manaburn.BURN_SAID}: surrounded')
    assert act.step.skill == TELEPORT
    assert manaburn.clear_of(act.step.spot, burners)
    assert min(math.dist(act.step.spot, b.at) for b in burners) > max(b.keep for b in burners)


def test_a_hop_chosen_again_before_it_lands_is_counted_once_and_the_pack_has_burn_hops() -> None:
    safety = module.Safety()
    for _ in range(3):
        act, _ = priced('herald-manaburn-surrounded', safety)
        assert isinstance(act, p.Move)
        assert act.reason.startswith(herald_pack.BACK_SAID)
    assert safety.burn_hops[HERALD][0] == 1  # the take counted 15:46:13.64 and 13.77 as hops 1 and 2 of 3
    assert not safety.pack_hops  # not the Herald pack's count
    safety.burn_hops[HERALD] = (manaburn.BURN_HOPS, (0.0, 0.0), (0.0, 0.0))
    _, decision = priced('herald-manaburn-surrounded', safety)
    assert not hops(decision)


def test_with_no_mana_no_teleport_is_chosen_and_the_leave_walks(monkeypatch) -> None:
    off(monkeypatch)
    act, _ = priced('herald-manaburn-burnt')
    assert isinstance(act, p.Move)
    assert act.step.skill == TELEPORT  # 15:46:15.40: a Teleport hop with mana 0, "pressed again", never cast
    monkeypatch.undo()
    act, decision = priced('herald-manaburn-burnt')
    assert isinstance(act, p.Move), decision['candidates']
    assert act.step.skill is None
    assert act.reason.startswith((manaburn.MANA_SAID, herald_pack.BACK_SAID))
    assert decision['budget'] == 0.0  # the mana floor: the life budget is 0
    teleports = [c for c in decision['candidates'] if c['skill'] == TELEPORT]
    assert teleports
    assert all(c['veto'] == manaburn.NO_TELEPORT for c in teleports)


def test_the_floor_reads_the_burn_across_looks_and_leaves_by_teleport_while_the_mana_pays(monkeypatch) -> None:
    # The pack's hop off: the mana leave alone, as for a pack of no Mana Burn in reach
    monkeypatch.setattr(module.Safety, 'burn_back', lambda self, p, demons: None)
    safety = module.Safety()
    priced('herald-manaburn-arriving', safety)  # mana 740
    act, decision = priced('herald-manaburn-burnt', safety)  # mana 10, the same clock
    assert isinstance(act, p.Move)
    assert act.reason.startswith(manaburn.MANA_SAID)
    assert 'gone within 1 s' in act.reason
    assert act.step.skill is None  # 10 mana: no Teleport
    # Under the reserve with the mana for a Teleport still there: the leave is a Teleport
    act, decision = priced('herald-manaburn-regen', module.Safety())
    assert isinstance(act, p.Move), decision['candidates']
    assert act.reason.startswith(manaburn.MANA_SAID)
    assert 'under the reserve' in act.reason
    assert act.step.skill == TELEPORT


def test_a_pack_with_no_mana_burn_at_low_mana_is_struck_not_left(monkeypatch) -> None:
    # 18:57:16.54, the Vile Witches' pack, mana 25 of 740: the leave by Teleport the take chose, and the hold now
    monkeypatch.setattr(manaburn, 'LEAVE_BURNERS_ONLY', False)
    act, decision = priced('herald-witches-low-mana')
    assert isinstance(act, p.Move)
    assert act.reason.startswith(manaburn.MANA_SAID)
    assert act.step.skill == TELEPORT
    assert decision['budget'] == 0.0
    monkeypatch.undo()
    safety = module.Safety()
    act, decision = priced('herald-witches-low-mana', safety)
    assert isinstance(act, p.Hold), decision['candidates']
    assert decision['budget'] > 0.0
    assert not [c for c in decision['candidates'] if c['why'].startswith(manaburn.MANA_SAID)]
    assert safety.mana_short is None  # 25 pays for a strike: no Rejuvenation for the mana either


def test_a_mana_burner_in_reach_or_a_burn_seen_still_leaves() -> None:
    low = 'mana 25 of 740, under the reserve 64, 1 in reach'
    assert manaburn.leave_for(low, False, 1) == low
    assert manaburn.leave_for(low, True, 0) == low
    assert manaburn.leave_for(low, False, 0) is None
    assert manaburn.leave_for(None, True, 3) is None
    # The Ghosts' pack (Mana Burn) under the reserve: the leave as before
    act, _ = priced('herald-manaburn-regen', module.Safety())
    assert isinstance(act, p.Move)
    assert act.reason.startswith(manaburn.MANA_SAID)


def test_with_no_leave_a_rejuvenation_answers_the_mana_only_under_one_strike() -> None:
    low = 'mana 10 of 740, under the reserve 64, 2 in reach'
    assert manaburn.short_of(None, low, 10.0) == low
    assert manaburn.short_of(None, low, manaburn.STRIKE_MANA) is None
    assert manaburn.short_of(low, low, 40.0) == low  # the burner's leave: its rule as before
    assert manaburn.short_of(None, None, 5.0) is None


def test_the_gloam_pack_is_hopped_out_of_18_not_10(monkeypatch) -> None:
    # 18:35:28.98 and 34.36, the tier 5 Herald of Gloams: the take's "pack: keeping range ... within 10", hop 1 and 2 of
    # 3, landed among the casters; with CASTER_RANGE the hop lands 18 off every one of them
    for name in ('herald-gloams-arriving', 'herald-gloams-pressed'):
        monkeypatch.setattr(manaburn, 'CASTER_RANGE', False)
        act, _ = priced(name)
        assert isinstance(act, p.Move)
        assert act.reason.startswith(f'{herald_pack.BACK_SAID}: 1 of the pack on the character within 10'), name
        monkeypatch.undo()
        _, casters = burning(name)
        assert len(casters) >= 12
        act, decision = priced(name)
        assert isinstance(act, p.Move), decision['candidates']
        assert act.reason.startswith(f'{herald_pack.BACK_SAID}: {manaburn.CASTER_SAID}'), name
        assert act.step.skill == TELEPORT
        assert manaburn.clear_of(act.step.spot, casters), name
        assert min(math.dist(act.step.spot, b.at) for b in casters) >= manaburn.FAST_KEEP


def test_starved_holding_is_forecast_to_kill_nothing(monkeypatch) -> None:
    monkeypatch.setattr(manaburn, 'BURN_RANGE', False)
    _, starved = priced('herald-manaburn-burnt')
    assert starved['killed'] == {}
    monkeypatch.setattr(manaburn, 'MANA_FLOOR', False)
    _, fed = priced('herald-manaburn-burnt')
    assert fed['killed']


def priced_toward(name: str, step: Step, herald: int = HERALD, before=None) -> dict:
    """The decision record at the cut look `name` with a level run's full clear going for the Herald by `step` (the
    goal of 15:46:11.9), as `priced` prices it otherwise."""
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
    stats = tuple((stat, value) for stat, value in snap['stats'])
    loot = Loot(life=snap['player']['life'], max_life=snap['player']['max_life'], stats=stats, belt=FULL_BELT)
    safety = module.Safety()
    safety.draw_lands = snap['draw_lands']
    look = safety.look(alive, loot, 'battle', seen.blocked, build.shield, settings, now=NOW, draw=build.draw)
    if before is not None:
        before(safety)  # a memory of earlier looks (`Safety.left_at`)
    leader = next(m for m in monsters if m.unit_id == herald)
    goal = Goal('the elite 38', (leader.x, leader.y), 'fight', 2.0, STANDING, herald, clearing=True)
    facts = replace(p.Facts(NOW, goal, False, True, True, lambda: step, snap['area']), near=True, quiet=0.2)
    run = p.Pursuit('pickup', NOW - 5.0, leash=p.FULL)
    safety.price(
        facts, run, look, loot, CALM, settings, seen, attack, lambda point: Step(point, TELEPORT),
        options=lambda point: (Step(point, TELEPORT), Step(point)), teleport_hands='battle',
    )  # fmt: skip
    return safety.decision


def test_the_approach_into_the_pack_is_barred_and_not_with_burn_range_off(monkeypatch) -> None:
    step = Step(INTO_THE_PACK, TELEPORT)

    def asked(decision: dict) -> dict:
        return next(c for c in decision['candidates'] if c['why'] == '' and c['place'] == INTO_THE_PACK)

    assert asked(priced_toward('herald-manaburn-arriving', step))['veto'] == manaburn.LANDED
    monkeypatch.setattr(manaburn, 'BURN_RANGE', False)
    monkeypatch.setattr(manaburn, 'FAST_RANGE', False)
    assert asked(priced_toward('herald-manaburn-arriving', step))['veto'] is None


def candidate(act: p.Act, mean: float, barred: str | None = None) -> p.Candidate:
    return p.Candidate(act, 1.0, Harm(mean, mean, barred=barred), unstruck=0.3 if isinstance(act, p.Move) else 0.0)


def test_the_arbiter_takes_the_mana_leave_over_a_cheaper_hold_unless_it_is_vetoed() -> None:
    goal = Goal('the fight', (0.0, 0.0), 'fight', 20.0, STANDING)
    leave = p.Move(Step((-16.0, 0.0), TELEPORT), goal, f'{manaburn.MANA_SAID}: mana 10 of 740', dodge=True)
    hold = p.Hold(goal)
    facts = p.Facts(0.0, goal, True, True, True, lambda: Step(goal.place), priced=True, budget=0.0, life=2000.0)
    assert p.arbitrate(replace(facts, candidates=(candidate(hold, 1.0), candidate(leave, 50.0)))) is leave
    vetoed = (candidate(hold, 1.0), candidate(leave, 50.0, barred='lethal'))
    assert p.arbitrate(replace(facts, candidates=vetoed)) is not leave


# -- the Rejuvenation for mana (manaburn.MANA_REJUVENATION; the player, 2026-10-21 ~16:30: "we can restore mana with
# rejuv potions, in a very scary moments, but make sure that we don't overuse it") --


def test_the_burnt_look_is_a_scary_moment_and_the_others_are_not() -> None:
    safety = module.Safety()
    priced('herald-manaburn-burnt', safety)
    look = safety.mana_look
    assert look is not None
    assert look.why is not None
    assert look.danger >= 9
    assert look.key == HERALD
    assert not look.teleport_out  # 10 mana: the leave walks
    assert manaburn.rejuvenation_for_mana(look, NOW, 4, math.inf, ()) is not None
    for name in ('herald-manaburn-surrounded', 'herald-manaburn-regen'):
        safety = module.Safety()
        priced(name, safety)
        found = safety.mana_look
        assert found is not None
        # 660 mana: no floor; 43 mana: the floor, but a Teleport out is chosen
        assert manaburn.rejuvenation_for_mana(found, NOW, 4, math.inf, ()) is None, name


class Drinker:
    def __init__(self, drunk_at: float = -math.inf) -> None:
        self.drunk_at = {PotionType.REJUVENATION: drunk_at}
        self.busy, self.readings, self.taken = False, [], []

    def shift_down(self, run) -> bool:
        return False

    def take(self, run, key, kind, loot, felt) -> bool:
        self.taken.append((key, kind))
        return True


def hunter_after(name: str, drinker: Drinker) -> SimpleNamespace:
    safety = module.Safety()
    priced(name, safety)
    return SimpleNamespace(safety=safety, drinker=drinker, tell=lambda run, said: None)


def drinks(hunter: SimpleNamespace, run: SimpleNamespace, loot: Loot, rejuvenations: int) -> bool:
    """`moves.mana_rejuvenation` on fakes of the hunter and the run (what it reads of them only)."""
    return moves.mana_rejuvenation(hunter, run, loot, rejuvenations)  # pyrefly: ignore[bad-argument-type]  # fakes


def test_the_hook_drinks_once_a_pack_and_keeps_the_last_two() -> None:
    run = SimpleNamespace(clock=lambda: NOW + 0.1)
    rejuvenation = 530  # native/layout.py REJUVENATION_POTIONS
    belt = (rejuvenation, rejuvenation, None, None) * 2 + (None,) * 8  # columns 1-2, two rows: 4 rejuvenations
    loot = Loot(life=2436, max_life=2907, belt=belt)
    drinker = Drinker()
    hunter = hunter_after('herald-manaburn-burnt', drinker)
    assert drinks(hunter, run, loot, 4)
    assert drinker.taken[0][1] == PotionType.REJUVENATION
    assert hunter.safety.mana_drunk == {HERALD: NOW + 0.1}
    assert not drinks(hunter, run, loot, 4)  # this pack had its one
    assert not drinks(hunter_after('herald-manaburn-burnt', Drinker()), run, loot, 2)  # the last 2 kept
    assert not drinks(hunter_after('herald-manaburn-burnt', Drinker(NOW - 5.0)), run, loot, 4)  # one 5 s ago


# -- the Arachnid Lair's second tier 5 Herald (take 20261021T172936Z-84, rca/2026-10-21/arachnid-herald-2-findings.md):
# at 20:31:17.14 "Teleport toward full clear: the hostile by the Herald coming" landed 7.6 from the omen's spot 0.4 s
# before the pack showed round it; 3509 life went in the next 7 s (manaburn.PACK_LANDING) --

SPIDER_OMEN = (7511.5, 5058.5)
BY_THE_OMEN = (7517.9, 5055.4)
A_SPIDER = 693245829  # a plain Flame Spider of the look, 27 away: the goal's unit (the Herald is not seen yet)


def test_the_teleport_onto_the_herald_coming_is_barred_while_its_omen_is_pending(herald2_on, monkeypatch) -> None:
    step = Step(BY_THE_OMEN, TELEPORT)

    def asked() -> dict:
        decision = priced_toward('herald-spiders-coming', step, herald=A_SPIDER)
        return next(c for c in decision['candidates'] if c['why'] == '' and c['place'] == BY_THE_OMEN)

    herald_pack.saw_omens([(SPIDER_OMEN, NOW + 3.0)])
    assert asked()['veto'] == manaburn.PACK_LANDED
    monkeypatch.setattr(manaburn, 'PACK_LANDING', False)
    assert asked()['veto'] != manaburn.PACK_LANDED
    monkeypatch.setattr(manaburn, 'PACK_LANDING', True)
    herald_pack.saw_omens([(SPIDER_OMEN, NOW - 1.0)])  # read out: the pack is seen by now, or never came
    assert asked()['veto'] != manaburn.PACK_LANDED


SPIDER_HERALD = 284207851
BACK_IN = (7511.857568053111, 5076.434313455158)  # 20:31:38.10: the asked Teleport, 9.1 from a member, 13.2 before


def test_the_teleport_back_into_the_pack_between_two_keep_range_hops_is_barred(herald2_on, monkeypatch) -> None:
    step = Step(BACK_IN, TELEPORT)

    def asked() -> dict:
        decision = priced_toward('herald-spiders-pingpong', step, herald=SPIDER_HERALD)
        return next(c for c in decision['candidates'] if c['why'] == '' and c['place'] == BACK_IN)

    assert asked()['veto'] == manaburn.PACK_LANDED
    monkeypatch.setattr(manaburn, 'PACK_LANDING', False)
    assert asked()['veto'] is None  # as played: taken, and hop 2 of 3 took the character out again 0.55 s later


def test_just_after_a_hop_with_the_demons_idle_by_the_character_the_teleport_back_in_is_barred(
    herald2_on, monkeypatch
) -> None:
    """The look of 20:31:38.10: the demons 0.6 from the character in neutral mode after the hop of 37.33, the nearest
    spider 12.8 from them (combat/pack.py REAGGRO_BY_MARK: the mark re-aggroes them, mark.py REMARK_AFTER_HOP)."""
    monkeypatch.setattr(manaburn, 'PACK_LANDING', False)
    step = Step(BACK_IN, TELEPORT)

    def asked() -> dict:
        decision = priced_toward('herald-spiders-pingpong', step, herald=SPIDER_HERALD)
        return next(c for c in decision['candidates'] if c['why'] == '' and c['place'] == BACK_IN)

    herald_pack.hopped(NOW - 0.5, 8.4)
    assert asked()['veto'] == herald_pack.REAGGRO_SAID
    herald_pack.hopped(NOW - herald_pack.REAGGRO_WAIT - 0.1, 8.4)  # the mark had its time
    assert asked()['veto'] is None
    herald_pack.hopped(NOW - 0.5, 8.4)
    monkeypatch.setattr(herald_pack, 'REAGGRO_BY_MARK', False)
    assert asked()['veto'] is None


LEFTOVER_MINION = 3149368047  # the tier 5 Herald's minion at 11/128, 23.9 off
PROGRESS = (4824.5, 5094.5)  # 21:07:23.72: the one progress move, barred


def test_at_full_life_a_leftover_minion_keeps_no_progress_move_out() -> None:
    """21:07:23.72 (take 20261021T180239Z-110): "retreating: no progress act fits the life budget" at 2723 of 2943
    life and a full belt; the one progress move barred by a keep range (the player: "there were EASY heralds")."""
    step = Step(PROGRESS, TELEPORT)

    def asked() -> dict:
        decision = priced_toward('herald-easy-leftover', step, herald=LEFTOVER_MINION)
        return next(c for c in decision['candidates'] if c['why'] == '' and c['place'] == PROGRESS)

    assert asked()['veto'] != manaburn.LANDED


def test_with_the_threat_gate_off_the_leftover_bars_it_as_played(monkeypatch) -> None:
    monkeypatch.setattr(manaburn, 'THREAT_GATE', False)
    step = Step(PROGRESS, TELEPORT)
    decision = priced_toward('herald-easy-leftover', step, herald=LEFTOVER_MINION)
    assert (
        next(c for c in decision['candidates'] if c['why'] == '' and c['place'] == PROGRESS)['veto'] == manaburn.LANDED
    )


def test_a_move_back_to_where_the_last_safety_hop_left_is_barred_for_a_few_seconds(monkeypatch) -> None:
    """The ping-pong of 21:23:39-43 (take 20261021T182256Z-115): a keep-range hop A -> B, then at B the retreat back
    to A, three times, no strike (macros/safety.py BOUNCE_BACK). Here: the look of 20:31:38.10, the character at B
    (7504.5, 5076.5) 0.5 s after a safety Teleport from A, the asked Teleport back to A."""
    monkeypatch.setattr(manaburn, 'PACK_LANDING', False)
    step = Step(BACK_IN, TELEPORT)
    here = (7504.5, 5076.5)

    def asked(at: float) -> dict:
        def hop(safety) -> None:
            safety.left_at = (BACK_IN, here, at)

        decision = priced_toward('herald-spiders-pingpong', step, herald=SPIDER_HERALD, before=hop)
        return next(c for c in decision['candidates'] if c['why'] == '' and c['place'] == BACK_IN)

    assert asked(NOW - 0.5)['veto'] == module.BOUNCED
    assert asked(NOW - module.BOUNCE_WINDOW - 0.1)['veto'] is None
    monkeypatch.setattr(module, 'BOUNCE_BACK', False)
    assert asked(NOW - 0.5)['veto'] is None


DARK_SHAMAN = 2304217088  # the Dark Shaman unique (61) of take 20261021T201038Z-35
ON_TO_THEM = (22608.5, 6626.2)  # 23:10:48.68: the one progress move, barred


def test_a_plain_mana_burn_pack_with_the_mana_full_keeps_no_progress_move_out(monkeypatch) -> None:
    """23:10:48.68 (manaburn.DRAIN_GATE): Dark Ones with Mana Burn 15-23 off, the mana 730 of 745, no burn seen: the
    progress move is no longer barred by their keep range; with DRAIN_GATE off it is, as played (31 hops, no strike)."""
    step = Step(ON_TO_THEM, TELEPORT)

    def asked() -> dict:
        decision = priced_toward('drain-fallen-pingpong', step, herald=DARK_SHAMAN)
        return next(c for c in decision['candidates'] if c['why'] == '' and c['place'] == ON_TO_THEM)

    assert asked()['veto'] != manaburn.LANDED
    monkeypatch.setattr(manaburn, 'DRAIN_GATE', False)
    assert asked()['veto'] == manaburn.LANDED
