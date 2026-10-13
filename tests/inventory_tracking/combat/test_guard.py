"""sim/guard.py: a pool on the character that takes some kinds of a blow before the resistances and stuns a melee
striker while it stands (rca/2026-10-13/re/notes-absorb.md); sim/monsters.py `Pack.stun`."""

from inventory_tracking.combat.sim.guard import STUN_MOST, Guard, GuardRule
from inventory_tracking.combat.sim.monsters import STAND, Pack, Walker


RULE = GuardRule(most=185.0, kinds=('physical',), stun=72)
DOOM_KNIGHT, DIABLO = 310, 243


def never() -> float:
    raise AssertionError('no roll for a monster that is not unique')


def test_the_pool_takes_only_its_kinds_up_to_what_is_left():
    guard = Guard(RULE, up=True)
    assert guard.take({'physical': 100.0, 'fire': 40.0}) == {'physical': 0.0, 'fire': 40.0}
    assert guard.left == 85.0
    assert guard.take({'physical': 100.0, 'cold': 5.0}) == {'physical': 15.0, 'cold': 5.0}
    assert (guard.left, guard.up, guard.falls, guard.taken) == (0.0, False, 1, 185.0)
    assert guard.take({'physical': 50.0}) == {'physical': 50.0}  # down: nothing taken


def test_a_cast_refills_the_pool_to_its_most():
    guard = Guard(RULE)
    assert not guard.up
    guard.take({'physical': 10.0})
    guard.set()
    guard.take({'physical': 150.0})
    guard.set()
    assert (guard.left, guard.sets) == (185.0, 2)


def test_a_melee_striker_is_stunned_while_the_guard_stands():
    guard = Guard(RULE, up=True)
    assert guard.stun_frames(DOOM_KNIGHT, 0, True, never) == 72
    assert guard.stun_frames(DIABLO, 0, True, never) == 0  # a boss never
    assert guard.stun_frames(DOOM_KNIGHT, 0, False, never) == 0  # one that cannot move never
    assert guard.stun_frames(DOOM_KNIGHT, 0x08, True, lambda: 0.95) == 0  # a unique on 10% of the rolls
    assert guard.stun_frames(DOOM_KNIGHT, 0x08, True, lambda: 0.05) == 72
    assert Guard(RULE).stun_frames(DOOM_KNIGHT, 0, True, never) == 0  # down: none
    assert Guard(GuardRule(1.0, ('physical',), 400), up=True).stun_frames(DOOM_KNIGHT, 0, True, never) == STUN_MOST


def test_a_stunned_monster_does_nothing_until_the_stun_is_over():
    walker = Walker(1, DOOM_KNIGHT, 0.0, 0.0)
    pack = Pack([walker], seed=3)
    pack.stun(1, 10, 72)
    assert (walker.doing, walker.until, walker.lands, walker.stunned) == (STAND, 82, -1, 82)
    for frame in range(10, 82):
        assert pack.step(frame, [(1.0, 0.0)]) == []
        assert walker.at == (0.0, 0.0)
        assert walker.doing == STAND
    pack.step(82, [(1.0, 0.0)])
    assert (walker.doing, walker.until) != (STAND, 82)  # it thought at once when the stun was over
