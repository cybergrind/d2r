"""The stash stop by plan (macros/visit.py `stash_stop`; macros/town-plan.md step 2) and the town visit (`visit`, step
3)."""

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import pytest

from inventory_tracking.game.decode import item_size
from inventory_tracking.game.layout import BANK
from inventory_tracking.game.records import Carried, Pack, StashView, Teleport, Thing
from inventory_tracking.items.metadata import metadata
from inventory_tracking.macros.actuator import Hand
from inventory_tracking.macros.cube import CUBE_CLASS, own_of
from inventory_tracking.macros.town import Exit, Holdings, Needs, stash_stop as plan_stop
from inventory_tracking.macros.visit import Hands, Visited, stash_stop, visit
from tests.inventory_tracking.macros.fakes import Game, player, world


FORTRESS = 103
FULL_PAGE: tuple[str, ...] = ('#' * 10,) * 10
OPEN_PAGE: tuple[str, ...] = ('.' * 10,) * 10


def class_of(name: str) -> int:
    [found] = [int(cid) for cid, base in metadata()['bases'].items() if base['name'] == name]
    return found


def thing(unit: int, name: str, x: int, y: int) -> Carried:
    txt = class_of(name)
    return Carried(unit, txt, x, y, item_size(txt))


THE_CUBE = Carried(1, CUBE_CLASS, 0, 0, (2, 2))
OWN_CHARMS = tuple(thing(2 + i, 'Grand Charm', 2 + i, 0) for i in range(4))  # the player's, columns 2-5
OWN = own_of((THE_CUBE, *OWN_CHARMS))


def fortress(pack: Pack, pages: Sequence[tuple[str, ...]], game: type[Game] = Game) -> Game:
    play = game(world(FORTRESS, player=player(FORTRESS, x=5048.0, y=5044.0)))
    play.pack = pack
    play.thing = Thing(9, BANK, 0, 5038.0, 5040.0)
    play.stash_pages = list(pages)
    play.shared_page = 2  # the Shared tab shows the page last looked at
    return play


def read(run) -> StashView:
    view = run.stash_view() if run.stash_view is not None else None
    assert view is not None
    return view


def stop(play: Game, junk: frozenset[int] = frozenset()) -> int:
    run = play.run()
    view = read(run)
    assert play.pack is not None
    return stash_stop(run, plan_stop(Holdings(play.pack, OWN, junk), view), inventory_key='i', own=OWN)


def test_a_visit_clicks_only_the_page_with_room():
    # 12:48 and 12:42 on 2026-10-18: every page full but shared page 5, the scan tried pages 0 to 5 (13-15 s), each full
    # page ~2.25 s (an arrow, a Ctrl + click, a 1.0 s wait for the refusal)
    ring, charm = thing(10, 'Ring', 6, 0), thing(11, 'Grand Charm', 7, 0)
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, ring, charm)), [FULL_PAGE] * 5 + [OPEN_PAGE])
    began = play.clock.now

    assert stop(play) == 2

    assert play.stash_clicks == [(5, 11), (5, 10)]  # the largest first, both onto shared page 5 and no other
    assert play.stash_refused == []
    assert sorted(play.page_items[5]) == [10, 11]
    assert play.stash_opened == 1
    assert play.world.open_panels == ()
    assert play.clock.now - began < 8.0  # the walk, the opening, the Shared tab at page 5, two clicks, Escape
    assert play.said[-1] == 'Stash: 2 items put in'


def test_a_full_stacks_item_is_never_clicked():
    # 06:08:50-55 on 2026-10-18: seven flawless gems of four full stacks refused, ~1.3 s each; 11:46: 2.3 s on a full
    # essence's refusal
    tal, hel = thing(20, 'Tal Rune', 6, 3), thing(21, 'Hel Rune', 7, 3)
    gem = thing(22, 'Flawless Sapphire', 8, 3)
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, tal, hel, gem)), [FULL_PAGE] * 6)
    play.stacks = {tal.txt: 99, hel.txt: 10, gem.txt: 99}

    assert stop(play) == 1

    assert [unit for _page, unit in play.stash_clicks] == [hel.unit_id]
    assert play.stacks[hel.txt] == 11
    assert play.pack is not None
    assert {i.unit_id for i in play.pack.items} >= {tal.unit_id, gem.unit_id}  # for Jamella and the cube


def test_a_full_stacks_material_is_put_down_with_the_stash_open():
    # A Twisted Essence no vendor buys (refused at 11:46, 11:51, 11:56 and 12:43 on 2026-10-18), its stack full: of no
    # use (the player, 10:37: "there is no use for it")
    essence = thing(23, 'Twisted Essence of Suffering', 9, 3)
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, essence)), [FULL_PAGE] * 6)
    play.stacks = {essence.txt: 99}

    assert stop(play) == 0

    assert play.fallen == [essence]
    assert play.stash_clicks == []


def test_a_cube_keeper_goes_through_the_room_the_inventory_keepers_left_in_one_walk():
    # 12:48 on 2026-10-18: a Linked Mail in the cube found no room in the inventory before the stash; the stash closed
    # with it still in the cube, and a second STASH leg after Jamella walked back and tried pages 0 to 5 (15.4 s).
    # Whether the stash's resource view takes a cube item out by a Ctrl + click is not known (probe P1): the stash is
    # closed, the cube emptied into the room made, and opened again where the character stands
    keepers = (thing(10, 'Grand Charm', 6, 0), thing(11, 'Grand Charm', 7, 0))
    cells = [(8, 0), (9, 0), (8, 1), (9, 1), (8, 2), (9, 2), (0, 2), (1, 2)] + [(x, 3) for x in range(10)]
    junk = tuple(thing(100 + i, 'Ring', x, y) for i, (x, y) in enumerate(cells))
    mail = Carried(50, class_of('Linked Mail'), 0, 0, (2, 3))
    pack = Pack((THE_CUBE, *OWN_CHARMS, *keepers, *junk), ('##.', '##.', '##.', '...'), frozenset({50}), (mail,))
    play = fortress(pack, [FULL_PAGE] * 5 + [('#' * 10,) * 6 + ('.' * 10,) * 4])

    assert stop(play, frozenset(i.unit_id for i in junk)) == 3

    assert sorted(play.page_items[5]) == [10, 11, 50]
    assert play.stash_refused == []
    assert play.pack is not None
    assert play.pack.in_cube == ()
    assert {i.unit_id for i in play.pack.items} == {THE_CUBE.unit_id, *(i.unit_id for i in (*OWN_CHARMS, *junk))}
    assert play.stash_opened == 2  # opened again in place: no walk back after Jamella
    assert play.world.open_panels == ()


def test_a_refused_put_falls_back_to_the_scan_for_that_item_only():
    # The plan's §5: a page told wrong (the stash changed by hand since the read) is refused; that item alone goes to
    # today's scan, page after page
    ring, charm = thing(10, 'Ring', 6, 0), thing(11, 'Ring', 7, 0)
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, ring, charm)), [FULL_PAGE] * 5 + [('.' + '#' * 9,) + ('#' * 10,) * 9])
    run = play.run()
    stale = read(run)
    stale = StashView((*stale.pages[:5], type(stale.pages[5])(5, ('..' + '#' * 8,) + ('#' * 10,) * 9)), stale.stacks)
    assert play.pack is not None

    moved = stash_stop(run, plan_stop(Holdings(play.pack, OWN), stale), inventory_key='i', own=OWN)

    assert moved == 1
    assert play.page_items[5] == [10]  # the first fitted the one free cell; the second was refused there
    assert play.stash_refused.count(11) >= 1
    assert play.pack is not None
    assert charm in play.pack.items  # every page full: it stays
    assert play.world.open_panels == ()


def test_the_next_stop_goes_to_the_shared_page_shown_last_with_no_arrow():
    # The Shared tab shows the page last looked at: page 5 again needs the tab's click alone, not four left arrows and
    # four right ones (5.3 s of the first stop's 7)
    from inventory_tracking.macros.visit import Remembered

    memory = Remembered()
    rings = [thing(10 + i, 'Ring', 6 + i, 0) for i in range(2)]
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, rings[0])), [FULL_PAGE] * 5 + [OPEN_PAGE])
    run = play.run()
    view = read(run)
    assert play.pack is not None
    stash_stop(run, plan_stop(Holdings(play.pack, OWN), view), inventory_key='i', own=OWN, memory=memory)
    assert memory.shared == 5
    play.pack = Pack((THE_CUBE, *OWN_CHARMS, rings[1]))
    view = read(run)
    clicks = len(play.keys.events)
    began = play.clock.now

    assert stash_stop(run, plan_stop(Holdings(play.pack, OWN), view), inventory_key='i', own=OWN, memory=memory) == 1

    assert play.stash_clicks[-1] == (5, rings[1].unit_id)
    assert play.stash_refused == []
    assert len(play.keys.events) - clicks < 20
    assert play.clock.now - began < 3.0


