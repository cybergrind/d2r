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
  goes where no way leads, and walls stop the blades;
- a move takes its time (`Game` makes every move in the instant of its input; `instant_moves=True`
  is that game again):
  - a walk (a left click on the ground or on a drop) is run a tick at a time at RUN_SPEED, straight
    where a straight way leads (combat/stance.py `way`), else along the cells of the walked way
    (macros/travel.py `walked_way`); the character is in the running mode meanwhile (RUNNING), and a
    drop is picked up when it stands on it. A new click redirects it from where it is. A cast ends
    it where the character is (the strike, a hop, a Blade Warp, any skill key), and a click made
    during a cast is a walk that begins when that cast is over (combat/stance.py WALK_LATENCY:
    "the cast that has to end, and the click");
  - a Teleport hop is a cast of macros/movement.py TELEPORT_JUMP's seconds (0.31), and the
    character is at the landing on the first tick at or after its end, not before; the charge is
    spent at the key. A Teleport key that comes during a cast is kept and cast when that cast is
    over (`Game.keeps_keys`), as the game does (macros/teleport.py `press_hop`);
  - a Blade Warp is builds/warlock/movement.py BLADE_WARP_JUMP: the cast (0.35 s), then the blade's
    flight at 45 units a second; the character casts where it stood until it is at the impact;
  - `Mobs.tick` is given the character's place of that tick, so it is struck on the way.

What the arena does not model, or takes as given (the calibration of Task 1.9 needs the list):

