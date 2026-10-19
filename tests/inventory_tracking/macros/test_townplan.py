"""The whole town visit simulated before its first click (macros/townplan.py; rca/2026-10-18/arch-town-planning.md step
M1), on today's misses kept as visit snapshots (fixtures/visits, written through macros/visitlog.py).

The fixtures are the stash stops test_town.py builds by hand from the logs; after a change there, write them again:

    uv run --offline python -c "from tests.inventory_tracking.macros.test_townplan import write; write()"
"""

import json
import re
from dataclasses import replace
from pathlib import Path

import pytest

from inventory_tracking.macros.cube import own_of
from inventory_tracking.macros.stash import is_potion
from inventory_tracking.macros.town import Exit, Needs, contract
from inventory_tracking.macros.townplan import RULED, Rulings, State, kind_of, kinds, plan_visit, simulate
from inventory_tracking.macros.visitlog import VERSION, Snapshot, load, snapshot_json
from inventory_tracking.macros.world import Pack
from tests.inventory_tracking.macros import test_town


FIXTURES = Path(__file__).parent / 'fixtures' / 'visits'
# Today's misses (rca/2026-10-18/arch-town-planning.md §2.1) with a fixture: the visit's clock and the keeper the
# contract named ("short of the contract: cube 1 items (<it>), 1 keepers carried (<it>)"). 15:01 has none: its cube's
# other five items are not in the log (the same class as 15:06)
LOGGED = {
    '1428': ('142812', 'unique Embossed Plate at (0, 0)'),
    '1455': ('145556', 'unique Spiked Club at (0, 0)'),
    '1505': ('150553', 'set Boots at (1, 0)'),
    '1514': ('151423', 'unique Serpentskin Armor at (0, 0)'),
    '1520': ('152018', 'unique Serpentskin Armor at (0, 0)'),
}
MISSED = ('cube', 'keepers')
# Visits kept as their service wrote them (runs/alt-d/<session>/visits/<HHMMSS>.json, every stop), not built by hand
REAL = {'1635': '163522'}  # the set Battle Boots behind the junk Fuscina, the third visit running (16:30-16:35)


def logged(case: str) -> tuple[str, str]:
    keeper = LOGGED[case][1]
    return f'cube 1 items ({keeper})', f'1 keepers carried ({keeper})'


def built(case: str) -> Snapshot:
    """The visit's start as test_town.py builds it (after Cain: its verdicts the junk)."""
    pack, own, junk = getattr(test_town, f'pack_{case}')()
    view = getattr(test_town, f'view_{case}')()
    full = frozenset(txt for txt in view.full() if not is_potion(txt))  # visit.py `_full_of`
    return Snapshot('start', pack, own, Needs(), Exit.WAYPOINT, view, junk, full=full, at=f'{case[:2]}:{case[2:]}:00')


def path_of(case: str) -> Path:
    return FIXTURES / f'2026-10-18-{REAL[case] if case in REAL else LOGGED[case][0]}.json'


def document(case: str) -> str:
    doc = {'version': VERSION, 'visit': LOGGED[case][0], 'logged': logged(case), 'stops': [snapshot_json(built(case))]}
    # One line to an item, a row, a cell: short lists of plain values kept on one line
    return re.sub(r'\[[^\[\]{}]*\]', lambda m: re.sub(r'\n\s*', '', m.group(0)), json.dumps(doc, indent=1)) + '\n'


def write() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    for case in LOGGED:
        path_of(case).write_text(document(case))


def fixture(case: str) -> Snapshot:
    """The visit's `start` snapshot (the plan's input)."""
    return load(path_of(case))[0]


@pytest.mark.parametrize('case', LOGGED)
def test_each_fixture_is_the_visit_test_town_builds_through_the_codec(case):
    assert fixture(case) == built(case)
    assert path_of(case).read_text() == document(case)


NO_PARK = Rulings(park_junk=False, keeper_in_cube=False)  # as the loop ran until the ruling of 16:50 on 2026-10-18
BEFORE_1750 = Rulings(keeper_in_cube=False)  # the park ruled, a keeper in the cube still a miss (16:50 to 17:50)


