"""The Lower Kurast loop: KP_6 plays games until it is toggled off (routes/lower-kurast-loop-plan.md phase 4).

The loop is a state machine read from where the character is, so it goes on from any point (`next_leg`): one leg a
run of the runner's (macros/runner.py LOOP), the next chosen when it is over. The legs are the routines built for
them: the next game and its prebuff (routines.py), the waypoint (waypoint.py), the KP_1 level run for the chests
(pursuit.py, run as attack mode: the runner starts it and comes back here when it ends), the pickup of what is left,
the portal (portal.py), Save and Exit. The player, 2026-10-16: games end in act 4 (portal → Kurast Docks → waypoint
→ Pandemonium Fortress → Save and Exit), where the next game starts by its waypoint.

A leg that `Abort`s (a place the loop has no leg for, a leg made again and again in one game with nothing coming of
it: `REPEATS`) or a game that lasts over GAME_SECONDS is recovered from by leaving the game (`recover`, `abandon`): the
player, 2026-10-17: "we should try to not stuck in some weird situation without being able to fix it from agent". It
stops by itself, saying why (`Macro: loop stopped: …`), with the character dead (`Dead`) and after RECOVERIES
recoveries within RECOVERY_SECONDS.
"""

import json
import math
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.levels.presets import display_name
from inventory_tracking.loot.runes import RUNES as RUNE_CLASSES
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import SURE_BLOCK, inventory_rows, loot, overflow, own_of, room_for, roomed
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.junk import MAGIC
from inventory_tracking.macros.portal import to_town
from inventory_tracking.macros.repair import (
    ENABLED,
    RETRY_GAMES,
    WEAR_CARRIED,
    affordable,
    back,
    gold,
    repair,
    unknown,
    wants,
    worn_out,
    worn_text,
)
from inventory_tracking.macros.routines import DEAD, character_keys, create_next_game, leave_game, prebuff
from inventory_tracking.macros.shop import SALE_MOST, gold_cap, restock, short
from inventory_tracking.macros.stash import INVENTORY_CELLS
from inventory_tracking.macros.waypoint import travel
from inventory_tracking.macros.world import Carried, World
from inventory_tracking.routes.model import LOOT, USE
from inventory_tracking.routes.progress import Progress


__all__ = ['LOWER_KURAST', 'Dead', 'Loop', 'next_leg']

KURAST_DOCKS, LOWER_KURAST, PANDEMONIUM_FORTRESS = 75, 79, 103
# The legs, as the HUD says them.
NEXT_GAME = 'next game'
SHOP = 'scrolls and keys'
REPAIR = "the staff's charges"
TO_THE_CHESTS = 'to Lower Kurast'
CHESTS = 'the chests'
PICK_UP = 'what is left'
PORTAL = 'Town Portal'
TO_THE_FORTRESS = 'to Pandemonium Fortress'
LEAVE = 'Save and Exit'
STASH = 'the stash'  # the trade session's second visit: the cube emptied once the sales made room
IDENTIFY = 'identify'  # the loop's items identified at Deckard Cain, appraised (macros/cain.py, macros/junk.py)
# How often one leg may be made in one game before the loop gives up on it: a pickup a drop at a time, the level run
# again after it stopped short, any other leg once more after a failure that left the character where it was.
REPEATS = {PICK_UP: 20, CHESTS: 3}
REPEAT = 2
# A game longer than this is left (a game takes 40-75 s, 2026-10-17); a leg's stop or such a game is recovered from
# by leaving the game at most RECOVERIES times in RECOVERY_SECONDS, then the loop stops
FULL_FILE = 'full-stacks.json'
# The trade (routes/lower-kurast-loop-plan.md §15; the player, 2026-10-17: "we need to perform mass identify at decard
# cain -> stash good -> sell junk -> return to loop"; then "probably we need to trade not by 2 junk items, but by
# remaining free slots"): the loop's unidentified items and its junk wait, in the inventory and the cube, until fewer
# than TRADE_ROOM cells are free in both together (a 2 x 4 shield, the largest candidate, fits nowhere); then the whole
# session at once: Cain identifies all, the stash beside him takes the keepers, Jamella buys all the junk. A visit to
# her made anyway for keys and scrolls sells what is carried too. (Counted by items before, 3 then 4 to Cain, 2 then 3
# to her: Cain nearly every game for one item, the trade ~6.8 s a cycle, 12:00-12:30 on 2026-10-17.)
TRADE_ROOM = 8
SELL_PASSES = 4  # the cube's junk out and sold, pass after pass, as the inventory's room allows
GAME_SECONDS = 240.0
LOADING_SECONDS = 10.0  # for a game's character to be read after it shows as in a game
# The character not moving STILL_SECONDS in a game, by STILL_UNITS, is the loop stuck too (the level run stood by a
# Flawless Diamond with the inventory full from 01:15:03 on 2026-10-17, the player's "we stuck, but didn't detect it
# in time"): the longest stand in a good game is a shop visit, under 15 s
STILL_SECONDS = 45.0
STILL_UNITS = 2.0
RECOVERIES = 3
RECOVERY_SECONDS = 600.0


