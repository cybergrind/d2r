"""Death Mark and the Defiler with a tier 4-5 Herald pack (builds/warlock/mark.py `pack_target`, defiler.py
`pack_gate`; combat/pack.py). The player, 2026-10-21 ~10:00: Q1 "the nearest pack member that can be clicked, the
Herald when it can be, no lock-out"; Q6 "a missing Defiler is summoned even under attack, from range". H-A of
09:30:41 (rca/2026-10-21/herald-fight-findings.md §1.1): three keys on a T5 Herald behind its minions took nowhere,
then the mark was locked out for 11.8 s and the pack ran 17.8 s with no mark."""

from inventory_tracking.builds.warlock import defiler as defiler_module, mark
from inventory_tracking.builds.warlock.skills import DEATH_MARK
from inventory_tracking.combat import pack
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.build import BuffFacts, DrawPrice
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, world


NOW = 100.0
GREAT_MARSH = 77
NOBODY = 0xFFFFFFFF
UNIQUE, MINION = 0x08, 0x10


def hulk(unit: int, x: float, y: float, flags: int = MINION, tier: int = 5) -> Monster:
    return Monster(unit, 128, 1, x, y, NOBODY, flags, life=128, max_life=128, tier=tier)


def demon(unit: int, txt: int, x: float, y: float) -> Monster:
    return Monster(unit, txt, 1, x, y, NOBODY, 0, ally=True, life=128, max_life=128)


# The character stands at (5000, 5000) (tests/.../macros/fakes.py `player`); the Herald 14 east.
HERALD = hulk(1, 5014.0, 5000.0, UNIQUE)
BEHIND = hulk(2, 5010.0, 4994.0)  # 11.7 off, drawn behind the Herald (x + y smaller), 7.2 from it
IN_FRONT = hulk(3, 5016.0, 5001.0)  # drawn in front of the Herald, 2.2 from it: the pointer on it names this one
FAR = hulk(4, 5017.0, 4990.0)  # 19.7 off
AT_HAND = (demon(70, 744, 5001.0, 5000.5), demon(71, 189, 5000.0, 5000.0))  # the Defiler and the Urdar by the character


def facts(*foes: Monster, demons=AT_HAND, cast_at=None, missed=None, draws=None) -> BuffFacts:
    seen = world(GREAT_MARSH, slots=HUNT_SLOTS, monsters=(*foes, *demons))
    return BuffFacts(
        seen, NOW, tuple(foes), tuple(foes), cast_at=cast_at or {}, missed=missed or {}, draws=draws
    )  # fmt: skip


def test_the_herald_is_marked_when_it_can_be_clicked_though_a_minion_is_nearer() -> None:
    assert mark.target(facts(HERALD, BEHIND, FAR)) == HERALD


def test_a_herald_covered_by_a_minion_in_front_leaves_the_mark_to_the_nearest_member_that_can_be_clicked() -> None:
    assert mark.target(facts(HERALD, BEHIND, IN_FRONT, FAR)) == BEHIND


def test_a_key_that_took_nowhere_goes_next_on_another_member_with_no_lock_out() -> None:
    # Three keys on the Herald, none shown: the executor kept its clock (the lock-out of macros/buffs.py `settle`)
    cast_at = {(DEATH_MARK, HERALD.unit_id): NOW - 2.0, (DEATH_MARK, None): NOW - 2.0}
    missed = {(DEATH_MARK, HERALD.unit_id): 3}
    asked = facts(HERALD, BEHIND, FAR, cast_at=cast_at, missed=missed)
    assert mark.target(asked) == BEHIND
    # Before: the Herald counted as marked for 11.76 s and nothing else was marked
    assert mark.marked(asked) == [HERALD]


def test_a_mark_whose_check_is_pending_is_taken_to_last() -> None:
    cast_at = {(DEATH_MARK, BEHIND.unit_id): NOW - 0.3, (DEATH_MARK, None): NOW - 0.3}
    missed = {(DEATH_MARK, BEHIND.unit_id): 1}  # an earlier key on it did not take; this one is still looked for
    assert mark.pack_lasts(facts(HERALD, BEHIND, cast_at=cast_at, missed=missed), BEHIND)
    assert mark.target(facts(HERALD, BEHIND, cast_at=cast_at, missed=missed)) is None