def test_a_remembered_page_the_player_changed_is_found_again_from_the_first():
    from inventory_tracking.macros.visit import Remembered

    memory = Remembered(shared=5)  # the player has looked at page 3 since, which is full
    ring = thing(10, 'Ring', 6, 0)
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, ring)), [FULL_PAGE] * 5 + [OPEN_PAGE])
    play.shared_page = 2  # page 3 shown on the Shared tab

    run = play.run()
    view = read(run)
    assert play.pack is not None
    assert stash_stop(run, plan_stop(Holdings(play.pack, OWN), view), inventory_key='i', own=OWN, memory=memory) == 1

    assert play.stash_clicks == [(3, ring.unit_id), (5, ring.unit_id)]
    assert play.page_items[5] == [ring.unit_id]


# The town visit (macros/visit.py `visit`; macros/town-plan.md step 3)

LK_NEEDS = Needs()  # the Warlock's 2 x 4, LK's two key stacks


def no_park(monkeypatch) -> None:
    """The stash stop as it was before the player's ruling of 16:50 on 2026-10-18 (town.py PARK_JUNK off)."""
    monkeypatch.setattr('inventory_tracking.macros.town.PARK_JUNK', False)


def no_waiting(monkeypatch) -> None:
    """A keeper left in the cube a miss, as before the player's ruling of 17:50 on 2026-10-18 (KEEPER_IN_CUBE off)."""
    monkeypatch.setattr('inventory_tracking.macros.visit.KEEPER_IN_CUBE', False)


class Town:
    """A visit's stops told apart in a fortress fake: Cain (`Hands.identify`), the stash (its openings), Jamella
    (shop.py `restock`: sells what it is given, buys the keys up), Halbu (repair.py `repair`), the walk to the
    waypoint."""

    def __init__(self, monkeypatch, play: Game, junked: frozenset[int] = frozenset()) -> None:
        import inventory_tracking.macros.visit as visit_module

        self.play, self.junked = play, set(junked)
        self.order: list[str] = []
        self.sold: list[int] = []
        self.offered: list[list[int]] = []
        self.hand_at: str | None = None  # the stop the player's hand cuts, once
        real_open = visit_module.open_stash

        def open_stash(run):
            self.order.append('stash')
            return real_open(run)

        def restock(run, sell=(), back=True, keys=None):
            assert not back  # the visit walks to the waypoint itself, after Halbu
            self.cut('jamella')
            self.order.append('jamella')
            self.offered.append([i.unit_id for i in sell])
            pack = carried(play)
            units = {i.unit_id for i in sell}
            self.sold += [i.unit_id for i in pack.items if i.unit_id in units]
            play.pack = replace(pack, items=tuple(i for i in pack.items if i.unit_id not in units), keys=keys)

        def repair(run, fix=True):
            self.cut('halbu')
            self.order.append('halbu')
            if play.staff is not None:
                play.staff = Teleport(play.staff.maximum, play.staff.maximum, False)
            return True

        def walk_until(run, place, bounds, what):
            self.order.append('waypoint')
            return run.world()

        monkeypatch.setattr(visit_module, 'open_stash', open_stash)
        monkeypatch.setattr(visit_module, 'restock', restock)
        monkeypatch.setattr(visit_module, 'repair', repair)
        monkeypatch.setattr(visit_module, 'walk_until', walk_until)
        monkeypatch.setattr('inventory_tracking.macros.repair.QUOTE_FILE', Path('/nonexistent/quote'))
        monkeypatch.setattr('inventory_tracking.macros.repair.STASH_TOUCHED', Path('/nonexistent/touched'))
        monkeypatch.setattr('inventory_tracking.macros.repair.unknown', lambda: False)  # his line learned

    def cut(self, stop: str) -> None:
        if self.hand_at == stop:
            self.hand_at = None
            raise Hand('the mouse was moved')

    def identify(self, items) -> int:
        self.order.append('cain')
        units = {i.unit_id for i in items}
        pack = carried(self.play)
        known = lambda found: tuple(replace(i, identified=True) if i.unit_id in units else i for i in found)  # ruff: ignore[lambda-assignment]
        self.play.pack = replace(pack, items=known(pack.items), in_cube=known(pack.in_cube))
        return len(units)

    def hands(self) -> Hands:
        run = self.run

        def judge(items):
            return [i for i in items if i.unit_id in self.junked]

        return Hands(lambda: 'i', self.identify, judge, lambda: run.stash_view() if run.stash_view else None)

    def visit(self, exit: Exit = Exit.WAYPOINT) -> Visited:
        self.run = self.play.run()
        return visit(self.run, self.hands(), LK_NEEDS, OWN, exit)

    def stops(self) -> list[str]:
        """The stops in order, a stash opened again in place told once."""
        return [stop for n, stop in enumerate(self.order) if n == 0 or self.order[n - 1] != stop]


def carried(play: Game) -> Pack:
    assert play.pack is not None
    return play.pack


def test_a_visit_goes_cain_the_stash_jamella_and_the_waypoint_once(monkeypatch, caplog):
    # 14:06 on 2026-10-18: identify, the stash, Jamella, then a second walk back to the stash for a cube keeper; the
    # player, 12:55: "we visit the stash only ONE time, no running back and forward"
    keeper = replace(thing(10, 'Ring', 6, 0), quality=4, identified=False)
    junk = replace(thing(11, 'Amulet', 7, 0), quality=4, identified=False)
    cubed = replace(thing(12, 'Ring', 0, 0), quality=4)  # identified junk in the cube
    pack = Pack((THE_CUBE, *OWN_CHARMS, keeper, junk), ('#..', '...', '...', '...'), frozenset({12}), (cubed,), keys=5)
    play = fortress(pack, [FULL_PAGE] * 5 + [OPEN_PAGE])
    town = Town(monkeypatch, play, frozenset({11, 12}))

    with caplog.at_level('INFO'):
        done = town.visit()

    assert town.stops() == ['cain', 'stash', 'jamella', 'waypoint']
    assert town.order.count('stash') == 1  # one walk, one opening
    assert play.page_items[5] == [10]  # the keeper onto the one page with room, identified at Cain first
    assert sorted(town.sold) == [11, 12]  # the inventory's junk and the cube's, out in the stash stop
    assert done.contract.misses == ()
    assert done.contract.cube == 0
    assert done.contract.block_free
    assert carried(play).keys == 24  # LK's two stacks
    assert play.world.open_panels == ()
    line = next(r.message for r in caplog.records if 'trade session done' in r.message)
    assert line.startswith('Macro: trade session done: cube 0 items, block 2x4 free, ')
    assert 'junk left 0, keys 24' in line
    assert '(cain ' in line
    assert ', halbu -, walk ' in line


def test_halbu_comes_after_jamella_and_a_game_left_from_beside_him_walks_nowhere(monkeypatch):
    # The player, 2026-10-17: "we repaired staff -> walked to wp -> walked to jamella"; 18:04:54: 8.6 s walked back to
    # the waypoint before Save and Exit
    junk = replace(thing(11, 'Amulet', 7, 0), quality=4)
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, junk), keys=24), [OPEN_PAGE] * 6)
    play.staff = Teleport(5, 69, False)  # under 20%: his repair
    town = Town(monkeypatch, play, frozenset({11}))

    done = town.visit(Exit.LEAVE)

    assert town.stops() == ['jamella', 'halbu']  # nothing for Cain nor the stash: neither walked to
    assert not done.repair_failed
    assert play.staff == Teleport(69, 69, False)

    play.pack = Pack((THE_CUBE, *OWN_CHARMS, replace(junk, unit_id=13)), keys=24)
    town.junked.add(13)
    play.staff = Teleport(60, 69, False)  # any charge missing in a visit, while the gold covers it
    town.order.clear()
    town.visit(Exit.WAYPOINT)
    assert town.stops() == ['jamella', 'halbu', 'waypoint']


def test_a_cube_long_battle_bow_goes_into_the_stash_in_the_same_stop(monkeypatch):
    # 14:06 on 2026-10-18: a unique Long Battle Bow (2 x 4) in the cube found no inventory room before the stash; a
    # second walk back after Jamella took it to page 5 in 7.2 s
    keepers = (thing(20, 'Grand Charm', 6, 0), thing(21, 'Grand Charm', 7, 0))
    cells = [(x, y) for x in (8, 9) for y in range(4)] + [(0, 2), (1, 2)] + [(x, 3) for x in range(6)]
    junk = tuple(thing(100 + n, 'Ring', x, y) for n, (x, y) in enumerate(cells))
    bow = Carried(50, class_of('Long Battle Bow'), 0, 0, (2, 4), quality=7)
    pack = Pack((THE_CUBE, *OWN_CHARMS, *keepers, *junk), ('##.',) * 4, frozenset({50}), (bow,), keys=24)
    play = fortress(pack, [FULL_PAGE] * 5 + [OPEN_PAGE])
    town = Town(monkeypatch, play, frozenset(i.unit_id for i in junk))

    done = town.visit()

    assert town.stops() == ['stash', 'jamella', 'waypoint']  # opened again in place for it: no walk back
    assert sorted(play.page_items[5]) == [20, 21, 50]
    assert carried(play).in_cube == ()
    assert sorted(town.sold) == sorted(i.unit_id for i in junk)
    assert done.contract.misses == ()


