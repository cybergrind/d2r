"""Death Mark again after a Battle Orders rebuff retreat (the coordinator, 2026-10-22, from the player's rulings
"Teleporting drops minion aggro: re-aggro with Death Mark" and "retreat and rebuff", then re-aggro with Death Mark).
Since the one designation (builds/warlock/mark.py DESIGNATED_MARK, 2026-10-22) the rebuff hop is a hop like any other
(`aggro_lost`), its mark after the rebuff's Battle Orders (`rebuff_waits`); `rebuff_target` is the mark before the model
(REMARK_AFTER_REBUFF, retired), kept for the off-and-on measure."""

import math

from inventory_tracking.builds.warlock import mark
from inventory_tracking.builds.warlock.echoing_strike.attack import ECHOING_STRIKE_ATTACK
from inventory_tracking.builds.warlock.skills import DEATH_MARK
from inventory_tracking.combat import pack
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.build import BuffFacts
from inventory_tracking.macros.safety import REBUFF_LANDS, Safety
from inventory_tracking.native.layout import BATTLE_ORDERS_SKILL
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, world


NOW = 100.0
CHOSEN = NOW - 1.5  # the safety chose the rebuff retreat
LANDED = NOW - 1.2  # and its Teleport landed 0.3 s later, 14 off
CAST = NOW - 0.4  # Battle Orders keyed at the landing
GREAT_MARSH = 77
NOBODY = 0xFFFFFFFF
UNIQUE, MINION = 0x08, 0x10


def foe(unit: int, x: float, y: float, flags: int = 0) -> Monster:
    return Monster(unit, 128, 1, x, y, NOBODY, flags, life=128, max_life=128, tier=0)


def demon(unit: int, txt: int, x: float, y: float) -> Monster:
    return Monster(unit, txt, 1, x, y, NOBODY, 0, ally=True, life=128, max_life=128)


# The character stands at (5000, 5000) (tests/.../macros/fakes.py `player`)
NEAR_LEADER = foe(1, 5012.0, 5000.0, UNIQUE)  # 12 off
FAR_LEADER = foe(2, 5018.0, 5000.0, UNIQUE)  # 18 off
TRASH = foe(3, 5006.0, 5000.0)  # 6 off, no leader
AT_HAND = (demon(70, 744, 5001.0, 5000.5), demon(71, 189, 5000.0, 5000.0))


def words(*states: int) -> bytes:
    raw = bytearray(32)
    for state in states:
        word, bit = divmod(state, 32)
        raw[word * 4 : word * 4 + 4] = (int.from_bytes(raw[word * 4 : word * 4 + 4], 'little') | 1 << bit).to_bytes(
            4, 'little'
        )
    return bytes(raw)


def facts(
    *foes: Monster,
    orders: float | None = CAST,
    marked: float | None = None,
    on: Monster | None = None,
    landed: float = LANDED,
    shown=(),
    demons=AT_HAND,
) -> BuffFacts:
    seen = world(GREAT_MARSH, slots=HUNT_SLOTS, monsters=(*foes, *demons))
    # The Battle Orders and Death Mark keys' clocks (None: none keyed)
    cast: dict[tuple[int, int | None], float] = {}
    for skill, at in ((BATTLE_ORDERS_SKILL, orders), (DEATH_MARK, marked)):
        if at is not None:
            cast[skill, None] = at
    if on is not None and marked is not None:
        cast[DEATH_MARK, on.unit_id] = marked  # the mark keyed on that one
    return BuffFacts(
        seen, NOW, tuple(foes), tuple(foes), cast_at=cast, rebuffed=CHOSEN, rebuff_landed=landed,
        states=lambda m: words(mark.MARK_STATE) if m.unit_id in shown else words(),
    )  # fmt: skip


def test_the_safety_keeps_the_rebuff_retreats_landing_only() -> None:
    safety = Safety()
    safety.landed(LANDED)
    assert safety.rebuff_landed == -math.inf  # no rebuff chosen: any other hop
    safety.rebuffed_at = CHOSEN
    safety.landed(CHOSEN - 0.1)  # a hop before the choice
    assert safety.rebuff_landed == -math.inf
    safety.landed(LANDED)
    assert safety.rebuff_landed == LANDED
    safety.landed(LANDED + 0.5)  # the next hop is the pursuit's: the first landing is kept
    assert safety.rebuff_landed == LANDED
    later = Safety(rebuffed_at=CHOSEN)
    later.landed(CHOSEN + REBUFF_LANDS + 0.1)  # landed too long after the choice: not the rebuff's
    assert later.rebuff_landed == -math.inf


