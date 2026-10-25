"""The pack's re-aggro with nobody designated (builds/warlock/mark.py REAGGRO_PACK), the mark at the landing before the
press (combat/pack.py MARK_AT_LANDING) and the demons' drag on a forgoable jump's price (combat/pack.py HOP_DRAG_PRICE),
2026-10-24. The player, ~11:30: "heralds/packs loose their aggro on minions and daemon/merc are staying not active for
some time after teleport"; 2026-10-21: "if you reposition - re-aggro again" (rca/2026-10-24/aggro-findings.md)."""

import logging
from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock import mark
from inventory_tracking.builds.warlock.skills import DEATH_MARK
from inventory_tracking.combat import pack
from tests.inventory_tracking.builds.warlock.test_designation import NOW, demon, facts as plain_facts, foe, keyed


PLAIN = 0x00
# A plain pack (no Herald, no immune, no leader) of Thorned Hulks 12-14 off; the demons by the character after a jump
PACK = tuple(foe(10 + i, 310, (5012.0 + i, 5002.0 + i % 2), flags=PLAIN) for i in range(3))
STRAY = foe(20, 310, (4985.0, 4990.0), flags=PLAIN)  # one apart from the rest
ALONG = (demon(70, 189, (5001.0, 5000.5)), demon(71, 744, (5000.5, 4999.0)))
STRIKING = (demon(70, 189, (5012.5, 5004.0)), demon(71, 744, (5013.0, 5000.5)))


def facts(*foes, **kw):
    """As the live fight asks: the safety's prices fresh, none of these priced (a plain pack the price leaves)."""
    return replace(plain_facts(*foes, **kw), draws={})


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setattr(mark, 'REAGGRO_PACK', True)


def test_off_a_plain_pack_after_a_jump_is_not_marked(monkeypatch) -> None:
    monkeypatch.setattr(mark, 'REAGGRO_PACK', False)  # on in the tree since 2026-10-24
    pack.hopped(NOW - 0.3, 20.0)
    assert mark.target(facts(*PACK, demons=ALONG)) is None
    assert mark.DESIGNATION.unit is None


def test_after_a_jump_the_pack_member_with_the_most_round_it_is_marked_at_once(on, caplog) -> None:
    caplog.set_level(logging.INFO)
    pack.hopped(NOW - 0.3, 20.0)
    asked = facts(*PACK, STRAY, demons=ALONG)
    chosen = mark.target(asked)
    # one with the whole pack within MARK_PACK (the nearest of those), not the stray
    assert chosen is not None
    assert chosen.unit_id == PACK[0].unit_id
    assert mark.DESIGNATION.rank == mark.REAGGRO_RANK
    assert mark.worth_a_mark(asked, chosen)
    assert mark.mark_ahead(asked)  # before the bout's first strike
    assert "the pack's re-aggro" in caplog.text


def test_marked_it_is_held_until_the_next_jump_takes_the_demons_off_it(on) -> None:
    pack.hopped(NOW - 0.3, 20.0)
    first = mark.target(facts(*PACK, demons=ALONG))
    assert first is not None
    lasting = keyed(first.unit_id, NOW + 0.1)
    held = facts(*PACK, demons=STRIKING, cast_at=lasting, now=NOW + 1.0)
    assert mark.target(held) is None  # the demons are on it
    pack.hopped(NOW + 3.0, 18.0)  # the next jump takes them along again
    again = mark.target(facts(*PACK, demons=ALONG, cast_at=lasting, now=NOW + 3.3))
    assert again is not None
    assert again.unit_id == first.unit_id


def test_no_mark_while_a_demon_strikes_already_nor_long_after_the_jump(on) -> None:
    pack.hopped(NOW - 0.3, 20.0)
    assert mark.target(facts(*PACK, demons=STRIKING)) is None
    pack.hopped(NOW - mark.REAGGRO_AFTER - 0.5, 20.0)
    assert mark.target(facts(*PACK, demons=ALONG)) is None  # no jump of late, and nobody on the character


def test_a_short_jump_or_a_mark_keyed_since_designates_nobody(on) -> None:
    pack.hopped(NOW - 0.3, 2.0)
    assert mark.target(facts(*PACK, demons=ALONG)) is None
    pack.hopped(NOW - 0.3, 20.0)
    since = {(DEATH_MARK, None): NOW - 0.1}
    assert mark.target(facts(*PACK, demons=ALONG, cast_at=since)) is None


def test_without_a_jump_the_pack_on_the_character_with_the_demons_off_it_is_marked(on) -> None:
    close = tuple(foe(30 + i, 310, (5003.0 + i, 5001.0), flags=PLAIN) for i in range(3))
    apart = (demon(70, 189, (4990.0, 4985.0)), demon(71, 744, (4991.0, 4985.0)))
    chosen = mark.target(facts(*close, demons=apart))
    assert chosen is not None
    assert chosen.unit_id in {m.unit_id for m in close}


