"""The mark first at a tier 5 Herald fight's landing (combat/pack.py HERALD_MARK_FIRST, 2026-10-24). The player, ~17:39:
"when we're repositioning for re-aggro against T5 heralds, the first things we need to do - drop off aggro from us ==
DM" (rca/2026-10-24/dm-latency-findings.md). Everywhere else the strike stays first. And the mark decided in the look
that presses the strike (macros/hunt.py MARK_WITH_PRESS)."""

import logging

import pytest

from inventory_tracking.combat import pack
from inventory_tracking.macros import hunt as hunt_module
from inventory_tracking.macros.actuator import Abort
from tests.inventory_tracking.macros.test_hunt import MINION, demon, foe, game, hunter, keys
from tests.inventory_tracking.macros.test_omen_opening import Logged


UNIQUE = 0x08  # game/layout.py UNIQUE_FLAG: the Herald among its pack
MANA_BURN = 25  # combat/threats/manaburn.py MANA_BURN
NEAR = ((5008.0, 5000.0), (5010.0, 5002.0), (5012.0, 4999.0))  # two members and the Herald, from (5000, 5000)
FAR = ((5023.5, 5000.0), (5025.0, 4998.0), (5024.0, 4997.5))  # 23.5-25.1 off: drawn, beyond the reach (22.1)


class Timed(Logged):
    """`Logged` with the fake clock of each append in `at`."""

    def __init__(self, name: str, order: list[str], clock) -> None:
        super().__init__(name, order)
        self.clock, self.at = clock, []

    def append(self, item) -> None:
        self.at.append(self.clock.now)
        super().append(item)


def played(
    monkeypatch,
    *,
    on: bool,
    tier: int = 5,
    landed: float | None = 0.1,
    until: float = 2.0,
    with_press: bool = False,
    herald: bool = True,
    burner: bool = False,
    any_member: bool = False,
    far: bool = False,
    landing_mark: bool = False,
    every_move: bool = False,
    no_burn: bool = False,
):
    """Attack mode alone on two tier `tier` Herald pack members 8-10 east (`burner`: with Mana Burn), the Herald itself
    12 east (`herald`), a demon of the character's beside it, a jump of 20 units landed `landed` s before (None: none):
    the game and the order of the marks and strikes. `any_member`: combat/pack.py HERALD_MARK_ANY_MEMBER. `far`: the
    members 23.5-25.1 off (FAR: drawn on the screen, beyond the strike's reach, echoing_strike REACH 22.1);
    `landing_mark`: macros/hunt.py LANDING_MARK; `every_move`: combat/pack.py DM_AFTER_EVERY_MOVE (R1); `no_burn`:
    combat/pack.py DM_MOVE_NO_BURN."""
    from inventory_tracking.builds.warlock import mark as mark_module

    monkeypatch.setattr(mark_module, 'why_not', lambda facts, monster: None)  # the mark's worth is not asked here
    monkeypatch.setattr(pack, 'HERALD_MARK_FIRST', on)
    monkeypatch.setattr(pack, 'HERALD_MARK_ANY_MEMBER', any_member)
    monkeypatch.setattr(pack, 'HERALD_MARK_NO_BURN', True)
    monkeypatch.setattr(hunt_module, 'MARK_WITH_PRESS', with_press)
    monkeypatch.setattr(hunt_module, 'LANDING_MARK', landing_mark)
    monkeypatch.setattr(pack, 'DM_AFTER_EVERY_MOVE', every_move)
    monkeypatch.setattr(pack, 'DM_MOVE_NO_BURN', no_burn)
    mods = (MANA_BURN,) if burner else ()
    (a, b, c) = FAR if far else NEAR
    members = (
        foe(10, *a, flags=MINION, tier=tier, life=900, max_life=900, modifiers=mods),
        foe(11, *b, flags=MINION, tier=tier, life=900, max_life=900, modifiers=mods),
    )
    if herald:
        members += (foe(12, *c, flags=UNIQUE, tier=tier, life=900, max_life=900, modifiers=mods),)
    play = game(*members, demon(x=4999.0, y=5001.0))
    CLOCK[:] = [play.clock]
    START[:] = [play.clock.now]
    play.toughness.update({10: 50, 11: 50, 12: 50})  # they stand the bout out
    hunt = hunter(play, pursuit=False)
    order: list[str] = []
    play.marks, play.strikes = Timed('mark', order, play.clock), Timed('strike', order, play.clock)
    run = play.run()
    run.actuator.drift, run.actuator.steady = 10**6, False
    if landed is not None:
        pack.hopped(play.clock.now - landed, 20.0)
    play.arrivals.append((play.clock.now + until, run.cancelled.set))
    with pytest.raises(Abort, match='cancelled'):
        hunt.attack_mode(run, keys)
    return play, order


def test_off_the_strike_goes_first_and_the_mark_under_it(monkeypatch) -> None:
    _play, order = played(monkeypatch, on=False)
    assert 'mark' in order
    assert order[0] == 'strike'