def test_after_the_rebuff_hop_and_the_cast_the_designated_leader_is_marked_again() -> None:
    before = NOW - 3.0  # the mark on the near leader, keyed before the rebuff retreat
    pack.hopped(LANDED, 14.0)  # the rebuff's Teleport landed, the demons came along (AT_HAND)
    asked = facts(FAR_LEADER, NEAR_LEADER, TRASH, marked=before, on=NEAR_LEADER)
    assert mark.target(asked) == NEAR_LEADER  # its mark lasts by the clock, but the jump took the demons off it
    assert mark.worth_a_mark(asked, NEAR_LEADER)
    pack.hopped(before - 1.0, 14.0)  # only a hop before the mark: the demons hold it, its state words show it
    assert mark.target(facts(FAR_LEADER, NEAR_LEADER, TRASH, marked=before, on=NEAR_LEADER, shown=(1,))) is None
    assert mark.target(asked) == NEAR_LEADER  # the words show no mark on it: run out, due again
    pack.hopped(LANDED, 14.0)
    keyed = facts(FAR_LEADER, NEAR_LEADER, TRASH, marked=NOW, on=NEAR_LEADER)  # the line is said after the key
    assert mark.target(keyed) is None  # marked again after the landing: once
    said = mark.mark_said(keyed, NEAR_LEADER)
    assert said is not None
    assert 'designated: a pack leader' in said
    other = mark.mark_said(keyed, FAR_LEADER)
    assert other is not None
    assert 'designated' not in other


def test_the_mark_at_a_rebuff_landing_waits_for_the_battle_orders_cast_there() -> None:
    pack.hopped(LANDED, 14.0)
    lasting = {'marked': NOW - 3.0, 'on': NEAR_LEADER}
    assert mark.target(facts(NEAR_LEADER, orders=None, **lasting)) is None  # 1.2 s: the cast is still to come
    waited = NOW - mark.REBUFF_CAST_WAIT - 0.1
    pack.hopped(waited, 14.0)
    assert mark.target(facts(NEAR_LEADER, orders=None, landed=waited, **lasting)) == NEAR_LEADER


def test_the_leader_the_strike_holds_comes_first(monkeypatch) -> None:
    monkeypatch.setattr(ECHOING_STRIKE_ATTACK.held, 'unit', FAR_LEADER.unit_id)
    assert mark.rebuff_target(facts(FAR_LEADER, NEAR_LEADER, TRASH)) == FAR_LEADER


def test_no_mark_while_it_still_shows_on_the_target(monkeypatch) -> None:
    assert mark.rebuff_target(facts(NEAR_LEADER, shown=(NEAR_LEADER.unit_id,))) is None
    monkeypatch.setattr(ECHOING_STRIKE_ATTACK.held, 'unit', FAR_LEADER.unit_id)
    assert mark.rebuff_target(facts(FAR_LEADER, NEAR_LEADER, shown=(FAR_LEADER.unit_id,))) is None


def test_it_waits_for_the_cast_at_the_landing_then_marks_without_it() -> None:
    assert mark.rebuff_target(facts(NEAR_LEADER, orders=None)) is None  # 1.2 s: the cast is still to come
    waited = NOW - mark.REBUFF_CAST_WAIT - 0.1
    assert mark.rebuff_target(facts(NEAR_LEADER, orders=None, landed=waited)) == NEAR_LEADER
    assert mark.rebuff_target(facts(NEAR_LEADER, orders=LANDED - 1.0)) is None  # a cast before the landing


def test_once_only_and_only_after_a_rebuff_landing(monkeypatch) -> None:
    assert mark.rebuff_target(facts(NEAR_LEADER, marked=NOW - 0.2)) is None  # marked after the landing
    assert mark.rebuff_target(facts(NEAR_LEADER, landed=-math.inf)) is None  # no rebuff landed: any other hop
    assert mark.rebuff_target(facts(NEAR_LEADER, landed=NOW - mark.REBUFF_REMARK_WITHIN - 0.1)) is None
    assert mark.rebuff_target(facts(NEAR_LEADER, demons=())) is None  # no demon to send
    assert mark.rebuff_target(facts(TRASH)) is None  # no leader in reach
    monkeypatch.setattr(mark, 'DESIGNATED_MARK', False)  # before the model: the rebuff hop's rule
    assert mark.target(facts(FAR_LEADER, NEAR_LEADER, TRASH, marked=NOW - 3.0, on=NEAR_LEADER)) == NEAR_LEADER
