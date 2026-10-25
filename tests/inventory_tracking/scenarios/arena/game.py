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
  says the game swallows some); the tail of a hop's cast after the landing and a wall in the
  blade's line are not there (a warp lands wherever there is footing); Blade Warp's casting delay
  is the game's, from the key and not from its cast (WARP_DELAY_OVER; a warp key in it is refused
  and counted, with the state the macro reads it by), and with `instant_moves` it is not there; the
  character is taken to be busy for the whole flight of the blade; a weapon swap is instant; a skill
  key pressed while the character is free is a cast of QUICK_CAST_SECONDS with its skill on the right
  button (`quick_cast`; the session of 2026-10-12 has 0.52 s from Psychic Ward's key to the first
  strike, twice), as a key kept during a cast; nothing happens between two looks at the game but the
  ticks (a cast, and a walk asked for during a cast, begin at
  the look after the cast's end, as `Game`'s casts do);
- the strike deals the same with either weapon set (damage.json knows no set), Sigil: Lethargy, Engorge,
  Hex: Purge and Consume change nothing (their casts are counted by `Game` and cost their cast time), and
  the companions deal no damage; the sigil shows as the game shows it (`Arena.lay_sigil`): its missile,
  the character's, lies on the ground under the pointer at its key from SIGIL_MISSILE_SHOWS after it, and
  its state (builds/warlock/buffs.py SIGIL_STATE) is on every monster within its radius from
  SIGIL_STATE_SHOWS after it, until SIGIL_LASTS; each new sigil ends the last (it slows nobody); Death
  Mark (`Arena.mark`, rca/2026-10-14/death-mark.md) on the live hostile under the pointer at its key sends
  the character's demons onto it MARK_JUMP after its key (the takes: 0.28 s) and holds them MARK_BESIDE
  from it while it lives and the mark lasts (whom a monster goes for is then the nearest body, as always
  here), and each blade on it takes the mark's flat points: the demons' own damage on it (the build's
  `gain`) is not played, so the arena sees the mark's cost and its draw-off and not what the demons add;
  Psychic Ward is a guard (combat/sim/guard.py, builds/warlock/ward.py: a pool of physical points taken
  before the resistances, a stun on a melee striker) set at the tick after its key, and only the types the
  client's rules play meet it;
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

Five rules a play may turn on (`rules`, 2026-10-21 and 22: what a tier 4-5 Herald pack fight needs, rca/2026-10-21/
herald-fight-findings.md §3.4 "what the arena lacks"). Each is off unless asked, so every scene fitted and pinned
before plays as it did:

- SIGIL_SLOWS: a hostile standing in the character's sigil (`sigil_lying` from SIGIL_STATE_SHOWS, within
  SIGIL_RADIUS) walks and swings at mobs.py SIGIL_SLOW (skills.txt 393: half);
- PETS_FIGHT: the character's demons (Death Mark's `sends`: the Defilers, the bound demon; not the mercenary)
  take the blows the monsters land on them (mobs.py `mate_blows`, raw points: a pet's resistances and Health Link are
  not played) and die at 0 (out of the world, `pet_deaths`); a scene's companion has its own life and most life, a
  Defiler the macro summons PET_POINTS. Each strikes the nearest live hostile within its reach at its points a frame
  (the build's damage.json `companions`, an unmeasured demon by builds/warlock/mark.py `demon_rate`), the kill counted
  as the character's; one not held by a mark goes for the nearest hostile within PET_ENGAGE of it and stands
  PET_STOP from it, else keeps up as `follow` has it (which runs in every scene with this rule). Their life shows in
  128ths of the most, as the client's monster life does;
- BODIES_BLOCK: a monster's stride does not end in another body (mobs.py `Horde.bodies`), and the character's walk
  does not go through a live hostile: blocked, it stands (the 09:30:52 "the character did not move");
- MANA_SHOWN (2026-10-22, rca/2026-10-22/walled-boss-findings.md §2): the character's mana and most mana (stats 8
  and 9) are shown to the macro as the scene's hero has them, as the live loot read shows them (combat/threats/
  manaburn.py `mana_of`): never spent nor burnt, mana is not counted. Off: no mana is shown, and the safety reads the
  mana as unknown (a draining hostile kept at range whatever it does, DRAIN_GATE).

- REVIVERS_RAISE (2026-10-23, combat/revivers.py REVIVERS_FIRST): a live reviver of the production table raises the
  nearest corpse of its family within its raise range back at full life, one every its table seconds (mobs.py
  `Mobs.raise_dead`); a unit killed again is a kill again (`kills` holds it twice).

