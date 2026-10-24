"""The potion detour that alternated with the fight, 2026-10-22 (rca/2026-10-22/potion-flipflop-findings.md).

- Sewers Level 1, 21:05:10-21:05:53 (take 20261022T180453Z-92): the belt's healing potions gone to the mercenary's
  healer (H0, 8 rejuvenations, the life full). Two super healing potions, A at (12646, 5439) and B at (12644, 5493),
  were both "left: guarded 15 s" (21:05:23.7 and 21:05:31.1), and from 21:05:33 the far detour (`scarce`) took them by
  turns: 14 Teleports between y 5437 and 5508, the character 4 units from A at 21:05:49.4 going back for B, while a
  Horadrim Ancient (unraveler4, Resurrect2) grew back 41 -> 81 of 128 and raised its Horror three times.
- 21:05:28.19: "(12644, 5493), 45 away, waits: the leader 2623779230 held is in reach", and 0.07 s later the same
  potion "is worth its detour": the wait did not reach the far detour.

Moved to test_hunt's level with their distances kept: the character at (5000, 5000) stands for (12642.5, 5467.5),
where it landed at 21:05:50.0 between the two.
"""

import logging
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

from inventory_tracking.game.records import HEALING, Drop, Loot, Monster
from inventory_tracking.macros import agenda as goal_agenda
from inventory_tracking.macros.goals import PICK_UP
from inventory_tracking.macros.hunting import choice, judging
from inventory_tracking.macros.hunting.base import BLOCK_SECONDS
from inventory_tracking.macros.pursuit import Move
from inventory_tracking.macros.supply import Potions
from tests.inventory_tracking.macros.test_hunt import game
from tests.inventory_tracking.macros.test_supply import AREA, JUV, running


HERE = (5000.0, 5000.0)  # (12642.5, 5467.5)
A = Drop(4101, 5003.5, 4971.5, 'a super healing potion', HEALING)  # (12646, 5439): 28.7 away
B = Drop(4102, 5001.5, 5025.5, 'a super healing potion', HEALING)  # (12644, 5493): 25.5 away
LIFE, MAX_LIFE = 2943, 2943
EIGHT = (JUV, JUV, None, None) * 4  # the belt then: no healing potion, 8 rejuvenations
# The Horror 1778783402 at (12650, 5486) then, 21 from the character: within the strike's reach
HORROR = Monster(1778783402, 4, 1, 5007.5, 5018.5, 0xFFFFFFFF, life=128, max_life=128)


def far_hunter(play, *potions: Drop, belt=EIGHT, life: int = LIFE):
    """A level run with `potions` remembered on the ground, each 1 s away by the navigator (2.0 + the pickup)."""
    loot = Loot(tuple(potions), belt, life, MAX_LIFE)
    hunt = running(play, loot=loot)
    hunt.potions.see(loot, AREA, HERE, play.clock.now, -1.0)
    hunt.travel.eta = lambda *args, **kwargs: 1.0
    return hunt


def detour(hunt, play, foes=()):
    play.world = replace(play.world, monsters=tuple(foes))
    hunt.fetching = (-1e9, hunt.fetching[1])  # judged now, as at the next judging
    return hunt.side_drop(play.run(), HERE, list(foes), play.world)


def test_two_potions_left_guarded_are_no_far_detour_by_turns(monkeypatch) -> None:
    """21:05:33-21:05:51: both potions left, the far detour went to them by turns. One ledger: none is a goal."""
    play = game()
    hunt = far_hunter(play, A, B)
    gone = play.clock.now - BLOCK_SECONDS - 1.0
    hunt.guarded_since.update({A.unit_id: gone, B.unit_id: gone})
    monkeypatch.setattr(choice, 'POTION_HELD', False)
    before = detour(hunt, play)
    assert before is not None
    assert before.unit_id in {A.unit_id, B.unit_id}  # the flip: a left potion "worth its detour"
    monkeypatch.setattr(choice, 'POTION_HELD', True)
    hunt.fetching = (-1e9, None)
    assert detour(hunt, play) is None
    # A potion given up by a knot of moves (judging.py STILL_BUDGET, `Hunter.side_left`) is left the same way
    hunt.guarded_since.clear()
    hunt.side_left[A.unit_id] = 'left: 6 s of moves round a knot (STILL_BUDGET)'
    found = detour(hunt, play)
    assert found is not None
    assert found.unit_id == B.unit_id


