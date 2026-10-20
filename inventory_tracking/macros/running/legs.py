"""The KP_6 loop's legs: the level run a leg posts, the way on, the leg's hands (macros/loop.py `LegHands`), the town
visit and the identify. A part of macros/runner.py `MacroRunner`, its methods bound there."""

import time
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from inventory_tracking.common import LOG
from inventory_tracking.input.keybindings import INVENTORY, action_key, show_items_key
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.agenda import ZONE_LEFT
from inventory_tracking.macros.cain import identify_all
from inventory_tracking.macros.cube import perfect_of, stash, stash_only, transmute, unpack
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.hunt import Hunter, threat
from inventory_tracking.macros.junk import identify, junk_of, named
from inventory_tracking.macros.loop import LegHands
from inventory_tracking.macros.navigation import Abilities, means
from inventory_tracking.macros.pickup import pick_up
from inventory_tracking.macros.portal import portal_source
from inventory_tracking.macros.pursuit import FULL, Pursuit
from inventory_tracking.macros.routines import show_items_on
from inventory_tracking.macros.running.base import PICK_SLACK, PICKUP, TRANSMUTES, VERDICT_SECONDS
from inventory_tracking.macros.skills import TELEPORT as TELEPORT_SKILL, skill_name
from inventory_tracking.macros.town import Contract, Exit, Needs, kept_gem
from inventory_tracking.macros.townexit import walk_out as walk_out_of_town
from inventory_tracking.macros.travel import cut
from inventory_tracking.macros.tzloop import full_clear
from inventory_tracking.macros.tzroutine import Itinerary, policy_of
from inventory_tracking.macros.visit import Hands, visit


if TYPE_CHECKING:
    from inventory_tracking.macros.runner import MacroRunner


def _loop_level_run(self: MacroRunner, hunter: Hunter, rush: bool = True, agenda: bool = False) -> None:
    """The loop's chests leg: the KP_1 level run through attack mode; its end is the leg's (`_run_over`). `rush`:
    past what does not attack (not for Andariel's fight); `agenda`: a terror zone kind's targets
    (macros/goals-plan.md)."""
    with self.lock:
        hunter.hand_over, hunter.run_over = self._hand_over, self._run_over
        hunter.carry_one = self._carry_one  # a refused unique Grand Charm: the Gheed's swap (macros/pickup.py)
        if agenda:
            hunter.agenda, hunter.agenda_policy = self.loop.agenda, self._agenda_policy
        post = Pursuit(
            PICKUP, time.monotonic(), advance=False, leash=FULL, rush=rush, looped=True, agenda=agenda,
            allowed=_trip_levels(self) if agenda else None,
        )  # fmt: skip
        hunter.post(post)
        self.attack_mode, self.attack_declined = True, False


def _trip_levels(self: MacroRunner) -> frozenset[int] | None:
    """The levels a terror zone run may go on into: its trip's (macros/tzroutine.py `Excursion.areas`), else its
    own level; None with no itinerary or level known ("it should run within terror zones", the player, 2026-10-19)."""
    plan, area = self.loop.agenda.plan, self.area_seen
    if not isinstance(plan, Itinerary) or area is None:
        return None
    trip = plan.excursion_of(area, self.loop.agenda.finished)
    return frozenset(trip.areas) if trip is not None else frozenset((area,))


def _agenda_policy(self: MacroRunner, area: int) -> str:
    """How a terror zone kind's level run works level `area` (macros/tzroutine.py `policy_of`)."""
    plan = self.loop.agenda.plan
    trip = plan.excursion_of(area, self.loop.agenda.finished) if isinstance(plan, Itinerary) else None
    wanted = getattr(self.progress, 'wanted', None)
    if trip is not None and area in trip.zone and wanted is not None and wanted(area) is False:
        # The zone moved on under the run (23:30 on 2026-10-19: Spider Forest explored 1.5 min after the zone went to
        # Dry Hills): the run ends here ("it should run within terror zones", the player). A level crossed on the way
        # is never in the zone: TRANSIT as before
        return ZONE_LEFT
    return policy_of(area, trip, full_clear(self.loop))


def _way_on(
    self: MacroRunner, run: Run, key_names, take_one: Callable[[], bool], level_run: Callable[[], None]
) -> None:
    """At the way on (stairs, a door): what lies there first, then the press through (macros/pursuit.py
    `to_the_door`); else the level run to it. The level is not come back to, so its loot goes first."""
    player = run.world().player
    if player is not None and self.at_the_way_on(player):
        if take_one():
            return
        self._teleport_step(run, key_names)
    else:
        level_run()