Bind Demon's key (whatever the rules) on a live hostile under the pointer that builds/warlock/bind.py `bindable`
calls a demon, with no bound demon out, makes it the character's BIND_TAKES after the key (`binds`): the capture's
chance and the cast's sequence are not played.
"""

import itertools
import json
import math
import random
import sys
from collections.abc import Callable, Generator, Iterable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path

from inventory_tracking.automation.heal import HealController
from inventory_tracking.automation.ledger import LedgerData
from inventory_tracking.automation.potions import PotionsController
from inventory_tracking.builds.warlock.bind import bindable, bound
from inventory_tracking.builds.warlock.buffs import SIGIL_LASTS, SIGIL_MISSILES, SIGIL_RADIUS, SIGIL_STATE
from inventory_tracking.builds.warlock.echoing_strike.attack import DUPLICATE
from inventory_tracking.builds.warlock.echoing_strike.damage import companion_table, damage_table
from inventory_tracking.builds.warlock.echoing_strike.hits import CONTACT_RADIUS
from inventory_tracking.builds.warlock.echoing_strike.mechanics import LIFE, OUT_FRAMES, cast
from inventory_tracking.builds.warlock.echoing_strike.sim.input import BIRTH_LAG
from inventory_tracking.builds.warlock.mark import (
    MARK_BESIDE,
    MARK_ELEMENTS,
    MARK_JUMP,
    MARK_POINTS,
    MARK_SECONDS,
    MARK_STATE,
    REMARK_HOP,
    TAKEN_ALONG,
    demon_rate,
    sends,
)
from inventory_tracking.builds.warlock.movement import BLADE_WARP_JUMP
from inventory_tracking.builds.warlock.skills import BIND_DEMON, BLADE_WARP, DEATH_MARK, ECHOING_STRIKE, SIGIL_LETHARGY
from inventory_tracking.builds.warlock.ward import PSYCHIC_WARD_GUARD
from inventory_tracking.combat.policy import RUN_MODES, Foe, walls
from inventory_tracking.combat.sim import casters
from inventory_tracking.combat.sim.casters import mind_of
from inventory_tracking.combat.sim.guard import Guard
from inventory_tracking.combat.stance import no_footing, way
from inventory_tracking.config import INPUT, HealingConfig
from inventory_tracking.game.layout import (
    DEFILER_CLASS,
    FULL_REJUVENATION,
    MONSTER_UNIT,
    NO_OWNER,
    OBJECT_UNIT,
    SUPER_HEALING,
)
from inventory_tracking.game.records import (
    GOLD,
    HEALING,
    REJUVENATION,
    VALUABLE,
    Drop,
    Loot,
    Monster,
    Teleport,
    Thing,
    World,
)
from inventory_tracking.input import Refused
from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.geometry import Point
from inventory_tracking.levels.model import Ground, Walkable
from inventory_tracking.macros.build import Attack
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.movement import TELEPORT_JUMP
from inventory_tracking.macros.routines import ACTING
from inventory_tracking.macros.skills import SWAP_WEAPONS, TELEPORT
from inventory_tracking.macros.teleport import WALKING
from inventory_tracking.macros.travel import walked_way
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
from inventory_tracking.native.layout import BELT_COLUMNS, BELT_SIZE, CORPSE_MODE, DEAD_MODES, HIRELING_CLASS_ID
from inventory_tracking.takes.timeline import GAME_RATE
from inventory_tracking.tracking.belt import potion_kind
from tests.inventory_tracking.macros.fakes import KEYS, Clock, Game, player
from tests.inventory_tracking.scenarios.arena.mobs import HERO_BODY, SIGIL_SLOW, Mobs, body_of, raw_resists
from tests.inventory_tracking.scenarios.arena.result import Result
from tests.inventory_tracking.scenarios.arena.scene import Scene
from tests.inventory_tracking.scenarios.threat.harness import RUN


POTIONS = {
    int(class_id): row
    for class_id, row in json.loads((Path(__file__).parent / 'potions.json').read_text()).items()
    if not class_id.startswith('_')
}
POTION_CLASS = {row['code']: class_id for class_id, row in POTIONS.items()}  # a scene's drop has the code
# The potions the pickup step sees on the ground and what it takes them for (game/
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
# Blade Warp's casting delay as the game plays it: the character's state 185 `cooldown` (game/
# `Player.cooldown`) is set WARP_DELAY_SHOWN after the key and cleared WARP_DELAY_OVER after it (the take of
# 12:33 on 2026-10-13: 0.20 s, then 0.80 s long, 64 warps of 64); a warp key before that is refused: it moves
# nobody and is counted (`Arena.refused_warps`, its seconds after the key before).
WARP_DELAY_SHOWN, WARP_DELAY_OVER = 0.20, 1.00
# Sigil: Lethargy as the takes of 2026-10-20 show it (builds/warlock/buffs.py, the medians): its missile 0.37 s after
# the key, its state on a monster 0.48 s after; the missile class of the radius the character's level gives
SIGIL_MISSILE_SHOWS, SIGIL_STATE_SHOWS = 0.37, 0.48
SIGIL_MISSILE = next(kind for kind, radius in SIGIL_MISSILES.items() if radius == SIGIL_RADIUS)
BODY_LIFT = 3.0  # units down the screen from the pointer's ground that a monster's picture still covers
BODY_HALF = 1.5  # units: how far from that line a monster's feet may be
# How the companions keep up with the character (`Arena.follow`), from the Chaos Sanctuary takes since 2026-10-12
# (rca/2026-10-13/sim-casters.md): by type, the distance to the character it stands at (the median) and its pace
# when it closes in (the median step of a frame it moved by less than 3 units): the Defiler 744 4.4 and 0.41, the
# mercenary 338 5.1 and 0.32, the Pit Lord 361 2.7 and 0.97. Each was within 19.6 to 28 units (p99) and came back
# from farther by a jump to within 0.6 of the character (689, 670 and 605 jumps): one farther than JUMP is put
# BESIDE it. Neither the jump's own rule nor a companion's going for monsters is played.
FOLLOW: dict[int, tuple[float, float]] = {744: (4.4, 0.41), 338: (5.1, 0.32), 361: (2.7, 0.97)}
FOLLOW_DEFAULT = (5.0, 0.4)
JUMP = 18.0
# A jump takes the demons near the character along and off the marked monster (`Game.drag`, the measure of
# builds/warlock/mark.py DESIGNATED_MARK, 2026-10-22). False (the default): the demons stay on it, as before.
HOP_DRAG = False
# ALLIES_ALONG (2026-10-23, rca/2026-10-23/death-canyon-findings.md): a Teleport takes every companion within
# TAKEN_ALONG of where it began along, the mercenary too (rca/2026-10-21/herald-gloam-findings.md §3, verified over
# 312 Teleports: an ally within 10 lands within 3 of the character on 95-100 % of them), each ALONG_GAP off the landing
# (the take: the merc within 3 for 42.9 of 46.5 s). Blade Warp is not a Teleport: not taken (not measured). False: the
# demons by HOP_DRAG alone and the merc by `follow`, as before
ALLIES_ALONG = False
# WARP_ALONG (2026-10-24, rca/2026-10-24/dm-latency-findings.md §11, stopwatch-findings.md §2): a Blade Warp takes the
# companions along as a Teleport does (with ALLIES_ALONG). Take 20261024T171736Z-71: the Blade Warp of 15 landed at
# 20:18:41.539 with the War Defiler and the bound demon 0.1 off the character, idle until the next Death Mark's curse
# at 43.062; the stopwatch's T5 stands of 18:49-21:03 run on across the moves' hops, the demons along on each. False:
# a Blade Warp takes none, as before
WARP_ALONG = False
ALONG_GAP = 1.0
ALONG_SIDES = 3
# MERC_HURT (2026-10-23, same findings): the mercenary takes the blows that land on it off its own life (its most from
# the scene, its share the row's 128ths), as the pets do (PETS_FIGHT), and is gone at 0 (the canyon's fell at 69.9 s
# of take 20261023T115109Z-46). False: it takes no life, as before
MERC_HURT = False
# PURE_BINDS (2026-10-24, rca/2026-10-23/realtime-3-findings.md §3): `read` is a look with the game's time in it (it
# holds the character in a hop's cast, ends a walk when a cast began, casts the keys kept during a cast), so a look a
# change adds changes the arena's fight by itself, never the game's (one extra look per strike aim: manaburn deaths 5
# -> 2 over seeds 1-8, no strike moved). True: a bind's look (macros/binding.py `newest_world`, every bind's one way
# to the newest world) is `peek`, the world as it stands with no look's side effects, for the play (`pure_binds`).
# False: a bind looks by `read`, as before.
PURE_BINDS = False
# HOP_IDLE (2026-10-24, rca/2026-10-24/aggro-findings.md §9; the player, ~11:30: "daemon/merc are staying not active
# for some time after teleport"): the demons a Teleport of REMARK_HOP or more took along (ALLIES_ALONG, HOP_DRAG) go for
# no hostile and strike none (`idling`) until a Death Mark's jump sends them or a time drawn from HOP_IDLE_LEFT. The
# live T4-5 Herald fights of 2026-10-24 (145 takes, 246 hops, scratchpad aggro/baseline.py): the share of hops with
# no demon striking yet and no mark keyed, by the seconds after the landing (Kaplan-Meier, censored at the next hop or
# mark); past the last knot the demons stay idle until a mark. False: they go for the hostiles at once, as before.
HOP_IDLE = False
HOP_IDLE_LEFT = ((0.0, 1.0), (0.25, 0.93), (0.5, 0.90), (1.0, 0.84), (1.5, 0.72), (2.0, 0.61), (3.0, 0.57))
# PETS_MARK_ONLY (2026-10-24, same findings; the player, 2026-10-14: "death mark is skill that forces daemons to
# attack"): a demon no Death Mark sends goes for no hostile (it keeps up with the character, `follow`) and strikes one
# in its reach on PET_OWN_STRIKE of the ticks only. The same live fights: some demon strikes on 66 % of the fight time
# 0.5-1 s after a mark's key, 26-28 % 2-8 s after, 10 % 12 s and more after; while none strikes the nearest demon stands
# a median 5.4 units from a hostile (a quarter within 2.8), so a hostile in reach is no reason by itself. False: a demon
# goes for any hostile within PET_ENGAGE and strikes every tick, as before.
PETS_MARK_ONLY = False
PET_OWN_STRIKE = 0.15
# The pets as the game plays them (2026-10-24 ~00:10, dm-latency-findings.md §11; the stopwatch's T5 stands of
# 18:49-21:03 and the player: a Teleport or a Blade Warp pulls the demons back to the character, they stand there, and
# the old curse does not send them again): ALLIES_ALONG, WARP_ALONG, HOP_IDLE and PETS_MARK_ONLY together
# (`pets_as_game`). Each stays False by itself, as before
PETS_AS_GAME = ('ALLIES_ALONG', 'WARP_ALONG', 'HOP_IDLE', 'PETS_MARK_ONLY', 'PETS_FOLLOW')
# PETS_FOLLOW (2026-10-25, the same): the companions keep up with the character and a Death Mark's demons go to its
# monster (`follow`) in every scene, not only the casters' scenes and those with PETS_FIGHT; where they stood still
# (the Baal chamber) a mark sent no one, and R1's idle-demon mark went out every PETS_AGAIN s for 50 s. False: as
# before
PETS_FOLLOW = False
BESIDE = 0.6
# The rules a play may turn on (the module text).
SIGIL_SLOWS, PETS_FIGHT, BODIES_BLOCK, MANA_SHOWN = 'sigil slows', 'pets fight', 'bodies block', 'mana shown'
REVIVERS_RAISE = 'revivers raise'
RULES = frozenset((SIGIL_SLOWS, PETS_FIGHT, BODIES_BLOCK, MANA_SHOWN, REVIVERS_RAISE))
# A Defiler the macro summons, in points: monstats warputriddefiler (744) MinHP(H) 300% of monlvl HP(H) 4205 at level
# 80 (pricing/raw/game-excel, 2026-10-21); the summon's own life bonus (skills.txt 377 calc1: 35% a level) is not
# counted. An assumption of this file.
PET_POINTS = 12_600.0
PET_ENGAGE = 10.0  # units from a pet within which it goes for a hostile (an assumption: the takes do not say)
PET_STOP = 2.5  # units from the hostile it goes for that it stands at (sim/monsters.py REACH x STOP is 2.7)
PET_REACH = 3.2  # units: a pet's reach where damage.json measures none (sim/monsters.py REACH)
BIND_TAKES = 0.6  # seconds from Bind Demon's key until the demon is the character's (an assumption)


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
    teleport: bool = False  # a Teleport's, which takes the allies near along (ALLIES_ALONG)


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
    def transaction(self) -> Generator[Ledger]:
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
    def attempt(self, target: object, request: PotionRequest) -> Generator[Attempt]:
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
            # the raw stat: points times 256 (game/ reads `stats.get(LIFE_STAT) >> 8`)
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


def pets_as_game(set_to: Callable[[object, str, bool], None] = setattr) -> None:
    """The pets as the game plays them (PETS_AS_GAME) turned on through `set_to` (a test's `monkeypatch.setattr`, so
    they are put back after it; the module's own `setattr` for a driver)."""
    module = sys.modules[__name__]
    for name in PETS_AS_GAME:
        set_to(module, name, True)


@contextmanager
def pure_binds(arena: Arena) -> Generator[None]:
    """Within the block a bind's look (macros/binding.py `newest_world`) is `arena.peek()` when PURE_BINDS is on."""
    if not PURE_BINDS:
        yield
        return
    from inventory_tracking.macros import binding

    looked = binding.newest_world

    def peeked(run: Run, *, light: bool = False) -> World:  # a light look leaves out what the game's look holds
        return arena.peek()

    binding.newest_world = peeked
    try:
        yield
    finally:
        binding.newest_world = looked


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
        rules: Iterable[str] = (),
    ) -> None:
        self.rules = frozenset(rules)
        assert self.rules <= RULES, self.rules - RULES
        self.scene = scene.copy()
        hero = self.scene.hero
        self.mobs = Mobs(self.scene, random.Random(seed), auras)
        # The companions keep up with the character (`follow`) in a scene of the types sim/casters.py plays (the
        # Chaos Sanctuary's), where whom a monster goes for is the nearest body; elsewhere they stand where the scene
        # has them, as every scene was fitted and pinned with (before 2026-10-13, casters.PLAYED off: everywhere).
        self.follows = casters.PLAYED and any(
            mind_of(mob.txt) for mob in self.scene.mobs if mob.owner is None and not mob.ally
        )
        stand = replace(
            player(hero.area),  # the fakes' character: its unit id and the mode it stands in
            name=hero.name, x=hero.at[0], y=hero.at[1],
            consume=hero.consume, hex_purge=hero.hex_purge, ward=hero.ward,
            right_skill=RIGHT_SKILL if hero.right_skill is None else hero.right_skill,
        )  # fmt: skip
        # A door row as the stance fixtures hold it: unit, txt, mode, x, y (mobs.py reads the same).
        doors = tuple(Door(row[0], row[1], row[2], float(row[3]), float(row[4])) for row in self.scene.doors)
        super().__init__(World(True, (), 'arena', tuple(hero.slots), player=stand, doors=doors))
        # Psychic Ward as a guard (builds/warlock/ward.py, sim/guard.py): up as the scene opens when the state
        # shows it there; a cast of it (`Game.wards`, one a cast) sets it at the next tick; at 0 its state is gone
        # (`play_tick`) and the build's buff rules cast it again. It meets only the blows of the types the client's
        # rules play (`Mobs._ruled`).
        self.guard = Guard(PSYCHIC_WARD_GUARD, up=bool(hero.ward))
        self.mobs.guard = self.guard
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
        self.raws = [raw_resists(found.codes) for found in hero.sets]
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
        # Death Mark (`mark`): (the marked unit, when the demons jump, when the mark ends), and every mark cast
        self.marked: tuple[int, float, float] | None = None
        self.mark_casts: list[tuple[float, int]] = []  # (clock, unit) of each mark that took
        # The mark that takes nowhere (2026-10-20's takes: 26 of 397 keys on a live target, 6.5%): the share of keys
        # that mark no one (`mark`, rolled by `mark_rolls`); 0: every key marks the hostile under the pointer. Every
        # key with where it went, None nowhere (`mark_keys`).
        self.mark_misses = 0.0
        self.mark_rolls = random.Random(seed + 7)
        self.mark_keys: list[tuple[float, int | None]] = []
        self.idle_until = -math.inf  # HOP_IDLE: the clock until which the demons taken along stand off the fight
        self.idle_rolls = random.Random(seed + 11)
        self.own_rolls = random.Random(seed + 13)  # PETS_MARK_ONLY: an unsent demon's strikes of its own
        self.sigil: tuple[Point, float] | None = None  # the character's last sigil: (where, the clock its cast began)
        # PETS_FIGHT: each pet's (life, most life) in points; the deaths (clock, unit, type); the points they dealt.
        self.pets: dict[int, tuple[float, float]] = {}
        self.pet_deaths: list[tuple[float, int, int]] = []
        self.pet_dealt = 0.0
        # Bind Demon: the unit under the pointer at the key and the clock it is the character's at; the binds made
        self.binding: tuple[int, float] | None = None
        self.binds: list[tuple[float, int]] = []
        self.summons: list[tuple[float, Point, Point]] = []  # each Defiler summoned: (clock, where, the character)
        self.flights: list[Flight] = []
        self.refused: list[Point] = []  # where a hop, a warp or a walk was aimed and nobody can go
        self.warped_at: float | None = None  # the clock at the last Blade Warp key the game took
        self.refused_warps: list[float] = []  # a warp key in the casting delay: seconds after the key before
        self.each_tick: Callable[[], None] | None = None  # the driver's: called after every tick
        self.world = replace(self.world, monsters=tuple(m for m in self.mobs.monsters() if m.mode not in DEAD_MODES))
        self.show()
        if not self.mobs.live():
            self.cleared_at = 0.0

    def _drops(self) -> list[Drop]:
        """The scene's drops as the pickup step reads them (game/memory.py `GameMemory.loot`): a pile
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
        the life in whole points (game/records.py `Loot.life`; 0 is unreadable there, so 1 at least
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
        # The same current-set stats the live loot read exposes to safety. No
        # opponent RNG, future potion, or unobserved alternate set is revealed.
        from inventory_tracking.macros.safety import RESISTS

        raw = self.raws[self.hand]
        values = (
            dict(raw)
            if raw is not None
            else {kind: (1 - through) * 100 for kind, through in self.resists[self.hand].items()}
        )
        curse = self.mobs.pack.minds.hex_on(0, self.mobs.frame)
        if curse is not None:
            for kind, delta in curse.resists.items():
                values[kind] = values.get(kind, 0.0) + delta
        stats = (
            *(
                (stat, round(values.get(kind, 0.0) + (100 if kind not in ('physical', 'magic') else 0)))
                for stat, kind in RESISTS
            ),
            (31, 771),
            (12, 94),
            (20, 10),
        )
        if MANA_SHOWN in self.rules:
            hero = self.scene.hero
            stats = (*stats, (8, round(hero.mana * 256)), (9, round(hero.max_mana * 256)))  # 8 fraction bits
        self.loot = replace(self.loot, life=life, max_life=round(self.max_life), stats=stats)

    def read(self) -> World:
        if self.over is not None:
            return self.world  # the world stands still: no cast ends, no held input casts
        stand = self.world.player
        if stand is not None and not self.instant_moves:
            since = math.inf if self.warped_at is None else self.clock.now - self.warped_at
            cooling = WARP_DELAY_SHOWN - EDGE <= since < WARP_DELAY_OVER - EDGE
            if stand.cooldown != cooling:
                self.world = replace(self.world, player=replace(stand, cooldown=cooling))
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

    def peek(self) -> World:
        """The world a look sees now, with none of `read`'s side effects (PURE_BINDS): the casting delay shown as
        `read` shows it, nothing held, halted, set out or cast, nothing stored."""
        world, stand = self.world, self.world.player
        if self.over is None and stand is not None and not self.instant_moves:
            since = math.inf if self.warped_at is None else self.clock.now - self.warped_at
            cooling = WARP_DELAY_SHOWN - EDGE <= since < WARP_DELAY_OVER - EDGE
            if stand.cooldown != cooling:
                world = replace(world, player=replace(stand, cooldown=cooling))
        return world

    def run(self, seed: int = 1) -> Run:
        run = super().run(seed)
        run.say = self.say
        run.corpses = self.mobs.corpses
        run.unit_states = self.unit_states  # whether a mark took (macros/buffs.py `Buffs.settle`)
        run.flights = self.missiles  # the monsters' and the character's sigil (`missiles`)
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
        if self.follows or PETS_FIGHT in self.rules or PETS_FOLLOW:
            self.follow()
        self.bound_now(now)
        mates = [m for m in self.world.monsters if m.ally or m.owner != NO_OWNER]
        companions = [(m.x, m.y) for m in mates]
        if len(self.wards) > self.guard.sets:
            self.guard.set()  # a cast of Psychic Ward since the last tick (`Game` counts it at its key)
        self.mobs.raw = self.raws[self.hand]  # what a curse moves (mobs.py RAW_RESISTS)
        self.mobs.pack.slowed = self.slow_at if SIGIL_SLOWS in self.rules else None
        if BODIES_BLOCK in self.rules:
            self.mobs.pack.bodies = [(self.here, HERO_BODY), *(((m.x, m.y), body_of(m.txt_id)) for m in mates)]
        blows = min(self.mobs.tick(self.here, companions, self.resists[self.hand]), self.life)
        if REVIVERS_RAISE in self.rules:
            self.mobs.raise_dead()
        if PETS_FIGHT in self.rules:
            self.pets_hurt(now, mates)
            self.pets_strike()
        self.taken += blows
        self.life -= blows
        stand = self.world.player
        if stand is not None and stand.ward and not self.guard.up:
            self.world = replace(self.world, player=replace(stand, ward=False))  # the pool ran out: the state is gone
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

    def follow(self) -> None:
        """The companions keep up with the character in a scene of the casters (`follows`): one
        farther than JUMP is put beside it, one farther than its HEEL walks toward it at its pace. The demons
        of a Death Mark (`marked`) stand MARK_BESIDE from the marked monster instead, on their own side of it,
        from their jump until it dies or the mark ends."""
        here, moved = self.here, []
        held = self.held()
        for monster in self.world.monsters:
            if not (monster.ally or monster.owner != NO_OWNER):
                moved.append(monster)
                continue
            if held is not None and sends(self.world, monster):
                gap = math.dist(held, (monster.x, monster.y))
                if abs(gap - MARK_BESIDE) > 0.5:
                    dx, dy = ((monster.x - held[0]) / gap, (monster.y - held[1]) / gap) if gap > 1e-6 else (1.0, 0.0)
                    monster = replace(monster, x=held[0] + dx * MARK_BESIDE, y=held[1] + dy * MARK_BESIDE)
                moved.append(monster)
                continue
            gap = math.dist(here, (monster.x, monster.y))
            heel, pace = FOLLOW.get(monster.txt_id, FOLLOW_DEFAULT)
            fights = (
                PETS_FIGHT in self.rules and sends(self.world, monster) and not self.idling() and not PETS_MARK_ONLY
            )
            foe = self.engaged(monster) if fights else None
            if foe is not None and gap <= JUMP:
                away = math.dist(foe, (monster.x, monster.y))
                share = min(pace, away - PET_STOP) / away if away > PET_STOP else 0.0
                moved.append(replace(monster, x=monster.x + (foe[0] - monster.x) * share,
                                     y=monster.y + (foe[1] - monster.y) * share))  # fmt: skip
                continue
            if gap > JUMP:
                spot = (here[0] + BESIDE, here[1])
            elif gap > heel:
                share = min(pace, gap - heel) / gap
                spot = (monster.x + (here[0] - monster.x) * share, monster.y + (here[1] - monster.y) * share)
            else:
                moved.append(monster)
                continue
            moved.append(replace(monster, x=spot[0], y=spot[1]))
        self.world = replace(self.world, monsters=tuple(moved))

    def along(self, start: Point, far: bool) -> None:
        """ALLIES_ALONG: a Teleport took every companion within TAKEN_ALONG of `start` along, each put ALONG_GAP off
        the landing on a side of its own; a demon of the mark off its monster when the jump was `far` (REMARK_HOP)."""
        here, moved, took = self.here, [], False
        index = 0
        for monster in self.world.monsters:
            if (monster.ally or monster.owner != NO_OWNER) and math.dist(start, (monster.x, monster.y)) <= TAKEN_ALONG:
                turn = index * math.tau / ALONG_SIDES
                index += 1
                took = took or (far and sends(self.world, monster))
                monster = replace(
                    monster, x=here[0] + ALONG_GAP * math.cos(turn), y=here[1] + ALONG_GAP * math.sin(turn)
                )
            moved.append(monster)
        self.world = replace(self.world, monsters=tuple(moved))
        if took:
            self.marked = None
            self.idle_after_hop()

    def drag(self, start: Point) -> None:
        """A jump of REMARK_HOP or more took the demons within TAKEN_ALONG of `start` along (HOP_DRAG): beside the
        landing, the mark's hold on its monster gone (the takes of 2026-10-21/22: 2.8 units off the marked one before a
        hop, 21 one second after; rca/2026-10-22/immune-mark-findings.md)."""
        here, moved, took = self.here, [], False
        for monster in self.world.monsters:
            if sends(self.world, monster) and math.dist(start, (monster.x, monster.y)) <= TAKEN_ALONG:
                monster, took = replace(monster, x=here[0] + BESIDE, y=here[1]), True
            moved.append(monster)
        self.world = replace(self.world, monsters=tuple(moved))
        if took:
            self.marked = None
            self.idle_after_hop()

    def idle_after_hop(self) -> None:
        """HOP_IDLE: the demons just taken along stand off the fight for a time drawn from HOP_IDLE_LEFT (the share
        still idle by the seconds after the landing, linear between knots; past its last, until a mark)."""
        if not HOP_IDLE:
            return
        roll = self.idle_rolls.random()
        seconds = math.inf
        for (early, more), (late, less) in itertools.pairwise(HOP_IDLE_LEFT):
            if less <= roll <= more:
                seconds = early + (late - early) * (more - roll) / (more - less) if more > less else late
                break
        self.idle_until = self.clock.now + seconds

    def idling(self) -> bool:
        """HOP_IDLE: whether the demons stand off the fight after a hop: the drawn time not over and no Death Mark's
        jump sent them since (`held`)."""
        if self.idle_until <= self.clock.now:
            return False
        if self.held() is not None:
            self.idle_until = -math.inf
            return False
        return True

    def engaged(self, pet: Monster) -> Point | None:
        """Where the hostile a pet goes for stands (PETS_FIGHT): the nearest live one within PET_ENGAGE of it."""
        at = (pet.x, pet.y)
        near = [self.mobs.mobs[unit].at for unit in self.mobs.live()]
        near = [spot for spot in near if math.dist(spot, at) <= PET_ENGAGE]
        return min(near, key=lambda spot: math.dist(spot, at)) if near else None

    def hurts(self, mate: Monster) -> bool:
        """Whether the blows on companion `mate` come off its life: a pet's (PETS_FIGHT), the mercenary's too with
        MERC_HURT."""
        if sends(self.world, mate):
            return True
        return MERC_HURT and mate.txt_id == HIRELING_CLASS_ID and (mate.ally or mate.owner != NO_OWNER)

    def pet_life(self, pet: Monster) -> tuple[float, float]:
        """A pet's (life, most life) in points: kept since its first tick; a scene's companion its own, one the macro
        summoned PET_POINTS."""
        found = self.pets.get(pet.unit_id)
        if found is None:
            mob = self.mobs.mobs.get(pet.unit_id)
            found = (mob.life, mob.full) if mob is not None and mob.full > 0 else (PET_POINTS, PET_POINTS)
            if mob is not None and pet.txt_id == HIRELING_CLASS_ID and found[0] <= 128 < found[1]:
                found = (found[1] * found[0] / 128, found[1])  # the scene's mercenary row: its life in 128ths
            self.pets[pet.unit_id] = found
        return found

    def pets_hurt(self, now: float, mates: list[Monster]) -> None:
        """The blows of this tick on the pets (PETS_FIGHT): off their life, shown in 128ths; one at 0 is gone."""
        hurt: dict[int, float] = {}
        for index, points in self.mobs.mate_blows:
            if 0 <= index < len(mates) and self.hurts(mates[index]):
                hurt[mates[index].unit_id] = hurt.get(mates[index].unit_id, 0.0) + points
        kept = []
        for monster in self.world.monsters:
            if not self.hurts(monster):
                kept.append(monster)
                continue
            life, full = self.pet_life(monster)
            life -= hurt.get(monster.unit_id, 0.0)
            self.pets[monster.unit_id] = (life, full)
            if life <= 0.0:
                self.pet_deaths.append((now, monster.unit_id, monster.txt_id))
                continue
            kept.append(replace(monster, life=max(1, round(128 * life / full)), max_life=round(full)))
        self.world = replace(self.world, monsters=tuple(kept))

    def pets_strike(self) -> None:
        """Each pet strikes the nearest live hostile within its reach at its points a frame (PETS_FIGHT)."""
        rates = companion_table()
        if self.idling():
            return
        unsent = PETS_MARK_ONLY and self.held() is None
        for pet in self.world.monsters:
            if not sends(self.world, pet):
                continue
            if unsent and self.own_rolls.random() >= PET_OWN_STRIKE:
                continue
            reach = rates.get(pet.txt_id, (PET_REACH, 0.0))[0]
            rate = demon_rate(pet.txt_id)
            live = [unit for unit in self.mobs.live() if math.dist(self.mobs.mobs[unit].at, (pet.x, pet.y)) <= reach]
            if not live or rate <= 0:
                continue
            unit = min(live, key=lambda found: math.dist(self.mobs.mobs[found].at, (pet.x, pet.y)))
            self.pet_dealt += rate
            if self.mobs.hit(unit, rate, by_pet=True):
                self.kills.append(unit)

    def bind(self, begun: float) -> None:
        """Bind Demon's key (the module text): the live demon under the pointer is the character's BIND_TAKES on."""
        unit = self.monster_under_pointer()
        if unit is None or bound(self.world):
            return
        found = next((m for m in self.world.monsters if m.unit_id == unit), None)
        if found is not None and bindable(found):
            self.binding = (unit, begun + BIND_TAKES)

    def bound_now(self, now: float) -> None:
        """A bind whose time has come: the monster out of the hostiles, an ally where it stands (`Mobs.turn`)."""
        if self.binding is None or now < self.binding[1]:
            return
        unit, _ = self.binding
        self.binding = None
        if unit not in self.mobs.live() or bound(self.world):
            return
        self.mobs.turn(unit)
        self.world = replace(
            self.world, monsters=tuple(replace(m, ally=True) if m.unit_id == unit else m for m in self.world.monsters)
        )
        self.binds.append((now, unit))

    def slow_at(self, at: Point) -> float:
        """The factor the character's sigil puts on a walker at `at` (SIGIL_SLOWS): SIGIL_SLOW within its radius
        while its state shows, 1 else."""
        sigil = self.sigil_lying(SIGIL_STATE_SHOWS)
        return SIGIL_SLOW if sigil is not None and math.dist(sigil, at) <= SIGIL_RADIUS else 1.0

    def held(self) -> Point | None:
        """Where the monster the demons hold stands: the marked one, alive, its mark on and the jump made."""
        if self.marked is None:
            return None
        unit, jump, until = self.marked
        now = self.clock.now
        if now >= until or unit not in self.mobs.live():
            self.marked = None
            return None
        return self.mobs.mobs[unit].at if now >= jump else None

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
                    if self.marked is not None and self.marked[0] == unit and self.clock.now < self.marked[2]:
                        dealt += MARK_POINTS * MARK_ELEMENTS  # the mark's flat points on each element of a hit
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
            busy_until = self.acting_until  # a key during a cast is cast once it is over
            if name in CAST_KEYS:
                self.halt()
            pets = {m.unit_id for m in self.world.monsters if m.txt_id == DEFILER_CLASS}
            super().act(event)  # Teleport's key comes back as `hop`, a held strike as `strike`
            self.summons += [
                (self.clock.now, (m.x, m.y), self.here)
                for m in self.world.monsters
                if m.txt_id == DEFILER_CLASS and m.unit_id not in pets
            ]
            if name in CAST_KEYS and free and self.acting_until is None:
                self.quick_cast(name)
            if key == KEYS[DEATH_MARK] and DEATH_MARK in self.world.slots:
                self.mark(self.clock.now if busy_until is None else busy_until)
            if name == KEYS[SIGIL_LETHARGY]:  # a mouse button (Button9) as the key file has it
                self.lay_sigil(self.clock.now if busy_until is None else busy_until)
            if key == KEYS[BIND_DEMON] and BIND_DEMON in self.world.slots:
                self.bind(self.clock.now if busy_until is None else busy_until)
            if key == KEYS[SWAP_WEAPONS]:
                self.swaps += 1
                self.hand = 1 - self.hand
        self.show()

    def mark(self, begun: float) -> None:
        """Death Mark's key: on the live hostile under the pointer, with a demon of the character's out (the skill
        needs one), the demons go to it MARK_JUMP after its cast begins (`begun`: the key, or the end of the cast
        under way at it) and hold it (`follow`) for MARK_SECONDS."""
        unit = self.monster_under_pointer()
        if unit is None or not any(sends(self.world, m) for m in self.world.monsters):
            self.mark_keys.append((self.clock.now, None))
            return
        if self.mark_misses and self.mark_rolls.random() < self.mark_misses:
            self.mark_keys.append((self.clock.now, None))
            return
        self.marked = (unit, begun + MARK_JUMP, begun + MARK_SECONDS)
        self.mark_casts.append((self.clock.now, unit))
        self.mark_keys.append((self.clock.now, unit))

    def lay_sigil(self, begun: float) -> None:
        """Sigil: Lethargy's key: its missile lies on the ground under the pointer, cast from `begun` (the key, or the
        end of the cast under way at it); it ends the last."""
        self.sigil = (self.ground_under_pointer(), begun)

    def sigil_lying(self, shows: float) -> Point | None:
        """Where the character's sigil lies, read `shows` or more after its cast began and before SIGIL_LASTS."""
        if self.sigil is None:
            return None
        at, begun = self.sigil
        return at if shows <= self.clock.now - begun <= SIGIL_LASTS else None

    def unit_states(self, monster: Monster) -> bytes:
        """A monster's state words as the game holds them (game/layout.py STATE_RUN): Death Mark's state (MARK_STATE)
        on the marked one while its mark lasts, from the key (the takes: it shows 0.3-0.8 s after); the sigil's
        (SIGIL_STATE) on one within its radius (`sigil_lying`); nothing else."""
        states = set()
        if self.marked is not None and self.marked[0] == monster.unit_id and self.clock.now < self.marked[2]:
            states.add(MARK_STATE)
        sigil = self.sigil_lying(SIGIL_STATE_SHOWS)
        if sigil is not None and math.dist(sigil, (monster.x, monster.y)) <= SIGIL_RADIUS:
            states.add(SIGIL_STATE)
        words = bytearray(32)
        for state in states:
            word, bit = divmod(state, 32)
            value = int.from_bytes(words[word * 4 : word * 4 + 4], 'little') | 1 << bit
            words[word * 4 : word * 4 + 4] = value.to_bytes(4, 'little')
        return bytes(words)

    def missiles(self, kinds: frozenset[int]) -> tuple[tuple[int, int, float, float], ...]:
        """The missiles in flight of the classes `kinds` as game/decode.py `flights` reads them: the monsters'
        (`Mobs.flights`) and the character's sigil while it lies (`sigil_lying`)."""
        found = self.mobs.flights(kinds)
        sigil = self.sigil_lying(SIGIL_MISSILE_SHOWS)
        if sigil is None or SIGIL_MISSILE not in kinds or self.world.player is None:
            return found
        return (*found, (self.world.player.unit_id, SIGIL_MISSILE, sigil[0], sigil[1]))

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

    def cast_to(self, spot: Point, seconds: float, teleport: bool = False) -> None:
        """The cast of a skill that puts the character at `spot` in `seconds` from now: it stands and
        casts until the first tick at or after that time, which has it there (`move`)."""
        self.halt()
        due = math.ceil((self.clock.now + seconds) * GAME_RATE - 1e-6)
        self.landing = Landing(max(due, self.time.ticks + 1), spot, teleport)
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
        self.cast_to(spot, TELEPORT_JUMP.takes(math.dist(self.here, spot)), teleport=True)

    def warp(self) -> None:
        """Blade Warp, cast now: the cast, then the blade's flight to the ground under the pointer
        (BLADE_WARP_JUMP), and the character is at the impact."""
        if not self.warp_lands:
            return
        now = self.clock.now
        if self.warped_at is not None and now - self.warped_at < WARP_DELAY_OVER - EDGE:
            self.refused_warps.append(now - self.warped_at)  # in the casting delay: the game takes no warp
            return
        self.warped_at = now
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
            start = self.here
            self.put(landing.spot)
            self.landing = None
            if ALLIES_ALONG and (landing.teleport or WARP_ALONG):
                self.along(start, math.dist(start, landing.spot) >= REMARK_HOP)
            elif HOP_DRAG and math.dist(start, landing.spot) >= REMARK_HOP:
                self.drag(start)
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
        if BODIES_BLOCK in self.rules and self.barred_by_bodies(here):
            self.halt()  # surrounded: the walk stands at the bodies (the module text)
            return
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

    def barred_by_bodies(self, spot: Point) -> bool:
        """Whether a step to `spot` goes into a live hostile's body (BODIES_BLOCK): within the two radii and nearer."""
        here = self.here
        for unit in self.mobs.live():
            mob = self.mobs.mobs[unit]
            gap = math.dist(spot, mob.at)
            if gap < HERO_BODY + body_of(mob.txt) and gap < math.dist(here, mob.at) - 1e-9:
                return True
        return False

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
        hostile = set(self.mobs.hostile)
        mates = [m for m in self.world.monsters if m.unit_id not in hostile]
        super().strike()
        if PETS_FIGHT in self.rules:
            # `Game.strike` takes its kill off the nearest body on the line, a companion of a type it does not know
            # (the bound demon, the mercenary) as readily as a hostile: with the pets real, they are kept (before
            # 2026-10-21 the scenes' companions were someone to go for only, and the plays are pinned so)
            kept = tuple(m for m in self.world.monsters if m.unit_id in hostile)
            self.world = replace(self.world, monsters=(*kept, *mates))
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