def test_a_visit_cut_by_the_players_hand_is_made_again_with_nothing_done_twice(monkeypatch):
    keeper = replace(thing(10, 'Ring', 6, 0), quality=4, identified=False)
    junk = replace(thing(11, 'Amulet', 7, 0), quality=4, identified=False)
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, keeper, junk), keys=5), [FULL_PAGE] * 5 + [OPEN_PAGE])
    town = Town(monkeypatch, play, frozenset({11}))
    town.hand_at = 'jamella'

    with pytest.raises(Hand):
        town.visit()
    assert town.stops() == ['cain', 'stash']
    done = town.visit()  # the leg made again (runner.py `_loop_stopped`): planned from what is carried now

    assert town.stops() == ['cain', 'stash', 'jamella', 'waypoint']  # neither Cain nor the stash again
    assert town.sold == [11]
    assert play.page_items[5] == [10]
    assert done.contract.misses == ()


def test_a_full_stacks_material_is_put_down_not_offered_to_jamella(monkeypatch):
    # 11:46, 11:51, 11:56 and 12:43 on 2026-10-18: Jamella refused a Twisted Essence of Suffering each session, its
    # stash stack full; the player: "there is no use for it", "we just need to make some space"
    essence = thing(23, 'Twisted Essence of Suffering', 9, 3)
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, essence), keys=1), [FULL_PAGE] * 6)
    play.stacks = {essence.txt: 99}
    town = Town(monkeypatch, play)

    done = town.visit()

    assert play.fallen == [essence]
    assert town.offered == [[]]  # Jamella for the keys alone
    assert done.full == frozenset({essence.txt})
    assert done.contract.misses == ()


def test_junk_left_unsold_is_short_of_the_contract(monkeypatch, caplog):
    import inventory_tracking.macros.visit as visit_module

    junk = replace(thing(11, 'Amulet', 7, 0), quality=4)
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, junk), keys=24), [OPEN_PAGE] * 6)
    town = Town(monkeypatch, play, frozenset({11}))
    monkeypatch.setattr(visit_module, 'restock', lambda run, sell=(), back=True, keys=None: None)  # none sold

    with caplog.at_level('INFO'):
        done = town.visit()

    assert done.contract.misses == ('junk left 1',)
    assert 'Macro: trade session done (short of the contract: junk left 1): cube 0 items' in caplog.text


def test_junk_no_sale_takes_at_the_gold_cap_is_put_down_in_town(monkeypatch, caplog):
    # 09:19:05 on 2026-10-20: the gold 920,176 of 940,000, the stash's full: 4 junk items kept took the 2x4 block. The
    # player: "we don't need money from selling these items"
    import inventory_tracking.macros.visit as visit_module

    junk = replace(thing(11, 'Amulet', 7, 0), quality=4)
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, junk), keys=24), [OPEN_PAGE] * 6)
    town = Town(monkeypatch, play, frozenset({11}))
    monkeypatch.setattr(visit_module, 'restock', lambda run, sell=(), back=True, keys=None: None)  # none sold
    monkeypatch.setattr(visit_module, 'gold', lambda run: 920_176)
    monkeypatch.setattr(visit_module, 'gold_cap', lambda run: 940_000)
    dropped: list[int] = []
    monkeypatch.setattr(visit_module, 'drop_item', lambda run, key, item, why: dropped.append(item.unit_id) or True)

    town.visit()

    assert dropped == [11]
    monkeypatch.setattr(visit_module, 'DROP_CAPPED_JUNK', False)
    dropped.clear()
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, junk), keys=24), [OPEN_PAGE] * 6)
    Town(monkeypatch, play, frozenset({11})).visit()
    assert dropped == []  # off: kept as before


# A cube keeper whose block the inventory's junk holds (rca/2026-10-18/town-remaining-findings.md §1)


@pytest.mark.parametrize(
    ('case', 'keeper', 'page', 'moved'),
    [
        ('1428', 31, 5, "the Amulet moved aside (4, 2) to (2, 3): room for the cube's Embossed Plate"),
        ('1455', 50, 5, "the Ring moved aside (3, 2) to (4, 0): room for the cube's Spiked Club"),
    ],
)
def test_a_visit_with_a_cube_keeper_behind_the_junk_ends_with_an_empty_cube_in_one_walk(
    monkeypatch, caplog, case, keeper, page, moved
):
    # 14:28:27 and 14:56:16 on 2026-10-18: "short of the contract: cube 1 items (unique Embossed Plate / Spiked Club at
    # (0, 0)), 1 keepers carried": the junk moved aside with the stash open, then the close and reopen in place
    import inventory_tracking.macros.visit as visit_module
    from tests.inventory_tracking.macros import test_town

    monkeypatch.setattr(visit_module, 'JAMELLA_FIRST', True)  # off until the player's ruling
    pack, own, junk = getattr(test_town, f'pack_{case}')()
    stash = getattr(test_town, f'view_{case}')()
    play = fortress(replace(pack, keys=24), [p.rows for p in stash.pages])
    play.stacks = dict(stash.stacks)
    town = Town(monkeypatch, play, junk)
    town.run = play.run()

    with caplog.at_level('INFO'):
        done = visit(town.run, town.hands(), LK_NEEDS, own, Exit.WAYPOINT)

    assert town.stops() == ['stash', 'jamella', 'waypoint']
    assert play.stash_opened == 2  # one walk: opened again in place
    assert keeper in play.page_items[page]
    assert carried(play).in_cube == ()
    assert sorted(town.sold) == sorted(junk)
    assert done.contract.misses == ()
    assert f'Macro: stash: {moved}' in caplog.text
    assert play.world.open_panels == ()


def test_the_junk_moved_into_the_cube_is_sold_at_jamella(monkeypatch, caplog):
    # No cell outside the plate's block for the junk Ring in it: the Ring into the cube beside the plate, the plate out,
    # the Ring sold from the cube at Jamella
    from tests.inventory_tracking.macros.test_town import BLOCK_BUT_ONE, grid

    ring = replace(thing(60, 'Ring', 4, 2), quality=4)
    rings = [replace(thing(61 + n, 'Ring', x, 3), quality=4) for n, x in enumerate((3, 4))]
    pack, own = grid(BLOCK_BUT_ONE, [ring, *rings])
    play = fortress(replace(pack, keys=24), [FULL_PAGE] * 5 + [OPEN_PAGE])
    junk = frozenset({60, 61, 62})
    town = Town(monkeypatch, play, junk)
    town.run = play.run()

    with caplog.at_level('INFO'):
        done = visit(town.run, town.hands(), LK_NEEDS, own, Exit.WAYPOINT)

    assert town.stops() == ['stash', 'jamella', 'waypoint']
    assert play.stash_opened == 2
    assert play.page_items[5] == [50]
    assert sorted(town.sold) == [60, 61, 62]
    assert carried(play).in_cube == ()
    assert done.contract.misses == ()
    assert "Macro: cube: 1 of 1 junk items put in for Jamella: room for the cube's Embossed Plate" in caplog.text


def test_the_players_item_by_its_stats_in_the_cube_is_kept_not_sold(monkeypatch, caplog):
    # 23:16:58 on 2026-10-18: the player's Kriss and +35 Life charm, put in the cube by hand, appraised vendor and sold.
    # The cube is the loop's (the player, 2026-10-19), but an item whose stats are one of the player's
    # (macros/volatile.py prints) is never junk: kept, never offered to Jamella
    from tests.inventory_tracking.macros.test_town import BLOCK_BUT_ONE, grid

    ring = replace(thing(60, 'Ring', 4, 2), quality=4)
    rings = [replace(thing(61 + n, 'Ring', x, 3), quality=4) for n, x in enumerate((3, 4))]
    pack, own = grid(BLOCK_BUT_ONE, [ring, *rings])
    play = fortress(replace(pack, keys=24), [FULL_PAGE] * 5 + [OPEN_PAGE])
    town = Town(monkeypatch, play, frozenset({60, 61, 62}))
    town.run = play.run()
    town.run.players_item = lambda item: item.unit_id == 60

    with caplog.at_level('INFO'):
        visit(town.run, town.hands(), LK_NEEDS, own, Exit.WAYPOINT)

    assert 60 not in town.sold
    assert sorted(town.sold) == [61, 62]
    assert "(the player's by its stats): kept, not sold" in caplog.text


