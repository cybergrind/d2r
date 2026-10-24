"""The way out of a mana-draining fight (combat/threats/drain_escape.py; rca/2026-10-23/death-manaburn-findings.md):
the numbers are the take's, 20261023T155650Z-88 (Flayer Dungeon Level 1, 18:57:29-45), a tier 5 Herald pack of Dark
Shapes (monstats wraith5) with plain ones about, whose blows burnt 468 then the rest of 745 mana."""

import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from inventory_tracking.combat.threats import drain_escape, manaburn


MONSTATS = Path(__file__).parents[3] / 'pricing' / 'raw' / 'd2data' / 'monstats.json'
DARK_SHAPE = 42  # monstats wraith5
FLAYER = 398  # monstats fetishblow3
FAST_BURN = (6, 25)  # Extra Fast, Mana Burn (monumod)


def hostile(unit: int, at: tuple[float, float], txt: int = DARK_SHAPE, mods: tuple[int, ...] = ()) -> SimpleNamespace:
    return SimpleNamespace(unit=unit, at=at, txt=txt, modifiers=mods, flags=0)


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setattr(drain_escape, 'MANA_ESCAPE', True)


def test_the_mana_element_rows_are_the_installed_games() -> None:
    if not MONSTATS.exists():
        pytest.skip('the installed game tables are not here (pricing/raw is git-ignored)')
    rows = json.loads(MONSTATS.read_text())
    found = {
        row['*hcIdx']: (row['El1Pct(H)'] / 100, float(row['El1MinD(H)']), float(row['El1MaxD(H)']))
        for row in rows.values()
        if row.get('El1Type') == 'mana' and row['El1MaxD(H)'] >= drain_escape.BURN_LEAST
    }
    assert found == drain_escape.MANA_ELEMENT
    assert not any(row.get(f'El{n}Type') == 'mana' for row in rows.values() for n in (2, 3))
    # The two small ones are left out: goatman6 10-20, foulcrow7 10-33
    assert not drain_escape.threat(585)
    assert not drain_escape.threat(592)


def test_off_a_plain_dark_shape_drains_nothing_and_on_it_does(on, monkeypatch) -> None:
    plain = hostile(1, (2.0, 0.0))
    assert drain_escape.drains(plain)
    assert not drain_escape.drains(hostile(2, (2.0, 0.0), FLAYER))
    assert drain_escape.drains(hostile(3, (2.0, 0.0), FLAYER, (25,)))  # Mana Burn on any type, as before
    # Alone it is fought as before until it burns: no burner by itself (item 2)
    assert manaburn.burners([plain]) == []
    assert [b.unit for b in drain_escape.typed_burners([plain, hostile(2, (2.0, 0.0), FLAYER)])] == [1]
    monkeypatch.setattr(drain_escape, 'MANA_ESCAPE', False)
    assert not drain_escape.drains(plain)


def test_one_drainer_kept_keeps_every_drainer_near(on) -> None:
    here = (0.0, 0.0)
    hostiles = [hostile(1, (20.0, 0.0), mods=FAST_BURN), hostile(2, (8.0, 3.0)), hostile(3, (45.0, 0.0))]
    found = manaburn.burners(hostiles)
    assert [b.unit for b in found] == [1]
    kept = list(found)
    assert {b.unit for b in drain_escape.widened(here, found, kept, False, hostiles)} == {1, 2}  # 3: past PACK_SEEN
    # No drain fight: the plain one alone is not kept; a burn remembered: it is
    assert drain_escape.widened(here, [], [], False, hostiles[1:]) == []
    assert {b.unit for b in drain_escape.widened(here, [], [], True, hostiles[1:])} == {2}


def test_the_take_s_burn_is_remembered_while_a_drainer_is_near(on) -> None:
    watch = drain_escape.BurnWatch()
    # 46.72 s of the take: 745 -> 277 between two looks with the plain Dark Shape 2.0 off
    watch.seen([(46.5, 745.0, 745.0)], 46.8, 277.0, 745.0, near=1)
    assert watch.points == pytest.approx(468.0)
    said = watch.leaving(47.9, 291.0, 745.0, near=3)
    assert said is not None
    assert drain_escape.BURN_SAID in said
    # Past BURN_HOLD with the mana under RECOVERED still; then recovered, then nobody near
    assert watch.leaving(46.8 + 10.0, 400.0, 745.0, near=1) is not None
    assert watch.leaving(46.8 + 10.0, 0.7 * 745, 745.0, near=1) is None
    assert watch.leaving(47.0, 277.0, 745.0, near=0) is None
    # A strike's and a Teleport's cost is no burn
    calm = drain_escape.BurnWatch()
    calm.seen([(10.0, 745.0, 745.0)], 10.5, 745.0 - 16 - 24, 745.0, near=2)
    assert calm.burnt_at == -math.inf


