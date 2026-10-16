"""The macro request's routines (first written for the Pindleskin runs of CybergrindAA), built from small steps.

`run_macro` picks by place (plan.md, decisions of 2026-10-06): where a run ends (Nihlathak's
Temple, Frigid Highlands, Bloody Foothills, the Fortress just after act 3, Catacombs Level 4
with Andariel dead, Tower Cellar Level 5 with the Countess dead) leave the game,
create the next one and prebuff; in the lobby create the next game and prebuff; anywhere else
prebuff where the character stands.
Prebuff: the prebuff rows of the build's buff plan, cast by the executor (buffs.py `Buffs.prebuff`).
For the Warlock: Consume cast anew on a Defiler (a standing one, else a summoned one), one Defiler
left out, then Hex: Purge and Psychic Ward (builds/warlock/buffs.py, casters.py).
"""

import math
import os
from collections.abc import Callable
from typing import TYPE_CHECKING

from inventory_tracking.common import LOG
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.skills import SWAP_WEAPONS, skill_name
from inventory_tracking.macros.view import (
    AIM_LIMITS as AIM_LIMITS,
    BODY_LIFT as BODY_LIFT,
    FEET as FEET,
    UNIT_PIXELS as UNIT_PIXELS,
    Viewport,
)
from inventory_tracking.macros.world import TRACE_RVAS, Player, World, next_name


if TYPE_CHECKING:
    from inventory_tracking.macros.build import Build  # build.py is above this module (`LoadTrace`)


NIHLATHAKS_TEMPLE = 121
# Where a farming run ends, so the macro request there leaves the game: Pindleskin's Temple, and for the
# Eldritch and Shenk run (user, 2026-10-06) the Frigid Highlands above its waypoint and the
# Bloody Foothills below it. On those two only within BOSS_UNITS of where a super unique of the level
# was last seen, Eldritch or Shenk (user, 2026-10-11: the request in the middle of a terrorized Frigid
# Highlands, 550 units from Eldritch, left the game where a prebuff was meant). Without the tracker's
# word on the level's super uniques the whole level counts, as before.
RUN_ENDS = frozenset((NIHLATHAKS_TEMPLE, 110, 111))
BOSS_LEVELS = frozenset((110, 111, 124, 74))
BOSS_UNITS = 100.0
# Mephisto and other act 3 runs end with a step into act 4, so the next game starts there
# (user, 2026-10-06): the Pandemonium Fortress is a run end for a while after the character
# came to it from act 3 (Kurast Docks to Durance of Hate Level 3). A game that started in the
# Fortress, or a return from the act 4 levels, is not.
# An Andariel run ends on her level once she is dead (user, 2026-10-07): the character on the
# level with no live Andariel in the unit table. No corpse is asked for: hers leaves the table
# 19 s after the kill (host). She is in the table from 86 units away; further off, at the
# stairs before the fight, the macro request leaves the game too.
CATACOMBS_4 = 37
ANDARIEL = 156  # as in terror/bosses.py
# A Countess run ends the same way (user, 2026-10-10): Tower Cellar Level 5 with no live Countess in
# the unit table. She has no class of her own: the super unique among the level's Dark Stalkers
# (terror/bosses.py).
TOWER_CELLAR_5 = 25
COUNTESS = 45
# A Nihlathak run ends where he was killed (user, 2026-10-11: the request beside his corpse, 13 s
# after the kill, only prebuffed): the Halls of Vaught with no live Nihlathak in the unit table, within
# BOSS_UNITS of where he was last seen (the level's only super unique). Not seen in this game, in
# the halls on the way to him, it prebuffs.
HALLS_OF_VAUGHT = 124
NIHLATHAK = 526  # as in terror/bosses.py
# A Summoner run ends the same way (user, 2026-10-11: "win-x at summoner's location should go
# save/exit -> new game -> prebuff"): the Arcane Sanctuary with no live Summoner in the unit table,
# within BOSS_UNITS of where he was last seen (the tracker gives him with the level's super uniques,
# though he carries the unique flag only: terror/tracker.py `supers`).
ARCANE_SANCTUARY = 74
SUMMONER = 250  # monstats.txt `summoner`
# The level -> its boss: with him alive the macro request never leaves, and without the tracker's
# word on where he was seen it does not leave either.
BOSS_OF = {HALLS_OF_VAUGHT: NIHLATHAK, ARCANE_SANCTUARY: SUMMONER}
SUPER_UNIQUE_FLAG = 0x02  # the monster's type flags, as terror/bosses.py
PANDEMONIUM_FORTRESS = 103
ACT_3 = range(75, 103)
ARRIVAL_SECONDS = 180.0