def test_an_amulet_kept_by_its_stats_is_no_junk(monkeypatch, caplog):
    # 03:48 on 2026-10-19: Corruption Scarab (+41 life) and Havoc Torc (+59 life) appraised vendor and sold; the
    # player's words keep a rare amulet with life, FCR or +2 skills (macros/keepers.py): no junk, never sold
    from tests.inventory_tracking.macros.test_town import BLOCK_BUT_ONE, grid

    ring = replace(thing(60, 'Ring', 4, 2), quality=4)
    rings = [replace(thing(61 + n, 'Ring', x, 3), quality=4) for n, x in enumerate((3, 4))]
    pack, own = grid(BLOCK_BUT_ONE, [ring, *rings])
    play = fortress(replace(pack, keys=24), [FULL_PAGE] * 5 + [OPEN_PAGE])
    town = Town(monkeypatch, play, frozenset({60, 61, 62}))
    town.run = play.run()
    town.run.kept_item = lambda item: '+41 life' if item.unit_id == 60 else None

    with caplog.at_level('INFO'):
        visit(town.run, town.hands(), LK_NEEDS, own, Exit.WAYPOINT)

    assert 60 not in town.sold
    assert sorted(town.sold) == [61, 62]
    assert '(kept by its stats (+41 life)): kept, not sold' in caplog.text


@pytest.mark.parametrize(
    ('case', 'keepers', 'name'), [('1505', (51, 53), 'Boots'), ('1514', (50, 41, 53), 'Serpentskin Armor')]
)
def test_jamella_comes_before_the_stash_when_only_the_junks_sale_lets_a_cube_keeper_out(
    monkeypatch, caplog, case, keepers, name
):
    # 15:05:53 on 2026-10-18: a junk Fuscina (2 x 4) held the inventory's only room, the cube full; the set Boots stayed
    # in the cube, "short of the contract: cube 1 items (set Boots at (1, 0))". Her first, then the stash: one walk to
    # each, the Boots out before the stash opens
    import inventory_tracking.macros.visit as visit_module
    from tests.inventory_tracking.macros import test_town

    monkeypatch.setattr(visit_module, 'JAMELLA_FIRST', True)  # off: the player ruled the park instead (16:50)
    no_park(monkeypatch)
    pack, own, junk = getattr(test_town, f'pack_{case}')()
    stash = getattr(test_town, f'view_{case}')()
    play = fortress(pack, [p.rows for p in stash.pages])
    play.stacks = dict(stash.stacks)
    town = Town(monkeypatch, play, junk)
    town.run = play.run()

    with caplog.at_level('INFO'):
        done = visit(town.run, town.hands(), LK_NEEDS, own, Exit.WAYPOINT)

    assert town.stops() == ['jamella', 'stash']  # the waypoint is beside the stash: no walk
    assert play.stash_opened == 1
    assert all(any(unit in items for items in play.page_items.values()) for unit in keepers)
    assert sorted(town.sold) == sorted(junk)
    assert carried(play).in_cube == ()
    assert done.contract.misses == ()
    assert f"Macro: town visit: Jamella before the stash: the cube's {name} has no room until the junk is sold" in (
        caplog.text
    )


def test_with_the_gold_near_its_cap_the_stash_still_comes_first(monkeypatch, caplog):
    # A sale near the cap drops the gold over it (15:33 on 2026-10-17): the deposit is the stash's, so no reorder
    import inventory_tracking.macros.visit as visit_module
    from tests.inventory_tracking.macros.test_town import pack_1505, view_1505

    pack, own, junk = pack_1505()
    stash = view_1505()
    play = fortress(pack, [p.rows for p in stash.pages])
    play.stacks = dict(stash.stacks)
    town = Town(monkeypatch, play, junk)
    town.run = play.run()
    monkeypatch.setattr(visit_module, 'JAMELLA_FIRST', True)
    no_park(monkeypatch)
    monkeypatch.setattr(visit_module, 'gold', lambda run: 990_000)
    monkeypatch.setattr(visit_module, 'gold_cap', lambda run: 990_000)

    with caplog.at_level('INFO'):
        visit(town.run, town.hands(), LK_NEEDS, own, Exit.WAYPOINT)

    assert town.stops()[:2] == ['stash', 'jamella']
    assert 'the gold is near its cap: the stash first' in caplog.text


# The visit's snapshots (macros/visitlog.py; step M0)


def test_a_visit_writes_a_snapshot_at_each_stop_and_its_contract_names_the_stranded_keeper(monkeypatch, tmp_path):
    # 15:05:53 on 2026-10-18 in the order of then (no park): the Boots left in the cube
    import inventory_tracking.macros.visitlog as visitlog
    from tests.inventory_tracking.macros.test_town import pack_1505, view_1505

    no_park(monkeypatch)
    no_waiting(monkeypatch)
    monkeypatch.setattr(visitlog, 'session_directory', lambda: tmp_path)
    # the Fuscina junk as at 15:05, before the best-copy ruling of 16:50 kept a first copy (macros/copies.py)
    monkeypatch.setattr('inventory_tracking.macros.copies.sold', lambda junk, directory: list(junk))
    pack, own, junk = pack_1505()
    stash = view_1505()
    play = fortress(pack, [p.rows for p in stash.pages])
    play.stacks = dict(stash.stacks)
    town = Town(monkeypatch, play, junk)
    town.run = play.run()

    done = visit(town.run, town.hands(), LK_NEEDS, own, Exit.WAYPOINT)

    boots = 'set Boots at (1, 0)'
    assert done.contract.misses[:2] == (f'cube 1 items ({boots})', f'1 keepers carried ({boots})')
    [path] = (tmp_path / 'visits').iterdir()
    stops = visitlog.load(path)
    assert [s.stop for s in stops] == ['start', 'stash', 'shops', 'end']
    assert stops[0].pack == pack
    assert stops[0].junk == junk
    assert stops[0].view is not None
    assert stops[1].view is not None  # the stash as read after its stop
    assert stops[-1].misses == done.contract.misses
    assert stops[-1].pack == carried(play)


def test_a_visit_with_room_has_no_miss_and_writes_nothing_without_a_run_directory(monkeypatch, caplog):
    keeper = replace(thing(10, 'Ring', 6, 0), quality=4)
    junk = replace(thing(11, 'Amulet', 7, 0), quality=4)
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, keeper, junk), keys=24), [FULL_PAGE] * 5 + [OPEN_PAGE])
    town = Town(monkeypatch, play, frozenset({11}))

    with caplog.at_level('INFO'):
        done = town.visit()

    assert done.contract.misses == ()
    assert 'visit snapshot' not in caplog.text


# The player's rulings of 16:50 on 2026-10-18: the junk parked in the stash for a cube keeper, the stash full


def replay(monkeypatch, pack: Pack, own, junk: frozenset[int], stash: StashView) -> tuple[Game, Town]:
    play = fortress(pack, [p.rows for p in stash.pages])
    play.stacks = dict(stash.stacks)
    town = Town(monkeypatch, play, junk)
    town.run = play.run()
    return play, town


@pytest.mark.parametrize(('case', 'keeper', 'page'), [('1505', 51, 4), ('1514', 50, 5), ('1520', 50, 5)])
def test_the_junk_holding_a_cube_keepers_way_is_parked_in_the_stash_and_sold_after(
    monkeypatch, caplog, case, keeper, page
):
    # "junk can be temporarily stored in stash, but sold after": the junk onto a shared page with the stash open, the
    # keeper out and onto its page, the junk back before the stash closes; one walk to the stash, her after it
    from tests.inventory_tracking.macros import test_town

    pack, own, junk = getattr(test_town, f'pack_{case}')()
    play, town = replay(monkeypatch, pack, own, junk, getattr(test_town, f'view_{case}')())

    with caplog.at_level('INFO'):
        done = visit(town.run, town.hands(), LK_NEEDS, own, Exit.WAYPOINT)

    assert town.stops() == ['stash', 'jamella', 'waypoint']
    assert play.stash_opened == 2  # opened again in place: no walk back
    assert keeper in play.page_items[page]
    assert all(40 not in units for units in play.page_items.values())  # the parked junk taken back
    assert sorted(town.sold) == sorted(junk)
    assert carried(play).in_cube == ()
    assert done.contract.misses == ()
    assert done.contract.stash_full == ()
    assert done.contract.in_stash == 0
    assert 'parked on page 5 for the stop: room for the cube' in caplog.text
    assert 'taken back from page 5 for Jamella' in caplog.text
    assert play.world.open_panels == ()