def test_the_potion_waits_while_the_fight_is_live_and_comes_back_after_it(monkeypatch, caplog) -> None:
    """21:05:10-21:05:28: a strike, a hop toward the potion, its guards, back: the fight first while it is on."""
    monkeypatch.setattr(choice, 'POTION_HELD', True)
    play = game()
    hunt = far_hunter(play, B)
    hunt.struck_at = play.clock.now - 0.5
    with caplog.at_level(logging.INFO):
        assert detour(hunt, play, [HORROR]) is None
    # The fight over (no strike for FIGHT_LIVE s, or nothing in reach): the potion is the detour again
    hunt.struck_at = play.clock.now - choice.FIGHT_LIVE - 0.1
    found = detour(hunt, play, [HORROR])
    assert found is not None
    assert found.unit_id == B.unit_id
    hunt.struck_at = play.clock.now - 0.5
    off = replace(HORROR, x=HERE[0] + hunt.reach + 5.0, y=HERE[1])
    found = detour(hunt, play, [off])
    assert found is not None
    assert found.unit_id == B.unit_id
    # The switch off: the detour in the middle of the fight, as on the day
    monkeypatch.setattr(choice, 'POTION_HELD', False)
    found = detour(hunt, play, [HORROR])
    assert found is not None
    assert found.unit_id == B.unit_id


def test_survival_first_the_potion_does_not_wait_under_the_floor_or_with_the_rejuvenations_spent(monkeypatch) -> None:
    monkeypatch.setattr(choice, 'POTION_HELD', True)
    play = game()
    floor = far_hunter(play, B).build.settings.safety.floor  # per cent of the life
    low = far_hunter(play, B, life=int(MAX_LIFE * (floor - 5.0) / 100.0))
    low.struck_at = play.clock.now - 0.5
    found = detour(low, play, [HORROR])
    assert found is not None
    assert found.unit_id == B.unit_id
    spent = far_hunter(play, B, belt=(JUV, JUV) + (None,) * 14)  # manaburn.KEPT_REJUVENATIONS left
    spent.struck_at = play.clock.now - 0.5
    found = detour(spent, play, [HORROR])
    assert found is not None
    assert found.unit_id == B.unit_id


def test_the_held_detour_keeps_its_potion_unless_another_is_more_than_held_reach_times_nearer(monkeypatch) -> None:
    """The character between two potions: each judging chose the nearer afresh; the held one is kept."""
    monkeypatch.setattr(choice, 'POTION_HELD', True)
    play = game()
    hunt = far_hunter(play, A, B)
    first = detour(hunt, play)
    assert first is not None
    assert first.unit_id == B.unit_id  # the nearer, 25.5 against 28.7
    # A hop north: A is a little nearer now; B is held
    hunt.potions.see(Loot((A, B), EIGHT, LIFE, MAX_LIFE), AREA, (5000.0, 4996.0), play.clock.now, -1.0)
    kept = choice.held_first(hunt.potions.lying(HEALING, (5000.0, 4996.0)), first, (5000.0, 4996.0))
    assert kept[0].unit == B.unit_id
    # One more than HELD_REACH times nearer takes it over
    close = (A.x, A.y + 10.0)
    taken = choice.held_first(hunt.potions.lying(HEALING, close), first, close)
    assert taken[0].unit == A.unit_id
    assert goal_agenda.HELD_REACH == 2.0


# --- the knot of moves and what lasts (judging.py STILL_BUDGET, NET_PROGRESS) ---

SEWERS_1 = 92
FAR_A = Drop(4101, 12646.0, 5439.0, 'a super healing potion', HEALING)
# The looks of 21:05:40.2-21:05:50.9 (seconds after 21:05:00, the character's place): the detour by turns
LOOKS = [
    (40.2, (12662.5, 5478.5)), (40.6, (12647.5, 5467.5)), (42.6, (12647.5, 5467.5)), (43.0, (12644.5, 5493.5)),
    (44.5, (12635.5, 5508.5)), (45.1, (12636.5, 5478.5)), (46.8, (12636.5, 5478.5)), (47.6, (12636.5, 5447.5)),
    (48.0, (12637.5, 5470.5)), (48.5, (12637.5, 5439.5)), (49.1, (12637.5, 5463.5)), (49.6, (12642.5, 5437.5)),
    (50.1, (12642.5, 5467.5)), (50.6, (12643.5, 5492.5)), (50.9, (12628.5, 5507.5)),
]  # fmt: skip
NO_RUN: Any = None  # the run is read only by a rush's chest
HOP = Move(None, None, 'toward a super healing potion, on the way')  # type: ignore[arg-type]
POTION_GOAL: Any = SimpleNamespace(label='a super healing potion, on the way', place=(FAR_A.x, FAR_A.y), do=PICK_UP,
                              unit=FAR_A.unit_id, stage=None, mark=None, clearing=False, guarded=True)  # fmt: skip