@pytest.mark.parametrize(
    ('case', 'before', 'ruled'),
    [
        ('1428', (), ()),  # the shuffle (town.py `_make_way`, live 15:02) frees the plate's block
        ('1455', (), ()),  # the same: the club's column
        ('1505', MISSED, ()),  # the Fuscina: no block for the Boots until it is sold; parked on page 5
        ('1514', MISSED, ()),  # the Bramble Mitts: none for the armor; parked
        ('1520', MISSED, ()),  # the Grand Charm: none for the armor; parked
    ],
)
def test_the_ruled_order_predicts_the_misses_the_code_leaves(case, before, ruled):
    plan = plan_visit(fixture(case), NO_PARK)

    assert plan is not None
    assert plan.variant == 'ruled'
    assert kinds(plan.misses) == before
    assert kinds(logged(case)) == MISSED  # what the visit logged then
    if before:
        assert plan.misses == logged(case)  # named as the contract names them

    plan = plan_visit(fixture(case), BEFORE_1750)  # the park ruled (the player, 16:50 on 2026-10-18)

    assert plan is not None
    assert plan.variant == 'ruled'
    assert kinds(plan.misses) == ruled
    assert plan.end.pack.in_cube == ()
    assert plan.end.parked == ()
    assert plan.end.pack.inventory.has_room(Needs().block)


VARIANTS = {
    'jamella first': Rulings(park_junk=False, jamella_first=True, keeper_in_cube=False),
    'drop junk': Rulings(park_junk=False, drop_junk=True, keeper_in_cube=False),
}


@pytest.mark.parametrize('case', ['1505', '1514', '1520'])
@pytest.mark.parametrize('variant', VARIANTS)
def test_each_ruling_variant_lets_the_stranded_keeper_out(case, variant):
    plan = plan_visit(fixture(case), VARIANTS[variant])

    assert plan is not None
    assert plan.variant == variant
    assert plan.misses == ()
    assert plan.end.pack.in_cube == ()
    assert plan.end.pack.inventory.has_room(Needs().block)


@pytest.mark.parametrize('case', ['1505', '1514', '1520'])
def test_a_keeper_left_in_the_cube_by_ruling_is_deferred_not_a_miss(case):
    plan = plan_visit(fixture(case), Rulings(park_junk=False, keeper_in_cube=True))

    assert plan is not None
    assert plan.misses == ()
    assert [i.unit_id for i in plan.deferred] == [{'1505': 51}.get(case, 50)]


def test_the_park_puts_the_junk_on_a_page_and_takes_it_back_before_the_stash_closes():
    # 15:05:53: the Fuscina (2 x 4) onto shared page 5 for the stop, the Boots out through its cells onto page 4, the
    # Fuscina back where it was, then sold; the cube's junk waits in it for her passes
    plan = plan_visit(fixture('1505'))

    assert plan is not None
    moves = [(s.stop, s.verb, s.item.unit_id, s.to) for s in plan.steps]
    assert ('stash', 'park', 40, 5) in moves
    assert moves.index(('stash', 'park', 40, 5)) < moves.index(('stash', 'page', 51, 4))
    assert moves.index(('stash', 'page', 51, 4)) < moves.index(('stash', 'unpark', 40, (3, 0)))
    assert moves.index(('stash', 'unpark', 40, (3, 0))) < moves.index(('jamella', 'sell', 40, None))
    assert not any(verb == 'out' and stop == 'stash' for stop, verb, _unit, _to in moves)
    assert {i.unit_id for i in plan.end.sold} == {40, 50, 54, 57}
    assert plan.end.parked == ()
    assert all(40 not in page.units for page in plan.end.pages)  # nothing of the junk left in the stash


def test_with_the_variants_off_only_the_ruled_order_is_simulated():
    assert Rulings() == RULED
    assert RULED.park_junk  # the player, 16:50 on 2026-10-18
    assert RULED.keeper_in_cube  # the player, 17:50: "keeper can wait in cube"
    for case in LOGGED:
        plan = plan_visit(fixture(case))
        assert plan is not None
        assert plan.variant == 'ruled'


# 16:35:22 on 2026-10-18 (service 20261018T133419Z-2e7dc9ff): a set Battle Boots (2 x 2, `self`) in the cube had room on
# shared page 5 (a 2 x 2 at (2, 8)), the inventory none: a junk unique Fuscina (2 x 4) at (3, 0) held the only room,
# two cells were free, and the cube held the Boots, three resources and a junk magic item. No shared page has a 2 x 4
# for the Fuscina (page 5: a 3 x 2, a 2 x 2 and a 1 x 2; pages 2 and 3: single cells), so the park the player ruled at
# 16:50 cannot be made here: the Boots stay, named, and it is no stash full (a page has their room)