class Dead(Abort):
    """The character is dead: the loop stops for the player."""


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
    # The loop's items still carried, by class and cell, kept from one KP_6 to the next and in `store` (by the
    # character's name) from one service to the next: an item the loop left in the inventory, the cube full, is still
    # the loop's when it starts again, not the player's (the player, 2026-10-16: "moving items to the cube from
    # inventory - seems not working. or working not always")
    mine: frozenset[tuple[int, int, int]] = frozenset()
    store: Path | None = None
    # The keys or the Town Portal charges under shop.py MIN_STOCK at the last leg's look: Jamella first (phase 8)
    short: bool = False
    # The game is to be left from wherever the character is (`recover`), and when the recoveries were
    abandon: bool = False
    recovered: list[float] = field(default_factory=list)
    # The game (None: the lobby) the loop was last seen in, and since when (`overdue`)
    seen: tuple[str | None, float] | None = None
    # The level card's marks by label, in tiles (levels/guide.py `marks`): the town's waypoint out of sight
    marks: Callable[[str], tuple[tuple[float, float], ...]] | None = None
    # The resource classes whose stash stack is full (99: the player, 2026-10-17, "we have 99 tal runes and cannot add
    # more. probably we better just sell them (and other runes that will have 99)"), kept in FULL_FILE beside `store`:
    # not picked up, and those carried are sold at Jamella (`selling`, shop.py `restock`)
    full: set[int] = field(default_factory=set)
    selling: tuple[Carried, ...] = ()
    # The staff's Teleport in the loop's moves (`teleports`): while the gold carried pays for it
    teleports: bool | None = None  # None: not decided since the start (`teleports`)
    capped: bool = False  # the gold carried too near its cap for a sale, at the last look (`leg`)
    wear: str = '?'  # the most worn item's durability at the last look (`leg`), for the log

    @property
    def sold_full(self) -> frozenset[int]:
        """The full stacks' classes that are not picked up and are sold: the runes alone. The ruling was the runes'
        ("other runes that will have 99"); a Flawless Amethyst whose stack was full was left on the ground twice, the
        player: "we just left flawlest amethyst and left the game. something is wrong" (15:19 on 2026-10-17). A gem
        of a full stack is picked up and kept carried, not sold, until the player rules on it."""
        return frozenset(txt for txt in self.full if txt in RUNE_CLASSES)

    # The staff's charges low enough for Halbu's repair (macros/repair.py `wants`), and the game count of a visit that
    # did not raise them (none tried again for RETRY_GAMES games)
    repair: bool = False
    repair_failed: int | None = None
    # A valuable the inventory has no room for, stood by: the loop's items go into the cube at the next leg
    # (`make_room`), once a game (`room_tried`, the game's name), before the loop stops for the player
    make_room: bool = False
    room_tried: str | None = None
    # Then one of the loop's items taken only to identify it dropped for the valuable's block (macros/cube.py
    # `drop_for`), once a game (`dropped`), before the loop stops for the player
    drop_room: bool = False
    dropped: str | None = None
    # The trade (MASS): the loop's items in the inventory and the cube the appraisal calls junk (macros/junk.py
    # `junk_of`, judged at each look in the fortress) and the unidentified ones; the game of the last visit to Cain and
    # to Jamella (each once a game); the inventory cells free at the last look; the stash's next visit made whatever
    # its room (the keepers, after Cain)
    junk: tuple[Carried, ...] = ()
    unknown: tuple[Carried, ...] = ()
    identified: str | None = None
    shopped: str | None = None
    free: int | None = None
    carrying: bool = False  # the loop's items in the inventory or the cube at the last look: a session has work
    reported: str | None = None  # the game whose trade session's state was said (`report`)
    cubed: bool = False  # the loop's items in the cube at the last look (the session's contract: an empty cube)
    restashed: str | None = None  # the game of the session's second visit to the stash (`STASH`)
    stash_now: bool = False
    waiting: bool = False  # for the game window's focus (runner.py): the watchdogs pause
    moved: tuple[tuple[float, float], float] | None = None  # where the character last moved to, and when (`still`)

    def start(self) -> None:
        self.full |= self._full_stored()
        self.on, self.made, self.own, self.abandon, self.seen, self.moved = True, Counter(), None, False, None, None

    def recover(self, why: object, now: float) -> bool:
        """Whether the loop goes on after `why` stopped a leg, by leaving the game: not with the character dead,
        nor after RECOVERIES recoveries within RECOVERY_SECONDS."""
        if isinstance(why, Dead):
            return False
        self.recovered = [at for at in self.recovered if now - at < RECOVERY_SECONDS]
        if len(self.recovered) >= RECOVERIES:
            return False
        self.recovered.append(now)
        self.abandon = True
        return True

    def overdue(self, game: str | None, now: float) -> bool:
        """Whether the loop has been in `game` (None: the lobby) over GAME_SECONDS, seen now."""
        if self.seen is None or self.seen[0] != game:
            self.seen = (game, now)
            return False
        return now - self.seen[1] > GAME_SECONDS and not self.abandon

    def still(self, where: tuple[float, float] | None, now: float) -> bool:
        """Whether the character, at `where` now, has stood within STILL_UNITS for over STILL_SECONDS."""
        if where is None:
            return False
        if self.moved is None or math.dist(where, self.moved[0]) > STILL_UNITS:
            self.moved = (where, now)
            return False
        if now - self.moved[1] > STILL_SECONDS and not self.abandon:
            self.moved = (where, now)  # once: the next stand counts afresh
            return True
        return False

    def stop(self) -> None:
        self.on = False

    def sort(self, held: frozenset[tuple[int, int, int]], name: str | None) -> None:
        """The carried items `held` told apart: at the loop's first look the player's are what is not the loop's
        (`mine`, read from `store` for the character `name`); then the loop's are what is not the player's."""
        if self.own is None:
            self.mine = self.mine or self._stored(name)
            self.own = held - self.mine
        mine = held - self.own
        if mine != self.mine:
            self.mine = mine
            self._keep(name)

    def walks_back(self, game: str) -> bool:
        """Whether the walk toward the waypoint follows a visit to Halbu: not with Jamella next (she stands 34 units
        off), nor when the game is left from there: a new game starts by its waypoint anyway (18:04:54 on 2026-10-17:
        8.6 s walked back before Save and Exit). The stash again for the cube's keepers is by the waypoint."""
        leaving = self.done == game and (self.restashed == game or not self.cubed)
        return not self.shop_next(game) and not leaving

    def shop_next(self, game: str) -> bool:
        """Whether Jamella is still to be visited in `game` (keys or scrolls short, or the session's sales): after Halbu
        the loop goes to her, not back to the waypoint first (the player, 2026-10-17: "we repaired staff -> walked to
        wp -> walked to jamella")."""
        return self.shopped != game and (self.short or (self.identified == game and bool(self.junk or self.selling)))

    def report(self, run: Run, game: str, pack, staff) -> None:
        """Once a session's legs are done (this game's, `identified`), what it left, as the player's contract has it
        (the player, 2026-10-17: "we must go to LK with all refilled and empty cube and free inventory slots"): the
        loop's items still in the cube, the inventory's free cells, the junk left, keys, scrolls, the staff's
        charges."""
        if self.identified != game or self.reported == game or self.own is None:
            return
        self.reported = game
        now = run.carried() if run.carried is not None else pack
        if now is None:
            return
        free = INVENTORY_CELLS - sum(item.size[0] * item.size[1] for item in now.items)
        left = [i for i in loot(now, self.own) if i.unit_id in {j.unit_id for j in self.junk}]
        charges = f'{staff.charges}/{staff.maximum}' if staff is not None else '?'
        whole = not now.in_cube and not left and not self.short
        LOG.info('Macro: trade session done%s: cube %d items, %d inventory cells free, junk left %d, keys %s, '
                 'portals %s, staff %s', '' if whole else ' (short of the contract)', len(now.in_cube), free,
                 len(left), now.keys, now.portals, charges)  # fmt: skip

    def _full_stored(self) -> set[int]:
        if self.store is None:
            return set()
        try:
            return {int(txt) for txt in json.loads((self.store.parent / FULL_FILE).read_text())}
        except OSError, ValueError, TypeError:
            return set()

    def keep_full(self) -> None:
        """`full` into FULL_FILE."""
        if self.store is None:
            return
        try:
            (self.store.parent / FULL_FILE).write_text(json.dumps(sorted(self.full)))
        except OSError as error:
            LOG.info('Macro: the full stacks are not kept: %s', error)

    def _stored(self, name: str | None) -> frozenset[tuple[int, int, int]]:
        if self.store is None or name is None:
            return frozenset()
        try:
            rows = json.loads(self.store.read_text()).get(name, [])
            return frozenset((int(txt), int(x), int(y)) for txt, x, y in rows)
        except OSError, ValueError, TypeError, AttributeError:
            return frozenset()

    def _keep(self, name: str | None) -> None:
        if self.store is None or name is None:
            return
        try:
            kept = json.loads(self.store.read_text()) if self.store.exists() else {}
            kept[name] = sorted(self.mine)
            self.store.write_text(json.dumps(kept))
        except (OSError, ValueError, TypeError, AttributeError) as error:
            LOG.info("Macro: the loop's items are not kept in %s: %s", self.store, error)

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
        stash: Callable[..., int] | None = None,
        identify: Callable[[tuple[Carried, ...]], object] | None = None,
        judge: Callable[[list[Carried]], list[Carried]] | None = None,
        bring: Callable[[list[Carried]], int] | None = None,
        arrange: Callable[[], object] | None = None,
    ) -> str:
        """Make the next leg (`next_leg`); the leg made. `level_run()` asks the runner for the KP_1 level run,
        which follows this leg; `pick_up()` takes one drop, False with nothing worth it on the ground; `stash(own)`
        moves the loop's items into the stash and the cube (macros/stash.py, macros/cube.py), `own` the inventory as the
        player keeps it, `keep` the units that stay (unidentified, junk), `force` whatever the room; `identify(items)`
        identifies the loop's `items` (at Cain, macros/cain.py); `judge(items)` says the junk among them (macros/junk.py
        `junk_of`); `bring(items)` takes items out of the cube into the inventory (macros/cube.py `unpack`);
        `arrange()` moves a key stack where the free cells make the largest block, once a session (macros/cube.py
        `arrange_keys`)."""
        world = run.world()
        if world.in_game and world.player is None:
            # A game still loading: its character not read yet. Waited for, not a leg's stop: three recoveries in 20 ms
            # from it stopped the loop (12:45:41 on 2026-10-17, "not in a game")
            world = run.seen(lambda w: w.player is not None or not w.in_game, LOADING_SECONDS) or run.world()
        if not world.in_game:
            self.abandon = False  # left
        pack = run.carried() if world.in_game and run.carried is not None else None
        self.short = short(pack)
        items = loot(pack, self.own) if pack and self.own else []
        in_town = world.player is not None and world.player.area == PANDEMONIUM_FORTRESS
        if pack is not None and self.own is not None:  # unread in the lobby: the last look's stand
            carried = [*items, *pack.in_cube]
            cube = roomed(pack).cube or ()
            in_inventory = INVENTORY_CELLS - sum(item.size[0] * item.size[1] for item in pack.items)
            in_cube = sum(row.count('.') for row in cube)
            self.free = in_inventory + in_cube  # the cube's room too: the trade waits until both are full
            if in_inventory < TRADE_ROOM and overflow(pack, self.own):
                # The cube's room in pieces none of the loop's items fits ('.#./.#./.#./...': 9 cells, two items
                # stayed out, the inventory full, a Rage Mask left, 12:44-12:45 on 2026-10-17): no room as such
                self.free = min(self.free, in_inventory)
            if not any(rows and room_for(rows, SURE_BLOCK) for rows in (inventory_rows(pack), cube)):
                # No SURE_BLOCK free in the inventory nor in the cube, whatever the cells count: no room as such
                self.free = min(self.free, TRADE_ROOM - 1)
            if in_town and self.free < TRADE_ROOM:
                # The trade's trigger told (a second session one game after a full one, 14:15 on 2026-10-17)
                LOG.info('Macro: loop: room low: %d cells free (inventory %d, cube %d, loop items %d in the inventory '
                         'and %d in the cube; cube rows %s)', self.free, in_inventory, in_cube, len(items),
                         len(pack.in_cube), '/'.join(cube))  # fmt: skip
            self.carrying = bool(items) or bool(pack.in_cube)
            self.cubed = bool(pack.in_cube)
            session = self.identified == (world.game_name if world.in_game else '') or self.free < TRADE_ROOM
            if in_town and in_inventory < TRADE_ROOM and in_cube >= 3 and items and not session:
                # the loop's items into the cube (the runner's `make_room`, no walk): the inventory's room for pickups,
                # between sessions only (in one it moved the session's junk into the cube, 13:03 on 2026-10-17)
                self.make_room = True
            self.unknown = tuple(i for i in carried if not i.identified and i.quality >= MAGIC)
            if in_town and judge is not None:
                self.junk = tuple(judge([i for i in carried if i.identified]))
        junked = {i.unit_id for i in self.junk}
        self.selling = tuple(i for i in items if i.txt in self.sold_full or i.unit_id in junked)
        keep = frozenset(i.unit_id for i in self.unknown) | junked
        staff = run.teleport() if world.in_game and run.teleport is not None else None
        waited = self.repair_failed is None or self.games - self.repair_failed >= RETRY_GAMES
        # His line learned first, his panel only opened (no gold spent) while repairs are off (macros/repair.py)
        in_session = world.in_game and self.identified == world.game_name
        # In a trade session any charge missing is repaired if the carried gold covers it (the player, 2026-10-17: "we
        # must go to LK with all refilled"); else under REPAIR_BELOW of them
        topped = tops_up(staff, in_session, self.reported == world.game_name)
        # A worn item low on durability: a repair of its own, the staff's charges full (Teleport of the character's own)
        wear = run.wear() if world.in_game and run.wear is not None else None
        self.wear = worn_text(wear)
        worn = worn_out(wear)
        coins = gold(run) if (staff is not None and (wants(staff) or topped)) or worn else None
        # Near the gold cap no sale is made (shop.py `restock`): the repair goes first then (`next_leg`)
        cap = gold_cap(run) if coins is not None else None
        self.capped = coins is not None and cap is not None and coins + SALE_MOST > cap
        charged = (wants(staff) or topped) and affordable(coins)
        mends = worn and coins is not None and coins >= WEAR_CARRIED
        self.repair = (charged or mends or ((staff is not None or wear is not None) and unknown())) and waited
        if pack is not None:
            self.sort(own_of(pack.items), world.player.name if world.player is not None else None)
        leg = next_leg(world, progress, self)
        game = world.game_name if world.in_game else ''
        self.count(world, leg)
        run.say(f'Loop: game {self.games + 1}, {leg}')
        if leg != NEXT_GAME:
            run.keys = character_keys(run, key_names)  # Swap Weapons among them: the arrival's check (`arrived`)
        if leg == NEXT_GAME:
            trace = create_next_game(run, world.game_name)
            run.keys = character_keys(run, key_names)
            prebuff(run, fresh=trace)
            self.prebuffed = run.world().game_name
        elif leg == SHOP:
            self.shopped = game
            cubed = [i for i in self.junk if pack is not None and i.unit_id in pack.cube_items]
            if cubed and bring is not None and self.own is not None and bring(cubed):
                # The cube's junk out before her window opens, as much as the room takes: one window sells it all (a
                # second pass opened it again, ~6 s: the player, 2026-10-17, "we spend a lot of time just to open
                # trade window")
                after = run.carried() if run.carried is not None else None
                if after is not None:
                    self.selling = tuple(
                        i for i in loot(after, self.own) if i.txt in self.sold_full or i.unit_id in junked
                    )
                    cubed = [i for i in cubed if i.unit_id in after.cube_items]
            if self.selling:
                LOG.info('Macro: loop: %s cells free: %d items sold', self.free, len(self.selling))
            # at a game's end the game is left from her: no walk back to the waypoint, and Save and Exit begins with the
            # character standing (a run back still under way spoilt it at 11:42:32 on 2026-10-17)
            # Not back to the waypoint with Halbu next: he stands 34 units from her, the waypoint west of both (the
            # player, 2026-10-17: "we repaired staff -> walked to wp -> walked to jamella")
            restock(run, self.selling, back=self.done != game and not cubed and not self.repair)
            for _ in range(SELL_PASSES):
                # The cube's junk out into the room the sales made, then sold too (the player: "both from cube and
                # inventory"); taken out first, a Grand Charm found no room and stayed (12:13:06 on 2026-10-17); as
                # much as the room takes each pass (one of four at 12:54:10)
                if not cubed or bring is None or self.own is None or not bring(cubed):
                    break
                after = run.carried() if run.carried is not None else None
                rest = tuple(i for i in loot(after, self.own) if i.unit_id in junked) if after is not None else ()
                if not rest:
                    break
                restock(run, rest, back=False)
                sold = {i.unit_id for i in rest}
                cubed = [
                    i for i in cubed if i.unit_id not in sold and after is not None and i.unit_id in after.cube_items
                ]
        elif leg == REPAIR:
            try:
                if not repair(run, fix=ENABLED) and ENABLED and affordable(gold(run)):
                    self.repair_failed = self.games  # not for want of gold: something else, not again for a while
            except Abort as stop:
                LOG.info('Macro: repair: %s: not tried again for %d games', stop, RETRY_GAMES)
                self.repair_failed = self.games
            self.repair = False
            if self.walks_back(game):
                back(run)
        elif leg in (TO_THE_CHESTS, LEAVE):
            if arrange is not None and self.identified == game and self.reported != game:
                try:
                    arrange()
                except Abort as stop:
                    LOG.info('Macro: inventory: the keys not arranged: %s', stop)
            self.report(run, game, pack, staff)
        if leg == TO_THE_CHESTS:
            # The carried gold once a game: the repairs' and the sales' (the player, 2026-10-17: "just use gold in the
            # inventory")
            coins = gold(run)
            LOG.info('Macro: loop: gold carried %s, the most worn item %s', coins, self.wear)
            self.teleports = teleports(coins, gold_cap(run), self.teleports)
            if stash is not None and self.own is not None:
                # What the loop carries goes into the stash first (none: nothing is walked to): a game begun with the
                # inventory full stood by a drop it had no room for (01:15 on 2026-10-17)
                stash(self.own, keep, self.stash_now)  # the unidentified and the junk stay
                self.stash_now = False
                self.keep_full()
            if self.prebuffed != game:
                prebuff(run)
                self.prebuffed = game
            travel(run, LOWER_KURAST, self.marks)
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
            travel(run, PANDEMONIUM_FORTRESS, self.marks)
        elif leg == STASH:
            self.restashed = game
            if stash is not None and self.own is not None:
                stash(self.own, keep, True)  # the cube's keepers out into the room the sales made, into the stash
        elif leg == IDENTIFY:
            self.identified = game
            # The session ends at Jamella even after a visit for keys this game (12:48:41 on 2026-10-17: keys first,
            # then the session, its junk left unsold)
            self.shopped = None
            if identify is not None:
                if self.unknown:
                    identify(self.unknown)
                # The keepers into the stash at once: it stands beside Cain (5019, 5040; he at 5023, 5033), out of
                # sight from Jamella's (12:13:16 on 2026-10-17); the junk and what is still unidentified stay
                after = run.carried() if run.carried is not None else None
                if stash is not None and self.own is not None and after is not None:
                    carried = [*loot(after, self.own), *after.in_cube]
                    self.junk = tuple(judge([i for i in carried if i.identified])) if judge is not None else ()
                    waiting = {i.unit_id for i in carried if not i.identified and i.quality >= MAGIC}
                    stash(self.own, frozenset(waiting | {i.unit_id for i in self.junk}), True)
                    self.keep_full()
        elif leg == LEAVE:
            in_town = world.player is not None and world.player.area == PANDEMONIUM_FORTRESS
            if stash is not None and self.own is not None and in_town:
                stash(self.own, keep, self.stash_now)  # the loop's items into the stash or the cube, before it is left
                self.stash_now = False
                self.keep_full()
            leave_game(run)
            self.abandon = False
            self.games += 1
        return leg


