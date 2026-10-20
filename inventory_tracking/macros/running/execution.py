"""A run's making and its routine: the run on the game's memory (`_execute`), the pad or the keys (`play_by`), the build
(`choosing`, `wear`), the routine's body (`perform`) and the teleport press's steps. A part of macros/runner.py
`MacroRunner`, its methods bound there."""

import math
import os
import random
import threading
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from inventory_tracking.common import LOG
from inventory_tracking.config import INPUT
from inventory_tracking.game.memory import GameMemory
from inventory_tracking.game.records import Player, World
from inventory_tracking.input.compositor import STEP_KEYS
from inventory_tracking.input.focus import FocusTracker, owns_process
from inventory_tracking.input.keybindings import INVENTORY, action_key, show_items_key
from inventory_tracking.input.keyboard import X11Keyboard
from inventory_tracking.levels.model import Ground, Target
from inventory_tracking.loot.api import FIELD, at_once, settle
from inventory_tracking.loot.hands import GameHands
from inventory_tracking.macros import route
from inventory_tracking.macros.actuator import Abort, Actuator, Cancelled
from inventory_tracking.macros.build import Build, choose
from inventory_tracking.macros.cta import cast_in_hand
from inventory_tracking.macros.cube import SURE_BLOCK, arrange_keys, close, drop_for, stash
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.goals import spot_of
from inventory_tracking.macros.hunt import Bearings, threat
from inventory_tracking.macros.keepers import amulet_keeper
from inventory_tracking.macros.opening import open_near
from inventory_tracking.macros.pad import PadActs, PadActuator, input_policy
from inventory_tracking.macros.pickup import SHUNNED, pick_up, wanted, worth_a_stop
from inventory_tracking.macros.routines import prebuff_keys, run_macro
from inventory_tracking.macros.running.base import (
    ATTACK,
    BUFF,
    DOOR_NEAR,
    DROPPED_SECONDS,
    FLIP_POLL,
    FLIP_SETTLE,
    FOCUS_POLL,
    HUNT_ELITES,
    LOOP,
    PICKUP,
    RESEARCH_ENV,
    STEPS,
    TELEPORT,
)
from inventory_tracking.macros.running.room import ROOM
from inventory_tracking.macros.running.valuables import tome_charges
from inventory_tracking.macros.skills import character_bindings, skill_keys
from inventory_tracking.macros.teleport import ready, step_toward
from inventory_tracking.macros.timing import Pace
from inventory_tracking.macros.travel import LOOPED, LOOPED_TELEPORT, cut
from inventory_tracking.macros.visit import note_view
from inventory_tracking.models import Actor, SessionIdentity
from inventory_tracking.native.memory import one_unit_table
from inventory_tracking.routes.model import FIGHT


if TYPE_CHECKING:
    from inventory_tracking.macros.runner import MacroRunner


