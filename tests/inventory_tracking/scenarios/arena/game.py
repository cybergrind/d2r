"""The arena: the scripted game of the macro tests (macros/fakes.py `Game`) made into a world that
answers back (framework-plan.md, Task 1.5; architecture.md §6).

`Game` already does what the macro's inputs do to the game: hops with their charge, Blade Warp, the
cast under a held strike with its cadence, the Quick Cast queue, the belt keys, the swap, walks,
drops and the hover record. `Arena` is that game set up from a `Scene`, with what a fight needs on top:

- time: the clock's `sleep` plays whole game ticks (GAME_RATE a second), the rest of a sleep is kept;
- the monsters are `Mobs` (mobs.py, the production monster model), ticked with the clock; what the
  macro reads as monsters, the dead and the corpses is theirs;
- each tick's blows come off the character's life, cut by the resistances of the weapon set in hand;
- a cast of the strike is the production blades (the build's mechanics.py `cast`, the
  contact radius, the duplicate rule, damage.json's points a contact), as scenarios/revivers/harness.py
  and scenarios/stance/harness.py apply them, on `Mobs.hit`; with the `attack` of another build
  (macros/build.py `Attack`) a cast of its skill takes what its `dealt` says, at once, on `Mobs.hit`;
- a belt key drinks by potions.json: a rejuvenation at once, a healing potion over its frames;
- at life 0 the character lies dead (native/layout.py CORPSE_MODE) and the world stands still;
- with a `HealingConfig` the standalone healer runs beside the macro: production `HealController`
  over production `PotionsController`, each tick, on the arena's life and belt (`Healer`);
- the scene's ground and doors are real: no hop, warp or walk ends where nobody can stand, no walk
  goes where no way leads, and walls stop the blades.

What the arena does not model, or takes as given (the calibration of Task 1.9 needs the list):

- a walk is over in the instant of its click, as in `Game`: the character is never seen running, and
  loses no time and takes no blow on the way. A hop and a Blade Warp land at once too;
- the strike deals the same with either weapon set (damage.json knows no set), Death Mark, Sigil:
  Lethargy, Engorge, Hex: Purge, Psychic Ward and Consume change nothing (their casts are counted by
  `Game` and cost their cast time), and the companions deal no damage;
- the blades return to where the character stood at the cast (as both harnesses), and a blade's
  focal point is the ground under the pointer at the cast's start;
- mana is not counted (combat/data/damage.json: the recorded mana never limited casting);
- the character's blows are never blocked, dodged or missed beyond what `Mobs` rolls, and it has no
  hit recovery: a blow never interrupts a cast;
- doors stand as the scene has them; nothing drops from a kill; a monster under the pointer is not in
  the hover record (only drops are);
- the healer sees this tick's life and belt (the real one samples them with a delay), and its key
  is down and up within the tick, so the macro never sees it held;
- RIGHT_SKILL, the potion a picked-up one lands on (`stow`), the staff's full charges and the sizes
  of drops are assumptions, said where they are set.
"""

import json
import math
import random
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path