def prebuff_keys(build: Build) -> tuple[int, ...]:
    """The skills whose keys the prebuff needs, from the prebuff rows of the build's buff plan (buffs.py
    `phase_keys`), in the order they are asked for."""
    from inventory_tracking.macros.buffs import phase_keys  # late: buffs.py is above this module

    return phase_keys(build.buffs, 'prebuff')


SWAP_TRIES = 3  # presses of Swap Weapons before the swap is given up
SWAP_SETTLE = 0.2  # seconds the character stands free before the first press of a swap
SWAP_WAIT = 0.5  # seconds a swap is given to show before the key is pressed again

# Window fractions. The screenshots (2000 x 1125) show the whole 2560 x 1440 output, whose top
# 22 pixels are the desktop bar, not the game window: y = (shot_y * 1.28 - 22) / 1418. Taking
# the screenshot fraction as it is put the click on the lower edge of the name field (host run
# 17:10, 2026-10-06: six clicks, no key taken).
SAVE_AND_EXIT = (0.5, 0.438)
GAME_NAME_FIELD = (0.8, 0.158)  # right of the text, so the caret lands at its end

# Player modes that are an action under way: attacks, casts, skill sequences (classic table).
ACTING = frozenset((7, 8, 10, 11, 12, 13, 14, 15, 16, 18))
QUICK_SECONDS = 1.0  # at most, for the skill key before to give the right button back (that Sigil: 0.9 s)
QUICK_UNSEEN = 0.35  # a key tapped with nothing held whose skill never showed on the button: not waited for
DEAD = frozenset((0, 17))
CREATE_LIMIT = 12.0  # seconds from Enter for the new game to exist
LOAD_MIN = 8.5  # seconds from Enter before the first key in a new game
LOAD_LIMIT = 40.0  # seconds from Enter the first summon may take
# A level change by a waypoint or a portal (`arrived`): the view byte shows a load within ARRIVAL_MARK of it if it
# shows one at all; the level comes up within ARRIVAL_LIMIT; with no load shown, ARRIVAL_SETTLE stands in. cyber17,
# 2026-10-16 (rca/2026-10-16/loop-first-game-findings.md §2): after the waypoint from act 4 to act 3 no input took for
# 4.5 s, the first that did 5.4 s after the arrival. The takes record the byte from then on (`view`).
ARRIVAL_MARK = 0.3
ARRIVAL_LIMIT = 20.0
ARRIVAL_SETTLE = 5.0
# monstats.txt rows with npc = 1 or inTown = 1 (installed game, 2026-10-07): townsfolk. Consume cannot
# take them, yet Kashya, Warriv and Cain stand where a new game starts and were in 13 of the 16 logged
# crowds (host, 2026-10-07), which stopped five prebuffs in the Rogue Encampment. Checked against the
# table again on 2026-10-11: 528 (evilhut, the imps' hut) and 540 (ancientbarb1) stood here with neither
# flag and killable = 1, so the hunt never struck a hut (user: "we don't target demon huts at all").
TOWN_NPCS = frozenset((
    146, 147, 148, 150, 152, 154, 155, 175, 176, 177, 178, 185, 195, 196, 197, 198, 199, 200, 201, 202,
    203, 204, 205, 210, 244, 245, 246, 251, 252, 253, 254, 255, 257, 264, 265, 266, 270, 272, 294, 296,
    297, 331, 367, 377, 378, 405, 406, 408, 512, 513, 514, 515, 516, 521, 522, 538, 539,
))  # fmt: skip
FIELD_ATTEMPTS = 6  # about eight seconds for the lobby to come up