- of a move: the run has one speed from its first tick to its last (no acceleration, no stamina,
  no faster run/walk of the gear), and the way round a wall is the walked way's cell centres, not the
  game's own path (a staircase up to 8% longer than the smooth line); bodies bar nothing (the
  character runs through monsters, and they through it); a block never stops a walk (as for a
  cast, below); a click under a cast is never swallowed (macros/travel.py `step_walk`
  says the game swallows some); the tail of a hop's cast after the landing, the casting delay of
  Blade Warp (builds/warlock/movement.py WARP_DELAY) and a wall in the blade's line are not there
  (a warp lands wherever there is footing); the character is taken to be busy for the whole flight
  of the blade; a weapon swap is instant; a skill key pressed while the character is free is a
  cast of QUICK_CAST_SECONDS with its skill on the right button (`quick_cast`; the session of 2026-10-12
  has 0.52 s from Psychic Ward's key to the first strike, twice), as a key kept during a cast; nothing happens
  between two looks at the game but the ticks (a cast, and a walk asked for during a cast, begin at
  the look after the cast's end, as `Game`'s casts do);
- the strike deals the same with either weapon set (damage.json knows no set), Death Mark, Sigil:
  Lethargy, Engorge, Hex: Purge, Psychic Ward and Consume change nothing (their casts are counted by
  `Game` and cost their cast time), and the companions deal no damage;
- the blades return to where the character stood at the cast (as both harnesses), and a blade's
  focal point is the ground under the pointer at the cast's start;
- mana is not counted (combat/data/damage.json: the recorded mana never limited casting);
- a tick's blows that take RECOVERY_SHARE of the most life or more stagger the character
  (`Arena.stagger`): it stands in the hit mode for RECOVERY_SECONDS, a walk ends, a cast whose blades
  are not born yet is lost and nothing is cast meanwhile. The share is the game's rule for one blow
  (a twelfth of the most life), applied here to a tick's sum; the length is the median of the 20
  spells of the hit mode in the takes of 2026-10-11 and 12 (0.34 s; deciles 0.25 to 0.41). A hop or a
  Blade Warp under way is not interrupted. A melee blow that would land is blocked with BLOCK_CHANCE
  (mobs.py `Mobs.block_chance`): it takes nothing and the character stands in the block mode for
  BLOCK_SECONDS, interrupted as by a stagger. The chance is the character's block stat (10 in the
  takes' `character_stats`, stat 20), which agrees with the count: 35 spells of mode 9 in the takes
  of 2026-10-11 and 12 beside some 300 drops of life; the length is their median (0.44 s; deciles
  0.41 to 0.46). No blow is dodged or missed beyond what `Mobs` rolls itself;
- doors stand as the scene has them; nothing drops from a kill;
- the scene's `things` are objects to operate (macros/opening.py): a click on one walks the character
  to it and operates it within OPEN_REACH. The hover record holds a monster before an object or a
  drop, as the game's does (probe.log of 2026-10-12 21:24:41: a chest 9 away not opened, "the aims and
  what was under them" a monster six times): the pointer is on a live hostile when the monster stands
  within BODY_HALF of the pointer's ground or of the ground up to BODY_LIFT below it on the screen (a
  body's picture stands above its feet). Both sizes are assumptions of this file, one for every type;
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
from inventory_tracking.builds.warlock.movement import BLADE_WARP_JUMP
from inventory_tracking.builds.warlock.skills import BLADE_WARP, ECHOING_STRIKE
from inventory_tracking.combat.policy import RUN_MODES, Foe, walls
from inventory_tracking.combat.stance import no_footing, way
from inventory_tracking.combat.timeline import GAME_RATE
from inventory_tracking.config import INPUT, HealingConfig
from inventory_tracking.input import Refused
from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.model import Ground, Walkable
from inventory_tracking.macros.build import Attack
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.movement import TELEPORT_JUMP
from inventory_tracking.macros.routines import ACTING
from inventory_tracking.macros.skills import SWAP_WEAPONS, TELEPORT
from inventory_tracking.macros.teleport import WALKING
from inventory_tracking.macros.travel import walked_way
from inventory_tracking.macros.world import (
    FULL_REJUVENATION,
    GOLD,
    HEALING,
    MONSTER_UNIT,
    NO_OWNER,
    OBJECT_UNIT,
    REJUVENATION,
    SUPER_HEALING,
    VALUABLE,
    Drop,
    Loot,
    Teleport,
    Thing,
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
from tests.inventory_tracking.scenarios.threat.harness import RUN


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
# The character's run, in units a second: the one speed measured from a named take
# (scenarios/threat/harness.py RUN = 18.75, "the character's run in the take 20261010T162810Z-35"),
# 0.75 of a unit a tick. Not the 20.0 of combat/stance.py RUN_SPEED (and scenarios/stance/harness.py),
# which is the number the production code prices a walk with: the world that judges that price
# must not take it from the code it judges.
RUN_SPEED = RUN
# The modes the arena shows a moving character in. No production module names them one by one:
RUNNING = 3  # combat/policy.py RUN_MODES and macros/teleport.py WALKING, "walk, run, town walk" = (2, 3, 6): the run
CASTING = 7  # the mode macros/fakes.py `Game.strike` gives a cast under way; one of macros/routines.py ACTING
assert RUNNING in RUN_MODES
assert RUNNING in WALKING
assert CASTING in ACTING
# The keys whose skill is cast where the character stands: a walk ends at one. Teleport and Blade Warp
# end it themselves when they are cast (`Arena.cast_to`); the swap is no cast.
CAST_KEYS = frozenset(key for skill, key in KEYS.items() if skill not in (SWAP_WEAPONS, TELEPORT, BLADE_WARP))
WALK_REACH = 40.0  # units: a click on ground further off walks nobody (`Game.act`)
STAGGERED = 4  # the character's mode while a blow has it stagger (the game's "get hit"); not one of ACTING
assert STAGGERED not in ACTING
RECOVERY_SHARE = 1 / 12  # of the most life: blows of a tick that take this much stagger the character
RECOVERY_SECONDS = 0.34  # how long it staggers (the module text has the measure)
QUICK_CAST_SECONDS = 0.38  # a cast of the character: 0.36 to 0.39 s recorded (macros/routines.py ONE_CAST)
BLOCKING = 9  # the character's mode while it blocks; not one of ACTING
assert BLOCKING not in ACTING
BLOCK_CHANCE = 0.10  # of a melee blow that would land (the module text has the measure)
BLOCK_SECONDS = 0.44
OPEN_REACH = 3.0  # units: an object clicked is operated from this near
BODY_LIFT = 3.0  # units down the screen from the pointer's ground that a monster's picture still covers
BODY_HALF = 1.5  # units: how far from that line a monster's feet may be


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
class Landing:
    """A hop or a Blade Warp under way: the character casts where it stood and is at `spot` at `tick`."""

    tick: int  # the game tick it stands there at
    spot: Point


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
    what its `dealt` says; None: Echoing Strike and the production blades. `instant_moves`: a walk, a
    hop and a Blade Warp are over in the instant of their input, as in `Game` (the module text has
    what a move is otherwise)."""

    def __init__(
        self,
        scene: Scene,
        *,
        seed: int = 1,
        osd: HealingConfig | None = None,
        healing_scale: float = 1.0,
        auras: Mapping[int, float] | None = None,  # unit -> the factor its aura or curse puts on the others' blows
        attack: Attack | None = None,
        instant_moves: bool = False,
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
        self.instant_moves = instant_moves
        self.stands = stand.mode  # the mode of a character that neither goes nor casts
        self.bound: tuple[Point, Drop | None] | None = None  # the walk asked for: its end, the drop to take there
        self.route: list[Point] = []  # the points of that walk still to run to; empty: not running
        self.landing: Landing | None = None  # the hop or the Blade Warp under way
        self.things = [Thing(prop.unit, prop.txt, prop.mode, *prop.at) for prop in self.scene.things]
        self.opening: int | None = None  # the unit id of the object the walk under way is to operate
        self.staggers = 0
        self.blocks = 0
        if not instant_moves:
            self.mobs.block_chance = BLOCK_CHANCE
        if not instant_moves:
            self.keeps_keys = True  # a Teleport key during a cast waits for the cast's end
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
        if self.instant_moves:
            return super().read()
        self.hold()
        before = self.acting_until
        super().read()
        if self.acting_until is not None and self.acting_until != before:
            self.halt()  # a cast began in this look: the character stands and casts
        else:
            self.set_out()
        return self.world

    def run(self, seed: int = 1) -> Run:
        run = super().run(seed)
        run.say = self.say
        run.corpses = self.mobs.corpses
        run.ground = lambda: self.ground if len(self.ground) else None
        run.things = lambda: tuple(self.things)
        run.containers = run.things
        return run

    def monster_under_pointer(self) -> int | None:
        """The live hostile whose picture the pointer is on (the module text has the box); the nearest."""
        gx, gy = self.ground_under_pointer()
        found: tuple[float, int] | None = None
        for unit in self.mobs.live():
            x, y = self.mobs.mobs[unit].at
            along = max(0.0, min(BODY_LIFT, ((x - gx) + (y - gy)) / 2))
            away = math.dist((x, y), (gx + along, gy + along))
            if away <= BODY_HALF and (found is None or away < found[0]):
                found = (away, unit)
        return None if found is None else found[1]

    def prop_under_pointer(self) -> Thing | None:
        """The scene's object whose picture the pointer is on, as `Game.thing_under_pointer` has one."""
        gx, gy = self.ground_under_pointer()
        lift = self.thing_above / 16
        for thing in self.things:
            at = (thing.x, thing.y)
            if math.dist((gx + lift, gy + lift), at) < 2 and math.dist(self.here, at) < 30:
                return thing
        return None

    def unit_under_pointer(self) -> tuple[int, int]:
        unit = self.monster_under_pointer()
        if unit is not None:
            return (MONSTER_UNIT, unit)
        thing = self.prop_under_pointer()
        if thing is not None:
            return (OBJECT_UNIT, thing.unit_id)
        return super().unit_under_pointer()

    def beside(self, thing: Thing) -> Point:
        """Where a click on the object walks the character: its place, or (an object stands where nobody
        does) the nearest footing on the line from it to the character."""
        at, here = (thing.x, thing.y), self.here
        gap = math.dist(at, here)
        for step in range(int(gap * 2) + 1):
            share = min(1.0, step * 0.5 / gap) if gap else 1.0
            spot = (at[0] + (here[0] - at[0]) * share, at[1] + (here[1] - at[1]) * share)
            if self.footing(spot):
                return spot
        return here

    def operate(self, unit: int) -> None:
        self.things = [replace(thing, mode=2) if thing.unit_id == unit else thing for thing in self.things]
        self.opening = None

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
        if not self.instant_moves:
            self.move()
        companions = [(m.x, m.y) for m in self.world.monsters if m.ally or m.owner != NO_OWNER]
        blows = min(self.mobs.tick(self.here, companions, self.resists[self.hand]), self.life)
        self.taken += blows
        self.life -= blows
        if self.life <= 0.0:
            self.die(now)
            return
        if self.mobs.blocked > self.blocks:
            self.blocks = self.mobs.blocked
            self.stagger(now, BLOCK_SECONDS, BLOCKING)
        if blows >= self.max_life * RECOVERY_SHARE and not self.instant_moves:
            self.stagger(now)
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

    def stagger(self, now: float, seconds: float = RECOVERY_SECONDS, mode: int = STAGGERED) -> None:
        """A heavy blow, or a blow blocked: the character stands in `mode` for `seconds` (the module text)."""
        if self.landing is not None:
            return
        self.staggers += 1
        self.flights = [flight for flight in self.flights if flight.birth <= self.time.ticks]
        self.halt()
        self.acting_until = max(self.acting_until or 0.0, now + seconds)
        self.mode(mode)

    def die(self, now: float) -> None:
        """The life is gone: the character lies dead (the mode macros/routines.py DEAD and
        native/layout.py PLAYER_DEAD_MODES know) and nothing happens in this world any more."""
        self.life, self.dead_at, self.over = 0.0, now, now
        self.acting_until, self.kept, self.kept_hop = None, [], False
        self.bound, self.route, self.landing = None, [], None
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

    def way_to(self, goal: Point) -> list[Point]:
        """The points a click on `goal` runs the character through, the goal last: the goal alone where
        a straight way leads (combat/stance.py `way`), else the cell centres of the way round what bars
        it (macros/travel.py `walked_way`, when it reaches the goal's cell). Empty: no footing there,
        or no way."""
        if self.barred is None:
            return [goal]
        if not self.footing(goal):
            return []
        if way(self.barred, self.here, goal):
            return [goal]
        found = walked_way(self.barred, self.here, goal)
        if not found or (math.floor(found[-1][0]), math.floor(found[-1][1])) != (
            math.floor(goal[0]),
            math.floor(goal[1]),
        ):
            return []
        return [*found, goal]

    def walkable_to(self, goal: Point) -> bool:
        """Whether a click walks the character to `goal` (`way_to`)."""
        return bool(self.way_to(goal))

    def act(self, event: tuple) -> None:
        if self.over is not None:
            return
        key = event[1] if event[0] == 'key' else None
        if key in COLUMN_OF:
            self.drink(COLUMN_OF[key], self.drinker)
            return
        if self.instant_moves:
            self.act_at_once(event, key)
        elif key == KEYS[BLADE_WARP] and BLADE_WARP in self.world.slots:
            self.warp()
        elif event[0] == 'click' and not self.keys.shift:
            self.click_ground()
        else:
            name = key if event[0] == 'key' else f'Button{event[1]}' if event[0] == 'button' else None
            free = self.acting_until is None
            if name in CAST_KEYS:
                self.halt()
            super().act(event)  # Teleport's key comes back as `hop`, a held strike as `strike`
            if name in CAST_KEYS and free and self.acting_until is None:
                self.quick_cast(name)
            if key == KEYS[SWAP_WEAPONS]:
                self.swaps += 1
                self.hand = 1 - self.hand
        self.show()

    def quick_cast(self, name: str) -> None:
        """A skill key pressed while the character is free: its cast takes the cast's time, with the skill
        on the right button meanwhile, as `Game.read` has a key that was kept during a cast."""
        stand = self.world.player
        assert stand is not None
        skill = next((skill for skill, key in KEYS.items() if key == name), None)
        if self.home_skill is None:
            self.home_skill = (stand.right_skill,)
        self.world = replace(self.world, player=replace(stand, mode=CASTING, right_skill=skill))
        self.acting_until = self.clock.now + QUICK_CAST_SECONDS

    def act_at_once(self, event: tuple, key: str | None) -> None:
        """An input as `Game` takes it, every move made in its instant (`instant_moves`)."""
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

    # -- a move in its time ----------------------------------------------------------------------------

    def mode(self, mode: int) -> None:
        stand = self.world.player
        assert stand is not None
        self.world = replace(self.world, player=replace(stand, mode=mode))

    def put(self, spot: Point) -> None:
        """The character at `spot`, with the way there counted (`Result.moved`)."""
        stand = self.world.player
        assert stand is not None
        self.moved += math.dist(self.here, spot)
        self.world = replace(self.world, player=replace(stand, x=spot[0], y=spot[1]))

    def click_ground(self) -> None:
        """A left click with no Shift: a walk to the ground under the pointer, or to the drop there and
        the drop taken on arrival. As `Game.act` has a click but for the time: none where no way leads,
        none on ground WALK_REACH away, and the clicks the fakes' game is told to lose are lost."""
        thing = self.prop_under_pointer() if self.monster_under_pointer() is None else None
        if thing is not None and thing.mode == 0:
            if math.dist(self.here, (thing.x, thing.y)) <= OPEN_REACH:
                self.operate(thing.unit_id)
                return
            self.bound, self.route = (self.beside(thing), None), []
            self.set_out()
            self.opening = thing.unit_id if self.bound is not None else None
            return
        drop = self.drop_under_pointer()
        goal = (drop.x, drop.y) if drop is not None else self.ground_under_pointer()
        if not self.walkable_to(goal):
            self.refused.append(goal)
        elif self.swallowed_clicks:
            self.swallowed_clicks -= 1
        elif drop is not None and self.deaf_picks:
            self.deaf_picks -= 1
        elif drop is not None or math.dist(goal, self.here) < WALK_REACH:
            if drop is None:
                self.walks.append(goal)
            self.bound, self.route = (goal, drop), []  # a walk under way is redirected from where it is
            self.set_out()

    def set_out(self) -> None:
        """The walk asked for begins, once the character is free: by the way from where it stands
        then (a click during a hop's cast is a walk from the landing). No way from there: no walk."""
        if self.bound is None or self.route or self.acting_until is not None:
            return
        goal = self.bound[0]
        self.route = self.way_to(goal)
        if self.route:
            self.mode(RUNNING)
        else:
            self.refused.append(goal)
            self.halt()

    def halt(self) -> None:
        """The walk is over where the character is: a cast began, or there is no way on."""
        self.bound, self.route, self.opening = None, [], None
        stand = self.world.player
        if stand is not None and stand.mode == RUNNING:
            self.mode(self.stands)

    def hold(self) -> None:
        """A hop or a Blade Warp under way is a cast until the character is there: `Game` gives a key it
        kept during a cast ACTING_SECONDS from that cast's end, whatever the key's own cast takes."""
        landing = self.landing
        if landing is not None and (self.acting_until is None or self.acting_until < landing.tick / GAME_RATE):
            self.acting_until = landing.tick / GAME_RATE

    def cast_to(self, spot: Point, seconds: float) -> None:
        """The cast of a skill that puts the character at `spot` in `seconds` from now: it stands and
        casts until the first tick at or after that time, which has it there (`move`)."""
        self.halt()
        due = math.ceil((self.clock.now + seconds) * GAME_RATE - 1e-6)
        self.landing = Landing(max(due, self.time.ticks + 1), spot)
        self.acting_until = self.landing.tick / GAME_RATE
        self.mode(CASTING)

    def hop(self) -> None:
        """Teleport, cast now (its key, or the key kept during the cast before: `Game.read`): on the
        ground under the pointer as it is now, where there is footing, at the sub-tile's centre (as
        scenarios/navigation/harness.py `WalledGame` lands a hop: every landing in the logs is at
        x.5), TELEPORT_JUMP's seconds from now. The staff's charge is spent with the cast."""
        if self.instant_moves:
            super().hop()
            return
        staff = self.staff
        charged = staff is not None and staff.in_hand and staff.charges > 0
        if not charged and not (staff is None and TELEPORT in self.world.slots):
            return
        aim = self.ground_under_pointer()
        if not self.footing(aim):
            self.refused.append(aim)  # aimed where nobody stands, it moves nobody and spends nothing
            return
        if staff is not None:
            self.staff = replace(staff, charges=staff.charges - 1)
            self.charges += 1
        spot = (int(aim[0]) + 0.5, int(aim[1]) + 0.5)
        self.cast_to(spot, TELEPORT_JUMP.takes(math.dist(self.here, spot)))

    def warp(self) -> None:
        """Blade Warp, cast now: the cast, then the blade's flight to the ground under the pointer
        (BLADE_WARP_JUMP), and the character is at the impact."""
        if not self.warp_lands:
            return
        spot = self.ground_under_pointer()
        if not self.footing(spot):
            self.refused.append(spot)
            return
        self.warps.append(spot)
        self.cast_to(spot, BLADE_WARP_JUMP.takes(math.dist(self.here, spot)))

    def move(self) -> None:
        """One tick of the character's own moves: a landing that is due, else a tick's run along the
        walk's points; at the last of them it stands and takes the drop it was sent for."""
        landing = self.landing
        if landing is not None and self.time.ticks >= landing.tick:
            self.put(landing.spot)
            self.landing = None
        stand = self.world.player
        assert stand is not None
        if not self.route or stand.mode != RUNNING:
            return
        here, left = self.here, RUN_SPEED / GAME_RATE
        while self.route and left > 0.0:
            gap = math.dist(here, self.route[0])
            if gap <= left:
                here, left = self.route.pop(0), left - gap
            else:
                here = (
                    here[0] + (self.route[0][0] - here[0]) * left / gap,
                    here[1] + (self.route[0][1] - here[1]) * left / gap,
                )
                left = 0.0
        self.put(here)
        if self.opening is not None:
            thing = next(thing for thing in self.things if thing.unit_id == self.opening)
            if math.dist(here, (thing.x, thing.y)) <= OPEN_REACH or not self.route:
                self.operate(thing.unit_id)
                self.halt()
                return
        if not self.route:
            drop = self.bound[1] if self.bound is not None else None
            self.halt()
            if drop is not None:
                self.take(drop)

    def take(self, drop: Drop) -> None:
        """The drop the character walked to leaves the ground, as `Game.act` takes one at its click; a
        potion goes to the belt (`stow`). Nothing if it is gone already."""
        if all(lying.unit_id != drop.unit_id for lying in self.loot.drops):
            return
        self.picked.append(drop.label)
        self.loot = replace(self.loot, drops=tuple(d for d in self.loot.drops if d.unit_id != drop.unit_id))
        if len(self.picked) in self.belt_after:
            self.loot = replace(self.loot, belt=self.belt_after[len(self.picked)])
        if drop.unit_id in self.drop_class:
            self.stow(self.drop_class[drop.unit_id])

    def strike(self) -> None:
        """A cast of Echoing Strike toward the pointer. `Game.strike` keeps its record of the cast
        (`strikes`), the casting mode and the cast's length; what it takes off a monster by its own
        count (`toughness`) is undone by `show`, and the production blades are let fly instead. With
        another build's `attack` its cast lands at once: what `dealt` takes off the hostiles alive."""
        self.halt()  # a cast: the walk ends where the character is
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