def test_a_reason_comes_before_the_re_aggro(on) -> None:
    pack.hopped(NOW - 0.3, 20.0)
    leader = foe(40, 310, (5013.0, 5003.0))
    chosen = mark.target(facts(*PACK, leader, demons=ALONG))
    assert chosen is leader
    assert mark.DESIGNATION.rank != mark.REAGGRO_RANK


def test_the_mark_at_the_landing_goes_before_the_press_only_while_on_and_just_landed(monkeypatch) -> None:
    pack.hopped(NOW - 0.3, 20.0)
    assert not pack.landing_ahead(NOW)
    monkeypatch.setattr(pack, 'MARK_AT_LANDING', True)
    assert pack.landing_ahead(NOW)
    assert not pack.landing_ahead(NOW + pack.LANDING_AHEAD)
    assert not pack.landing_ahead(NOW, [HERALD])  # a tier 4-5 Herald pack in reach: the strike stays first
    monkeypatch.setattr(pack, 'LANDING_IN_PACK', True)
    assert pack.landing_ahead(NOW, [HERALD])


def test_a_jump_that_takes_striking_demons_along_costs_the_drag(monkeypatch) -> None:
    here, spot, foes = (5000.0, 5000.0), (5020.0, 5000.0), [(5004.0, 5000.0)]
    by_pack = [(5003.0, 5001.0)]
    assert pack.drag_seconds(here, spot, by_pack, foes) == 0.0  # off
    monkeypatch.setattr(pack, 'HOP_DRAG_PRICE', True)
    assert pack.drag_seconds(here, spot, by_pack, foes) == pack.DRAG_SECONDS
    assert pack.drag_seconds(here, (5002.0, 5000.0), by_pack, foes) == 0.0  # a short jump takes nobody off
    assert pack.drag_seconds(here, spot, [(5003.0, 5030.0)], foes) == 0.0  # idle: nothing lost
    assert pack.drag_seconds(here, spot, [(4980.0, 5000.0)], [(4983.0, 5000.0)]) == 0.0  # not taken along
    assert pack.drag_seconds(here, spot, None, foes) == 0.0  # not attacking


# Take 20261024T084322Z-86, 11:44:23: the tier 5 Undead Stygian Doll Herald (216, unit 3904379104) 15-20 off with
# members within 4 of it, one member apart and nearer: the pack's order marked the member first
DOLL = 216
HERALD = foe(3904379104, DOLL, (5015.0, 5003.0), tier=5)
ROUND_IT = tuple(foe(500 + i, DOLL, (5015.5 + i, 5004.0), flags=0x10, tier=5) for i in range(3))
APART = foe(2681112001, DOLL, (5008.0, 4994.0), flags=0x10, tier=5)


def test_off_the_pack_order_marks_an_uncovered_member_before_the_doll_herald(monkeypatch) -> None:
    monkeypatch.setattr(mark, 'DOLL_HERALD_FIRST', False)  # on in the tree since 2026-10-24
    chosen = mark.target(facts(HERALD, *ROUND_IT, APART, demons=ALONG))
    assert chosen is not None
    assert chosen.unit_id == APART.unit_id


def test_the_doll_herald_is_marked_first_and_again_after_a_jump(monkeypatch) -> None:
    monkeypatch.setattr(pack, 'DM_AFTER_EVERY_MOVE', False)  # the mark's own rules (R1 on: below)
    monkeypatch.setattr(mark, 'DOLL_HERALD_FIRST', True)
    asked = facts(HERALD, *ROUND_IT, APART, demons=ALONG)
    assert mark.target(asked) is HERALD
    assert mark.mark_ahead(asked)
    assert mark.DESIGNATION.rank == mark.HERALD_RANK
    lasting = keyed(HERALD.unit_id, NOW + 0.1)
    assert mark.target(facts(HERALD, *ROUND_IT, APART, demons=STRIKING, cast_at=lasting, now=NOW + 1.0)) is None
    pack.hopped(NOW + 2.0, 15.0)
    assert mark.target(facts(HERALD, *ROUND_IT, APART, demons=ALONG, cast_at=lasting, now=NOW + 2.3)) is HERALD


def test_a_members_mark_lasting_the_doll_herald_goes_after_mark_again(monkeypatch) -> None:
    monkeypatch.setattr(mark, 'DOLL_HERALD_FIRST', True)
    member = keyed(APART.unit_id, NOW - 0.5)
    assert mark.target(facts(HERALD, *ROUND_IT, APART, demons=ALONG, cast_at=member)) is None
    later = keyed(APART.unit_id, NOW - mark.MARK_AGAIN - 0.1)
    assert mark.target(facts(HERALD, *ROUND_IT, APART, demons=ALONG, cast_at=later)) is HERALD