def screen_fraction(player: Player, x: float, y: float, aspect: float) -> tuple[float, float]:
    """Where a unit at world (x, y) is drawn, as window fractions; `aspect` is width / height (view.py)."""
    return Viewport(aspect).body((player.x, player.y), x, y)


def world_point(player: Player, x: float, y: float, aspect: float) -> tuple[float, float]:
    """The ground point drawn at window fraction (x, y): the inverse of `screen_fraction` for feet."""
    return Viewport(aspect).world((player.x, player.y), x, y)


def on_screen(point: tuple[float, float]) -> bool:
    return Viewport().on_screen(point)


def quick_cast_over(run: Run, skill: int) -> None:
    """Wait for the skill key tapped before this one to be done with the right mouse button. A key
    with Quick Cast puts its skill on the button for the cast and the one from before back after.
    Tower Cellar 1, 20:00:12 on 2026-10-11: Sigil: Lethargy tapped under the held strike was still
    waiting when Teleport's key came 0.4 s later; the game put the Sigil on the button, took it for
    "the one from before" and left it there, and attack mode stopped ("Echoing Strike is on no skill
    key and on neither mouse button") until the player put the strike back by hand; twice that game.
    A look since the key that showed its skill on the button (`Run.quick_shown`, any look of the run's)
    counts as seen: then only the button's return is waited for (the Chaos Sanctuary, 2026-10-14: a Sigil
    after a Death Mark waited out the second with its cast long over, rca/2026-10-14/death-mark-engage.md)."""
    if run.quick is None or run.quick[0] == skill:
        return
    before, home, tapped, held = run.quick
    seen = run.quick_shown
    waiting = run.clock() - tapped < QUICK_SECONDS  # else the key before is long done or dropped: nothing to wait for
    while True:
        player = run.world().player
        if player is None or player.right_skill is None or home is None:
            break
        seen = seen or player.right_skill == before
        if seen and player.right_skill == home:
            break  # it was on the button and is off it again
        if not seen and not held and player.mode not in ACTING and run.clock() - tapped >= QUICK_UNSEEN:
            break  # never came on: cast without the button showing it, or not taken at all
        if run.clock() - tapped >= QUICK_SECONDS:
            # Said only for a wait made or a skill still on the button: a key that comes long after the one before
            # finds the button given back and waits for nothing (every Death Mark of 2026-10-14 followed a "Blade
            # Warp still on the right button" of a warp seconds old).
            if player.right_skill == before or waiting:
                LOG.info('Macro: %s still on the right button %.1fs after its key', skill_name(before), QUICK_SECONDS)
            break
        run.pace.sleep(0.02)
    run.quick = None


def press_skill(run: Run, skill: int, poll: float = 0.03, *, wait: bool = True) -> float:
    """Press the skill's key once the character is free to act, looked for every `poll` seconds.
    `wait` off: pressed now, whatever the character does; the game keeps a Quick Cast key pressed
    during a cast and casts it when that cast is over (teleport.press_hop). In controller mode the skill's
    pad record, toward what the caller aimed it at (macros/pad.py `PadActs.cast`). Returns the clock time
    the key went down: a casting delay runs from it, not from the key's release a hold later."""
    if run.pad is None:
        quick_cast_over(run, skill)  # the right mouse button's Quick Cast: none in controller mode
    if wait:
        ready = run.expect('character ready', lambda w: w.player is not None and w.player.mode not in ACTING, 2.5, poll)
    else:
        ready = run.world()
    if ready.player is not None and ready.player.mode in DEAD:
        raise Abort('the character is dead')
    home = ready.player.right_skill if ready.player is not None else None
    held = bool(run.actuator.holding or run.actuator.holding_buttons)  # under a held strike the game makes it wait
    run.quick = (skill, home, run.clock(), held) if home != skill and run.pad is None else None
    run.quick_shown = False
    run.say(skill_name(skill))
    LOG.info(
        'Macro: %s on %s, player mode %s',
        skill_name(skill),
        run.keys[skill],
        ready.player.mode if ready.player else None,
    )
    down = run.clock()
    if run.pad is not None:
        run.pad.cast(skill)
        return down
    run.actuator.tap(run.keys[skill])
    return down


