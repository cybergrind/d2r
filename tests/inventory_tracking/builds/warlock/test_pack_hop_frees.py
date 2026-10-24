"""The Herald marks that went after the strike at a landing (2026-10-24, rca/2026-10-24/dm-latency-findings.md §8),
replayed on the takes' own frames: builds/warlock/mark.py PACK_HOP_FREES, macros/hunt.py HERALD_MARK_SHOWN and
SETTLE_BEFORE_FIRST."""

import math
from types import SimpleNamespace

import pytest

from inventory_tracking.builds.warlock import mark
from inventory_tracking.builds.warlock.skills import DEATH_MARK
from inventory_tracking.combat import pack
from inventory_tracking.game.records import Monster
from inventory_tracking.game.view import Viewport
from inventory_tracking.macros import hunt as hunt_module
from inventory_tracking.macros.build import BuffFacts


PLAYER = 809342382
NOBODY = 0xFFFFFFFF
REACH = 22.08  # echoing_strike REACH: those nearer are in reach (no wall on these frames)
ASPECT = 2560 / 1418  # the player's window


def monster(unit, txt, x, y, flags, tier, life, *, ally=False):
    return Monster(unit, txt, 1, x, y, NOBODY, flags, ally=ally, life=life, max_life=128, tier=tier)


# Take 20261024T155059Z-113, the look that pressed the strike 147 ms after the landing at 18:52:58.418 (a Teleport of
# 16.0): the last mark (5.80 s before, on 1107037081, 25.0 off) had gone onto a neighbour ("did not take", settled at
# 18:52:58.889), the members within the strike's reach were not designated
CASE_1852 = SimpleNamespace(
    here=(10102.5, 5191.5),
    hop=16.0,
    look=0.147,
    foes=(
        monster(1556751232, 614, 10093.5, 5173.12, 0, 0, 128),
        monster(3626906257, 631, 10078.93, 5190.81, 8, 5, 115),  # the Herald, 23.6 off
        monster(2680240532, 631, 10068.5, 5210.78, 16, 5, 78),
        monster(1107037081, 631, 10078.5, 5184.5, 16, 5, 117),  # marked 5.80 s before, 25.0 off
        monster(528659241, 631, 10052.5, 5202.5, 16, 5, 63),
        monster(778375616, 614, 10094.5, 5174.5, 0, 0, 128),
        monster(4229372232, 631, 10084.93, 5188.94, 16, 5, 76),  # 17.8: in reach
        monster(1340120266, 631, 10075.5, 5193.5, 16, 5, 68),
        monster(2969437644, 631, 10085.78, 5188.16, 16, 5, 67),  # 17.1
        monster(1057334866, 631, 10057.19, 5203.34, 16, 5, 97),
        monster(689701208, 508, 10123.5, 5202.5, 0, 0, 128),
        monster(670051941, 631, 10047.22, 5215.35, 16, 5, 113),
        monster(1484718822, 631, 10085.78, 5188.16, 16, 5, 66),  # 17.1
    ),
    demons=(
        monster(1047338132, 744, 10101.11, 5190.11, 0, 0, 128, ally=True),
        monster(1344187098, 189, 10102.1, 5191.9, 8, 0, 128, ally=True),
    ),
    marks={1107037081: 5.80},
    designated=(1107037081, "the tier 5 Herald pack's member (the pack's order)"),
)
IN_REACH_1852 = {4229372232, 2969437644, 1484718822}

