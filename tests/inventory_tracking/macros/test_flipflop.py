"""The goal flip-flop of Tower Cellar Level 1, 2026-10-22 20:04:15-20:04:26 (take 20261022T170322Z-21,
rca/2026-10-22/flipflop-findings.md): a group of 10 behind a wall, out of the read after one hop of its way round,
and the Next level mark; 26 Teleports in 10 s round (12702, 5170), no kill, the group then left alive.
The agenda's held target (agenda.py HELD_GOALS) and the knot of moves (hunting/judging.py STILL_BUDGET)."""

from types import SimpleNamespace

from inventory_tracking.macros import agenda as agenda_module
from inventory_tracking.macros.agenda import GROUP_NEAR, HELD_REACH, KILL, PLUS, Agenda, LevelView
from inventory_tracking.macros.hunting import judging
from inventory_tracking.macros.pursuit import Move


TOWER_CELLAR_1 = 21
NEXT_LEVEL = (12722.5, 5176.5)  # where the level run teleported to, the Next level mark
OUT_OF_READ = (12688.5, 5164.5)  # one hop of the way round the wall west: none of the 10 in the client's read
# The group of 10 (monstats 21, mode 1, never moved), from the take's frames at 20:04:14
GROUP = (
    (3551757191, (12759.5, 5132.5)),
    (241644423, (12754.5, 5149.5)),
    (483305230, (12752.5, 5149.5)),
    (2271676175, (12758.5, 5135.5)),
    (966626844, (12751.5, 5153.5)),
    (1933253688, (12754.5, 5152.5)),
    (4191789507, (12761.5, 5132.5)),
    (2536741315, (12757.5, 5151.5)),
    (3974934753, (12759.5, 5138.5)),
    (3866507376, (12757.5, 5132.5)),
)
NEAREST = 966626844


def look(here, crowd=(), unseen=()) -> LevelView:
    return LevelView(TOWER_CELLAR_1, here, policy=PLUS, frontier=lambda: None, crowd=crowd, unseen=unseen)


def test_the_group_out_of_the_read_on_its_way_round_stays_the_goal_while_held(monkeypatch) -> None:
    monkeypatch.setattr(agenda_module, 'HELD_GOALS', True)
    agenda = Agenda()
    agenda.begin('cyber21')
    first = agenda.in_level(look(NEXT_LEVEL, crowd=GROUP))
    assert first is not None
    assert (first.kind, first.unit, first.label) == (KILL, NEAREST, 'a group of 10')
    # One hop west: the client holds none of the 10 and the nearest is 66 off (past GROUP_NEAR); the tracker's last
    # places hold them. Before HELD_GOALS this look gave the route's goal (the Next level) back: the flip
    away = agenda.in_level(look(OUT_OF_READ, unseen=GROUP))
    assert away is not None
    assert (away.kind, away.unit) == (KILL, NEAREST)
    assert agenda.held is not None
    assert agenda.held[1] == frozenset(unit for unit, _ in GROUP)
    # The tracker forgets them (not where they were seen: looked at, not found): the goal is resolved
    assert agenda.in_level(look(OUT_OF_READ)) is None
    assert agenda.held is None
    # Past HELD_REACH times GROUP_NEAR the held group is let go too
    far = (GROUP[4][1][0] - GROUP_NEAR * HELD_REACH - 5.0, GROUP[4][1][1])
    agenda.in_level(look(NEXT_LEVEL, crowd=GROUP))
    assert agenda.in_level(look(far, unseen=GROUP)) is None
    # The switch off: the look out of the read chooses afresh, as before (the route's goal)
    monkeypatch.setattr(agenda_module, 'HELD_GOALS', False)
    agenda.in_level(look(NEXT_LEVEL, crowd=GROUP))
    assert agenda.in_level(look(OUT_OF_READ, unseen=GROUP)) is None


def test_a_group_only_remembered_is_no_new_goal_and_the_held_one_wins_a_near_tie(monkeypatch) -> None:
    monkeypatch.setattr(agenda_module, 'HELD_GOALS', True)
    agenda = Agenda()
    agenda.begin('cyber21')
    # Never chosen: the remembered ones out of the read make no group goal of their own
    assert agenda.in_level(look(OUT_OF_READ, unseen=GROUP)) is None
    # Hysteresis: another group a little nearer than the held one does not take the goal over
    agenda.in_level(look(NEXT_LEVEL, crowd=GROUP))
    other = tuple((900 + index, (NEXT_LEVEL[0] - 30.0, NEXT_LEVEL[1] + 6.0 * index)) for index in range(4))
    kept = agenda.in_level(look(NEXT_LEVEL, crowd=(*GROUP, *other)))
    assert kept is not None
    assert kept.unit == NEAREST
    # One more than HELD_REACH times nearer does
    close = tuple((950 + index, (NEXT_LEVEL[0] - 8.0, NEXT_LEVEL[1] + 4.0 * index)) for index in range(4))
    taken = agenda.in_level(look(NEXT_LEVEL, crowd=(*GROUP, *close)))
    assert taken is not None
    assert taken.unit == 950