def test_on_at_a_t5_herald_fight_s_landing_the_mark_goes_first_then_the_strike(monkeypatch) -> None:
    play, order = played(monkeypatch, on=True)
    assert order[0] == 'mark'
    first = order.index('strike')
    # one mark (its key and the fake's confirming press, buffs.py QUICK_CONFIRM) on the pack's member the mark rules
    # pick, then the strike at the next look
    assert set(play.marks[:first]) in ({10}, {11}, {12})
    assert first <= 2


@pytest.mark.parametrize(('tier', 'landed'), [(4, 0.1), (5, None), (5, pack.LANDING_AHEAD + 0.5)])
def test_on_a_tier_4_pack_or_no_landing_keeps_the_strike_first(monkeypatch, tier, landed) -> None:
    _play, order = played(monkeypatch, on=True, tier=tier, landed=landed)
    assert order[0] == 'strike'


def test_on_the_fight_casts_hold_keeps_the_strike_first(monkeypatch) -> None:
    # Melee blows that take the life can come in reach (macros/hunt.py FIGHT_CAST_REACH): no mark before the press
    monkeypatch.setattr(hunt_module.Hunter, 'fight_facts', _barred(hunt_module.Hunter.fight_facts))
    _play, order = played(monkeypatch, on=True)
    assert order[0] == 'strike'


def test_on_a_t5_pack_without_its_herald_in_the_read_keeps_the_strike_first(monkeypatch) -> None:
    # The ruling's scope ("against T5 heralds"): the minions alone, the Herald dead or out of the read
    _play, order = played(monkeypatch, on=True, herald=False)
    assert order[0] == 'strike'


def test_the_wide_form_marks_first_on_the_minions_alone(monkeypatch) -> None:
    # HERALD_MARK_ANY_MEMBER: any tier 5 member in reach, as live from 18:49
    _play, order = played(monkeypatch, on=True, herald=False, any_member=True)
    assert order[0] == 'mark'


def test_on_a_mana_burning_herald_pack_keeps_the_strike_first(monkeypatch) -> None:
    # HERALD_MARK_NO_BURN (the arena's manaburn seed 3: the mark first died, the strike first lived): drainers about
    _play, order = played(monkeypatch, on=True, burner=True)
    assert order[0] == 'strike'


def test_on_the_safety_s_burn_leave_keeps_the_strike_first(monkeypatch) -> None:
    # The safety's burn leave standing (macros/safety.py `burn_leaving`), no drainer in the read
    monkeypatch.setattr(hunt_module.Hunter, 'burning', lambda self, world, foes: True)
    _play, order = played(monkeypatch, on=True)
    assert order[0] == 'strike'


def _barred(fight_facts):
    from dataclasses import replace

    def barred(self, *args, **kwargs):
        return replace(fight_facts(self, *args, **kwargs), cast_barred='blows of 9999 of 2000 can come within 0.5 s')

    return barred


def looks_between(monkeypatch, **kw) -> int:
    """The fight's looks (each asks `Hunter.bout_reach`) after the strike's first press and before the first mark."""
    chosen: list[float] = []
    reach = hunt_module.Hunter.bout_reach

    def counted(self, *args, **kwargs):
        chosen.append(self.clock_now())
        return reach(self, *args, **kwargs)

    monkeypatch.setattr(hunt_module.Hunter, 'bout_reach', counted)
    monkeypatch.setattr(hunt_module.Hunter, 'clock_now', lambda self: CLOCK[0].now, raising=False)
    play, order = played(monkeypatch, on=False, **kw)
    assert order[0] == 'strike'
    assert play.marks
    strikes, marks = play.strikes, play.marks
    assert isinstance(strikes, Timed)
    assert isinstance(marks, Timed)
    return sum(1 for at in chosen if strikes.at[0] <= at < marks.at[0])  # the fake notes a strike at its cast


CLOCK: list = []
START: list = []  # the fake clock when `played` began


@pytest.mark.parametrize('with_press', [False, True])
def test_with_press_the_mark_is_decided_in_the_look_that_pressed_the_strike(monkeypatch, with_press) -> None:
    # A Herald pack's member is the designated one after a jump (builds/warlock/mark.py `pack_designated`): off, its
    # mark is decided a FRAME and a whole look after the strike's press (live: 41 + 81 ms p50); on, in the look that
    # pressed it, once its cast shows. The strike stays first either way (HERALD_MARK_FIRST off).
    looks = looks_between(monkeypatch, with_press=with_press, tier=4)
    assert (looks == 0) == with_press