def knot_hunter() -> Any:  # a Hunter's double: what the budgets read
    potions = Potions()
    potions.see(Loot((FAR_A,), EIGHT, LIFE, MAX_LIFE), SEWERS_1, (12642.5, 5467.5), 0.0, -1.0)
    return SimpleNamespace(
        dance=None, still=None, slain=(None, frozenset()), potions=potions, side_left={}, base=POTION_GOAL,
        bearings=SimpleNamespace(progress=None, marks=None), known_level=lambda player: None,
        pass_by=lambda *args, **kwargs: None,
    )  # fmt: skip


def monster(unit, life, mode=1):
    return Monster(unit, 104, mode, 12642.0, 5510.0, 0xFFFFFFFF, life=life, max_life=128)


def world_at(spot, monsters=()) -> Any:  # a World's double
    return SimpleNamespace(monsters=list(monsters), player=SimpleNamespace(x=spot[0], y=spot[1], area=SEWERS_1))


def play_looks(hunt, lives) -> list[float]:
    """The looks' no_progress with the Ancient's life (`lives(t)`); the times it gave the potion up."""
    given = []
    for t, spot in LOOKS:
        world = world_at(spot, [monster(2283311785, lives(t))])
        if judging.no_progress(hunt, NO_RUN, world, POTION_GOAL, HOP, t, None):
            given.append(t)
    return given


def test_the_detour_by_turns_is_a_knot_and_its_potion_is_left(monkeypatch) -> None:
    monkeypatch.setattr(choice, 'POTION_HELD', True)
    hunt = knot_hunter()
    grows = lambda t: 61 + int(t - 40.2)  # ruff: ignore[lambda-assignment]  the Ancient growing back: no blow lasts
    given = play_looks(hunt, grows)
    assert given
    assert given[0] <= 50.9
    assert FAR_A.unit_id in hunt.side_left
    assert 'STILL_BUDGET' in hunt.side_left[FAR_A.unit_id]
    # The switch off: a pickup is a kept goal, the clock never runs
    monkeypatch.setattr(choice, 'POTION_HELD', False)
    assert play_looks(knot_hunter(), grows) == []


def test_what_grows_back_or_was_raised_is_no_progress_and_a_first_death_is(monkeypatch) -> None:
    monkeypatch.setattr(judging, 'NET_PROGRESS', True)
    hunt = knot_hunter()
    horror = 1778783402
    # Seen dead once (21:05:15.7), raised (21:05:18.3) at 128: its second death is no lasting kill
    judging.slain_before(hunt, world_at(LOOKS[0][1]), frozenset({horror}))
    raised = judging.slain_before(hunt, world_at(LOOKS[0][1]), frozenset())
    assert horror in raised
    assert not judging.progressed(frozenset({horror}), {}, frozenset(), {}, raised)
    assert judging.progressed(frozenset({2283311785}), {}, frozenset(), {}, raised)  # a first death
    # A blow on the raised one is none; one under the clock's snapshot is
    assert not judging.progressed(frozenset(), {horror: 40}, frozenset(), {horror: 128}, raised)
    assert judging.progressed(frozenset(), {2283311785: 50}, frozenset(), {2283311785: 51}, raised)
    # Another level forgets them
    other: Any = SimpleNamespace(monsters=[], player=SimpleNamespace(x=0.0, y=0.0, area=SEWERS_1 + 1))
    assert judging.slain_before(hunt, other, frozenset()) == frozenset()
    monkeypatch.setattr(judging, 'NET_PROGRESS', False)
    assert judging.slain_before(hunt, world_at(LOOKS[0][1]), frozenset()) == frozenset()