def test_the_1635_visit_with_no_page_for_the_fuscina_leaves_the_boots_waiting_in_the_cube_not_the_stash_full(
    monkeypatch, caplog
):
    # 16:35:22 on 2026-10-18 (fixtures/visits/2026-10-18-163522.json): no shared page has a 2 x 4 for the Fuscina, so
    # nothing is parked; the Boots stay in the cube, as the visit logged. Room on page 5 for them:
    # no stash full (the loop goes on). Since 17:50 ("keeper can wait in cube") they wait for the next visit: named on
    # the contract as deferred, no miss, one line saying so
    from inventory_tracking.macros.visitlog import load
    from tests.inventory_tracking.macros.test_visitlog import fixture, path_of

    start = fixture('1635')
    assert start.view is not None
    play, town = replay(monkeypatch, start.pack, start.own, start.junk, start.view)

    with caplog.at_level('INFO'):
        done = visit(town.run, town.hands(), LK_NEEDS, start.own, Exit.WAYPOINT)

    boots = 'set Battle Boots at (0, 0)'
    assert load(path_of('1635'))[-1].misses == (f'cube 1 items ({boots})', f'1 keepers carried ({boots})')  # then
    assert done.contract.deferred == (boots,)
    assert not any(miss.startswith(('cube ', '1 keepers')) for miss in done.contract.misses)
    assert done.contract.cube == 1  # its cells the cube's, as the loop's room counts them
    assert [i.unit_id for i in carried(play).in_cube] == [704388917]
    assert caplog.text.count(f'Macro: town visit: {boots} waits in the cube for the next visit') == 1
    assert 'short of the contract: cube' not in caplog.text
    assert done.contract.stash_full == ()
    assert 'parked on page' not in caplog.text
    assert 'Macro: stash: full' not in caplog.text
    assert sorted(town.sold) == sorted(start.junk)  # the Fuscina and the cube's junk, at Jamella


def test_a_keeper_no_page_has_room_for_is_the_stash_full_named_on_the_contract(monkeypatch, caplog):
    # "if stash is full - we need to stop loop": the unique Ring has no page with room (every page full); the contract
    # names it for the loop (runner.py stops on `Contract.stash_full`), one log line
    ring = replace(thing(10, 'Ring', 6, 0), quality=7)
    junk = replace(thing(11, 'Amulet', 7, 0), quality=4)
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, ring, junk), keys=24), [FULL_PAGE] * 6)
    town = Town(monkeypatch, play, frozenset({11}))

    with caplog.at_level('INFO'):
        done = town.visit()

    assert done.contract.stash_full == ('unique Ring at (6, 0)',)
    assert caplog.text.count('Macro: stash: full: unique Ring at (6, 0)') == 1
    assert '1 keepers carried (unique Ring at (6, 0))' in done.contract.misses
    assert town.sold == [11]
    assert play.stash_clicks == []  # no page tried and refused


def test_junk_a_park_left_in_the_stash_is_named_on_the_contract(monkeypatch, caplog):
    # Never meant to happen: the parked Fuscina did not come back (its click refused, say); the contract names it
    import inventory_tracking.macros.visit as visit_module
    from tests.inventory_tracking.macros.test_town import pack_1505, view_1505

    pack, own, junk = pack_1505()
    play, town = replay(monkeypatch, pack, own, junk, view_1505())
    monkeypatch.setattr(visit_module, '_unpark', lambda run, rect, parked, tally: list(parked))

    with caplog.at_level('INFO'):
        done = visit(town.run, town.hands(), LK_NEEDS, own, Exit.WAYPOINT)

    assert 40 in play.page_items[5]
    assert done.contract.in_stash == 1
    assert '1 junk parked on a page (unique Fuscina at (0, 0))' in done.contract.misses
    assert 'Macro: stash: 1 junk left parked in the stash: Fuscina on page 5' in caplog.text


def test_a_stop_that_gives_up_after_the_park_takes_the_junk_back_first(monkeypatch, caplog):
    # A failure between the park and the take back (here the moves aside): the stash opened again in place, the
    # Fuscina taken back, then the stop gives up as before (the Boots stay in the cube); nothing of the junk left there
    import inventory_tracking.macros.visit as visit_module
    from inventory_tracking.macros.actuator import Abort
    from tests.inventory_tracking.macros.test_town import pack_1505, view_1505

    def broken(run, rect, moves, later):
        raise Abort('the Key was not taken up')

    pack, own, junk = pack_1505()
    play, town = replay(monkeypatch, pack, own, junk, view_1505())
    monkeypatch.setattr(visit_module, '_aside', broken)

    with caplog.at_level('INFO'):
        done = visit(town.run, town.hands(), LK_NEEDS, own, Exit.WAYPOINT)

    assert all(40 not in units for units in play.page_items.values())
    assert 'the parked Fuscina taken back from page 5 for Jamella' in caplog.text
    assert 'Macro: stash: the Key was not taken up: the visit goes on' in caplog.text
    assert 40 in town.sold
    assert done.contract.in_stash == 0
    assert any(miss.startswith('cube 1 items (set Boots') for miss in done.contract.misses)


def test_a_parked_junk_landing_on_another_page_than_recorded_is_still_taken_back_and_sold(monkeypatch, caplog):
    # The parked Fuscina lies on page 1, its park recorded on page 5: taken back by its unit id from wherever it lies
    import inventory_tracking.macros.visit as visit_module
    from tests.inventory_tracking.macros.test_town import pack_1505, view_1505

    real_park = visit_module._park

    def elsewhere(run, rect, parks, tally, later, parked):
        real_park(run, rect, [replace(put, to=1) for put in parks], tally, later, parked)
        parked[:] = [(item, 5) for item, _page in parked]  # recorded as planned, not where it went

    pack, own, junk = pack_1505()
    play, town = replay(monkeypatch, pack, own, junk, view_1505())
    assert play.stash_pages is not None
    play.stash_pages[1] = OPEN_PAGE  # room on page 1 too, after page 5 in the parks' order: still planned onto 5
    monkeypatch.setattr(visit_module, '_park', elsewhere)

    with caplog.at_level('INFO'):
        done = visit(town.run, town.hands(), LK_NEEDS, own, Exit.WAYPOINT)

    assert 'the parked Fuscina taken back from page 1 for Jamella' in caplog.text
    assert all(40 not in units for units in play.page_items.values())
    assert 40 in town.sold
    assert done.contract.junk_left == 0
    assert done.contract.in_stash == 0


def test_junk_left_on_a_stash_page_counts_as_junk_left(monkeypatch, caplog):
    # 21:55:45 on 2026-10-19: "junk left 0" with junk on a stash page. A parked one not taken back is junk left
    import inventory_tracking.macros.visit as visit_module
    from tests.inventory_tracking.macros.test_town import pack_1505, view_1505

    pack, own, junk = pack_1505()
    _play, town = replay(monkeypatch, pack, own, junk, view_1505())
    monkeypatch.setattr(visit_module, '_unpark', lambda run, rect, parked, tally: list(parked))

    with caplog.at_level('INFO'):
        done = visit(town.run, town.hands(), LK_NEEDS, own, Exit.WAYPOINT)

    assert done.contract.junk_left == 1
    assert 'junk left 1' in done.contract.misses
    assert ', junk left 1, ' in caplog.text


# 21:55:19-45 on 2026-10-19, game 31 (fixtures/visits/2026-10-19-215519.json): a magic Matriarchal Javelin in the cube,
# appraised `vendor` at Cain, was no junk (pickmode.py `sellable` took magic items only of the skill types) and went
# onto shared page 1, planned 3; the player: "we had put trash item for sale and forgot to pick it and sell"
JAVELIN, CHECKED = 3254005591, 4042921899  # the Javelin; the Small Charm appraised `check`
VISIT_2155 = Path(__file__).parent / 'fixtures' / 'visits' / '2026-10-19-215519.json'


def test_the_2155_magic_javelin_appraised_vendor_is_sold_not_stashed(monkeypatch, caplog):
    from inventory_tracking.macros.junk import junk_of
    from inventory_tracking.macros.visitlog import load

    start = load(VISIT_2155)[0]
    assert start.view is not None
    assert JAVELIN not in start.junk  # as the visit judged it then
    play, town = replay(monkeypatch, start.pack, start.own, start.junk, start.view)
    verdicts = dict.fromkeys((*start.junk, JAVELIN), 'vendor') | {CHECKED: 'check'}
    hands = replace(town.hands(), judge=lambda items: junk_of(items, lambda units: {u: verdicts[u] for u in units}))

    with caplog.at_level('INFO'):
        done = visit(town.run, hands, start.needs, start.own, Exit.WAYPOINT)

    assert '8 junk' in caplog.text  # 7 then
    assert all(JAVELIN not in units for units in play.page_items.values())
    assert JAVELIN in town.sold
    assert sorted(town.sold) == sorted((*start.junk, JAVELIN))
    assert any(CHECKED in units for units in play.page_items.values())  # `check`: stashed
    assert done.contract.junk_left == 0
    assert carried(play).in_cube == ()