# Shares of the gold cap: Teleport from the first, Blade Warp alone under the second. 0.6/0.3 left it off for long
# stretches: a session's sales (~40-100k) pay less than its repairs (~85k), and the gold has no other use in the loop
# (the player, 2026-10-17: "if we make enough gold - we can use teleport staff more often"). Off under 15% (141,000
# at level 94: a full repair, ~118,000, is still paid from it)
TELEPORT_ON, TELEPORT_OFF = 0.35, 0.15
GOLD_CAP = 990_000  # the cap at level 99, for a level unread


DEPOSIT_NEAR = 2 * SALE_MOST  # gold this near the cap is deposited at the stash (macros/stash.py `deposit`)
DEPOSIT_ROOM = 250_000  # down to the cap less this: room for a session's sales, Teleport still on (TELEPORT_ON)


def deposit_to(coins: int | None, cap: int | None) -> int | None:
    """The carried gold to keep when the stash is open, None for no deposit: near the cap a sale drops the gold over it
    on the ground (the player, 2026-10-17: "probably we need to move extra gold to our cube [stash]")."""
    if coins is None or cap is None or coins < cap - DEPOSIT_NEAR:
        return None
    return cap - DEPOSIT_ROOM


def tops_up(staff, in_session: bool, reported: bool) -> bool:
    """Whether a trade session repairs any charge missing (the player, 2026-10-17: "we must go to LK with all
    refilled"): only until it is done (`Loop.report`); one done at a game's start sent the loop to Halbu again at the
    game's end for 5 charges, ~8 s (15:48:43 on 2026-10-17)."""
    return staff is not None and in_session and not reported and staff.charges < staff.maximum