def _execute(self: MacroRunner, cancelled: threading.Event, routine: str) -> None:
    press = self.press
    build = self.build
    if build is None:
        raise Abort('no build to play: the runner was given none')

    def mark(name: str) -> None:
        if press is not None:
            press.mark(name)

    with self.capture_lock:
        mark('locked')
        self.source.ensure_connected()
        pid, images, capture = self.source.pid, self.source.images, self.source.capture
    table = one_unit_table(capture)
    if table is None:
        raise Abort('the game is not attached')
    session = SessionIdentity(pid, images['identity']['start_ticks'], 0)
    if self.focus is None:
        self.focus = FocusTracker(INPUT)
        self.focus.wait_ready(timeout=1)
    focus = self.focus
    memory = GameMemory(pid, images['candidate_base'], table)
    memory.ground_seen = self.ground_seen  # one census across runs (game/memory.py `_census`)
    reads = [0, 0.0]  # how many looks at the game this run took, and their seconds (latency.py)

    looked = self.looked

    def look():
        began = time.perf_counter()
        try:
            return memory.world(light=run.light > 0)
        finally:
            took = time.perf_counter() - began
            reads[0] += 1
            reads[1] += took
            if looked is not None:
                looked(took)

    try:
        with X11Keyboard().connect(exclusive=False) as keys:
            if keys is None:
                raise Abort('no X display')

            def focused() -> bool:
                return focus(session) and owns_process(keys.focused_window_pid(), session)

            pace = Pace(random.Random())
            actuator = Actuator(keys, focused, pace)
            actuator.mark = mark
            actuator.cancelled = cancelled
            actuator.noted = self.noted  # the pointer check's abort goes into the take (actuator.py)
            if routine in STEPS or routine in (ATTACK, BUFF, LOOP):
                actuator.allow(*STEP_KEYS)  # the binding's own keys; the macro request waits for a release instead

            def key_names(world, skills=None):
                # `skills` None: the keys of the prebuff of the build the run plays (routines.prebuff_keys)
                if world.player is None:
                    raise Abort('not in a game')
                show_items = show_items_key(self.saved_games, world.player.name)
                if show_items:
                    actuator.allow(show_items)
                wanted = prebuff_keys(run.build) if skills is None else skills
                name = world.player.name
                try:
                    if run.pad is not None:  # controller mode: the records' labels (macros/pad.py)
                        return run.pad.keys(wanted, lambda: character_bindings(self.saved_games, name))
                    bindings = character_bindings(self.saved_games, name)
                    return skill_keys(world.slots, bindings, wanted)
                except (OSError, ValueError) as exc:
                    raise Abort(str(exc)) from exc

            run = Run(
                look,
                actuator,
                pace,
                cancelled=cancelled,
                say=self._say,
                hands=memory.hands,
                teleport=memory.teleport,
                loot=lambda: self._sighted(
                    memory,
                    self._picked(
                        self.put_down.see(self.belt.see(memory.loot(**wanted()))), lambda: tome_charges(memory)
                    ),
                ),
                build=build,
            )
            if os.environ.get(RESEARCH_ENV):
                run.research = memory.hover_candidates  # a scan of the whole data section per Consume
            run.hovered = memory.hovered
            run.own_teleport = memory.own_teleport
            run.worn_skills = memory.worn_skills
            if self.hunter is not None:
                self.hunter.room_maker = self._room_in_cube
                self.hunter.room_trip = self._room_trip_due  # the shared no-room routine's trip (running/room.py)
                self.hunter.can_trip = self._room_trip_possible
                self.hunter.looping = lambda: self.loop.on  # the sweep holds a plain valuable then (`take_one`)
                # A big field item identified at the level run's first quiet look (loot/api.py FIELD_AT_ONCE; the
                # player, 2026-10-20 ~14:28: "space for mid-run identifying big items")
                self.hunter.field_now = lambda run: at_once(lambda: field_hands(self, run))
            run.wear = memory.wear
            run.cta = memory.cta
            run.arrival_swap = lambda: cast_in_hand(run, key_names)
            run.lasting = self.lasting  # the buffs' casts that took, across runs (macros/buffs.py `took_of`)
            run.hover_note = memory.hover_note
            run.mark = mark
            run.warn = self._warn
            run.stand_by = self._stand_by
            run.hurry = self.hurry
            run.deadline = self.deadline
            run.warps = memory.warps
            run.things = memory.things
            run.containers = memory.containers
            run.carried = memory.carried
            run.stock = memory.stock
            run.stash_view = memory.stash_view
            self.item_stats = memory.item_stats
            run.players_item = lambda item: self.loop.players_item(item, memory.item_stats(item.unit_id))
            run.kept_item = lambda item: amulet_keeper(item, memory.item_stats(item.unit_id))
            run.objects = memory.objects
            run.corpses = memory.corpses
            run.flights = memory.flights
            if self.healer is not None:
                run.given = lambda kind, ledger=self.healer: ledger.given_at(Actor.MERC, kind)
                run.ledger = self.healer  # the drinker claims the character's potion in it
            run.arrival = lambda: self.journey.arrival(time.monotonic())
            run.supers = self.supers
            run.ending = self.progress.ending if self.progress is not None else None
            run.ground = self.ground
            # The field identify (loot/api.py, M4 of loot/design.md): only in the KP_6 loop, at its sites (`settle`)
            FIELD.looping = lambda: self.loop.on
            FIELD.trip = self._field_trip  # no room in the cube either: the room rules' trip (FIELD_AT_ONCE, ~14:58)
            run.field = lambda when: FIELD.settle(field_hands(self, run), when)
            self.play_by(run, actuator, routine)
            mark('ready')
            try:
                self.perform(run, actuator, routine, key_names)
            finally:
                if run.pad is not None:
                    run.pad.actuator.neutral()  # nothing of the pad is left held after a run
    finally:
        memory.close()
        if press is not None:
            press.notes.update(reads=reads[0], read_ms=round(1000 * reads[1], 1))