def _loop_hands(self: MacroRunner, run: Run, key_names) -> LegHands:
    """The hands of one leg of the KP_6 loop (macros/loop.py `LegHands`)."""
    hunter = self.hunter

    def labels() -> None:
        # Item labels on before a level run (routines.py `show_items_on`)
        world = run.world()
        name = world.player.name if world.player is not None else None
        show_items_on(run, show_items_key(self.saved_games, name) if name else None)

    agenda = self.loop.kind.agenda

    def level_run() -> None:
        if hunter is None:
            raise Abort('no level guide to hunt with')
        labels()  # the player's hard rule
        if agenda:
            self._loop_level_run(hunter, rush=False, agenda=True)  # the terror zone kinds: the agenda's targets
        else:
            self._loop_level_run(hunter)

    def way_on() -> None:
        self._way_on(run, key_names, take_one, level_run)

    def walk_out(to: int) -> None:
        # The town's walls and rooms from the level guide's map (macros/townexit.py)
        walk_out_of_town(run, lambda: hunter.level() if hunter is not None and hunter.level is not None else None, to)

    def fight() -> None:
        if hunter is None:
            raise Abort('no level guide to hunt with')
        labels()
        self._loop_level_run(hunter, rush=False)

    def fight_back() -> None:
        # Beset (macros/loop.py FIGHT_BACK): the kind's own level run, past nothing, so the attacker is fought
        if hunter is None:
            raise Abort('no level guide to hunt with')
        labels()
        self._loop_level_run(hunter, rush=False, agenda=agenda)

    def take_one() -> bool:
        level = hunter.level() if hunter is not None and hunter.level is not None else None
        # No room for a valuable: a 'room' stop, and the room rules make room (the player, 2026-10-18: "we should
        # stop and clear inventory with our designated town routine")
        if pick_up(run, level, key_names, lambda: None, threat(run), looped=True):
            return True
        # Else a valuable seen this game and not picked up is gone back for (routes/lower-kurast-loop-plan.md §14)
        return self._fetch(run, level, key_names)

    def inventory_key() -> str | None:
        world = run.world()
        return action_key(self.saved_games, world.player.name, INVENTORY) if world.player is not None else None

    def transmute_gems(full: frozenset[int]) -> tuple[int, int]:
        # Kept flawless gems, three into a perfect one at the stash (the player, 2026-10-17: "we need to cube 3
        # flawless -> perfect"); what has no room meanwhile is put down and picked up after (2026-10-18: "drop on
        # the ground then pickup and move to cube"). Returns (made, still on the ground).
        key = inventory_key()
        if key is None:
            return 0, 0
        parked: list[int] = []

        def staying() -> frozenset[tuple[int, int, int]]:
            # the cube takes the loop's items, not the full stacks' runes and materials (for Jamella)
            pack = run.reads.carried()
            sold = self.loop.sold_full
            held = {(i.txt, i.x, i.y) for i in pack.items if i.txt in sold} if pack is not None else set()
            return (self.loop.own or frozenset()) | held

        def park(unit_id: int) -> None:
            self.put_down.park(unit_id)
            parked.append(unit_id)

        made = left = 0
        for txt in sorted(t for t in full if perfect_of(t) not in (None, *full)):
            for _ in range(TRANSMUTES):
                done = transmute(run, key, txt, park)
                made += done
                if parked:
                    stash(run, key, staying())  # room to pick them up
                    for _ in range(len(parked) + PICK_SLACK):
                        if not pick_up(run, None, key_names, lambda: None):
                            break
                    now = run.reads.carried()
                    held = {i.unit_id for i in (*now.items, *now.in_cube)} if now is not None else set()
                    left = sum(1 for unit in parked if unit not in held)
                    LOG.info('Macro: cube: %d put down for the transmute, %d picked up again', len(parked),
                             len(parked) - left)  # fmt: skip
                    parked.clear()
                if not done:
                    break
        if made:
            # A kept gem still carried (a fourth of a kind) waits in the emptied cube for its next three; left in
            # the 2 x 4 block it broke the contract (2026-10-19 07:26)
            try:
                stash_only(run, key, self.loop.own or frozenset(), lambda item: kept_gem(item, full))
            except Abort as stop:
                if run.stops(stop):
                    raise
                LOG.info('Macro: cube: the kept gems not put in: %s', stop)
        return made, left

    def town_visit(exit: Exit) -> Contract:
        return self._shared_town_visit(run, exit, transmute_gems)

    def identify_loot(items: Sequence) -> None:
        self._identify_loot(run, items)

    def bring(items: Sequence) -> int:
        key = inventory_key()
        return unpack(run, key, items) if key is not None else 0

    def sighted(area: int | None) -> str | None:
        found = [s for s in self.sightings.outstanding() if area is None or s.area == area]
        return f'{found[0].label} at ({found[0].x:.0f}, {found[0].y:.0f})' if found else None

    def terrorized(area: int) -> bool | None:
        wanted = getattr(self.progress, 'wanted', None)
        return wanted(area) if wanted is not None else None

    def navigate() -> None:
        if hunter is None:
            return
        world = run.world()
        build = run.build or self.build
        free = None
        for moves in build.movement if build is not None else ():
            for source in getattr(moves, 'sources', ()):
                skill = source.jump.skill
                if skill != TELEPORT_SKILL and skill in world.slots and free is None:
                    free = skill_name(skill)
        found = means(
            Abilities(
                run.reads.own_teleport(),
                run.reads.teleport(),
                self.loop.teleports,
                free,
            )
        )
        if hunter.looped is not found.intent:
            LOG.info('Macro: navigation: %s (%s)', found.kind, found.why)
        hunter.looped = found.intent

    return LegHands(
        level_run,
        take_one,
        visit=town_visit,
        identify=identify_loot,
        bring=bring,
        way_on=way_on,
        fight=fight,
        fight_back=fight_back,
        left=self.valuable_left,
        sighted=sighted,
        terrorized=terrorized,
        navigate=navigate,
        walk_out=walk_out,
    )