def teleports(coins: int | None, cap: int | None, now: bool | None) -> bool | None:
    """Whether the loop's moves take the staff's Teleport this game (travel.py LOOPED_TELEPORT): from TELEPORT_ON of
    the gold cap carried, until under TELEPORT_OFF of it; as it was, with the gold unread. With charges, ~7 a cycle
    (~11,900 gold), it spends about twice what the sales bring: the gold over the cap would fall to the ground at a sale
    (the player, 2026-10-17: "if we make enough gold - we can use teleport staff more often to speed up things")."""
    if coins is None:
        return now
    most = cap or GOLD_CAP
    if now is None:
        # The first look since a start: on over TELEPORT_OFF. Each restart began it off, and at 527,000-588,000 carried
        # (under TELEPORT_ON) 12 of 24 stays were made without it, 32.9 s against 26.0 (16:40-16:50 on 2026-10-17)
        now = coins >= TELEPORT_OFF * most
        LOG.info(
            'Macro: loop: %d gold carried of %d: %s',
            coins,
            most,
            'Teleport in the moves' if now else 'Blade Warp alone',
        )
        return now
    if coins >= TELEPORT_ON * most:
        if not now:
            LOG.info('Macro: loop: %d gold carried of %d: Teleport in the moves', coins, most)
        return True
    if coins < TELEPORT_OFF * most:
        if now:
            LOG.info('Macro: loop: %d gold carried of %d: Blade Warp alone', coins, most)
        return False
    return now