def test_while_a_mark_lasts_and_the_pack_is_on_the_demons_nothing_is_marked_again() -> None:
    holding = (demon(70, 744, 5011.0, 4996.0), demon(71, 189, 5012.0, 4997.0))  # 11-12 off, by the pack
    cast_at = {(DEATH_MARK, BEHIND.unit_id): NOW - 5.0, (DEATH_MARK, None): NOW - 5.0}
    assert mark.target(facts(HERALD, BEHIND, FAR, demons=holding, cast_at=cast_at)) is None


def test_while_a_mark_lasts_and_the_pack_still_comes_at_the_character_it_is_marked_again() -> None:
    close = hulk(5, 5006.0, 5000.0)  # 6 off, the demons at the character: it goes for the character
    cast_at = {(DEATH_MARK, BEHIND.unit_id): NOW - 5.0, (DEATH_MARK, None): NOW - 5.0}
    assert mark.target(facts(HERALD, BEHIND, close, cast_at=cast_at)) == HERALD
    soon = {(DEATH_MARK, BEHIND.unit_id): NOW - 1.0, (DEATH_MARK, None): NOW - 1.0}  # within MARK_AGAIN
    assert mark.target(facts(HERALD, BEHIND, close, cast_at=soon)) is None


def test_a_plain_minion_of_the_pack_is_marked_whatever_the_safetys_price(monkeypatch) -> None:
    price = DrawPrice(BEHIND.unit_id, -0.5, -0.01, 0.1, 0.37, 1.9)  # priced as not paying, no pressure
    asked = facts(HERALD, BEHIND, draws={BEHIND.unit_id: price})
    assert mark.why_not(asked, BEHIND) is None
    monkeypatch.setattr(pack, 'MARK_ANY_MEMBER', False)
    assert mark.why_not(asked, BEHIND) is not None


def test_with_the_switch_off_the_herald_comes_first_as_before(monkeypatch) -> None:
    monkeypatch.setattr(pack, 'MARK_ANY_MEMBER', False)
    assert mark.target(facts(HERALD, BEHIND, IN_FRONT, FAR)) == HERALD


def test_a_tier_3_pack_is_left_to_the_rules_before() -> None:
    low = hulk(1, 5014.0, 5000.0, UNIQUE, tier=3)
    assert not mark.pack_marked(facts(low, hulk(2, 5010.0, 4994.0, tier=3)))


def test_a_missing_defiler_is_summoned_from_range_whatever_its_price() -> None:
    alone = (demon(71, 189, 5000.0, 5000.0),)
    at_range = facts(HERALD, BEHIND, FAR, demons=alone)
    assert defiler_module.pack_gate(at_range)
    assert defiler_module.worth_a_defiler(at_range, None)
    pressed = facts(HERALD, hulk(5, 5004.0, 5000.0), demons=alone)  # a member on the character within 10
    assert not defiler_module.pack_gate(pressed)
    assert not defiler_module.pack_gate(facts(hulk(1, 5014.0, 5000.0, UNIQUE, tier=0), demons=alone))


def test_with_the_gate_off_the_defiler_goes_by_its_price(monkeypatch) -> None:
    monkeypatch.setattr(pack, 'DEMON_GATE', False)
    assert not defiler_module.pack_gate(facts(HERALD, BEHIND, FAR, demons=(demon(71, 189, 5000.0, 5000.0),)))


# -- the mark again after a hop (the player, 2026-10-21 ~21:05: "when we're teleporting - our minions are teleporting
# with us and stop attacking ... if you reposition - re-aggro again"; since 2026-10-22 the one designation's rule,
# mark.py DESIGNATED_MARK `aggro_lost`, which retired REMARK_AFTER_HOP and MARK_HELD_LEADER) --