QUEUED_SECONDS = 0.09  # after a cast's end, for the cast of a key pressed during it to show
THROUGH_POLL = 0.01
ONE_CAST = 0.45  # seconds no single cast of the character lasts (0.36 to 0.39 s recorded): longer, a second one ran


def press_through(run: Run, skill: int) -> None:
    """The skill's key pressed at once, also during a cast: the game keeps a Quick Cast key that comes
    during a cast and casts it on the first frame the character is free (the client's code, read on
    2026-10-12, macros/plan.md). When that cast ends and none follows within QUEUED_SECONDS the game
    did not keep the press, and it is pressed again, the character being free then. With `press_skill`
    alone a key under the held strike waited for a look to fall into the instant between two casts:
    1.1 s for a Sigil and 1.4 s for an Engorge in the fight of Tower Cellar 5 (22:50:44 and :47 on
    2026-10-11), the strike's aim frozen meanwhile; the caller lets the strike go first.
    In controller mode the record is pressed once the character is free: what is watched below is the mouse's
    Quick Cast."""
    if run.pad is not None:
        press_skill(run, skill, THROUGH_POLL)
        return
    world = run.world()
    busy = world.player is not None and world.player.mode in ACTING
    press_skill(run, skill, THROUGH_POLL, wait=not busy)
    if not busy:
        return
    tapped = run.clock()

    def shown(w: World) -> bool:
        # A Quick Cast key puts its skill on the right button for its cast (Sigil: Lethargy 0.12 s,
        # Engorge 0.12 s, Blade Warp 0.37 s in the take of Tower Cellar 5): the cast is the key's.
        return w.player is not None and w.player.right_skill == skill

    over = run.seen(lambda w: shown(w) or (w.player is not None and w.player.mode not in ACTING), 2.5, THROUGH_POLL)
    if over is None or shown(over) or run.clock() - tapped > ONE_CAST:
        return  # its cast was seen, or the character cast for longer than the one cast that was under way
    taken = run.seen(
        lambda w: shown(w) or (w.player is not None and w.player.mode in ACTING), QUEUED_SECONDS, THROUGH_POLL
    )
    if taken is None:
        LOG.info(
            'Macro: the game did not keep the %s key pressed during the cast before: pressed again', skill_name(skill)
        )
        press_skill(run, skill, THROUGH_POLL)


def standable(ground: Ground, here: tuple[float, float], spot: tuple[float, float]) -> bool:
    """Whether a summon can be put at world `spot`: every unit of the straight way to it from the
    character is ground to walk on, as far as the level map knows (a spot behind a wall takes none)."""
    steps = max(1, math.ceil(math.dist(here, spot)))
    return all(
        ground.walkable(here[0] + (spot[0] - here[0]) * k / steps, here[1] + (spot[1] - here[1]) * k / steps)
        is not False
        for k in range(1, steps + 1)
    )


def cast(run: Run, skill: int) -> None:
    """A self or area cast with no known mark in memory yet: the cast animation is the evidence."""
    press_skill(run, skill)
    if run.seen(lambda w: w.player is not None and w.player.mode in ACTING, 0.8) is None:
        LOG.warning('Macro: no cast seen after %s', skill_name(skill))
    run.pause('key')


class LoadTrace:
    """Research: when each traced byte changed after Enter, logged once the first summon works."""

    def __init__(self, run: Run) -> None:
        self.run, self.started = run, run.clock()
        self.last: bytes | None = None
        self.changes: list[str] = []

    def __call__(self, world: World) -> None:
        if self.last is not None and world.trace != self.last and len(world.trace) == len(self.last):
            at = self.run.clock() - self.started
            self.changes += [
                f'{at:.2f}s {rva:#x} {old}->{new}'
                for rva, old, new in zip(TRACE_RVAS, self.last, world.trace, strict=True)
                if old != new
            ]
        self.last = world.trace

    def finish(self) -> None:
        self.run.observe = None
        LOG.info(
            'Macro: first summon %.2fs after Enter; byte changes: %s',
            self.run.clock() - self.started,
            '; '.join(self.changes[-60:]) or 'none',
        )