# Take 20261024T162759Z-104, the look 170 ms after the landing at 19:30:51.185 (a Teleport of 18.2): the designated
# member, the elite 82 3241908774 (marked 4.68 s before, 20.9 off), drawn past the aim's limits ("its body is off the
# screen at (0.93, 0.39)")
CASE_1930 = SimpleNamespace(
    here=(5389.57, 4919.57),
    hop=18.2,
    look=0.170,
    foes=(
        monster(1188706955, 310, 5402.5, 4913.5, 0, 0, 15),
        monster(3241908774, 82, 5401.66, 4902.5, 8, 5, 36),
        monster(1531227559, 82, 5393.5, 4903.5, 0, 0, 20),
        monster(4150824372, 82, 5390.5, 4915.5, 0, 0, 15),
        monster(2194909113, 310, 5404.5, 4919.5, 0, 0, 7),
        monster(1692084049, 82, 5399.5, 4908.5, 0, 0, 15),
        monster(3181524691, 82, 5397.5, 4914.5, 0, 0, 15),
        monster(3513365468, 310, 5404.5, 4914.5, 0, 0, 5),
        monster(3055552989, 82, 5382.42, 4905.58, 16, 5, 85),
        monster(2282010472, 82, 5397.5, 4903.5, 16, 5, 5),
        monster(285249261, 82, 5405.36, 4913.13, 16, 5, 47),
        monster(631738227, 310, 5403.5, 4915.5, 0, 0, 5),
        monster(340630133, 82, 5382.5, 4915.5, 0, 0, 10),
        monster(2558535542, 82, 5402.79, 4903.27, 16, 5, 26),
    ),
    demons=(
        monster(2461937872, 744, 5387.93, 4917.93, 0, 0, 128, ally=True),
        monster(1231039863, 189, 5389.5, 4919.5, 8, 0, 128, ally=True),
    ),
    marks={3241908774: 4.68},
    designated=(3241908774, "the tier 5 Herald pack's marked member"),
)

NOW = 1000.0


def facts_of(case, monkeypatch, *, shown_only: bool = False) -> BuffFacts:
    """The case's look: the jump landed `look` s before, the marks' keys (the last one under None too), the
    designation before it; `shown_only`: those in reach drawn inside the aim's limits alone (HERALD_MARK_SHOWN)."""
    player = SimpleNamespace(unit_id=PLAYER, x=case.here[0], y=case.here[1], area=1, mode=1)
    world = SimpleNamespace(player=player, monsters=case.foes + case.demons, slots={DEATH_MARK: 'd'})
    reachable = [m for m in case.foes if math.dist(case.here, (m.x, m.y)) <= REACH]
    if shown_only:
        view = Viewport(ASPECT)
        reachable = [m for m in reachable if view.on_screen(view.body(case.here, m.x, m.y))]
    cast_at = {(DEATH_MARK, unit): NOW - ago for unit, ago in case.marks.items()}
    cast_at[DEATH_MARK, None] = NOW - min(case.marks.values())
    monkeypatch.setattr(pack.HOP, 'at', NOW - case.look)
    monkeypatch.setattr(pack.HOP, 'units', case.hop)
    monkeypatch.setattr(mark.DESIGNATION, 'unit', case.designated[0])
    monkeypatch.setattr(mark.DESIGNATION, 'reason', case.designated[1])
    monkeypatch.setattr(mark.DESIGNATION, 'rank', mark.PACK_RANK)
    return BuffFacts(world=world, now=NOW, foes=case.foes, reachable=tuple(reachable), cast_at=cast_at)  # type: ignore[arg-type]


@pytest.mark.parametrize('on', [False, True])
def test_a_jump_frees_the_pack_s_order_from_a_mark_lasting_out_of_reach(monkeypatch, on) -> None:
    # 18:52:58.418: off, the mark lasting on 1107037081 (25.0 off, not pressing) leaves nobody designated, so the
    # strike went first; on, the jump that took the demons along frees the order: a member in reach
    monkeypatch.setattr(mark, 'PACK_HOP_FREES', on)
    facts = facts_of(CASE_1852, monkeypatch)
    assert mark.dragged(facts)
    chosen = mark.pack_designated(facts)
    if on:
        assert chosen is not None
        assert chosen.unit_id in IN_REACH_1852
    else:
        assert chosen is None


def test_the_designated_member_was_drawn_past_the_aim_s_limits() -> None:
    # 19:30:51.185, as the live line says: its body off the screen at (0.93, 0.39)
    view = Viewport(ASPECT)
    target = next(m for m in CASE_1930.foes if m.unit_id == 3241908774)
    body = view.body(CASE_1930.here, target.x, target.y)
    assert not view.on_screen(body)
    assert body[0] == pytest.approx(0.93, abs=0.02)