from inventory_tracking.automation.heal import HealController
from inventory_tracking.automation.ledger import LedgerData
from inventory_tracking.automation.potions import PotionsController
from inventory_tracking.builds.warlock.echoing_strike.attack import DUPLICATE
from inventory_tracking.builds.warlock.echoing_strike.damage import damage_table
from inventory_tracking.builds.warlock.echoing_strike.hits import CONTACT_RADIUS
from inventory_tracking.builds.warlock.echoing_strike.mechanics import LIFE, OUT_FRAMES, cast
from inventory_tracking.builds.warlock.echoing_strike.sim.input import BIRTH_LAG
from inventory_tracking.builds.warlock.skills import BLADE_WARP, ECHOING_STRIKE
from inventory_tracking.combat.policy import Foe, walls
from inventory_tracking.combat.stance import no_footing, way
from inventory_tracking.combat.timeline import GAME_RATE
from inventory_tracking.config import INPUT, HealingConfig
from inventory_tracking.input import Refused
from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.model import Ground, Walkable
from inventory_tracking.macros.build import Attack
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.skills import SWAP_WEAPONS, TELEPORT
from inventory_tracking.macros.travel import walked_way
from inventory_tracking.macros.world import (
    FULL_REJUVENATION,
    GOLD,
    HEALING,
    NO_OWNER,
    REJUVENATION,
    SUPER_HEALING,
    VALUABLE,
    Drop,
    Loot,
    Teleport,
    World,
)
from inventory_tracking.models import (
    Actor,
    BeltCell,
    BeltSnapshot,
    PlayerHealth,
    PotionRequest,
    PotionType,
    Refusal,
    SessionIdentity,
    State,
)
from inventory_tracking.native.layout import BELT_COLUMNS, BELT_SIZE, CORPSE_MODE, DEAD_MODES
from inventory_tracking.tracking.belt import potion_kind
from tests.inventory_tracking.macros.fakes import KEYS, Clock, Game, player
from tests.inventory_tracking.scenarios.arena.mobs import Mobs
from tests.inventory_tracking.scenarios.arena.result import Result
from tests.inventory_tracking.scenarios.arena.scene import Scene


Point = tuple[float, float]
POTIONS = {
    int(class_id): row
    for class_id, row in json.loads((Path(__file__).parent / 'potions.json').read_text()).items()
    if not class_id.startswith('_')
}
POTION_CLASS = {row['code']: class_id for class_id, row in POTIONS.items()}  # a scene's drop has the code
# The potions the pickup step sees on the ground and what it takes them for (macros/world.py
# `GameMemory.loot`: only these two are worth a belt cell), with the labels it gives them.
GROUND_POTIONS = {
    FULL_REJUVENATION: (REJUVENATION, 'a full rejuvenation potion'),
    SUPER_HEALING: (HEALING, 'a super healing potion'),
}
COLUMN_OF = {key: column for column, key in INPUT.column_keys.items()}  # a belt key -> its column, 1 to 4
BELT_ROWS = BELT_SIZE // BELT_COLUMNS
# The skill on the right mouse button, which a scene's hero does not say: Echoing Strike, as the
# player casts it and as every recorded battle has it (scenarios/battle/fixtures/*/probe.log:
# "Echoing Strike (right click)"; scenarios/loop/helpers.py `recorded_world`). An assumption of this
# file. It decides more than the input: the healer sends no potion while a key is down
# (input/facade.py `_Attempt.guard`), and a strike held on its key is one, a mouse button is not.
RIGHT_SKILL = ECHOING_STRIKE
SERVE, OSD = 'serve', 'osd'  # who drank (result.py `Result.potions`): the macro's or the player's key, the healer
EDGE = 1e-9  # seconds: a sleep that ends on a tick's time plays that tick


class Ticks(Clock):
    """The fakes' clock, playing the game as it moves: a sleep runs every whole game tick that falls
    due in it, each at its own time, and what is left over counts toward the next sleep's first."""

    def __init__(self, tick: Callable[[], None]) -> None:
        super().__init__()
        self.ticks = 0  # game ticks played
        self.tick = tick

    def sleep(self, seconds: float) -> None:
        until = self.now + seconds
        while (self.ticks + 1) / GAME_RATE <= until + EDGE:
            self.ticks += 1
            self.now = self.ticks / GAME_RATE  # what a tick stamps is its own time, to the last bit
            self.tick()
        # Never short of what was asked: a caller that sleeps what is left of a wait must find it over
        # (macros/timing.py `Pace.sleep`), which a clock rounded to its ticks would not always give.
        self.now = max(self.now, until)

    def step(self) -> None:
        """Sleep to the next tick and play it: how time passes while nobody sleeps on the clock."""
        self.sleep(max((self.ticks + 1) / GAME_RATE - self.now, 0.0))


@dataclass
class Flight:
    """One cast's blades in the air, as the harnesses hold them (scenarios/revivers/harness.py `run`)."""

    birth: int  # the tick of the blades' first frame
    paths: list[list[Point]]  # echoing_strike.cast: a blade's place by frame
    first: set[tuple[int, str]] = field(default_factory=set)  # (unit, leg) a blade of this cast has touched
    touched: list[set[tuple[int, str]]] = field(default_factory=list)  # the same, blade by blade