def swap_until(run: Run, in_hand: Callable[[], bool], tries: int = SWAP_TRIES) -> bool:
    """Press Swap Weapons until `in_hand()` says the wanted set is held, at most `tries` times, each
    given SWAP_WAIT to show. The game drops a swap pressed in the last moments of a cast or right after
    a teleport lands, though the character already reads as free (host, 2026-10-10 17:26: five swaps
    in one run pressed 0.05-0.4 s after a cast never came, each waited on for 1.2 s). A swap that came
    shows within 0.3 s, so a press that shows nothing in SWAP_WAIT was dropped and is made again."""
    settle(run)
    for tried in range(1, tries + 1):
        press_skill(run, SWAP_WEAPONS)
        deadline = run.clock() + SWAP_WAIT
        while True:
            run.world()  # a cancel stops here
            if in_hand():
                if run.pad is not None:
                    LOG.info('Pad swap: the weapons changed after %d presses of the key in controller mode', tried)
                return True
            if run.clock() >= deadline:
                break
            run.pace.sleep(0.03)
    if run.pad is not None:
        LOG.info('Pad swap: the weapons did not change after %d presses of the key in controller mode', tries)
    return False


def settle(run: Run, seconds: float = SWAP_SETTLE, limit: float = 1.0) -> None:
    """Wait until the character has read as free for `seconds` on end (`limit` at most): the first swap
    pressed right behind a cast was dropped more often than not (host, 17:46 on 2026-10-10: nine of
    eleven swaps took a second press, half a second each)."""
    began = free_since = run.clock()
    while True:
        world = run.world()
        now = run.clock()
        if world.player is None or world.player.mode in ACTING:
            free_since = now
        if now - free_since >= seconds or now - began >= limit:
            return
        run.pace.sleep(0.02)


def take_weapons(run: Run, wanted: frozenset[str], what: str, *, until: float | None = None) -> None:
    """Have the weapon set holding `wanted` (base codes) in hand, swapping if the other one is; it is
    left in hand afterwards. `until` (a clock time) keeps trying that long: a game that has just come up takes
    no input for a while. Nothing known to want, or the hands
    unreadable: nothing is done."""
    hands = run.hands
    if hands is None or not wanted:
        return

    def in_hand() -> bool:
        return bool(wanted & set(hands()))

    run.world()  # a cancel stops here
    if in_hand():
        return
    while not swap_until(run, in_hand):
        if until is None or run.clock() >= until:
            raise Abort(f'the {what} weapons are not in hand after a swap')
        run.pause('screen')
    run.pause('key')


def take_prebuff_weapons(run: Run, *, until: float | None = None) -> None:
    """The set the buffs are cast with in hand (user, 2026-10-06)."""
    take_weapons(run, run.prebuff_hands, 'prebuff', until=until)


def take_battle_weapons(run: Run) -> None:
    """The main set in hand: for a fight, and before a game is left (user, 2026-10-10: the other set
    is for teleporting only, and the character should not be saved holding it). A swap that does not
    come is logged, not a stop: the fight and the exit go on with what is held."""
    if run.hands is None or not run.battle_hands or not run.hands() or run.battle_hands & set(run.hands()):
        return
    try:
        take_weapons(run, run.battle_hands, 'main')
    except Abort as stop:
        if run.stops(stop):
            raise
        LOG.info('Macro: %s; going on with what is held', stop)


def prebuff(run: Run, *, fresh: LoadTrace | None = None) -> None:
    """The prebuff phase of the buff plan of the build the run plays (buffs.py `Buffs.prebuff`), with the
    weapon set its rows need in hand first: after a game just made (`fresh`) the first cast may have to wait
    for it to take input. A build with no prebuff row has nothing to cast, and that is the reason it stops with."""
    from inventory_tracking.macros.buffs import Buffs  # late: buffs.py is above this module

    buffs = Buffs(run.build)
    if not buffs.rows('prebuff'):
        raise Abort(f'nothing to prebuff: the build ({run.build.name}) has no prebuff of its own')
    buffs.prebuff(run, fresh=fresh)