def test_the_doll_herald_the_keys_did_not_take_on_goes_back_to_the_pack_order(monkeypatch) -> None:
    monkeypatch.setattr(mark, 'DOLL_HERALD_FIRST', True)
    failed = {(DEATH_MARK, HERALD.unit_id): mark.MARK_RECASTS}
    chosen = mark.target(facts(HERALD, *ROUND_IT, APART, demons=ALONG, missed=failed))
    assert chosen is not None
    assert chosen.unit_id != HERALD.unit_id


# Take 20261024T102258Z-116, 13:23:50: the tier 5 Herald (class 634, unit 809272624) 19 off with 10 members within 4
# of it, those drawn in front covering it; the pack's order marked members, the Herald only at 13:24:02.8
T5 = 634
T5_HERALD = foe(809272624, T5, (5013.0, 5014.0), tier=5)
ROUND_T5 = tuple(foe(600 + i, T5, (5013.5 + i % 4, 5014.5 + i // 4), flags=0x10, tier=5) for i in range(10))
NEARER = foe(1347195473, T5, (5009.0, 4996.0), flags=0x10, tier=5)


def test_off_a_covered_t5_herald_loses_to_an_uncovered_member(monkeypatch) -> None:
    monkeypatch.setattr(mark, 'HERALD_FIRST', False)
    chosen = mark.target(facts(T5_HERALD, *ROUND_T5, NEARER, demons=ALONG))
    assert chosen is not None
    assert chosen.unit_id != T5_HERALD.unit_id


def test_herald_first_marks_the_covered_t5_herald_and_again_after_a_jump(monkeypatch) -> None:
    monkeypatch.setattr(pack, 'DM_AFTER_EVERY_MOVE', False)  # the mark's own rules (R1 on: below)
    monkeypatch.setattr(mark, 'HERALD_FIRST', True)
    asked = facts(T5_HERALD, *ROUND_T5, NEARER, demons=ALONG)
    assert mark.target(asked) is T5_HERALD
    assert mark.DESIGNATION.rank == mark.HERALD_RANK
    lasting = keyed(T5_HERALD.unit_id, NOW + 0.1)
    assert mark.target(facts(T5_HERALD, *ROUND_T5, NEARER, demons=STRIKING, cast_at=lasting, now=NOW + 1.0)) is None
    pack.hopped(NOW + 2.0, 15.0)
    assert mark.target(facts(T5_HERALD, *ROUND_T5, NEARER, demons=ALONG, cast_at=lasting, now=NOW + 2.3)) is T5_HERALD


def test_herald_first_leaves_a_herald_the_keys_did_not_take_on_to_the_pack_order(monkeypatch) -> None:
    monkeypatch.setattr(mark, 'HERALD_FIRST', True)
    failed = {(DEATH_MARK, T5_HERALD.unit_id): mark.MARK_RECASTS}
    chosen = mark.target(facts(T5_HERALD, *ROUND_T5, NEARER, demons=ALONG, missed=failed))
    assert chosen is not None
    assert chosen.unit_id != T5_HERALD.unit_id


def test_only_death_mark_goes_through_the_fight_casts_hold_and_only_while_on(monkeypatch) -> None:
    from inventory_tracking.builds.warlock.skills import SIGIL_LETHARGY

    assert not pack.through_hold(DEATH_MARK)
    monkeypatch.setattr(pack, 'MARK_THROUGH_HOLD', True)
    assert pack.through_hold(DEATH_MARK)
    assert not pack.through_hold(SIGIL_LETHARGY)


@pytest.mark.parametrize('first', ['DOLL_HERALD_FIRST', 'HERALD_FIRST'])
def test_r1_the_herald_first_rulings_still_pick_the_mark_after_a_move(monkeypatch, first) -> None:
    # R1 (combat/pack.py DM_AFTER_EVERY_MOVE): the target after a move is the mark rules' own pick, so the doll Herald
    # and HERALD_FIRST still decide; the designation is the move's (MOVE_RANK)
    monkeypatch.setattr(pack, 'DM_AFTER_EVERY_MOVE', True)
    monkeypatch.setattr(mark, first, True)
    herald, round_it, apart = (
        (HERALD, ROUND_IT, APART) if first == 'DOLL_HERALD_FIRST' else (T5_HERALD, ROUND_T5, NEARER)
    )
    asked = facts(herald, *round_it, apart, demons=ALONG)
    assert mark.target(asked) is herald
    assert mark.DESIGNATION.rank == mark.MOVE_RANK