@dataclass
class Stream:
    """A healing potion at work: its points come a frame at a time."""

    each: float  # points a frame
    frames: int  # frames left


class Ledger:
    """The healer's ledger in memory: what automation/ledger.py `PotionLedger` keeps in a locked file
    for the processes of one host, here for the one arena. `PotionsController` asks it for a
    transaction and reads and writes the transaction's `data`."""

    def __init__(self) -> None:
        self.data = LedgerData.empty('arena')

    @contextmanager
    def transaction(self) -> Iterator[Ledger]:
        yield self

    def save(self) -> None:
        pass


class Attempt:
    """One try of the healer's key, with the two refusals of input/facade.py `_Attempt.guard` that
    have a meaning here: the game is not focused, or a key is down (the strike held on its key is)."""

    def __init__(self, arena: Arena, request: PotionRequest) -> None:
        self.arena, self.request = arena, request
        self.refusal = self.guard()

    def guard(self) -> Refusal | None:
        if not self.arena.focused:
            return Refusal.UNFOCUSED
        return Refusal.KEY_HELD if self.arena.keys.any_key_held() else None

    def send(self) -> float:
        refusal = self.guard()
        if refusal is not None:
            raise Refused(refusal)
        self.arena.drink(self.request.item.column, OSD)
        return self.arena.clock()


class Hand:
    """The healer's key delivery (input/facade.py `Delivery`) into the arena's belt."""

    def __init__(self, arena: Arena) -> None:
        self.arena = arena

    @contextmanager
    def attempt(self, target: object, request: PotionRequest) -> Iterator[Attempt]:
        yield Attempt(self.arena, request)


class Healer:
    """The standalone healer (`make osd`) beside the macro: the production rule, `HealController` over
    `PotionsController` with the thresholds, cooldowns, pending and retry rules of the `HealingConfig`
    given, stepped once a tick on the arena's life and belt. Only its file ledger and its X11 key
    delivery are the arena's own (`Ledger`, `Hand`)."""

    def __init__(self, arena: Arena, config: HealingConfig) -> None:
        if config.actor != Actor.PLAYER:
            raise ValueError("the arena has no mercenary: the healer is the player's")
        self.arena = arena
        potions = PotionsController(config, Ledger(), Hand(arena), clock=arena.clock)  # type: ignore[arg-type]
        self.controller = HealController(config, potions)
        self.session = SessionIdentity(1, 'arena', 1)
        self.outcomes: dict[str, int] = {}  # what its steps came to, counted (models.py `Outcome`)

    def step(self) -> None:
        arena = self.arena
        belt, ids = arena.loot.belt, arena.belt_ids
        # The hotkey row by kind, as tracking/state.py `read_belt` gives it to the healer.
        row = [(potion_kind(belt[cell]), BeltCell(cell + 1, ids[cell] or 0)) for cell in range(BELT_COLUMNS)]
        state = State(
            sampled_at=arena.clock(),
            session=self.session,
            # the raw stat: points times 256 (macros/world.py reads `stats.get(LIFE_STAT) >> 8`)
            health=PlayerHealth(round(arena.life * 256), round(arena.max_life * 256)),
            belt=BeltSnapshot(
                contents=belt,
                healing_cells=tuple(cell for kind, cell in row if kind == PotionType.HEALING),
                rejuvenation_cells=tuple(cell for kind, cell in row if kind == PotionType.REJUVENATION),
                item_ids=tuple(sorted(found for found in ids if found is not None)),
            ),
        )
        outcome = str(self.controller.step(state).outcome)
        self.outcomes[outcome] = self.outcomes.get(outcome, 0) + 1