def leave_game(run: Run) -> None:
    if run.pad is not None:  # the menus take the mouse's click (macros/pad.py `input_policy`)
        raise Abort('Save and Exit needs mouse mode: click once to switch, then press again')
    world = run.world()
    for _ in range(3):  # Escape closes an open panel first
        if not world.open_panels:
            break
        run.actuator.tap('Escape')
        run.pause('key')
        world = run.world()
    if world.open_panels:
        raise Abort(f'{world.open_panels[0]} stays open')
    take_battle_weapons(run)
    run.say('Save and Exit')
    run.actuator.tap('Escape')
    run.expect('quit menu', lambda w: w.quit_menu, 2)
    run.pause('screen')
    run.actuator.move(*SAVE_AND_EXIT, scatter=(60, 8))
    run.actuator.click()
    run.expect('leaving the game', lambda w: not w.in_game, 10)


def arrived(run: Run, where: str, *, loading: bool = False) -> None:
    """After a level change by a waypoint or a portal: wait until the game takes input, as a new game is waited for
    (`create_next_game`). `loading`: the view byte was seen at 0 since the click. The level is said playable when the
    byte comes back; a change that never shows a load waits ARRIVAL_SETTLE."""
    began = run.clock()
    if loading or run.seen(lambda w: w.view == 0, ARRIVAL_MARK) is not None:
        if run.seen(lambda w: w.view != 0, ARRIVAL_LIMIT) is None:
            raise Abort(f'{where}: the level did not come up in {ARRIVAL_LIMIT:g}s')
        LOG.info('Macro: %s: playable %.2fs after the arrival (its view byte)', where, run.clock() - began)
        return
    LOG.info('Macro: %s: no load shown; %gs for the game to take input', where, ARRIVAL_SETTLE)
    while run.clock() - began < ARRIVAL_SETTLE:
        run.world()
        run.pace.sleep(0.1)


def create_next_game(run: Run, last: str) -> LoadTrace:
    try:
        name = next_name(last)
    except ValueError as exc:
        raise Abort(str(exc)) from exc
    run.say(f'Creating {name}')
    # The name in memory is the lobby field's own text (record probe: it shrank and grew as the
    # user typed), so every edit is checked there. The lobby takes a moment to accept input and
    # nothing in memory says when (plan.md, R3): the first Backspace that shortens the name does.
    run.pause('screen')
    world = run.world()
    if world.in_game or world.game_name != last:
        raise Abort('not in the lobby')
    for _ in range(FIELD_ATTEMPTS):
        run.actuator.move(*GAME_NAME_FIELD, scatter=(25, 4))
        run.actuator.click()
        run.pause('key')
        run.actuator.tap('End')
        run.actuator.tap('BackSpace')
        if run.seen(lambda w: w.game_name == last[:-1], 0.6) is not None:
            break
        run.pause('screen')
        run.pause('screen')
    else:
        raise Abort('the game name field did not take the keys')
    # Only the end that differs is retyped (user, 2026-10-06): cyber36 -> one Backspace and `7`.
    kept = len(os.path.commonprefix((last, name)))  # ruff: ignore[os-path-commonprefix] two names, by character
    for _ in range(len(last) - kept - 1):
        run.pause('type')
        run.actuator.tap('BackSpace')
    run.expect('shortened game name', lambda w: w.game_name == last[:kept], 1)
    run.pause('key')
    run.actuator.type_text(name[kept:])
    run.expect(f'game name {name}', lambda w: w.game_name == name, 1)  # never Enter on another name
    run.pause('key')
    run.actuator.tap('Return')
    trace = LoadTrace(run)
    run.observe = trace
    # The game exists within a second or two of Enter; without it there is an error dialog
    # (host, 18:35 on 2026-10-06), which the macro leaves for the player.
    if run.seen(lambda w: w.in_game and w.game_name == name, CREATE_LIMIT) is None:
        raise Abort(f'{name} was not created (is there an error on screen?)')
    # The character and the town's units exist while the loading screen is still up. The view
    # byte (world.VIEW_RVA) is 0 while the game loads and comes back when it can be played. If
    # it never shows the loading at all, the measured LOAD_MIN from Enter stands in; either way
    # the first summon is tried until it appears (prebuff, `fresh`).
    marked = run.seen(lambda w: w.view == 0, 3) is not None
    run.expect('town', lambda w: w.player is not None and w.player.in_town and bool(w.monsters), 45)
    if marked:
        if run.seen(lambda w: w.view != 0, LOAD_LIMIT) is None:
            # 12:33 and 12:47 on 2026-10-11: the character stood in town the whole wait, both times with
            # the player in another window from the load on. Whether the byte waits for the focus is not known.
            away = '' if run.actuator.focused() else ' (the game window is not in front)'
            raise Abort(f'loaded game: not seen in {LOAD_LIMIT:g}s{away}')
    else:
        LOG.warning('Macro: no loading mark; waiting %ss from Enter', LOAD_MIN)
        while run.clock() - trace.started < LOAD_MIN:
            run.world()
            run.pace.sleep(0.1)
    LOG.info('Macro: game loaded %.2fs after Enter', run.clock() - trace.started)
    run.pause('screen')
    return trace