@pytest.mark.parametrize(('shown', 'frees'), [(False, False), (False, True), (True, False), (True, True)])
def test_with_the_members_on_the_screen_and_the_order_freed_one_that_can_be_hovered_is_designated(
    monkeypatch, shown, frees
) -> None:
    # 19:30:51.185: with all in reach the marked one off the screen is designated again (its key refused); with
    # those on the screen alone (HERALD_MARK_SHOWN) and the jump freeing the order (PACK_HOP_FREES), one on the screen
    monkeypatch.setattr(mark, 'PACK_HOP_FREES', frees)
    facts = facts_of(CASE_1930, monkeypatch, shown_only=shown)
    chosen = mark.pack_designated(facts)
    view = Viewport(ASPECT)
    if not shown:
        assert chosen is not None
        assert chosen.unit_id == 3241908774
    elif frees:
        assert chosen is not None
        assert chosen.unit_id != 3241908774
        assert view.on_screen(view.body(CASE_1930.here, chosen.x, chosen.y))
    else:
        assert chosen is None


def test_herald_mark_shown_keeps_the_hostiles_on_the_screen_alone(monkeypatch) -> None:
    # macros/hunt.py `Hunter.first_facts`: the reach it asks the FIRST rows with
    monkeypatch.setattr(hunt_module, 'HERALD_MARK_SHOWN', True)
    monkeypatch.setattr(hunt_module, 'SETTLE_BEFORE_FIRST', False)
    world = SimpleNamespace(player=SimpleNamespace(x=CASE_1930.here[0], y=CASE_1930.here[1]))
    reachable = [m for m in CASE_1930.foes if math.dist(CASE_1930.here, (m.x, m.y)) <= REACH]
    seen: list = []
    hunter = SimpleNamespace(fight_facts=lambda run, world, foes, reach, prey: seen.append(reach) or 'facts')
    asked = hunt_module.Hunter.first_facts(hunter, None, world, CASE_1930.foes, reachable, None, ASPECT)  # type: ignore[arg-type]
    assert asked == 'facts'
    assert 3241908774 not in {m.unit_id for m in seen[0]}
    assert len(seen[0]) < len(reachable)


@pytest.mark.parametrize('on', [False, True])
def test_settle_before_first_settles_the_first_rows_last_casts(monkeypatch, on) -> None:
    # 18:52:58.418: the mark that went onto a neighbour is found out before the first look asks the rows
    monkeypatch.setattr(hunt_module, 'SETTLE_BEFORE_FIRST', on)
    monkeypatch.setattr(hunt_module, 'HERALD_MARK_SHOWN', False)
    monkeypatch.setattr(pack, 'FIRST', {DEATH_MARK})
    row = SimpleNamespace(skill=DEATH_MARK, shows=lambda words: True)
    settled: list = []
    buffs = SimpleNamespace(rows=lambda phase: (row,), settle=lambda run, row, facts: settled.append(row.skill))
    run = SimpleNamespace(clock=lambda: NOW)
    hunter = SimpleNamespace(fight_facts=lambda *args: BuffFacts(world=None, now=NOW), buffs=buffs)  # type: ignore[arg-type]
    hunt_module.Hunter.first_facts(hunter, run, SimpleNamespace(player=None), (), (), None, ASPECT)  # type: ignore[arg-type]
    assert settled == ([DEATH_MARK] if on else [])


def cursed(*units: int):
    """State words with Death Mark's state (mark.py MARK_STATE) on `units`, none on the rest."""

    def words(monster) -> bytes:
        raw = bytearray(32)
        if monster.unit_id in units:
            word, bit = divmod(mark.MARK_STATE, 32)
            raw[word * 4 : word * 4 + 4] = (1 << bit).to_bytes(4, 'little')
        return bytes(raw)

    return words


@pytest.mark.parametrize(('on', 'curse', 'again'), [(False, True, True), (True, True, False), (True, False, True)])
def test_remark_unshown_no_mark_again_on_a_cursed_monster(monkeypatch, on, curse, again) -> None:
    # 19:30:51.185 (the elite 82 3241908774, marked 4.68 s before): "its mark again" after the jump of 18.2, and the
    # truth tool found the curse on it at the key ("already on"). On, no mark again while the curse shows
    from dataclasses import replace

    monkeypatch.setattr(mark, 'REMARK_UNSHOWN', on)
    facts = facts_of(CASE_1930, monkeypatch)
    facts = replace(facts, states=cursed(3241908774) if curse else cursed())
    target = next(m for m in CASE_1930.foes if m.unit_id == 3241908774)
    assert mark.aggro_lost(facts, target) is again