def field_hands(self: MacroRunner, run: Run) -> GameHands:
    """The field routine's hands over `run` (loot/hands.py): the loop's cells (`Loop.own`), the identify worker's
    appraisal, the runner's put-downs."""

    def inventory_key() -> str | None:
        player = run.world().player
        return action_key(self.saved_games, player.name, INVENTORY) if player is not None else None

    loop = self.loop
    return GameHands(
        run,
        inventory_key=inventory_key,
        own=lambda pack: loop.own,
        appraise=self.appraise,
        put_down=self.put_down,
        cain_ahead=lambda: (loop.room_low and loop.carrying) or loop.short or loop.repair,  # the next visit's errands
    )


def play_by(self: MacroRunner, run: Run, actuator: Actuator, routine: str) -> None:
    """The run plays by the pad when the game is in controller mode (macros/pad.py `input_policy`: the game's mode
    followed, never changed; Abort when the routine cannot be played in it now). The keys' actuator is told the
    mode either way: it presses no mouse button in controller mode."""
    play = self.pad_play
    if play is None:
        return
    actuator.mode = play.mode
    mode = play.mode()
    if self.settling:
        # The request made again after a flip (`again`): the flip under way is waited out, not refused
        self.settling = False
        ends = time.monotonic() + FLIP_SETTLE
        while mode is not None and mode.pending and time.monotonic() < ends and not run.cancelled.is_set():
            run.cancelled.wait(FLIP_POLL)
            mode = play.mode()
    if not input_policy(mode, enabled=play.enabled):
        actuator.keyboard_run = True  # the game leaving keyboard mode stops it (actuator.py `guard`)
        return
    pad = PadActs(run, PadActuator(play.device, play.mode, actuator), play.controller, play.bindings, play.route)
    run.pad = pad
    run.hovered = pad.target
    LOG.info('Macro: %s in controller mode, by the pad', routine)