def test_a_new_games_shared_tab_opens_on_its_first_page_not_the_one_remembered():
    # 02:36:57 on 2026-10-19: the Spiked Shield went onto page 1, planned 3, the Shared tab remembered on page 3 from
    # the visit before, in another game; 21:55:27: the Javelin the same. A new game's tab opens on page 1
    from inventory_tracking.macros.visit import Remembered

    memory = Remembered(shared=5, shared_game='cyber31')
    ring = thing(10, 'Ring', 6, 0)
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, ring)), [OPEN_PAGE] * 2 + [FULL_PAGE] * 3 + [OPEN_PAGE])
    play.shared_page = 0  # page 1 shown, the game cyber32's own
    run = play.run()
    view = read(run)
    assert play.pack is not None
    stop = plan_stop(Holdings(play.pack, OWN), view)
    assert [put.to for put in stop.puts] == [5]

    assert stash_stop(run, stop, inventory_key='i', own=OWN, memory=memory) == 1

    assert play.stash_clicks == [(5, ring.unit_id)]
    assert memory.shared == 5
    assert memory.shared_game == 'cyber32'


def test_the_stops_line_names_the_page_a_put_went_onto_not_the_one_planned(caplog):
    # 21:55:29 on 2026-10-19: "7 items put in (pages 3,4)", the Javelin on page 1
    from inventory_tracking.macros.visit import Remembered

    memory = Remembered(shared=5, shared_game='cyber32')  # this game's, but the player has looked at page 1 since
    ring = thing(10, 'Ring', 6, 0)
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, ring)), [OPEN_PAGE] * 2 + [FULL_PAGE] * 3 + [OPEN_PAGE])
    play.shared_page = 0
    run = play.run()
    view = read(run)
    assert play.pack is not None
    stop = plan_stop(Holdings(play.pack, OWN), view)
    assert [put.to for put in stop.puts] == [5]

    with caplog.at_level('INFO'):
        assert stash_stop(run, stop, inventory_key='i', own=OWN, memory=memory) == 1

    assert play.page_items[1] == [ring.unit_id]
    assert 'Macro: stash: the Ring went onto page 1, planned 5: page 1 is the one shown' in caplog.text
    assert 'Macro: stash: by the view: 1 items put in (pages 1),' in caplog.text


# The 99 rune stacks cubed at the stash (the player, 17:50 on 2026-10-18: "cubed, aim to 80 or lower")


class RuneStash(Game):
    """The fortress with the resource tabs' cube: a Ctrl + Shift + right click on a stack's slot on the Runes or Gems
    tab moves up to `take` of it into the cube's next free cells (the player, 14:28 on 2026-10-18; live from 18:27),
    a Ctrl + Shift + left click one (18:48),
    the cube's Transmute button on a resource tab makes the recipe of the game's data (cube.py `rune_recipe`: its runes
    and its gem, nothing else) when `converts`; `right_clicked`: the classes so taken."""

    take = 3
    converts = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.right_clicked: list[int] = []
        self.left_clicked: list[int] = []  # the classes a Ctrl + Shift + left click on a slot took one of

    def act(self, event) -> None:
        import math
        from collections import Counter

        from inventory_tracking.macros.cube import rune_recipe, rune_slot, stash_transmute
        from inventory_tracking.macros.waypoint import panel_point
        from tests.inventory_tracking.macros.fakes import WINDOW

        pack = self.pack
        if pack is not None and 'stash' in self.world.open_panels and self.stash_tab in (2, 4):
            if event[0] == 'button' and event[1] == 3 and {'Control_L', 'Shift_L'} <= set(event[3]):
                txt = next((int(t) for t in metadata()['bases'] if (at := rune_slot(int(t))) and math.dist(
                    panel_point(WINDOW, *at), event[2]) < 0.01), None)  # fmt: skip
                if txt is not None:
                    self.right_clicked.append(txt)
                    moved = min(self.take, self.stacks.get(txt, 0))
                    self.stacks[txt] = self.stacks.get(txt, 0) - moved
                    used = {(i.x, i.y) for i in pack.in_cube}
                    cells = [(x, y) for y in range(4) for x in range(3) if (x, y) not in used][:moved]
                    base = 9000 + 10 * len(self.right_clicked)
                    new = tuple(Carried(base + n, txt, x, y, (1, 1)) for n, (x, y) in enumerate(cells))
                    inside = (*pack.in_cube, *new)
                    self.pack = replace(pack, in_cube=inside, cube_items=frozenset(i.unit_id for i in inside))
                return
            if event[0] == 'click' and self.keys.ctrl and self.keys.shift:
                # A Ctrl + Shift + left click on a stack's slot: one of it into the cube (the player, 18:48)
                txt = next((int(t) for t in metadata()['bases'] if (at := rune_slot(int(t))) and math.dist(
                    panel_point(WINDOW, *at), event[1]) < 0.01), None)  # fmt: skip
                if txt is not None:
                    self.left_clicked.append(txt)
                    if self.stacks.get(txt, 0) > 0:
                        self.stacks[txt] -= 1
                        used = {(i.x, i.y) for i in pack.in_cube}
                        x, y = next((x, y) for y in range(4) for x in range(3) if (x, y) not in used)
                        new = Carried(9900 + len(self.left_clicked), txt, x, y, (1, 1))
                        inside = (*pack.in_cube, new)
                        self.pack = replace(pack, in_cube=inside, cube_items=frozenset(i.unit_id for i in inside))
                    return
            if event[0] == 'click' and math.dist(event[1], panel_point(WINDOW, *stash_transmute())) < 0.01:
                self.transmutes.append(tuple(i.unit_id for i in pack.in_cube))
                kinds = Counter(i.txt for i in pack.in_cube)
                runes, recipe = next(
                    ((t, r) for t in kinds if (r := rune_recipe(t)) is not None and kinds[t] == r.runes), (None, None)
                )
                wanted = Counter({runes: recipe.runes, **dict.fromkeys(recipe.gems, 1)}) if recipe else None
                if self.converts and recipe is not None and kinds == wanted:
                    made = Carried(9500 + len(self.transmutes), recipe.into, 0, 0, (1, 1))
                    self.pack = replace(pack, in_cube=(made,), cube_items=frozenset({made.unit_id}))
                return
        super().act(event)


def runes_stop(**counts: int) -> tuple[RuneStash, Carried]:
    tal = thing(20, 'Tal Rune', 6, 3)
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, tal)), [FULL_PAGE] * 6, RuneStash)
    play.stacks = {class_of(name.replace('_', ' ')): count for name, count in counts.items()}
    assert isinstance(play, RuneStash)
    return play, tal


def test_the_full_tal_stack_is_cubed_three_times_at_the_stash_and_the_carried_tal_goes_on_after(caplog):
    play, tal = runes_stop(Tal_Rune=99, Ral_Rune=10)
    ral = class_of('Ral Rune')

    with caplog.at_level('INFO'):
        assert stop(play) == 1  # the carried Tal, onto the room the transmutes made

    assert len(play.transmutes) == 3
    assert (play.stacks[tal.txt], play.stacks[ral]) == (91, 13)
    assert carried(play).in_cube == ()
    assert all(i.unit_id != tal.unit_id for i in carried(play).items)
    assert play.stash_opened == 1  # in the one opening: no walk, no opening more
    assert caplog.text.count('Macro: cube: three Tal Rune into a Ral Rune at the stash') == 3
    assert 'Macro: stash: runes cubed: 3 of 3 planned, 1 carried runes put after' in caplog.text
    assert play.world.open_panels == ()


def test_a_right_click_that_moves_nothing_makes_no_transmute_and_leaves_the_rune_carried(caplog):
    play, tal = runes_stop(Tal_Rune=99, Ral_Rune=10)
    play.take = 0  # the gesture not as the player said (probe P3)

    with caplog.at_level('INFO'):
        assert stop(play) == 0

    assert play.transmutes == []
    assert play.stacks[tal.txt] == 99
    assert carried(play).in_cube == ()
    assert any(i.unit_id == tal.unit_id for i in carried(play).items)  # stays carried, never into the scan
    assert 'Macro: stash: a Ctrl + Shift + right click on the Tal Rune stack put nothing into the cube' in caplog.text


def test_a_transmute_that_makes_nothing_puts_the_runes_back_on_their_stack(caplog):
    play, tal = runes_stop(Tal_Rune=99, Ral_Rune=10)
    play.converts = False

    with caplog.at_level('INFO'):
        stop(play)

    assert len(play.transmutes) == 1  # one try, then no more
    assert play.stacks[tal.txt] == 99  # the three back on it
    assert carried(play).in_cube == ()
    assert 'Macro: stash: three Tal Rune not transmuted: the cube holds Tal Rune, Tal Rune, Tal Rune' in caplog.text