def test_after_a_hop_the_held_member_is_marked_again_at_once_whatever_its_time_left(monkeypatch) -> None:
    monkeypatch.setattr(pack, 'DM_AFTER_EVERY_MOVE', False)  # the mark's own rules (R1 on: `test_r1_*` below)
    marked_at = {(DEATH_MARK, None): NOW - 3.0, (DEATH_MARK, BEHIND.unit_id): NOW - 3.0}
    asked = facts(HERALD, BEHIND, IN_FRONT, cast_at=marked_at)
    assert mark.target(asked) is None  # a mark lasts on BEHIND, the pack not pressing: kept, as before
    pack.hopped(NOW - 0.4, 14.0)  # a keep-range Teleport landed 0.4 s ago
    assert mark.target(asked) == BEHIND
    assert mark.worth_a_mark(asked, BEHIND)
    pack.hopped(NOW - 0.4, 2.0)  # a side step takes no demon along
    assert mark.target(asked) is None
    pack.hopped(NOW - 3.5, 14.0)  # a hop before the mark's key
    assert mark.target(asked) is None
    pack.hopped(
        NOW - 2.5, 14.0
    )  # long ago but after the key, nothing keyed since: the demons still idle by the character
    assert mark.target(asked) == BEHIND
    monkeypatch.setattr(mark, 'DESIGNATED_MARK', False)  # before the model (REMARK_AFTER_HOP was off)
    assert mark.target(asked) is None


def test_after_a_hop_marked_once_more_and_not_again_and_with_no_held_one_the_packs_first_member() -> None:
    pack.hopped(NOW - 0.4, 14.0)
    after = {(DEATH_MARK, None): NOW - 0.2, (DEATH_MARK, BEHIND.unit_id): NOW - 0.2}  # the re-mark keyed after landing
    assert mark.target(facts(HERALD, BEHIND, cast_at=after)) is None
    long_ago = {(DEATH_MARK, None): NOW - 30.0, (DEATH_MARK, BEHIND.unit_id): NOW - 30.0}  # run out
    assert mark.target(facts(HERALD, BEHIND, IN_FRONT, FAR, cast_at=long_ago)) == BEHIND  # pack_target's order
    assert not mark.worth_a_mark(facts(HERALD, BEHIND, demons=()), BEHIND)  # no demon to send


def test_in_a_herald_pack_the_packs_order_goes_before_the_leader_the_strike_holds(monkeypatch) -> None:
    from inventory_tracking.builds.warlock.echoing_strike.attack import ECHOING_STRIKE_ATTACK

    monkeypatch.setattr(pack, 'DM_AFTER_EVERY_MOVE', False)  # the mark's own rules (R1 on: `test_r1_*` below)
    # MARK_HELD_LEADER (off, retired 2026-10-22): the pack's own order holds in a tier 4-5 pack; with True the pack
    # spread off the demons in the arena's seed 3 of the T5 hulks (rca/2026-10-21/arachnid-herald-2-findings.md §13)
    monkeypatch.setattr(ECHOING_STRIKE_ATTACK.held, 'unit', IN_FRONT.unit_id)  # held: a minion drawn in front
    assert mark.target(facts(HERALD, BEHIND, IN_FRONT, FAR)) == BEHIND
    lasting = {(DEATH_MARK, None): NOW - 3.0, (DEATH_MARK, BEHIND.unit_id): NOW - 3.0}
    assert mark.target(facts(HERALD, BEHIND, IN_FRONT, FAR, cast_at=lasting)) is None  # its mark lasts: kept