class Arena(Game):
    """A scene as a game the macro can play: see the module text. `seed` is the monsters' rolls;
    `osd` runs the healer beside the macro; `healing_scale` is the class and Vitality factor on a
    healing potion's points, which potions.json does not hold. `attack` is the attack of the build
    played when it is not Echoing Strike: the held input of its skill casts it, and a cast takes
    what its `dealt` says; None: Echoing Strike and the production blades."""

    def __init__(
        self,
        scene: Scene,
        *,
        seed: int = 1,
        osd: HealingConfig | None = None,
        healing_scale: float = 1.0,
        auras: Mapping[int, float] | None = None,  # unit -> the factor its aura or curse puts on the others' blows
        attack: Attack | None = None,
    ) -> None:
        self.scene = scene.copy()
        hero = self.scene.hero
        self.mobs = Mobs(self.scene, random.Random(seed), auras)
        stand = replace(
            player(hero.area),  # the fakes' character: its unit id and the mode it stands in
            name=hero.name, x=hero.at[0], y=hero.at[1],
            consume=hero.consume, hex_purge=hero.hex_purge, ward=hero.ward,
            right_skill=RIGHT_SKILL if hero.right_skill is None else hero.right_skill,
        )  # fmt: skip
        # A door row as the stance fixtures hold it: unit, txt, mode, x, y (mobs.py reads the same).
        doors = tuple(Door(row[0], row[1], row[2], float(row[3]), float(row[4])) for row in self.scene.doors)
        super().__init__(World(True, (), 'arena', tuple(hero.slots), player=stand, doors=doors))
        self.attack = attack
        if attack is not None:
            self.strike_skill = attack.skill
        self.time = Ticks(self.tick)  # the game's clock; `clock` is the same, as `Game` names it
        self.clock = self.time
        self.ground = Ground(Walkable(**grid) for grid in self.scene.ground)
        self.barred = no_footing(self.ground, doors)  # where nobody stands or walks; None: open ground
        self.walls = walls(self.ground, doors)  # what stops a blade; None: nothing
        self.damage_of = damage_table()
        self.healing_scale = healing_scale
        # The weapon sets: the one in hand first, as `Game.sets` has them.
        self.hand = hero.hand
        self.resists = [dict(found.resist) for found in hero.sets]
        self.sets = [hero.sets[hero.hand].codes, hero.sets[1 - hero.hand].codes]  # type: ignore[assignment]
        staffed = next((index for index, found in enumerate(hero.sets) if found.teleport_charges is not None), None)
        if staffed is not None:
            charges = hero.sets[staffed].teleport_charges
            assert charges is not None
            # The staff's full charges are not in a scene: taken as what it has (nothing reads them here).
            self.staff = Teleport(charges, charges, staffed == hero.hand)
        # The life, the belt and the drops.
        self.life, self.max_life = float(hero.life), float(hero.max_life)
        belt = (*hero.belt, *(None,) * BELT_SIZE)[:BELT_SIZE]
        self.belt_ids: list[int | None] = [None if held is None else 1000 + cell for cell, held in enumerate(belt)]
        self.next_item = 1000 + BELT_SIZE
        self.drop_class: dict[int, int] = {}  # a potion on the ground: its unit -> its item class
        self.loot = Loot(tuple(self._drops()), belt, 0, round(self.max_life))
        self.streams: list[Stream] = []
        self.drinker = SERVE  # who presses the belt keys that come as events
        self.healer = Healer(self, osd) if osd is not None else None
        # A Defiler the macro summons must not take a monster's unit id (`Game` numbers them from here).
        self.next_unit = max((mob.unit for mob in self.scene.mobs), default=0) + 1000
        # What the play came to (`result`).
        self.over: float | None = None  # the clock when the world stood still: the death, or `end`
        self.dead_at: float | None = None
        self.cleared_at: float | None = None
        self.taken = 0.0
        self.kills: list[int] = []
        self.casts = 0
        self.moved = 0.0
        self.potions: list[tuple[float, int, str]] = []
        self.charges = 0
        self.swaps = 0
        self.told: list[tuple[float, str]] = []
        self.flights: list[Flight] = []
        self.refused: list[Point] = []  # where a hop, a warp or a walk was aimed and nobody can go
        self.each_tick: Callable[[], None] | None = None  # the driver's: called after every tick
        self.world = replace(self.world, monsters=tuple(m for m in self.mobs.monsters() if m.mode not in DEAD_MODES))
        self.show()
        if not self.mobs.live():
            self.cleared_at = 0.0

    def _drops(self) -> list[Drop]:
        """The scene's drops as the pickup step reads them (macros/world.py `GameMemory.loot`): a pile
        of gold, a potion worth a belt cell (a smaller one is not read at all), and every other one a
        valuable under its code. The sizes of valuables and the inventory's room are not in a scene:
        one cell each (`Drop.size`) and room unread (`Loot.room`), so room is never short."""
        found = []
        for drop in self.scene.drops:
            class_id = POTION_CLASS.get(drop.code)
            if drop.gold:
                found.append(Drop(drop.unit, *drop.at, f'{drop.gold} gold', GOLD, (0, 0)))
            elif class_id in GROUND_POTIONS:
                kind, label = GROUND_POTIONS[class_id]
                self.drop_class[drop.unit] = class_id
                found.append(Drop(drop.unit, *drop.at, label, kind))
            elif class_id is None:
                found.append(Drop(drop.unit, *drop.at, drop.code, VALUABLE))
        return found

    # -- what the macro reads ------------------------------------------------------------------------

    @property
    def here(self) -> Point:
        stand = self.world.player
        assert stand is not None
        return (stand.x, stand.y)

    def show(self) -> None:
        """The world as it is now, for the next look: the hostiles alive and the dead from `Mobs`,
        every other monster (a companion of the scene's, a Defiler the macro summoned) as it was, and
        the life in whole points (macros/world.py `Loot.life`; 0 is unreadable there, so 1 at least
        while the character lives)."""
        hostile = set(self.mobs.hostile)
        theirs = [m for m in self.mobs.monsters() if m.unit_id in hostile]
        others = tuple(m for m in self.world.monsters if m.unit_id not in hostile)
        self.world = replace(
            self.world,
            monsters=(*(m for m in theirs if m.mode not in DEAD_MODES), *others),
            dead=frozenset(m.unit_id for m in theirs if m.mode in DEAD_MODES),
        )
        life = 0 if self.dead_at is not None else max(round(self.life), 1)
        self.loot = replace(self.loot, life=life, max_life=round(self.max_life))

    def read(self) -> World:
        if self.over is not None:
            return self.world  # the world stands still: no cast ends, no held input casts
        return super().read()

    def run(self, seed: int = 1) -> Run:
        run = super().run(seed)
        run.say = self.say
        run.corpses = self.mobs.corpses
        run.ground = lambda: self.ground if len(self.ground) else None
        return run

    def say(self, text: str) -> None:
        """A line the macro says, with the arena's time (`Result.said`); none after the world stood still."""
        if self.over is None:
            self.said.append(text)
            self.told.append((self.clock.now, text))

    # -- time ----------------------------------------------------------------------------------------

    def tick(self) -> None:
        """One game tick: the monsters move and strike, the blows come off the life, the potions at
        work give their frame, the healer looks, the blades in the air fly on."""
        if self.over is None:
            self.play_tick()
        if self.each_tick is not None:
            self.each_tick()

    def play_tick(self) -> None:
        now = self.clock.now
        companions = [(m.x, m.y) for m in self.world.monsters if m.ally or m.owner != NO_OWNER]
        blows = min(self.mobs.tick(self.here, companions, self.resists[self.hand]), self.life)
        self.taken += blows
        self.life -= blows
        if self.life <= 0.0:
            self.die(now)
            return
        for stream in self.streams:
            self.life = min(self.life + stream.each, self.max_life)
            stream.frames -= 1
        self.streams = [stream for stream in self.streams if stream.frames > 0]
        self.show()
        if self.healer is not None:
            self.healer.step()
        self.fly()
        self.show()
        if self.cleared_at is None and not self.mobs.live():
            self.cleared_at = now

    def die(self, now: float) -> None:
        """The life is gone: the character lies dead (the mode macros/routines.py DEAD and
        native/layout.py PLAYER_DEAD_MODES know) and nothing happens in this world any more."""
        self.life, self.dead_at, self.over = 0.0, now, now
        self.acting_until, self.kept, self.kept_hop = None, [], False
        stand = self.world.player
        assert stand is not None
        self.world = replace(self.world, player=replace(stand, mode=CORPSE_MODE))
        self.show()

    def end(self) -> None:
        """The play is over: the world stands still from here (the driver, at its horizon)."""
        if self.over is None:
            self.over = self.clock.now

    def fly(self) -> None:
        """The blades in the air at this tick, each on the monsters within the contact radius: once a
        leg for a blade, a cast's later blades on the same monster and leg at the duplicate share."""
        frame = self.time.ticks
        for flight in self.flights:
            k = frame - flight.birth
            if not 0 <= k < LIFE:
                continue
            leg = 'out' if k <= OUT_FRAMES else 'back'
            for blade, path in enumerate(flight.paths):
                if k >= len(path):
                    continue
                for unit in self.mobs.live():
                    mob, key = self.mobs.mobs[unit], (unit, leg)
                    if key in flight.touched[blade] or math.dist(path[k], mob.at) > CONTACT_RADIUS:
                        continue
                    flight.touched[blade].add(key)
                    dealt = self.damage_of(mob.txt) * (DUPLICATE if key in flight.first else 1.0)
                    flight.first.add(key)
                    if self.mobs.hit(unit, dealt):
                        self.kills.append(unit)
        self.flights = [flight for flight in self.flights if frame - flight.birth < LIFE]

    # -- what the inputs do --------------------------------------------------------------------------

    def footing(self, spot: Point) -> bool:
        return self.barred is None or not self.barred(spot)

    def walkable_to(self, goal: Point) -> bool:
        """Whether a click walks the character to `goal`: footing there and a way to it, straight
        (combat/stance.py `way`) or round what bars it (macros/travel.py `walked_way`, to the goal's cell)."""
        if self.barred is None:
            return True
        if not self.footing(goal):
            return False
        if way(self.barred, self.here, goal):
            return True
        found = walked_way(self.barred, self.here, goal)
        return bool(found) and (math.floor(found[-1][0]), math.floor(found[-1][1])) == (
            math.floor(goal[0]),
            math.floor(goal[1]),
        )

    def act(self, event: tuple) -> None:
        if self.over is not None:
            return
        key = event[1] if event[0] == 'key' else None
        if key in COLUMN_OF:
            self.drink(COLUMN_OF[key], self.drinker)
            return
        jump = key == KEYS[TELEPORT] or (key == KEYS[BLADE_WARP] and BLADE_WARP in self.world.slots)
        if jump and not self.footing(self.ground_under_pointer()):
            # As scenarios/navigation/harness.py `WalledGame`: aimed where nobody stands, it moves nobody.
            self.refused.append(self.ground_under_pointer())
            return
        if event[0] == 'click' and not self.keys.shift:
            drop = self.drop_under_pointer()
            goal = (drop.x, drop.y) if drop is not None else self.ground_under_pointer()
            if not self.walkable_to(goal):
                self.refused.append(goal)
                return
        before, lying = self.here, self.loot.drops
        charges = self.staff.charges if self.staff is not None else 0
        super().act(event)
        stand = self.world.player
        assert stand is not None
        if key == KEYS[TELEPORT] and self.here != before:
            # The sub-tile's centre, as `WalledGame` lands a hop: every landing in the logs is at x.5.
            self.world = replace(self.world, player=replace(stand, x=int(stand.x) + 0.5, y=int(stand.y) + 0.5))
        self.moved += math.dist(before, self.here)
        if self.staff is not None:
            self.charges += charges - self.staff.charges
        if key == KEYS[SWAP_WEAPONS]:
            self.swaps += 1
            self.hand = 1 - self.hand
        for drop in lying:
            if drop not in self.loot.drops and drop.unit_id in self.drop_class:
                self.stow(self.drop_class[drop.unit_id])
        self.show()

    def strike(self) -> None:
        """A cast of Echoing Strike toward the pointer. `Game.strike` keeps its record of the cast
        (`strikes`), the casting mode and the cast's length; what it takes off a monster by its own
        count (`toughness`) is undone by `show`, and the production blades are let fly instead. With
        another build's `attack` its cast lands at once: what `dealt` takes off the hostiles alive."""
        origin, focal = self.here, self.ground_under_pointer()
        super().strike()
        self.show()
        if self.attack is not None:
            self.land(origin, focal, self.attack)
            return
        paths = cast(origin, focal, lambda frame: origin, self.walls)
        self.flights.append(Flight(self.time.ticks + BIRTH_LAG, paths, set(), [set() for _ in paths]))
        self.casts += 1

    def land(self, origin: Point, focal: Point, attack: Attack) -> None:
        """A cast of a build's attack that is not the blades: `attack.dealt` from where the character
        stands at the ground under the pointer, off each hostile alive, in the tick of the cast (no
        flight, no wall: the attack's own model says who is hit)."""
        mobs = self.mobs
        foes = {unit: Foe(mobs.mobs[unit].txt, mobs.mobs[unit].at, mobs.mobs[unit].life) for unit in mobs.live()}
        for unit, points in attack.dealt(origin, focal, foes).items():
            if mobs.hit(unit, points):
                self.kills.append(unit)
        self.casts += 1
        self.show()

    def drink(self, column: int, who: str) -> bool:
        """The belt key of `column` (1 to 4): the potion of its hotkey cell is drunk and the column's
        other potions come down a row (the game's belt; automation/potions.py counts on it: "Drain
        the fullest column first"). `Game` only empties the hotkey cell. A rejuvenation gives its
        share of the most life at once, a healing potion its points times `healing_scale` over its
        frames (potions.json); whatever else the cell held is gone for nothing."""
        cell = column - 1
        belt = list(self.loot.belt)
        class_id = belt[cell]
        if class_id is None or self.over is not None:
            return False
        for cells in (belt, self.belt_ids):
            for row in range(BELT_ROWS - 1):
                cells[cell + row * BELT_COLUMNS] = cells[cell + (row + 1) * BELT_COLUMNS]
            cells[cell + (BELT_ROWS - 1) * BELT_COLUMNS] = None
        self.loot = replace(self.loot, belt=tuple(belt))
        potion = POTIONS.get(class_id, {})
        if potion.get('kind') == 'rejuvenation':
            self.life = min(self.life + self.max_life * potion['share'] / 100, self.max_life)
        elif potion.get('kind') == 'healing':
            self.streams.append(Stream(potion['points'] * self.healing_scale / potion['frames'], potion['frames']))
        self.potions.append((self.clock.now, class_id, who))
        self.show()
        return True

    def stow(self, class_id: int) -> None:
        """A potion picked up lands in the belt: on the first column that holds its kind and has a free
        cell, else in the first empty column; with neither it goes to the inventory, which the arena
        does not have. The rule is this file's assumption (`Game` puts nothing in the belt but what a
        test scripts in `belt_after`)."""
        belt = list(self.loot.belt)
        kind = potion_kind(class_id)
        columns = [list(range(column, BELT_SIZE, BELT_COLUMNS)) for column in range(BELT_COLUMNS)]
        alike = [
            cells for cells in columns if potion_kind(belt[cells[0]]) == kind and None in map(belt.__getitem__, cells)
        ]
        empty = [cells for cells in columns if all(belt[cell] is None for cell in cells)]
        for cells in (*alike, *empty)[:1]:
            cell = next(cell for cell in cells if belt[cell] is None)
            belt[cell], self.belt_ids[cell] = class_id, self.next_item
            self.next_item += 1
        self.loot = replace(self.loot, belt=tuple(belt))

    # -- what it came to -----------------------------------------------------------------------------

    def result(self) -> Result:
        return Result(
            scene=self.scene.name,
            seconds=self.clock.now if self.over is None else self.over,
            dead_at=self.dead_at,
            cleared_at=self.cleared_at,
            taken=self.taken,
            kills=list(self.kills),
            casts=self.casts,
            moved=self.moved,
            potions=list(self.potions),
            charges=self.charges,
            swaps=self.swaps,
            said=list(self.told),
        )