# --- the knot of moves (judging.py STILL_BUDGET) ---

# The log's looks, 20:04:15.773-20:04:25.671: (seconds, the goal, the character's place)
FLIPS = [
    (15.773, 'group', (12722.5, 5176.5)), (16.416, 'group', (12708.5, 5175.5)), (16.798, 'next', (12688.5, 5164.5)),
    (17.170, 'group', (12705.5, 5173.5)), (17.570, 'next', (12688.5, 5159.5)), (17.947, 'group', (12700.5, 5173.5)),
    (18.297, 'next', (12688.5, 5154.5)), (18.756, 'next', (12695.5, 5173.5)), (19.176, 'group', (12722.5, 5171.5)),
    (19.519, 'group', (12708.5, 5172.5)), (19.972, 'next', (12687.5, 5162.5)), (20.338, 'group', (12702.5, 5173.5)),
    (20.715, 'next', (12687.5, 5157.5)), (21.121, 'next', (12697.5, 5173.5)), (21.520, 'group', (12722.5, 5171.5)),
    (21.935, 'next', (12694.5, 5173.5)), (22.318, 'group', (12724.5, 5176.5)), (22.696, 'group', (12710.5, 5174.5)),
    (23.077, 'next', (12687.5, 5167.5)), (23.430, 'group', (12708.5, 5172.5)), (23.800, 'next', (12687.5, 5162.5)),
    (24.157, 'group', (12702.5, 5173.5)), (24.521, 'next', (12687.5, 5157.5)), (24.899, 'next', (12697.5, 5173.5)),
    (25.258, 'group', (12722.5, 5171.5)), (25.671, 'next', (12694.5, 5173.5)),
]  # fmt: skip
HOP = Move(None, None, 'toward full clear: a group of 10')  # type: ignore[arg-type]


def goal_of(which: str) -> SimpleNamespace:
    if which == 'group':
        return SimpleNamespace(label='full clear: a group of 10', place=(12756.9, 5140.6), do='fight', unit=NEAREST,
                               stage=None, mark=None, clearing=True)  # fmt: skip
    return SimpleNamespace(label='Next level', place=(12722.3, 5175.9), do='enter', unit=None, stage=None,
                           mark=object(), clearing=False)  # fmt: skip


def hunter() -> SimpleNamespace:
    passed = Passes()
    return SimpleNamespace(
        dance=None, still=None, bearings=SimpleNamespace(progress=None, marks=None), known_level=lambda player: None,
        pass_by=lambda goal, why, now, rooms=(): passed.append((goal.label, now, why)), passed=passed,
        knots={},
    )  # fmt: skip


class Passes(list):
    """The fake's passes: `pass_by`'s list, plus the knot's units (judging.py KNOT_PASSES_PLACE)."""

    def __init__(self) -> None:
        super().__init__()
        self.units: dict[int, float] = {}

    def get(self, unit, default=0.0):
        return self.units.get(unit, default)

    def __setitem__(self, unit, until) -> None:  # type: ignore[override]
        self.units[unit] = until


def world_at(spot, monsters=()) -> SimpleNamespace:
    return SimpleNamespace(monsters=list(monsters), player=SimpleNamespace(x=spot[0], y=spot[1], area=TOWER_CELLAR_1))


def test_the_flip_flops_moves_are_a_knot_and_the_group_is_passed_within_the_budget(monkeypatch) -> None:
    monkeypatch.setattr(judging, 'STILL_BUDGET', True)
    h = hunter()
    for now, which, spot in FLIPS:
        judging.no_progress(h, None, world_at(spot), goal_of(which), HOP, now, None)  # type: ignore[arg-type]
        if h.passed:
            break
    assert h.passed, 'the knot was never given up'
    label, at, why = h.passed[0]
    assert label == 'full clear: a group of 10'
    assert at - FLIPS[0][0] <= judging.DANCE_SECONDS + 1.0  # not the 10 s of CLEAR_SECONDS, nor never
    assert 'STILL_BUDGET' in why
    monkeypatch.setattr(judging, 'STILL_BUDGET', False)
    h = hunter()
    for now, which, spot in FLIPS:
        judging.no_progress(h, None, world_at(spot), goal_of(which), HOP, now, None)  # type: ignore[arg-type]
    assert not h.passed  # DANCE_BUDGET alone: the goal's change at every look restarted it