def test_after_a_hop_no_mark_again_when_no_demon_came_along(monkeypatch) -> None:
    monkeypatch.setattr(pack, 'DM_AFTER_EVERY_MOVE', False)  # the mark's own rules (R1 on: `test_r1_*` below)
    # The arena's T5 hulks, seed 3: the approach hops took no demon along; a mark again after each cost the sigil's
    # cover (held share 0.844 against 0.85; rca/2026-10-21/arachnid-herald-2-findings.md §13)
    pack.hopped(NOW - 0.4, 14.0)
    marked_at = {(DEATH_MARK, None): NOW - 3.0, (DEATH_MARK, BEHIND.unit_id): NOW - 3.0}
    away = (demon(70, 744, 5030.0, 5000.0), demon(71, 189, 5031.0, 5001.0))  # 30 off, on the far side
    assert not mark.aggro_lost(facts(HERALD, BEHIND, IN_FRONT, demons=away, cast_at=marked_at), BEHIND)
    assert mark.target(facts(HERALD, BEHIND, IN_FRONT, demons=away, cast_at=marked_at)) is None
    assert mark.aggro_lost(facts(HERALD, BEHIND, IN_FRONT, cast_at=marked_at), BEHIND)  # AT_HAND: came along
    assert mark.target(facts(HERALD, BEHIND, IN_FRONT, cast_at=marked_at)) == BEHIND
    by_it = (demon(70, 744, 5011.0, 4995.0), demon(71, 189, 5009.0, 4994.0))  # within 10 of the character, on it
    assert not mark.aggro_lost(facts(HERALD, BEHIND, IN_FRONT, demons=by_it, cast_at=marked_at), BEHIND)


def test_r1_a_mark_lasting_holds_nothing_back_with_the_demons_idle_by_the_character(monkeypatch) -> None:
    # R1 (combat/pack.py DM_AFTER_EVERY_MOVE; the player 2026-10-24 ~20:24, "cast DM after the TP, so daemon is
    # forced to attack"): the demons by the character (AT_HAND) with a mark lasting on BEHIND, MARK_AGAIN gone: again
    monkeypatch.setattr(pack, 'DM_AFTER_EVERY_MOVE', True)
    lasting = {(DEATH_MARK, None): NOW - 3.0, (DEATH_MARK, BEHIND.unit_id): NOW - 3.0}
    asked = facts(HERALD, BEHIND, IN_FRONT, FAR, cast_at=lasting)
    assert mark.move_reason(asked) == mark.PETS_SAID
    assert mark.target(asked) == BEHIND  # the held one again: the rules' own pick
    assert mark.worth_a_mark(asked, BEHIND)
    soon = {(DEATH_MARK, None): NOW - 0.5, (DEATH_MARK, BEHIND.unit_id): NOW - 0.5}
    assert mark.target(facts(HERALD, BEHIND, IN_FRONT, FAR, cast_at=soon)) is None  # PETS_AGAIN not gone


def test_r1_after_a_hop_that_pulled_the_demons_back_the_mark_goes_out_once(monkeypatch) -> None:
    # R1 (the player ~20:24: "cast DM after the TP, so daemon is forced to attack"): a hop of REMARK_HOP or more that
    # took the demons along (AT_HAND, idle by the character) has the mark out at once, whatever the curse's state on
    # the old target; one key after the landing ends it. A hop that left them 30 off on their monsters is no reason
    # (2026-10-25: the arena's Baal chamber, 7 marks after moves with the Defiler 2.8 off Baal)
    monkeypatch.setattr(pack, 'DM_AFTER_EVERY_MOVE', True)
    pack.hopped(NOW - 0.4, 14.0)
    marked_at = {(DEATH_MARK, None): NOW - 1.0, (DEATH_MARK, BEHIND.unit_id): NOW - 1.0}  # under PETS_AGAIN
    asked = facts(HERALD, BEHIND, IN_FRONT, cast_at=marked_at)
    assert mark.move_reason(asked) == mark.MOVE_SAID
    assert mark.target(asked) is not None
    after = {(DEATH_MARK, None): NOW - 0.2, (DEATH_MARK, BEHIND.unit_id): NOW - 0.2}  # keyed after the landing
    assert mark.move_reason(facts(HERALD, BEHIND, IN_FRONT, cast_at=after)) is None
    away = (demon(70, 744, 5030.0, 5000.0), demon(71, 189, 5031.0, 5001.0))
    assert mark.move_reason(facts(HERALD, BEHIND, IN_FRONT, demons=away, cast_at=marked_at)) is None