def perform(self: MacroRunner, run: Run, actuator: Actuator, routine: str, key_names) -> None:
    """One routine on the run made for it (`_execute`), by the build chosen at its first look (`choosing`)."""
    self.choosing(run)
    if self.hunter is not None:
        self.hunter.bearings = Bearings(self.progress, self.target, self.marks, self.supers)
    if routine == TELEPORT and self.jumps:
        self._jump(run, key_names)  # hop by hop to the next goal (running/jump.py)
    elif routine == TELEPORT and self.pursues(run, key_names):
        pass  # one pass of the pursuit's decision made the press (hunting/moves.py `pursue_once`)
    elif routine == TELEPORT:
        self._teleport_step(run, key_names)
    elif routine == PICKUP:
        hunter = self.hunter
        if hunter is None:
            raise Abort('no level guide to hunt with')
        level = hunter.level() if hunter.level is not None else None
        stepped = []

        def otherwise(run=run, hunter=hunter, level=level, stepped=stepped) -> None:
            if open_near(run, level, key_names, threat(run)):  # a chest by the character, a super chest
                return
            with run.lightly():
                player = run.world().player
            if self.progress is not None and player is not None and self.progress.ending(player.area):
                # The route's bosses are dead: nothing is sought; the press is the route's (the ground called
                # clean, then the game left), as the teleport key's is.
                self.staged(run, key_names, lambda card: None)
                return
            if player is not None and self.at_the_way_on(player):
                # At the route's door the press goes through (rca/2026-10-15/kp1-door-findings.md).
                self.staged(run, key_names, lambda card: None)
                return
            stepped.append(hunter.step(run, key_names))

        # No room: the shared routine's trip may follow the stop (running/room.py, `_guarded`)
        pick_up(run, level, key_names, otherwise, threat(run), trips=self._room_trip_possible())
        if stepped:
            self.attack_mode = True  # nothing to pick up or open: a seek step, the mode follows
    elif routine == LOOP:
        self.loop.marks = self.marks
        note_view(run, self.stash_memory)  # the stash as read, once a game in the Fortress (town-plan.md step 0)
        if self.loop.tidy_panels:
            self.loop.tidy_panels = False
            left = [panel for panel in ('inventory', 'cube') if panel in run.world().open_panels]
            if left:
                LOG.info('Macro: loop: %s open as the loop is turned on: closed', ' and '.join(left))
                close(run, ('inventory', 'cube'))
        if self.loop.make_room:
            self.loop.make_room = False
            world = run.world()
            key = action_key(self.saved_games, world.player.name, INVENTORY) if world.player is not None else None
            if key is not None and self.loop.own is not None:
                try:
                    settle(run, 'room')  # the field identify's failures put down first (loot/design.md §2.4)
                    # A key stack out of the 2 x 4 block first: the room is often there already, in pieces
                    arrange_keys(run, key)
                    stash(run, key, self.loop.own)  # the loop's items into the cube: room for what lies there
                except Abort as stop:
                    if cut(run, stop):
                        raise
                    LOG.info('Macro: loop: no room made in the cube: %s', stop)
        if self.loop.drop_room:
            self.loop.drop_room = False
            world = run.world()
            key = action_key(self.saved_games, world.player.name, INVENTORY) if world.player is not None else None
            if key is not None and self.loop.own is not None:
                try:
                    settle(run, 'room')  # the field identify's failures first: their room may be enough (drop_for)
                    gone = drop_for(run, key, self.loop.own, SURE_BLOCK)
                except Abort as stop:
                    if cut(run, stop):
                        raise
                    LOG.info('Macro: loop: no item dropped: %s', stop)
                else:
                    if gone is not None:
                        SHUNNED[gone.unit_id] = run.clock() + DROPPED_SECONDS  # not taken up again this game
        if actuator.keys.focused_window_rect() is None:
            # The game's window lost the focus (the player at another window): nothing can be clicked, so the loop
            # waits, and the watchdogs (`poll`) count none of it
            LOG.info('Macro: loop: waiting for the game window to have the focus')
            self.loop.waiting = True
            try:
                while actuator.keys.focused_window_rect() is None:
                    if run.cancelled.wait(FOCUS_POLL):
                        raise Cancelled
            finally:
                self.loop.waiting, self.loop.seen, self.loop.moved = False, None, None
            LOG.info('Macro: loop: the game window has the focus again')
        if self.hunter is not None:
            # Teleport while the gold pays for the staff's charges (macros/loop.py `teleports`), and always when it
            # is the character's own (Enigma: no charge, no swap)
            own = run.reads.own_teleport()
            looped = LOOPED_TELEPORT if self.loop.teleports or own else LOOPED
            if own and self.hunter.looped is not looped:
                LOG.info("Macro: loop: Teleport is the character's own: in every move")
            self.hunter.looped = looped

        self.loop.leg(
            run,
            key_names,
            self.progress,
            self._loop_hands(run, key_names),
            item_stats=self.item_stats,
            shown=self.stash_memory,
        )
    elif routine == ROOM:
        self._room_errand(run, key_names)  # an activity by hand's trip for room (running/room.py)
    elif routine == BUFF:
        self._keep_buffs(run, key_names)  # the buffs kept up while the player plays by hand (running/buffing.py)
    elif routine in (HUNT_ELITES, ATTACK):
        if self.hunter is None:
            raise Abort('no level guide to hunt with')
        if routine == ATTACK:
            actuator.drift, actuator.steady = 10**6, False  # the player's hand is on the mouse all along
            self.hunter.pick = self._pick
            self.hunter.attack_mode(run, key_names)
        else:
            self.hunter.seek(run, key_names)
    else:
        run_macro(run, key_names)


def pursues(self: MacroRunner, run: Run, key_names) -> bool:
    """With the pursuit on for some build: the teleport press made by one pass of attack mode's decision
    (hunting/moves.py `pursue_once`); whether it was. A press whose goal is a fight turns the mode on, unless the
    player's toggle turned it off (rca/2026-10-13/kp4-findings.md §1, §2.8)."""
    walker = self.hunter
    if walker is None or not any(build.settings.pursuit for build in (*self.builds, self.fallback) if build):
        return False
    ready(run)  # the run's first look that shows the character names the build (`choosing`)
    wants = not self.attack_declined
    found = walker.pursue_once(run, key_names, attacking=self.attack_mode or wants)
    if found is None:
        return False
    if found.goal is not None and found.goal.do == FIGHT and wants:
        self.attack_mode = True  # the mode follows this step (`_follow`)
    return True


