"""loot/design.md §7 M3: the planning moved from macros/cube.py and macros/town.py into loot/storage.py plans every
recorded town visit as before, byte for byte (visit_replay.py).

- The kept fixtures (fixtures/visits: 13 visits, 52 stops, chosen to cover a full stash page, keepers in the cube,
  moves aside, junk into the cube, a stranded and a waiting keeper, rune transmutes, the gold deposit, key moves)
  against the golden plans the code before the move wrote, through the re-exports and through loot/storage.py
  directly.
- Opt-in (slow): every visit recorded on this host (runs/alt-d/*/visits, git-ignored) and the macros fixtures, through
  the code of OLD_COMMIT loaded from git and the code now.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from inventory_tracking.loot import storage
from inventory_tracking.macros import cube, town
from inventory_tracking.macros.visitlog import Snapshot
from tests.inventory_tracking.loot.visit_replay import (
    FIXTURES,
    GOLDEN,
    digests,
    old_modules,
    old_room,
    plans,
    stops,
    text,
    visit_files,
)


MACROS_FIXTURES = Path(__file__).parents[1] / 'macros' / 'fixtures' / 'visits'
GOLDEN_PLANS: dict[str, dict[str, str]] = json.loads(GOLDEN.read_text())
KEPT_STOPS = dict(stops(sorted(p for p in FIXTURES.glob('*.json') if p != GOLDEN)))


@pytest.fixture(autouse=True)
def _gems_rule_before(monkeypatch):
    # The golden plans are the rule before macros/town.py GEMS_KEEP_FLAWLESS (2026-10-21): its gem transmutes are
    # checked apart (`test_the_gem_rule_only_adds_gem_transmutes_to_each_kept_stop`)
    monkeypatch.setattr(town, 'GEMS_KEEP_FLAWLESS', None)


def test_the_gem_rule_only_adds_gem_transmutes_to_each_kept_stop(monkeypatch):
    # With GEMS_KEEP_FLAWLESS on, each kept stop plans as before but for gem transmutes after its rune transmutes
    # (three flawless into a perfect, never a perfect cubed, 15 left a kind) and carried gems onto the room they make
    added = 0
    for name, snapshot in KEPT_STOPS.items():
        if snapshot.view is None:
            continue
        holdings = storage.Holdings(snapshot.pack, snapshot.own, snapshot.junk, snapshot.unknown)
        before = town.stash_stop(holdings, snapshot.view, snapshot.needs)
        monkeypatch.setattr(town, 'GEMS_KEEP_FLAWLESS', 15)
        now = town.stash_stop(holdings, snapshot.view, snapshot.needs)
        monkeypatch.setattr(town, 'GEMS_KEEP_FLAWLESS', None)
        gems = now.runes[len(before.runes) :]
        assert now.runes[: len(before.runes)] == before.runes, name
        assert now.rune_puts[: len(before.rune_puts)] == before.rune_puts, name
        assert len(gems) <= town.GEM_TRANSMUTES, name
        assert all(town.perfect_of(step.txt) == step.into and step.gem is None for step in gems), name
        counts = dict(snapshot.view.stacks)
        for step in gems:
            counts[step.txt] -= 3
        assert all(count >= 15 for txt, count in counts.items() if town.gem_recipe(txt) is not None and
                   any(step.txt == txt for step in gems)), name  # fmt: skip
        rest = {key: getattr(now, key) for key in ('puts', 'out_for_sale', 'drops', 'shuffles', 'parks', 'full')}
        assert rest == {key: getattr(before, key) for key in rest}, name
        added += len(gems)
    assert added > 0  # the kept stops hold flawless stacks over 15


def test_the_golden_file_covers_every_kept_stop():
    assert sorted(KEPT_STOPS) == sorted(GOLDEN_PLANS)
    assert len(KEPT_STOPS) >= 50


@pytest.mark.parametrize('name', sorted(KEPT_STOPS))
def test_the_reexports_plan_each_kept_stop_as_before(name):
    assert digests(plans(KEPT_STOPS[name], town, cube)) == GOLDEN_PLANS[name]


def direct(snapshot: Snapshot) -> dict[str, str]:
    """The plans `plans` names, made by loot/storage.py's own functions (no wrapper), as digests."""
    pack, own, view = snapshot.pack, snapshot.own, snapshot.view
    made: dict[str, Any] = {
        'cube.loot': storage.loot(pack, own),
        'cube.roomed': storage.roomed(pack),
        'cube.plan': storage.plan(storage.roomed(pack), own),
        'cube.overflow': storage.overflow(pack, own),
        'cube.keys_move': storage.keys_move(pack),
        'cube.keys_move.sure': storage.keys_move(pack, storage.SURE_BLOCK),
        'town.surplus': storage.surplus(
            [*storage.loot(pack, own), *pack.in_cube], view if view is not None else snapshot.full
        ),
    }
    space = storage.room(storage.Storage(pack, own))
    made['loop.room'] = {
        'free': space.free,
        'inventory': space.inventory,
        'cube': space.cube,
        'rows': list(space.rows),
        'low': storage.room_low(storage.Storage(pack, own)),
    }
    if view is not None:
        holdings = storage.Holdings(pack, own, snapshot.junk, snapshot.unknown)
        deposit = town.deposit_to(snapshot.gold, snapshot.cap)
        stop = storage.stash_stop(holdings, view, snapshot.needs.block, deposit_to=deposit)
        unparked = storage.stash_stop(holdings, view, snapshot.needs.block, park=False)
        made |= {
            'town.stash_stop': stop,
            'town.stash_stop.unparked': unparked,
            'town.after': storage.after(pack, stop),
            'town.place': storage.place(view.pages, [*storage.loot(pack, own), *pack.in_cube]),
            'town.rune_transmutes': storage.rune_transmutes(dict(view.stacks)),
            'town.uncubed': storage.uncubed(dict(view.stacks)),
        }
    return digests(made)