def test_a_wraith_running_in_is_on_the_character(on) -> None:
    watch = drain_escape.BurnWatch()
    here = (0.0, 0.0)
    shape = [hostile(1, (17.0, 0.0), mods=FAST_BURN)]
    assert not watch.closing_in(10.0, here, manaburn.burners(shape), shape)
    shape = [hostile(1, (12.0, 0.0), mods=FAST_BURN)]
    near = manaburn.burners(shape)
    assert watch.closing_in(10.3, here, near, shape)  # 5 units nearer in 0.3 s, within its 18
    standing = drain_escape.BurnWatch()
    standing.closing_in(10.0, here, near, shape)
    assert not standing.closing_in(10.3, here, near, shape)
    # A Mana Burn Flayer or Gloam running in is not: the demons hold the one, the other casts
    for txt in (FLAYER, 118):
        other = drain_escape.BurnWatch()
        before = [hostile(2, (17.0, 0.0), txt, FAST_BURN)]
        other.closing_in(10.0, here, manaburn.burners(before), before)
        after = [hostile(2, (12.0, 0.0), txt, FAST_BURN)]
        assert not other.closing_in(10.3, here, manaburn.burners(after), after)


def test_no_clear_landing_is_urgent_only_for_a_drainer_coming_or_an_extra_fast_one(on) -> None:
    fast = manaburn.burners([hostile(1, (12.0, 0.0), FLAYER, FAST_BURN)])
    slow = manaburn.burners([hostile(1, (12.0, 0.0), FLAYER, (25,))])
    assert drain_escape.urgent(fast, False)
    assert not drain_escape.urgent(slow, False)
    assert drain_escape.urgent(slow, True)


def test_the_leave_lands_out_of_reach_and_the_way_back_when_nothing_round_is_clear(on) -> None:
    here = (0.0, 0.0)
    pack = [hostile(u, (-6.0 - u, float(u % 3))) for u in range(1, 6)]
    burning = manaburn.burners(pack)
    spots = drain_escape.far_spots(here, burning, pack)
    assert spots
    assert all(drain_escape._margin(s, drain_escape._keeps(burning, pack)) >= drain_escape.LEAVE_CLEAR for s in spots)
    assert spots[0][0] > 20  # away from the pack, out of reach
    # A corridor: footing only along y = 0 between x -40 and 18; the pack came in behind, east, on the way back
    watch = drain_escape.BurnWatch()
    for t, x in enumerate((30.0, 24.0, 18.0, 12.0, 6.0, 0.0)):
        watch.walked(float(t), (x, 0.0))
    narrow = [hostile(u, (6.0 + u, 0.0)) for u in range(1, 4)]
    burning = manaburn.burners(narrow)
    footed = lambda p: abs(p[1]) < 1.0 and -40.0 <= p[0] <= 18.0  # ruff: ignore[lambda-assignment]
    spots = drain_escape.far_spots(here, burning, narrow, footed, watch)
    assert spots[0] == pytest.approx((-24.0, 0.0))  # west, out of reach; -27 and -30 are 13 and 10 from the end
    assert (-30.0, 0.0) not in [(round(x), round(y)) for x, y in spots]
    # The way back past the pack (Teleport flies over it) gains room and has a way on: kept after the ring's
    assert spots[1:] == [(18.0, 0.0)]


def test_a_landing_in_a_pocket_comes_after_one_with_a_way_on(on) -> None:
    keeps = [((10.0, 0.0), 10.0)]
    pocket = (-20.0, 0.0)  # footing within 3 of it alone: no ring spot 16-28 off on footing
    footed = lambda p: math.dist(p, pocket) <= 3.0 or math.dist(p, (0.0, 40.0)) <= 12.0  # ruff: ignore[lambda-assignment]
    assert drain_escape.exits(pocket, keeps, None)
    assert not drain_escape.exits(pocket, keeps, footed)
    assert drain_escape.exits((0.0, 20.0), keeps, footed)  # (0, 36) is on footing and farther from the drainer
    assert drain_escape.opened([pocket, (0.0, 20.0)], keeps, footed) == [(0.0, 20.0)]
    assert drain_escape.opened([pocket], keeps, footed) == [pocket]  # nothing better: the pocket still