def _identify_loot(self: MacroRunner, run: Run, items: Sequence) -> None:
    # Mass identify at Deckard Cain (the player, 2026-10-17: "we need to perform mass identify at decard cain"),
    # the Tome of Identify the fallback (macros/cain.py, macros/junk.py)
    try:
        done = identify_all(run, items)
    except Abort as stop:
        if cut(run, stop):
            raise
        LOG.info('Macro: identify: Cain: %s: the tome instead', stop)
        player = run.world().player
        key = action_key(self.saved_games, player.name, INVENTORY) if player is not None else None
        pack = run.reads.carried()
        inside = {i.unit_id for i in pack.items} if pack is not None else set()
        try:
            done = len(identify(run, key, [i for i in items if i.unit_id in inside])) if key else 0
        except Abort as again:
            if cut(run, again):
                raise
            LOG.info('Macro: identify: %s', again)
            return
    units = {item.unit_id for item in items}
    if done and run.seen(lambda w: units <= set(self.verdicts()), VERDICT_SECONDS) is None:
        LOG.info('Macro: identify: %d of %d appraised in time', len(units & set(self.verdicts())), len(units))
    pack = run.reads.carried()
    if pack is not None:
        for item in (*pack.items, *pack.in_cube):
            if item.unit_id in units and item.unit_id in self.verdicts():
                LOG.info('Macro: identify: appraised %s at (%d, %d): %s', named(item), item.x, item.y,
                         self.verdicts()[item.unit_id])  # fmt: skip
    run.say(f'Identified {done}')


def _shared_town_visit(
    self: MacroRunner,
    run: Run,
    exit: Exit,
    transmute_gems: Callable[[frozenset[int]], tuple[int, int]] | None = None,
) -> Contract:
    """The town visit (macros/visit.py `visit`) for the loop's items (its `own`: the player's protected cells,
    macros/volatile.py)."""

    def inventory_key() -> str | None:
        player = run.world().player
        return action_key(self.saved_games, player.name, INVENTORY) if player is not None else None

    def identify_loot(items: Sequence) -> None:
        self._identify_loot(run, items)

    own = self.loop.own
    if own is None:
        raise Abort("the player's items are not told apart yet")
    hands = Hands(inventory_key, identify_loot, lambda items: junk_of(items, self.appraise),
                  lambda: run.reads.stash_view(), transmute_gems, appraise=self.appraise)  # fmt: skip
    needs = Needs(keys=self.loop.kind.keys, portals=self.loop.portal or portal_source(run))
    done = visit(run, hands, needs, own, exit, full=frozenset(self.loop.full),
                 waited=self.loop.repair_waited(), memory=self.stash_memory)  # fmt: skip
    if done.full != frozenset(self.loop.full):
        self.loop.full = set(done.full)
        self.loop.keep_full()
    if done.repair_failed:
        self.loop.repair_failed = self.loop.games
    return done.contract