def test_the_1635_visit_replays_its_logged_miss_and_the_park_finds_no_page_for_the_fuscina():
    start = fixture('1635')
    stops = load(path_of('1635'))
    boots = 'set Battle Boots at (0, 0)'
    assert [s.stop for s in stops] == ['start', 'stash', 'shops', 'end']
    assert stops[-1].misses == (f'cube 1 items ({boots})', f'1 keepers carried ({boots})')
    assert start.predicted == stops[-1].misses  # the shadow plan foresaw it

    for rulings in (NO_PARK, BEFORE_1750, RULED):
        plan = plan_visit(start, rulings)
        assert plan is not None
        assert plan.variant == 'ruled'
        # Since 17:50 ("keeper can wait in cube") the Boots wait in the cube for the next visit: deferred, no miss
        assert plan.misses == (() if rulings.keeper_in_cube else stops[-1].misses)
        assert [i.unit_id for i in plan.deferred] == ([704388917] if rulings.keeper_in_cube else [])
        assert plan.contract.deferred == ((boots,) if rulings.keeper_in_cube else ())
        assert not any(s.verb == 'park' for s in plan.steps)
        assert {i.unit_id for i in plan.end.sold} == {4008087079, 4258077775}  # the Fuscina and the cube's junk, after
    first = plan_visit(start, VARIANTS['jamella first'])
    assert first is not None
    assert first.misses == ()  # her first would (not ruled: JAMELLA_FIRST off)


def test_the_1635_visit_with_a_2x4_on_a_shared_page_parks_the_fuscina_and_stashes_the_boots():
    # The same visit with page 4's last two columns free in its six first rows: the Fuscina parked first, onto their
    # top (the Ctrl + click's first fit), the Boots out through its cells onto the 2 x 2 below it on the same page
    # (`place` gives them page 4, the first with room), the Fuscina back and sold after, nothing left parked
    start = fixture('1635')
    assert start.view is not None
    room = replace(start.view.pages[4], rows=('#' * 8 + '..',) * 6 + start.view.pages[4].rows[6:])
    pages = (*start.view.pages[:4], room, *start.view.pages[5:])

    plan = plan_visit(replace(start, view=replace(start.view, pages=pages)))

    assert plan is not None
    assert plan.misses == ()
    moves = [(s.stop, s.verb, s.item.unit_id, s.to) for s in plan.steps]
    assert ('stash', 'park', 4008087079, 4) in moves
    assert ('stash', 'page', 704388917, 4) in moves
    assert ('stash', 'unpark', 4008087079, (3, 0)) in moves
    assert {i.unit_id for i in plan.end.sold} == {4008087079, 4258077775}
    assert plan.end.pack.in_cube == ()
    assert plan.end.parked == ()
    assert all(4008087079 not in page.units for page in plan.end.pages)


@pytest.mark.parametrize('case', LOGGED)
@pytest.mark.parametrize('rulings', [RULED, *VARIANTS.values()])
def test_no_variant_moves_the_players_own_items_or_sells_a_keeper(case, rulings):
    start = fixture(case)
    plan = plan_visit(start, rulings)

    assert plan is not None
    own = [i for i in start.pack.items if (i.txt, i.x, i.y) in start.own]
    assert all(i in plan.end.pack.items for i in own)  # the player's, where they were
    full = plan.end.full  # a full stack's material put down; no rune sold (the player, 17:50 on 2026-10-18)
    assert all(i.unit_id in start.junk for i in plan.end.sold)
    assert all(s.item.unit_id in start.junk or s.item.txt in full for s in plan.steps if s.verb in ('sell', 'drop'))
    assert all(s.item.unit_id in start.junk for s in plan.steps if s.verb in ('park', 'unpark'))
    # Every miss named, and the contract on the end state says the same
    done = contract(plan.end.pack, start.own, start.needs, junk=start.junk, full=plan.end.full)
    assert kinds(plan.misses) == kinds(done.misses) or plan.deferred