def test_a_way_that_goes_somewhere_is_no_knot_and_a_kill_or_the_goal_reached_restarts_it() -> None:
    group = goal_of('group')
    # Hops round a wall: west, then north, then east to the group (25 units a hop, 0.4 s a look, 12 s)
    way = [(12708.5 - 20.0 * i, 5175.5) for i in range(5)] + [(12628.5, 5175.5 - 25.0 * i) for i in range(1, 6)]
    way += [(12628.5 + 25.0 * i, 5050.5) for i in range(1, 15)]
    h = hunter()
    for index, spot in enumerate(way):
        judging.no_progress(h, None, world_at(spot), group, HOP, 0.4 * index, None)  # type: ignore[arg-type]
    assert not h.passed
    # There and back once (a dead end): no knot
    h = hunter()
    there_back = [(12700.0 + 10.0 * i, 5170.0) for i in range(8)] + [(12770.0 - 10.0 * i, 5170.0) for i in range(8)]
    for index, spot in enumerate(there_back):
        judging.no_progress(h, None, world_at(spot), group, HOP, 0.4 * index, None)  # type: ignore[arg-type]
    assert not h.passed
    # The knot with a kill seen every few looks: progress each time, never given up
    h = hunter()
    for index, (now, which, spot) in enumerate(FLIPS):
        corpses = [SimpleNamespace(unit_id=500 + i, mode=0, ally=False) for i in range(index // 6)]
        judging.no_progress(h, None, world_at(spot, corpses), goal_of(which), HOP, now, None)  # type: ignore[arg-type]
    assert not h.passed
    # The goal reached at every few looks (a chest opened, a room stood at): progress too
    h = hunter()
    for index, (now, which, spot) in enumerate(FLIPS):
        there = index % 6 == 5
        judging.no_progress(h, None, world_at(spot), goal_of(which), HOP, now, None, there=there)  # type: ignore[arg-type]
    assert not h.passed


def test_a_drop_a_wait_and_a_boss_stage_are_never_given_up_by_the_knot() -> None:
    for kept in (
        SimpleNamespace(label='Shael Rune', place=(12641.0, 5041.0), do='pick up', unit=1, stage=None, mark=None,
                        clearing=False),
        SimpleNamespace(label='Andariel', place=(0.0, 0.0), do='fight', unit=2, stage=SimpleNamespace(kind='fight'),
                        mark=None, clearing=True),
    ):  # fmt: skip
        h = hunter()
        for now, _which, spot in FLIPS:
            judging.no_progress(h, None, world_at(spot), kept, HOP, now, None)  # type: ignore[arg-type]
        assert not h.passed


# --- a knot passes its place (judging.py KNOT_PASSES_PLACE), Claw Viper Temple 1, 03:26-03:31 on 2026-10-23 ---


def viper(unit, x) -> SimpleNamespace:
    return SimpleNamespace(unit_id=unit, x=x, y=9588.0, txt_id=74)


def test_a_knot_passes_the_whole_row_out_of_reach_and_longer_when_again(monkeypatch) -> None:
    row = [viper(unit, 15118.0 + 2 * unit) for unit in range(1, 9)] + [viper(99, 15300.0)]
    goal = SimpleNamespace(label='full clear: the monster 74 (3)', place=(15124.0, 9588.0), unit=3, clearing=True)
    found = hunter()
    monkeypatch.setattr(judging, 'KNOT_PASSES_PLACE', True)
    judging.pass_the_knot(found, world_at((15120.0, 9570.0), row), goal, 100.0)  # type: ignore[arg-type]
    assert set(found.passed.units) == set(range(1, 9))  # the far one (99) is not of the knot
    assert all(until == 100.0 + judging.choice.PASS_SECONDS for until in found.passed.units.values())
    judging.pass_the_knot(found, world_at((15120.0, 9570.0), row), goal, 140.0)  # type: ignore[arg-type]
    assert all(until == 140.0 + judging.KNOT_AGAIN_SECONDS for until in found.passed.units.values())
    off = hunter()
    monkeypatch.setattr(judging, 'KNOT_PASSES_PLACE', False)
    judging.pass_the_knot(off, world_at((15120.0, 9570.0), row), goal, 100.0)  # type: ignore[arg-type]
    assert off.passed.units == {}