def test_a_visit_sells_no_rune_and_cubes_the_full_stack(monkeypatch, caplog):
    # The player, 17:50 on 2026-10-18: a full stack's Tal Runes no longer sold at Jamella; the junk beside it still is
    tal = thing(20, 'Tal Rune', 6, 3)
    junk = replace(thing(11, 'Amulet', 7, 0), quality=4)
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, tal, junk), keys=24), [FULL_PAGE] * 6, RuneStash)
    play.stacks = {tal.txt: 99, class_of('Ral Rune'): 10}
    town = Town(monkeypatch, play, frozenset({11}))

    with caplog.at_level('INFO'):
        done = town.visit()

    assert town.sold == [11]
    assert all(tal.unit_id not in offered for offered in town.offered)
    assert play.stacks[tal.txt] == 91
    assert done.contract.misses == ()
    assert tal.txt not in done.full  # the stack has room again: picked up again (runner.py `_picked`)


# Gem recipes (the player, 18:31 on 2026-10-18: "yes, loop should use required gems + runes")


def test_a_thul_stack_over_80_is_cubed_with_a_chipped_topaz_from_its_stack(caplog):
    play, _tal = runes_stop(Thul_Rune=95, Amn_Rune=50, Chipped_Topaz=5)
    thul, amn, topaz = class_of('Thul Rune'), class_of('Amn Rune'), class_of('Chipped Topaz')

    with caplog.at_level('INFO'):
        stop(play)

    assert play.right_clicked == [thul] * 3  # three runes a right click
    assert play.left_clicked == [topaz] * 3  # the one gem its recipe takes (cubemain.txt), a left click each
    assert (play.stacks[thul], play.stacks[amn], play.stacks[topaz]) == (86, 53, 2)  # one gem a transmute, none back
    assert carried(play).in_cube == ()
    assert caplog.text.count('Macro: cube: three Thul Rune and a Chipped Topaz into a Amn Rune at the stash') == 3
    assert play.world.open_panels == ()


def test_a_gem_the_right_click_does_not_bring_puts_the_runes_back_and_ends_the_transmutes(caplog):
    # The stash as read had a Chipped Topaz; the stack shows none when clicked: the three Thul back, nothing left
    play, _tal = runes_stop(Thul_Rune=95, Amn_Rune=50, Chipped_Topaz=5)
    run = play.run()
    view = read(run)
    play.stacks[class_of('Chipped Topaz')] = 0
    assert play.pack is not None

    with caplog.at_level('INFO'):
        stash_stop(run, plan_stop(Holdings(play.pack, OWN), view), inventory_key='i', own=OWN)

    assert isinstance(play, RuneStash)
    assert play.left_clicked == [class_of('Chipped Topaz')]  # one left click on the empty gem stack, then no more
    assert play.transmutes == []
    assert play.stacks[class_of('Thul Rune')] == 95
    assert carried(play).in_cube == ()
    assert 'Macro: stash: the Chipped Topaz for three Thul Rune not taken into the cube' in caplog.text


def test_a_rune_whose_gem_is_missing_is_skipped_with_one_line(monkeypatch, caplog):
    junk = replace(thing(11, 'Amulet', 7, 0), quality=4)
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, junk), keys=24), [FULL_PAGE] * 6, RuneStash)
    play.stacks = {class_of('Thul Rune'): 95, class_of('Amn Rune'): 50}
    town = Town(monkeypatch, play, frozenset({11}))

    with caplog.at_level('INFO'):
        town.visit()

    assert isinstance(play, RuneStash)
    assert play.right_clicked == []
    assert play.left_clicked == []
    assert (
        caplog.text.count(
            'Macro: stash: rune stacks over 80 not cubed: Thul Rune 95: no Chipped Topaz in the stash for its recipe '
            '(3 Thul Runes + 1 Chipped Topaz -> Amn Rune)'
        )
        == 1
    )


def test_unread_stash_retries_a_large_cube_keeper_after_inventory_keepers_make_room(monkeypatch):
    # 20:48:36 on 2026-10-18: a 2x3 Humongous stayed in the cube even though the scan stored five keepers and
    # finished with a 2x4 inventory block free. The scan needs a second opening in place while still at the stash.
    rings = tuple(thing(100 + n, 'Ring', 6 + n % 4, n // 4) for n in range(12))
    axe = replace(thing(50, 'Giant Axe', 0, 0), quality=7)
    pack = Pack((THE_CUBE, *OWN_CHARMS, *rings), ('##.', '##.', '##.', '...'), frozenset({50}), (axe,), keys=24)
    play = fortress(pack, [OPEN_PAGE] * 6)
    town = Town(monkeypatch, play)
    town.hands = lambda: Hands(lambda: 'i', town.identify, lambda items: [], lambda: None)

    done = town.visit(Exit.LEAVE)

    assert done.contract.misses == ()
    assert carried(play).in_cube == ()
    assert any(axe.unit_id in items for items in play.page_items.values())
    assert play.stash_opened == 2


def test_unread_stash_moves_junk_aside_for_a_cube_keeper_before_jamella(monkeypatch):
    # 21:03:47 on 2026-10-18: the unread scan stored six items, but junk rings at (3,1) and (3,2)
    # still blocked a 2x3 Humongous. Jamella sold them afterward, leaving the axe in the cube.
    fixed = tuple(
        thing(300 + y * 10 + x, 'Small Charm', x, y)
        for y in range(4)
        for x in range(10)
        if x in (2, 5, 6, 7, 8, 9) or (y >= 2 and x in (0, 1))
    )
    rings = tuple(
        thing(100 + n, 'Ring', x, y) for n, (x, y) in enumerate(((3, 0), (4, 0), (4, 1), (4, 2), (3, 3), (4, 3)))
    )
    junk = (thing(201, 'Ring', 3, 1), thing(202, 'Ring', 3, 2))
    axe = replace(thing(50, 'Giant Axe', 0, 0), quality=7)
    pack = Pack((THE_CUBE, *fixed, *rings, *junk), ('##.', '##.', '##.', '...'),
                frozenset({50}), (axe,), keys=24)  # fmt: skip
    play = fortress(pack, [OPEN_PAGE] * 6)
    town = Town(monkeypatch, play, frozenset(i.unit_id for i in junk))
    town.hands = lambda: Hands(lambda: 'i', town.identify, lambda items: [i for i in items if i.unit_id in town.junked],
                               lambda: None)  # fmt: skip
    town.run = play.run()

    done = visit(town.run, town.hands(), LK_NEEDS, own_of((THE_CUBE, *fixed)), Exit.LEAVE)

    assert town.stops() == ['jamella']  # the unread scan opens the stash through its own macro
    assert done.contract.misses == ()
    assert carried(play).in_cube == ()
    assert any(axe.unit_id in items for items in play.page_items.values())
    assert sorted(town.sold) == [201, 202]


def test_a_refusal_with_the_stash_unread_is_no_full_stack_and_the_item_stays_carried(monkeypatch, caplog):
    # 22:14 on 2026-10-18: the scan's refused Deep Worldstone Shard was taken for a full stack (it held 83): dropped in
    # town, kept in FULL_FILE, and every Deep Shard after was left on the ground (01:59 on 2026-10-19)
    shard = thing(70, 'Deep Worldstone Shard', 6, 0)
    pack = Pack((THE_CUBE, *OWN_CHARMS, shard), ('...', '...', '...', '...'), keys=24)
    play = fortress(pack, [OPEN_PAGE] * 6)
    play.stash_refuses = {shard.txt}
    town = Town(monkeypatch, play)
    town.hands = lambda: Hands(lambda: 'i', town.identify, lambda items: [], lambda: None)

    with caplog.at_level('INFO'):
        done = town.visit(Exit.LEAVE)

    assert shard.txt not in done.full
    assert any(i.unit_id == 70 for i in carried(play).items)
    assert 'refused with the stash unread, kept carried, not counted full: Deep Worldstone Shard' in caplog.text


# One short re-read before the scan, page after page (the player, 2026-10-19: "a quick re-read; the page-by-page scan
# stays as the fallback but should rarely run")


def flaky(town: Town, unread: int) -> list[int]:
    """The stash view unread for its first `unread` reads, then as memory holds it; the reads counted."""
    reads: list[int] = []

    def view() -> StashView | None:
        reads.append(len(reads))
        return None if len(reads) <= unread else read(town.run)

    town.hands = lambda: Hands(lambda: 'i', town.identify, lambda items: [], view)
    return reads


def test_a_stash_unread_for_a_moment_is_read_again_and_the_stop_goes_by_its_plan(monkeypatch, caplog):
    # Unread at Cain and at the stash stop, read the next look: the planned put onto page 5, no scan
    keeper = replace(thing(10, 'Ring', 6, 0), quality=4)
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, keeper), keys=24), [FULL_PAGE] * 5 + [OPEN_PAGE])
    town = Town(monkeypatch, play)
    town.run = play.run()
    reads = flaky(town, unread=2)

    with caplog.at_level('INFO'):
        done = visit(town.run, town.hands(), LK_NEEDS, OWN, Exit.LEAVE)

    assert caplog.text.count('Macro: stash: the view read on the second try') == 1
    assert 'the stash is not read' not in caplog.text
    assert 'still unread' not in caplog.text
    assert play.stash_clicks == [(5, 10)]  # the plan's page, no other tried
    assert play.page_items[5] == [10]
    assert done.contract.misses == ()
    assert len(reads) >= 3