def test_an_unread_stash_gives_no_plan():
    assert plan_visit(replace(fixture('1505'), view=None)) is None


def test_the_contracts_misses_are_told_by_their_part():
    assert [kind_of(m) for m in ('cube 1 items (x)', 'block 2x4 taken', 'junk left 2', '1 keepers carried (x)',
                                 'keys 3 of 24', 'portals 1', '2 left on the ground', '1 junk parked on a page')] == [
        'cube', 'block', 'junk', 'keepers', 'keys', 'portals', 'ground', 'parked'
    ]  # fmt: skip
    assert kinds(['keys 3 of 24', 'junk left 1', 'cube 1 items']) == ('cube', 'junk')


def test_a_park_with_no_page_room_is_not_made():
    start = fixture('1505')
    assert start.view is not None
    full = replace(start.view, pages=tuple(replace(p, rows=('#' * 10,) * 10) for p in start.view.pages))
    state = State.of(replace(start, view=full))
    assert state is not None

    end, steps = simulate(state, start.needs)

    assert not any(s.verb == 'park' for s in steps)
    assert end.parked == ()


def test_a_visit_with_room_ends_with_the_cube_empty_and_the_junk_sold():
    # 14:06 on 2026-10-18 as test_visit.py makes it: a keeper onto page 5, the inventory's and the cube's junk sold
    the_cube, charms = test_town.THE_CUBE, test_town.OWN_CHARMS
    keeper = replace(test_town.thing(10, 'Ring', 6, 0), quality=4)
    junk = replace(test_town.thing(11, 'Amulet', 7, 0), quality=4)
    cubed = replace(test_town.thing(12, 'Ring', 0, 0), quality=4)
    pack = Pack((the_cube, *charms, keeper, junk), ('#..', '...', '...', '...'), frozenset({12}), (cubed,), keys=24)
    view = test_town.view({5: test_town.OPEN_PAGE})
    start = Snapshot('start', pack, own_of((the_cube, *charms)), Needs(), Exit.WAYPOINT, view, frozenset({11, 12}))

    plan = plan_visit(start)

    assert plan is not None
    assert plan.misses == ()
    assert [(s.stop, s.verb, s.item.unit_id) for s in plan.steps] == [
        ('stash', 'page', 10),
        ('stash', 'out', 12),
        ('jamella', 'sell', 11),
        ('jamella', 'sell', 12),
    ]
    assert plan.end.pages[5].units == {10}


def test_a_keeper_no_page_takes_stays_a_miss_with_the_ruling():
    # "keeper can wait in cube" is the keeper with room on a page; one with none is the stash full: still a miss
    start = fixture('1635')
    assert start.view is not None
    full = replace(start.view, pages=tuple(replace(p, rows=('#' * 10,) * 10) for p in start.view.pages))

    plan = plan_visit(replace(start, view=full))

    assert plan is not None
    assert plan.deferred == ()
    assert kinds(plan.misses) == MISSED


def test_the_plan_makes_the_rune_transmutes_and_sells_no_rune():
    # The player, 17:50 on 2026-10-18: "cubed, aim to 80 or lower": three transmutes of the 99 Tal Runes at the stash,
    # the carried Tal onto the room they make; none sold at Jamella
    the_cube, charms = test_town.THE_CUBE, test_town.OWN_CHARMS
    tal = test_town.thing(20, 'Tal Rune', 6, 3)
    junk = replace(test_town.thing(11, 'Amulet', 7, 0), quality=4)
    pack = Pack((the_cube, *charms, tal, junk), ('...',) * 4, keys=24)
    view = test_town.view(Tal_Rune=99, Ral_Rune=10)
    start = Snapshot('start', pack, own_of((the_cube, *charms)), Needs(), Exit.WAYPOINT, view, frozenset({11}))

    plan = plan_visit(start)

    assert plan is not None
    assert plan.misses == ()
    moves = [(s.stop, s.verb, s.item.txt, s.to) for s in plan.steps]
    ral = test_town.class_of('Ral Rune')
    assert moves.count(('stash', 'runes', tal.txt, ral)) == 3
    assert ('stash', 'tab', tal.txt, -4) in moves
    assert [i.unit_id for i in plan.end.sold] == [11]
    assert dict(plan.end.stacks)[tal.txt] == 91
    assert dict(plan.end.stacks)[ral] == 13