def character_keys(run: Run, key_names) -> dict[int, str]:
    """The keys of the prebuff for the character in the game, and its weapon sets noted for the run: those
    of the build the run plays (`Run.build`, which the runner has chosen by this look at the latest). A
    character whose build names no weapon sets (`Build.weapons`: no layer of its own) has no macro."""
    world = run.world()
    if world.player is None:
        raise Abort('not in a game')
    loadout = run.build.weapons
    if loadout is None:
        raise Abort(f'no macro for {world.player.name}')
    run.prebuff_hands = loadout.prebuff
    run.battle_hands = loadout.battle
    return key_names(world)


def run_ended(run: Run, world: World) -> bool:
    if world.player is None:
        return False
    if run.ending is not None and run.ending(world.player.area):
        # The route's bosses are dead and what is left is the loot and the leaving (user, 2026-10-13: Diablo
        # dead in the Chaos Sanctuary, and the request only cast the buffs).
        return True
    boss = BOSS_OF.get(world.player.area)
    if boss is not None and any(m.txt_id == boss for m in world.monsters):
        return False
    if world.player.area in BOSS_LEVELS and run.supers is not None:
        here = (world.player.x, world.player.y)
        seen = run.supers(world.player.area)
        near = [spot for spot in seen if math.dist(here, spot) <= BOSS_UNITS]
        LOG.info(
            'Macro: %d super uniques seen on level %d, %d within %.0f',
            len(seen),
            world.player.area,
            len(near),
            BOSS_UNITS,
        )
        return bool(near)
    if world.player.area in RUN_ENDS:
        return True
    if boss is not None:
        return False  # without the tracker's word on where he was seen: no leaving in the middle of the halls
    if world.player.area == CATACOMBS_4:
        return all(monster.txt_id != ANDARIEL for monster in world.monsters)
    if world.player.area == TOWER_CELLAR_5:
        return not any(m.txt_id == COUNTESS and m.flags & SUPER_UNIQUE_FLAG for m in world.monsters)
    if world.player.area != PANDEMONIUM_FORTRESS or run.arrival is None:
        return False
    previous, seconds = run.arrival()
    LOG.info('Macro: in the Fortress, %.0fs after level %s', seconds, previous)
    return previous in ACT_3 and seconds <= ARRIVAL_SECONDS


def run_macro(run: Run, key_names) -> None:
    """`key_names(world)` gives the key per skill for the character in the game (skills.py)."""
    world = run.world()
    if not world.in_game and run.pad is not None:  # the lobby's name field takes the mouse's click
        raise Abort('a new game needs mouse mode: click once to switch, then press again')
    if not world.in_game:
        # The lobby (user, 2026-10-06): make the next game and prebuff. Which character it is
        # shows only in the game, so it and its keys are checked there, before any skill key.
        # On any other screen out of a game the name field never answers and the macro stops.
        run.actuator.wait_released()
        trace = create_next_game(run, world.game_name)
        run.keys = character_keys(run, key_names)
        prebuff(run, fresh=trace)
    else:
        run.keys = character_keys(run, key_names)
        run.actuator.wait_released()
        if run_ended(run, world):
            leave_game(run)
            trace = create_next_game(run, world.game_name)
            if key_names(run.world()) != run.keys:
                raise Abort('the skill keys changed')
            prebuff(run, fresh=trace)
        else:
            prebuff(run)
    run.say('Prebuff done')