def next_leg(world: World, progress: Progress | None, loop: Loop) -> str:
    """The leg the loop makes next from where the character is; `Abort` where it has none."""
    if not world.in_game:
        return NEXT_GAME
    player = world.player
    if player is None:
        raise Abort('not in a game')
    if player.mode in DEAD:
        raise Dead('the character is dead')
    if loop.abandon:
        return LEAVE
    if player.area == PANDEMONIUM_FORTRESS:
        game = world.game_name
        # The trade session (TRADE_ROOM), once a game when the room is low and the loop carries anything: Cain if there
        # is anything to identify, the stash (keepers, resources), Jamella (junk, keys, scrolls); the repair as ever.
        # The player, 2026-10-17: "we should aim for runs where identifying is triggered: we moved all good to our
        # chest, moved all resources, sold all junk, refill tp/keys, repaired staff if we can afford it; thus -> have
        # full cube free slots + some free inventory slots"; "we do not need to go cain every game"
        cramped = loop.free is not None and loop.free < TRADE_ROOM
        # Any errand to a vendor is the whole session: the room low, keys or scrolls short, the staff to repair (the
        # player, 15:52 on 2026-10-17: "when we get to maintenance (refilling, trading, repairing) - it is better to
        # identify everything, stash good, sell junk, refill, optionally repair ... right now we're running between
        # vendors/stash/waypoint with items that could be already 10 times sold"). At a game's end the room alone:
        # a refill or a repair waits for the next game's start, as before
        errand = cramped or (loop.done != game and (loop.short or loop.repair))
        if errand and loop.carrying and loop.identified != game:
            return IDENTIFY
        to_sell = len(loop.junk) + sum(1 for i in loop.selling if i.txt in loop.sold_full)
        # a batch, or what there is when the room is low; a visit made anyway (`short`) sells it all too
        batch = loop.shopped != game and to_sell > 0 and (cramped or loop.identified == game)
        # The session's contract (an empty cube): the stash again when the sales have made room for the cube's keepers
        # (13:15:47 on 2026-10-17: three stayed in the cube, the inventory full of the junk still to sell)
        if loop.identified == game and loop.shopped == game and loop.cubed and loop.restashed != game:
            # Halbu first when he is due: he stands by Jamella, the stash by the waypoint, west (the session of 16:54 on
            # 2026-10-17 went Jamella, the stash, Halbu, across the fortress and back)
            return REPAIR if loop.repair else STASH
        if batch and loop.repair and loop.capped:
            # The gold near its cap, no sale is made: the repair first, its cost the sales' room (15:33:27 on
            # 2026-10-17: three items kept at 908,518 of 940,000, then the repair spent 39,237)
            return REPAIR
        if loop.done == game:
            if batch:
                return SHOP
            # a session at a game's end repairs before the game is left (the contract: "all refilled")
            return REPAIR if loop.repair and loop.identified == game else LEAVE
        if loop.short or batch:
            return SHOP
        return REPAIR if loop.repair else TO_THE_CHESTS
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