def test_a_stash_still_unread_after_the_re_read_is_scanned_page_by_page(monkeypatch, caplog):
    from inventory_tracking.macros.visit import REREAD_SECONDS

    keeper = replace(thing(10, 'Ring', 6, 0), quality=4)
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS, keeper), keys=24), [FULL_PAGE] * 5 + [OPEN_PAGE])
    town = Town(monkeypatch, play)
    town.run = play.run()
    reads = flaky(town, unread=1_000)
    play.stash_pages = None  # the pages take items by `stash_room`

    with caplog.at_level('INFO'):
        visit(town.run, town.hands(), LK_NEEDS, OWN, Exit.LEAVE)

    assert caplog.text.count('Macro: stash: the view still unread: page by page') == 1
    assert 'Macro: town visit: the stash is not read: the scan, page after page' in caplog.text
    assert 'read on the second try' not in caplog.text
    assert [i.unit_id for i in play.stashed] == [10]  # the scan stored it
    assert 3 <= len(reads) <= 3 + round(REREAD_SECONDS / 0.05) + 2  # Cain's, the stop's, the beat's few


def test_a_stash_unread_with_nothing_to_put_in_is_not_read_again(monkeypatch, caplog):
    # No keeper carried and no gold to deposit: no scan would run, so no re-read either
    play = fortress(Pack((THE_CUBE, *OWN_CHARMS), keys=24), [OPEN_PAGE] * 6)
    town = Town(monkeypatch, play)
    town.run = play.run()
    reads = flaky(town, unread=1_000)

    with caplog.at_level('INFO'):
        visit(town.run, town.hands(), LK_NEEDS, OWN, Exit.LEAVE)

    assert 'Macro: stash: the view' not in caplog.text
    assert len(reads) == 2


@pytest.mark.parametrize('broken', [False, True])
def test_the_loot_shadow_only_logs_beside_the_visit_and_never_changes_it(monkeypatch, caplog, broken):
    # loot/design.md §7 M1 (the player, 2026-10-20 ~09:33: "start M0+M1"): the new decisions are logged beside the
    # visit's; the visit does the same with the shadow working or broken
    import inventory_tracking.loot.shadow as shadow_module

    shadow = shadow_module.Shadow(shadow_module.Book())
    if broken:
        monkeypatch.setattr(shadow, '_town', lambda *args: 1 / 0)
    monkeypatch.setattr(shadow_module, 'SHADOW', shadow)
    keeper = replace(thing(10, 'Ring', 6, 0), quality=4, identified=False)
    junk = replace(thing(11, 'Amulet', 7, 0), quality=4, identified=False)
    cubed = replace(thing(12, 'Ring', 0, 0), quality=4)
    pack = Pack((THE_CUBE, *OWN_CHARMS, keeper, junk), ('#..', '...', '...', '...'), frozenset({12}), (cubed,), keys=5)
    play = fortress(pack, [FULL_PAGE] * 5 + [OPEN_PAGE])
    town = Town(monkeypatch, play, frozenset({11, 12}))

    with caplog.at_level('INFO'):
        done = town.visit()

    assert town.stops() == ['cain', 'stash', 'jamella', 'waypoint']
    assert play.page_items[5] == [10]
    assert sorted(town.sold) == [11, 12]
    assert done.contract.misses == ()
    if broken:
        assert 'Macro: loot: shadow: town failed (ZeroDivisionError' in caplog.text
    else:
        assert 'Macro: loot: shadow: town: 3 items' in caplog.text
        assert 'old sell' in caplog.text


def test_m2_sells_the_cheap_duplicate_keep_decides_gives_up_and_never_the_players(monkeypatch, caplog):
    # The player, 2026-10-20 ~15:05: "Sell cheap duplicates" (loot/design.md §7 M2, keep.DECIDES): what
    # loot/api.py `sold_copies` gives up is junk for Jamella; the player's by its stats still never is
    from inventory_tracking.loot import api as loot_api, keep
    from tests.inventory_tracking.macros.test_town import BLOCK_BUT_ONE, grid

    ring = replace(thing(60, 'Ring', 4, 2), quality=4)
    rings = [replace(thing(61 + n, 'Ring', x, 3), quality=4) for n, x in enumerate((3, 4))]
    pack, own = grid(BLOCK_BUT_ONE, [ring, *rings])
    play = fortress(replace(pack, keys=24), [FULL_PAGE] * 5 + [OPEN_PAGE])
    town = Town(monkeypatch, play, frozenset({60}))
    town.run = play.run()
    town.run.players_item = lambda item: item.unit_id == 62
    monkeypatch.setattr(keep, 'DECIDES', True)
    monkeypatch.setattr(
        loot_api, 'sold_copies',
        lambda carried, junk, spared, *_: {61: ('unique Ring', 'K6 a surplus copy'), 62: ('unique Ring', 'K6')},
    )  # fmt: skip

    with caplog.at_level('INFO'):
        visit(town.run, town.hands(), LK_NEEDS, own, Exit.WAYPOINT)

    assert sorted(town.sold) == [60, 61]
    assert 'Macro: town visit: unique Ring (unit 61) sold by the keep rules (M2): K6 a surplus copy' in caplog.text
    monkeypatch.setattr(keep, 'DECIDES', False)
    play2 = fortress(replace(pack, keys=24), [FULL_PAGE] * 5 + [OPEN_PAGE])
    town2 = Town(monkeypatch, play2, frozenset({60}))
    town2.run = play2.run()
    visit(town2.run, town2.hands(), LK_NEEDS, own, Exit.WAYPOINT)
    assert sorted(town2.sold) == [60]


def test_m6_the_keep_rules_decide_every_sale_and_the_old_chain_is_not_asked(monkeypatch, caplog):
    # The player, 2026-10-20 16:55: "go ahead with the merge agent" (loot/keep.py TOWN_DECIDES): the visit's junk is
    # loot/api.py `town_sold` after the worker's appraisal; junk.py `junk_of` (`Hands.judge`) is not asked, the player's
    # by its stats still never sold; a failure of the rules sells nothing
    from inventory_tracking.loot import api as loot_api, keep
    from tests.inventory_tracking.macros.test_town import BLOCK_BUT_ONE, grid

    ring = replace(thing(60, 'Ring', 4, 2), quality=4)
    rings = [replace(thing(61 + n, 'Ring', x, 3), quality=4) for n, x in enumerate((3, 4))]
    pack, own = grid(BLOCK_BUT_ONE, [ring, *rings])
    monkeypatch.setattr(keep, 'TOWN_DECIDES', True)
    asked: list[list[int]] = []

    def judged(play_hands: Hands) -> Hands:
        def judge(items):
            raise AssertionError('junk_of asked with TOWN_DECIDES on')

        return replace(play_hands, judge=judge, appraise=lambda units: asked.append(sorted(units)) or {})

    monkeypatch.setattr(
        loot_api, 'town_sold',
        lambda carried, spared, *_: {61: ('magic Ring', 'K8 worthless'), 62: ('magic Ring', 'K8 worthless')},
    )  # fmt: skip
    play = fortress(replace(pack, keys=24), [FULL_PAGE] * 5 + [OPEN_PAGE])
    town = Town(monkeypatch, play, frozenset({60}))
    town.run = play.run()
    town.run.players_item = lambda item: item.unit_id == 62
    with caplog.at_level('INFO'):
        visit(town.run, judged(town.hands()), LK_NEEDS, own, Exit.WAYPOINT)

    assert sorted(town.sold) == [61]
    assert len(asked) == 1
    assert {60, 61, 62} <= set(asked[0])  # the loop's identified items, appraised once
    assert 'Macro: town visit: magic Ring (unit 61) sold by the keep rules: K8 worthless' in caplog.text

    def broken(*_args):
        raise OSError('the collection is locked')

    monkeypatch.setattr(loot_api, 'town_sold', broken)
    play2 = fortress(replace(pack, keys=24), [FULL_PAGE] * 5 + [OPEN_PAGE])
    town2 = Town(monkeypatch, play2, frozenset({60}))
    town2.run = play2.run()
    with caplog.at_level('INFO'):
        visit(town2.run, judged(town2.hands()), LK_NEEDS, own, Exit.WAYPOINT)
    assert town2.sold == []
    assert 'the keep rules failed (OSError: the collection is locked): nothing sold' in caplog.text
