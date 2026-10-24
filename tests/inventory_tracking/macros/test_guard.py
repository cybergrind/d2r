"""The stand guard's verdicts (macros/guard.py `Guard.look`), as pure functions of the poll's looks."""

from inventory_tracking.macros.guard import HIT_SHARE, QUIET, Act, Guard, Look


GAME = 'cyberg65'
MOST = 2943


def look(now: float, *, life: int = MOST, near: bool = False, **changes) -> Look:
    facts = {'game': GAME, 'in_town': False, 'dead': False, 'life': (life, MOST), 'near': near, 'loop_on': False}
    facts.update(changes)
    return Look(now, **facts)


def armed() -> Guard:
    guard = Guard()
    assert guard.arm('Superior Flail lies on the ground: the loop stops here')
    return guard


def test_unarmed_it_does_nothing():
    assert Guard().look(look(1.0, near=True)) is Act.NOTHING


def test_a_hostile_near_or_a_hit_is_a_fight_a_small_regain_is_not():
    guard = armed()
    assert guard.look(look(1.0)) is Act.NOTHING
    assert guard.look(look(2.0, life=MOST - 3)) is Act.NOTHING  # under HIT_SHARE
    assert guard.look(look(3.0, life=MOST)) is Act.NOTHING  # regained
    assert guard.look(look(4.0, life=MOST - int(HIT_SHARE * MOST) - 1)) is Act.FIGHT
    assert guard.fighting
    assert guard.fights == 1
    guard = armed()
    assert guard.look(look(1.0, near=True)) is Act.FIGHT


def test_the_fight_ends_after_quiet_and_starts_again_on_the_next_threat():
    guard = armed()
    assert guard.look(look(1.0, near=True)) is Act.FIGHT
    assert guard.look(look(2.0)) is Act.NOTHING
    assert guard.look(look(2.0 + QUIET - 0.5)) is Act.NOTHING
    assert guard.look(look(2.0 + QUIET)) is Act.CALM
    assert not guard.fighting
    assert guard.armed
    assert guard.look(look(20.0, near=True)) is Act.FIGHT
    assert guard.fights == 2


def test_a_run_or_a_mode_at_work_is_left_alone():
    guard = armed()
    assert guard.look(look(1.0, near=True, busy=True)) is Act.NOTHING
    assert not guard.fighting


def test_the_loop_on_a_death_or_another_game_ends_the_watch():
    for over in (look(1.0, near=True, loop_on=True), look(1.0, near=True, dead=True), look(1.0, near=True, game=None)):
        assert armed().look(over) is Act.DISARM, over
    guard = armed()
    assert guard.look(look(1.0)) is Act.NOTHING
    assert guard.look(look(2.0, near=True, game='cyberg66')) is Act.DISARM


def test_in_town_nothing_and_its_fight_ends():
    guard = armed()
    assert guard.look(look(1.0, near=True, in_town=True)) is Act.NOTHING
    assert guard.look(look(2.0, near=True)) is Act.FIGHT
    assert guard.look(look(3.0, near=True, in_town=True)) is Act.CALM