@pytest.mark.parametrize('name', sorted(KEPT_STOPS))
def test_storage_itself_plans_each_kept_stop_as_before(name):
    made = direct(KEPT_STOPS[name])
    assert made == {key: GOLDEN_PLANS[name][key] for key in made}


def test_the_loops_room_count_is_the_one_before_the_move():
    # macros/loop.py `Loop.look` counted the room inline before M3 (visit_replay.py `old_room`); storage.room now
    for name, snapshot in KEPT_STOPS.items():
        space = storage.room(storage.Storage(snapshot.pack, snapshot.own))
        before = old_room(snapshot.pack, snapshot.own, cube)
        assert (space.free, space.inventory, space.cube, list(space.rows)) == (
            before['free'], before['inventory'], before['cube'], before['rows']
        ), name  # fmt: skip
        assert space.low == before['low'], name


def test_the_kept_fixtures_cover_the_planning_paths():
    # The cases the stash stop's plan branches on: each in at least one kept stop
    found: set[str] = set()
    for snapshot in KEPT_STOPS.values():
        made = plans(snapshot, town, cube)
        stop = made.get('town.stash_stop')
        if stop is not None:
            found |= {f'stop.{key}' for key in ('puts', 'out_for_sale', 'shuffles', 'into_cube', 'stranded', 'full',
                                                'waits', 'runes') if stop[key]}  # fmt: skip
            found |= {'stop.deposit'} if stop['deposit_to'] is not None else set()
            found |= {'stop.tab'} if any(put['to'] < 0 for put in stop['puts']) else set()
            found |= {'unread_way'} if any(made['town.unread_way_for_cube']) else set()
        found |= {'keys_move'} if made['cube.keys_move'] else set()
        found |= {'overflow'} if made['cube.overflow'] else set()
        found |= {'room.low'} if made['loop.room']['low'] else set()
        found |= {'room.fine'} if not made['loop.room']['low'] else set()
    wanted = {'stop.puts', 'stop.out_for_sale', 'stop.shuffles', 'stop.into_cube', 'stop.stranded', 'stop.full',
              'stop.waits', 'stop.runes', 'stop.deposit', 'stop.tab', 'unread_way', 'keys_move', 'overflow',
              'room.low', 'room.fine'}  # fmt: skip
    assert wanted <= found, wanted - found


@pytest.mark.slow
def test_every_recorded_visit_on_this_host_plans_as_with_the_old_code():
    paths = [*visit_files(), *sorted(MACROS_FIXTURES.glob('*.json'))]
    old = old_modules()
    if old is None:
        pytest.skip('the code before M3 is not loadable from git (visit_replay.py OLD_COMMIT)')
    old_town, old_cube = old
    compared, differ = 0, []
    for name, snapshot in stops(paths):
        before, now = plans(snapshot, old_town, old_cube), plans(snapshot, town, cube)
        space = storage.room(storage.Storage(snapshot.pack, snapshot.own))
        now['storage.room'] = {'free': space.free, 'inventory': space.inventory, 'cube': space.cube,
                               'rows': list(space.rows), 'low': space.low}  # fmt: skip
        before['storage.room'] = before['loop.room']
        compared += 1
        if text(before) != text(now):
            differ.append((name, sorted(key for key in now if text(now[key]) != text(before.get(key)))))
    assert compared > 0
    assert not differ, differ[:5]