def test_cornered_the_teleport_goes_past_the_pack(on) -> None:
    here = (0.0, 0.0)
    keeps = [((x, y), 18.0) for x, y in ((8.0, 0.0), (6.0, 4.0), (6.0, -4.0), (-8.0, 0.0))]
    spots = drain_escape.passing(here, keeps, lambda p: abs(p[1]) < 1.0)
    assert spots
    assert all(min(math.dist(s, at) for at, _ in keeps) >= drain_escape.PASS_CLEAR for s in spots)


def test_blade_warp_pays_its_mana_and_teleport_is_left_to_its_own_bar(on, monkeypatch) -> None:
    assert manaburn.skill_mana(drain_escape.SKILL_ROWS[390]) == 15.0  # skills.txt 390 at level 1
    assert drain_escape.unpaid(390, 0.0)
    assert drain_escape.unpaid(390, 14.9)
    assert not drain_escape.unpaid(390, 15.0)
    assert not drain_escape.unpaid(390, None)  # unread: paid
    assert not drain_escape.unpaid(54, 0.0)  # Teleport: manaburn.py's bar
    monkeypatch.setattr(drain_escape, 'MANA_ESCAPE', False)
    assert not drain_escape.unpaid(390, 0.0)


def test_switched_off_the_module_adds_nothing(monkeypatch) -> None:
    monkeypatch.setattr(drain_escape, 'MANA_ESCAPE', False)
    here = (0.0, 0.0)
    pack = [hostile(u, (-6.0 - u, 0.0)) for u in range(1, 4)]
    watch = drain_escape.BurnWatch()
    watch.seen([(1.0, 745.0, 745.0)], 1.2, 100.0, 745.0, near=3)
    watch.walked(1.2, here)
    assert watch.burnt_at == -math.inf
    assert watch.trail == []
    assert watch.leaving(1.3, 100.0, 745.0, near=3) is None
    assert drain_escape.far_spots(here, [], pack) == []
    assert not drain_escape.gains(here, (20.0, 0.0), [], pack)
    assert not watch.closing_in(1.3, here, manaburn.burners(pack))


# -- BURN_COVER (2026-10-24, rca/2026-10-24/manaburn-cycle-findings.md §3): the leave held by what the next burn
# would leave --


@pytest.fixture
def cover(monkeypatch):
    monkeypatch.setattr(drain_escape, 'MANA_ESCAPE', True)
    monkeypatch.setattr(drain_escape, 'BURN_COVER', True)


def burnt(at: float, points: float) -> drain_escape.BurnWatch:
    watch = drain_escape.BurnWatch()
    watch.burnt_at, watch.points = at, points
    return watch


def test_a_refill_does_not_end_the_leave_while_the_pack_covers_the_character(cover) -> None:
    # The arena's manaburn-death seed 3: burnt 482 at 2.3 s, the Rejuvenation at 12.6 s filled 739, 14 drainers in
    # reach; the leave let go there before, and two blows took the mana to 0
    assert burnt(2.3, 482.0).leaving(12.9, 739.0, 745.0, near=14) is not None


def test_a_lone_drainer_after_a_refill_that_covers_another_burn_lets_the_leave_go(cover) -> None:
    # Live 18:53:12.1 (take 20261024T155059Z-113): burnt 557 1.6 s before, mana 735 of 745, one Ghost in reach
    assert burnt(10.4, 557.0).leaving(12.1, 735.0, 745.0, near=1) is None


def test_a_lone_drainer_s_recovery_is_as_before(cover) -> None:
    # Live 18:53:25-31: burnt 519, mana 288-423 of 745 with 1-2 Ghosts: under RECOVERED the leave stays, over it not
    assert burnt(21.2, 519.0).leaving(28.0, 400.0, 745.0, near=2) is not None
    assert burnt(21.2, 519.0).leaving(31.0, 460.0, 745.0, near=2) is None
    # within BURN_HOLD, under one burn and the reserve: kept
    assert burnt(21.2, 519.0).leaving(22.0, 500.0, 745.0, near=1) is not None


def test_the_cover_lapses_with_the_burn_and_needs_a_drainer_in_reach(cover) -> None:
    watch = burnt(0.0, 500.0)
    assert watch.leaving(drain_escape.RECOVER_SECONDS + 0.1, 10.0, 745.0, near=14) is None
    assert watch.leaving(1.0, 10.0, 745.0, near=0) is None


def test_with_burn_cover_off_the_refill_lets_go_as_before(monkeypatch) -> None:
    monkeypatch.setattr(drain_escape, 'MANA_ESCAPE', True)
    monkeypatch.setattr(drain_escape, 'BURN_COVER', False)
    assert burnt(2.3, 482.0).leaving(12.9, 739.0, 745.0, near=14) is None
    assert burnt(10.4, 557.0).leaving(12.1, 735.0, 745.0, near=1) is not None  # BURN_HOLD