@pytest.mark.parametrize(
    ('kind', 'burns'),
    [('plain', False), ('mana burn', True), ('drainer by type', True), ('far mana burn', False), ('burn leave', True)],
)
def test_burning_reads_the_game_s_own_monster_records(kind, burns) -> None:
    # Hunter.burning on game/records.py Monsters as the read gives them (txt_id, modifiers, x, y), not the safety's
    # Hostile: a drainer within PACK_SEEN (Mana Burn, or a type that drains, Dark Shape 42), or the safety's burn leave
    from inventory_tracking.game.records import Monster

    far = pack.PACK_SEEN + 5.0 if kind == 'far mana burn' else 8.0
    txt = 42 if kind == 'drainer by type' else 19
    mods = (MANA_BURN,) if 'mana burn' in kind else ()
    member = foe(10, 5000.0 + far, 5000.0, txt_id=txt, flags=MINION, tier=5, modifiers=mods)
    assert type(member) is Monster
    play = game(member)
    hunt = hunter(play, pursuit=False)
    if kind == 'burn leave':
        hunt.safety.burn_leaving = 'mana 10 of 400, mana burn 120 0.5 s ago, 1 drainers in reach'
    assert hunt.burning(play.world, [member]) is burns


@pytest.mark.parametrize(
    ('landing_mark', 'landed', 'marks'), [(True, 0.1, True), (False, 0.1, False), (True, None, False)]
)
def test_landing_mark_marks_a_t5_pack_on_the_screen_beyond_the_strike_s_reach(
    monkeypatch, landing_mark, landed, marks
) -> None:
    # macros/hunt.py LANDING_MARK (take 20261024T161813Z-108, 19:20:30.723: the pack 22.6-29.2 off, nothing of it in
    # the strike's reach): Death Mark has no range of its own (skills.txt range "none"), the member on the screen is
    # marked at the landing; off, or with no landing, nothing in reach is no fight and no mark
    play, order = played(monkeypatch, on=True, far=True, landing_mark=landing_mark, landed=landed, until=1.0)
    assert bool(play.marks) is marks
    assert 'strike' not in order  # nothing within the strike's reach
    if marks:
        marked = play.marks
        assert isinstance(marked, Timed)
        assert set(marked) <= {10, 11, 12}
        assert marked.at[0] - START[0] < 0.5  # at the landing, not a look later


def test_r1_marks_first_at_a_hard_fight_s_landing_the_pack_beyond_the_strike(monkeypatch, caplog) -> None:
    # R1 (DM_AFTER_EVERY_MOVE, the player ~20:24: "you need to cast DM after the TP"): HERALD_MARK_FIRST and
    # LANDING_MARK off, the T5 pack 23.5-25.1 off: the landing's hook casts the mark before any strike
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        play, order = played(monkeypatch, on=False, far=True, every_move=True, until=1.0)
    assert play.marks
    assert order[0] == 'mark'
    assert 'a hard fight (DM_AFTER_EVERY_MOVE)' in caplog.text


@pytest.mark.parametrize('no_burn', [False, True])
def test_r1_s_landing_mark_keeps_off_a_mana_burning_pack_with_no_burn(monkeypatch, caplog, no_burn) -> None:
    # DM_MOVE_NO_BURN covers the landing's hook too (macros/hunt.py `landing_members`, 2026-10-24 ~23:10): without it
    # the landing's mark among the Dark Shapes killed test_manaburn_death.py's seeds 1 and 3 with R1 on
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        played(monkeypatch, on=False, far=True, burner=True, every_move=True, no_burn=no_burn, until=1.0)
    assert ('a hard fight (DM_AFTER_EVERY_MOVE)' in caplog.text) is not no_burn


def test_r1_leaves_a_regular_fight_s_landing_to_the_mark_s_own_rules(monkeypatch) -> None:
    # The player ~20:27: "we don't need to cast DM like every second for regular enemies": tier 0, three of a pack
    _play, before = played(monkeypatch, on=False, tier=0, every_move=False)
    _play, after = played(monkeypatch, on=False, tier=0, every_move=True)
    assert after == before


def test_landing_mark_only_with_herald_mark_first(monkeypatch) -> None:
    play, _order = played(monkeypatch, on=False, far=True, landing_mark=True, until=1.0)
    assert not play.marks


@pytest.mark.parametrize(
    ('waits', 'pressed_after', 'held'), [(True, False, True), (True, True, False), (False, False, False)]
)
def test_landing_upkeep_waits_for_the_strike_after_a_t5_landing(monkeypatch, waits, pressed_after, held) -> None:
    # LANDING_UPKEEP_WAITS (the same take: Psychic Ward's upkeep cast put the fight's first look 0.53 s after the
    # landing): the upkeep waits at a T5 Herald landing until the strike is pressed after the jump
    monkeypatch.setattr(hunt_module, 'LANDING_UPKEEP_WAITS', waits)
    member = foe(10, 5008.0, 5000.0, flags=MINION, tier=5)
    play = game(member)
    hunt = hunter(play, pursuit=False)
    run = play.run()
    pack.hopped(play.clock.now - 0.1, 20.0)
    hunt.pressed_at = play.clock.now if pressed_after else -1.0
    monkeypatch.setattr(hunt_module.Hunter, 'landing_members', lambda self, run, world, foes: list(foes))
    asked: list[bool] = []
    monkeypatch.setattr(hunt.buffs, 'first', lambda *args, **kwargs: asked.append(True))
    assert hunt.upkeep(run, play.world, [member], keys) is False
    assert (not asked) is held
