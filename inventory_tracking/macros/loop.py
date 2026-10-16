"""The Lower Kurast loop: KP_6 plays games until it is toggled off (routes/lower-kurast-loop-plan.md phase 4).

The loop is a state machine read from where the character is, so it goes on from any point (`next_leg`): one leg a
run of the runner's (macros/runner.py LOOP), the next chosen when it is over. The legs are the routines built for
them: the next game and its prebuff (routines.py), the waypoint (waypoint.py), the KP_1 level run for the chests
(pursuit.py, run as attack mode: the runner starts it and comes back here when it ends), the pickup of what is left,
the portal (portal.py), Save and Exit. The player, 2026-10-16: games end in act 4 (portal → Kurast Docks → waypoint
→ Pandemonium Fortress → Save and Exit), where the next game starts by its waypoint.

It stops by itself, saying why (`Macro: loop stopped: …`): a leg that `Abort`s, the character dead, a place the loop
has no leg for, and a leg made again and again in one game with nothing coming of it (`REPEATS`).
"""

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

from inventory_tracking.levels.presets import display_name
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import own_of
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.portal import to_town
from inventory_tracking.macros.routines import DEAD, character_keys, create_next_game, leave_game, prebuff
from inventory_tracking.macros.waypoint import travel
from inventory_tracking.macros.world import World
from inventory_tracking.routes.model import LOOT, USE
from inventory_tracking.routes.progress import Progress


__all__ = ['LOWER_KURAST', 'Loop', 'next_leg']

KURAST_DOCKS, LOWER_KURAST, PANDEMONIUM_FORTRESS = 75, 79, 103
# The legs, as the HUD says them.
NEXT_GAME = 'next game'
TO_THE_CHESTS = 'to Lower Kurast'
CHESTS = 'the chests'
PICK_UP = 'what is left'
PORTAL = 'Town Portal'
TO_THE_FORTRESS = 'to Pandemonium Fortress'
LEAVE = 'Save and Exit'
# How often one leg may be made in one game before the loop gives up on it: a pickup a drop at a time, the level run
# again after it stopped short, any other leg once more after a failure that left the character where it was.
REPEATS = {PICK_UP: 20, CHESTS: 3}
REPEAT = 2


@dataclass
class Loop:
    """The loop's memory across its legs: on or off, the games played, the game prebuffed in, the game whose chests
    are done (the portal cast), and how often each leg was made in a game."""

    on: bool = False
    games: int = 0
    prebuffed: str | None = None
    done: str | None = None
    made: Counter[tuple[str, str]] = field(default_factory=Counter)
    # The inventory as the player keeps it, by class and cell, read at the loop's first leg in a game: what is not in
    # it is the loop's, moved into the cube before a game is left (macros/cube.py, phase 9)
    own: frozenset[tuple[int, int, int]] | None = None

    def start(self) -> None:
        self.on, self.made, self.own = True, Counter(), None

    def stop(self) -> None:
        self.on = False

    def count(self, world: World, leg: str) -> None:
        """`leg` made once more where `world` is; `Abort` when that is more than REPEATS allows. A game's legs count
        in that game; the lobby's (the next game) count by the game just left, so each game left has its own: counted
        all in one, the third game the loop made stopped it, "next game again and again in the lobby" (20:55:43 and
        21:05:53 on 2026-10-16, each the third game after KP_6)."""
        where = world.game_name if world.in_game else f'the lobby after {world.game_name or "no game"}'
        self.made[where, leg] += 1
        if self.made[where, leg] > REPEATS.get(leg, REPEAT):
            raise Abort(f'{leg} again and again in {where}: nothing came of it')

    def leg(
        self,
        run: Run,
        key_names,
        progress: Progress | None,
        level_run: Callable[[], None],
        pick_up: Callable[[], bool],
        stash: Callable[[frozenset[tuple[int, int, int]]], int] | None = None,
    ) -> str:
        """Make the next leg (`next_leg`); the leg made. `level_run()` asks the runner for the KP_1 level run,
        which follows this leg; `pick_up()` takes one drop, False with nothing worth it on the ground; `stash(own)`
        moves the loop's items into the cube (macros/cube.py), `own` the inventory as the player keeps it."""
        world = run.world()
        leg = next_leg(world, progress, self)
        game = world.game_name if world.in_game else ''
        self.count(world, leg)
        if self.own is None and world.in_game and run.carried is not None:
            pack = run.carried()
            if pack is not None:
                self.own = own_of(pack.items)
        run.say(f'Loop: game {self.games + 1}, {leg}')
        if leg != NEXT_GAME:
            run.keys = character_keys(run, key_names)  # Swap Weapons among them: the arrival's check (`arrived`)
        if leg == NEXT_GAME:
            trace = create_next_game(run, world.game_name)
            run.keys = character_keys(run, key_names)
            prebuff(run, fresh=trace)
            self.prebuffed = run.world().game_name
        elif leg == TO_THE_CHESTS:
            if self.prebuffed != game:
                prebuff(run)
                self.prebuffed = game
            travel(run, LOWER_KURAST)
        elif leg == CHESTS:
            level_run()
        elif leg == PICK_UP:
            if not pick_up() and progress is not None:
                progress.looted(LOWER_KURAST)
        elif leg == PORTAL:
            if not pick_up():
                self.done = game
                to_town(run, key_names)
        elif leg == TO_THE_FORTRESS:
            self.done = game  # left Lower Kurast: a game begun here is not the loop's to play
            travel(run, PANDEMONIUM_FORTRESS)
        elif leg == LEAVE:
            if stash is not None and self.own is not None:
                stash(self.own)  # the loop's items into the cube, before the game is left
            leave_game(run)
            self.games += 1
        return leg


def next_leg(world: World, progress: Progress | None, loop: Loop) -> str:
    """The leg the loop makes next from where the character is; `Abort` where it has none."""
    if not world.in_game:
        return NEXT_GAME
    player = world.player
    if player is None:
        raise Abort('not in a game')
    if player.mode in DEAD:
        raise Abort('the character is dead')
    if player.area == PANDEMONIUM_FORTRESS:
        return LEAVE if loop.done == world.game_name else TO_THE_CHESTS
    if player.area == LOWER_KURAST:
        step = progress.step(LOWER_KURAST) if progress is not None else None
        if step is not None and step.stage.kind == USE:
            return CHESTS
        if step is not None and step.stage.kind == LOOT:
            return PICK_UP
        return PORTAL
    if player.area == KURAST_DOCKS:
        return TO_THE_FORTRESS
    raise Abort(f'the loop has nothing to do in {display_name(player.area)}')