def staged(self: MacroRunner, run: Run, key_names, plain: Callable[[Target | None], None]) -> None:
    """One press of the stage the level is at (macros/route.py `press`); `plain` is the step toward the
    card's mark for a level or a stage without one of its own."""
    walker = self.hunter

    def leave_the_game(run: Run, key_names) -> None:
        self.attack_mode = False  # as the macro request ends it
        self._end_run('the game is left')
        route.leave(run, key_names)

    route.press(
        run,
        self.progress,
        self.target,
        self.marks,
        key_names,
        plain=plain,
        level=lambda: walker.level() if walker is not None and walker.level is not None else None,
        attack=lambda: setattr(self, 'attack_mode', True),
        leave=leave_the_game,
    )


def at_the_way_on(self: MacroRunner, player: Player) -> bool:
    """Whether the route's stage on the character's level is its way on (a door, stairs, a portal) and the
    character is within DOOR_NEAR of its mark, where a level run ends (pursuit.py `to_the_door`). A tour's mark (the
    Canyon's tombs: the card leads with the nearest not yet entered) is one too: the TZ loop's way on through it
    (2026-10-20: without it the way on ran the level again to the same entrance)."""
    staged = route.staged(self.progress, player.area)
    way = staged is not None and bool(staged[1].to or staged[1].tours)
    card = self.target() if self.target is not None and staged is not None and way else None
    if card is None or staged is None or card.area != player.area or card.label != staged[1].mark:
        return False
    return math.dist((player.x, player.y), spot_of(card)) <= DOOR_NEAR


def _teleport_step(self: MacroRunner, run: Run, key_names) -> None:
    """One teleport press with no pursuit to make it: a step of the level's stage (`staged`), else the plain step.
    Also the Andariel loop's press through the stairs."""
    walker = self.hunter

    def empty(target: Target, run=run) -> bool:
        # A chest mark with no chest shown at it is done with (route.note_empty; the player, 2026-10-16).
        return route.note_empty(run, target, self.progress, self.marks)

    def plain(card: Target | None, run=run, walker=walker) -> None:
        drop = worth_a_stop(run) if walker is not None else None
        if walker is None:
            step_toward(run, card, key_names, empty=empty)
        elif drop is not None:
            # The step does not leave a valuable behind: this press takes it, the next hops.
            LOG.info('Macro: the teleport step takes %s first', drop.label)
            pick_up(run, walker.level() if walker.level is not None else None, key_names, lambda: None)
        elif card is not None and walker.boss_step(run, card, key_names):
            pass  # the boss stands where its mark has no shot at it: the step went for the boss
        else:
            step_toward(
                run,
                card,
                key_names,
                lambda target: walker.foot_step(run, target, key_names),
                lambda target, player, spot: walker.warp_hop(run, target, player, spot, key_names),
                empty=empty,
            )

    self.staged(run, key_names, plain)


def choosing(self: MacroRunner, run: Run) -> None:
    """Have the run's build chosen at its first look that shows a character (macros/build.py `choose`), on the
    routine's own look so it costs none; anew each run, so another character is followed."""
    fallback = self.fallback
    if fallback is None:
        raise Abort('no build to play: the runner was given none')
    read, chosen = run.read, []

    def first() -> World:
        world = read()
        if not chosen and world.player is not None:
            chosen.append(True)  # once a run
            self.wear(run, choose(self.builds, world, fallback))
        return world

    run.read = first


def wear(self: MacroRunner, run: Run, build: Build) -> None:
    """`build` is the one the run plays, and the hunt with it."""
    if build is not self.build:
        LOG.info('Macro: the build is %s%s', build.name, '' if build.weapons else ', no weapon sets of its own')
    self.build = run.build = build
    if build.weapons is not None:
        # Every run knows the build's weapon sets: the teleport step's empty-staff swap (hunt.py `empty_hop`)
        # did nothing in a run that held none (2026-10-13 12:33).
        run.prebuff_hands, run.battle_hands = build.weapons.prebuff, build.weapons.battle
    if self.hunter is not None:
        self.hunter.use(build)


def ground(self: MacroRunner) -> Ground | None:
    """The walkable ground of the level the guide has a map of (routines.open_spots), None without one."""
    hunter = self.hunter
    level = hunter.level() if hunter is not None and hunter.level is not None else None
    return Ground(level.ground) if level is not None and level.ground else None
