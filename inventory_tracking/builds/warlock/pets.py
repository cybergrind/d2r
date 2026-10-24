"""The character's pets watched: each one's life over the last seconds, its fall, its loss, and whether an Engorge
brought a heal (rca/2026-10-21/demon-lost-findings.md). The buff plan (buffs.py `engorge_first`) asks it every look of
the fight and casts Engorge by what it finds; the caster (casters.py `engorge`) tells it when a key went.

The player, 2026-10-21 ~15:45, of the bound Urdar lost to a tier 5 Dark Archer Herald pack: "we have lost our daemon.
analyze and remember how it was done: heavy hitting enemies, several engagements without healing him and monitoring
of his health / could be very easily avoided if we just have use engorge"; "also note, herald was a t5 dark archier -
these especially dangerous".

The pets: the units Death Mark sends (mark.py `sends`: the Defilers, the other summons, the bound demon), never the
mercenary. A monster's life reads in the client's 128ths of its maximum (buffs.py LIFE_SHARE). Pure but for its memory
and its log lines; the memory belongs to one buff executor (`watch_of`).
"""

import math
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

from inventory_tracking.builds.warlock.bind import SUMMONED
from inventory_tracking.builds.warlock.mark import sends
from inventory_tracking.combat.pack import ask_pull, pulled, since_hop
from inventory_tracking.common import LOG
from inventory_tracking.game.layout import DEFILER_CLASS
from inventory_tracking.game.records import Monster, World
from inventory_tracking.native.layout import DEAD_MODES
from inventory_tracking.terror.danger import table as threat_table


# The pet's life said in the log (item 4 of the findings' fix): a line when its life falls fast or under a share
# (`tell`), one when it is lost (`look`), one when an Engorge brought no heal (`judge`). False: the watch keeps its
# memory and says nothing.
PET_LINES = True
LIFE_SHARE = 128  # a monster's life as the client holds it: 128ths of its maximum (buffs.py LIFE_SHARE)
PET_HISTORY = 3.0  # seconds of life kept a pet: the line's "-55 in 1.4s" looks this far back
# A pet falling: this many 128ths lost within PET_FALL_SECONDS (the highest life in them against the last). The take
# 20261021T124057Z-22: the Urdar went 128 -> 105 in 0.45 s as the pack reached it, 128 -> 104 in 0.9 s after its one
# heal, 111 -> 73 in 0.6 s; the Defiler 89 -> 29 in 0.16 s. Over today's 142 takes (2.3 h) 15 in 1.0 s, or under 70%,
# holds a pet 21 s an hour (5 s the bound demon, 16 s the Defilers): ~35 casts an hour at the danger's cadence. 10
# gives 20% more onsets with no loss among them; 20 misses a third of the Defilers' falls.
PET_FALL = 15
PET_FALL_SECONDS = 1.0
PET_SAY_SECONDS = 3.0  # a pet's danger said again this often while it lasts (at its onset at once)
PACK_SAY_SECONDS = 15.0  # the pack's danger said at most this often
# Whether an Engorge brought a heal (the findings' cause 2: the cast at 15:41:36.6 went with an object, type 2, under
# the pointer, and the Urdar's life went 37 -> 34, no heal): a rise of PET_HEALED 128ths or more on a pet with room for
# it, within ENGORGE_HEAL_SHOWS of the key, is a heal. Engorge heals 30% and 1% a level of the pet's life (skills.txt
# 379 calc1 ln34, Param3 30, Param4 1): 38/128 at least; the Urdar's regeneration gives +1 in 0.4 s. The one heal of the
# take showed 0.1-0.3 s after its key (100 -> 128).
PET_HEALED = 10
ENGORGE_HEAL_SHOWS = 0.8  # seconds
PET_FORGET = 10.0  # seconds a pet not seen is kept
TICK = 1e-6  # seconds: a clock summed from steps that holds "this long after"
# The fight pulled off the bound demon (item 5; the player, 2026-10-21 ~16:30: "Yes, pull it out"): with no Engorge
# landing (PULL_UNHEALED in a row that brought no heal, or none keyed for PULL_DRY s of its danger) and the bound demon
# under PULL_BELOW of its life, the tier 4-5 pack's hop back is asked for its sake (combat/pack.py `ask_pull`,
# macros/safety.py `Safety.pack_back`): the character Teleports to a ring beyond the demon from the pack, the demon
# follows it out of the crowd; priced and vetoed by the safety as the keeping-range hops, PACK_HOPS a pack at most (a
# pack that drains mana: its own hop, `burn_back`, BURN_HOPS).
# The take: the Urdar at 34/128 from 15:41:34.9, no Engorge landed since 15:41:29.96: asked from then. False: nothing
# is pulled; `pull_wanted` only says when it would be.
PET_PULL = True
PULL_BELOW = 0.3
PULL_UNHEALED = 2  # Engorges in a row that brought no heal
PULL_DRY = 1.5  # seconds of danger with no Engorge keyed
PULL_HOLD = 1.0  # seconds one ask stands (asked again at every look while it holds)
# No pull again while the bound demon stands out with the character (within PULL_OUT of it) under PULL_REST s after a
# hop landed (combat/pack.py `since_hop`): the hop took it along already and another takes it along again (the
# coordinator, 2026-10-21 ~22:00: 21:05:50-52, "bound Act 5 Combatant at 31/128, 20 Engorges with no heal", 4 hops
# in 2 s that pushed the fight from 25 to 44+ units off an easy Herald; rca/2026-10-21/arachnid-herald-2-findings.md).
# False: asked again at every look while the pull is wanted, as before.
PULL_ONCE_OUT = True
PULL_OUT = 5.0  # units
PULL_REST = 3.0  # seconds after a landing
# Engorge learns from what its key did (the player, 2026-10-23: "your goal is to maximize exp/hour";
# rca/2026-10-23/unraveler-findings.md). Live 15:07:41-15:09:46 (take 20261023T120656Z-66, a tier 5 Unraveler Herald
# pack): 27 keys, 20 on the one corpse 3426990368, "brought no heal" again and again, the pets 128/128 and their
# Engorge state on most of it; each key let the held strike go 0.53 s (the take's button events). Over last night's and
# today's takes (20.6 h) 554 of 1,614 keys did nothing: 248 with the state off and still off after, 286 with the
# state up on every pet and none with room for a heal, 20 again on a corpse that had shown nothing (1 of 21 such keys
# took). Engorge's buff (skills.txt 379 aurastate engorge, ln56) lasts 47.3 s at the character's level (the median of
# the takes' state spans after one key). True: a corpse whose key showed no effect (no heal on a pet with room for one,
# no ENGORGE_STATE turned on on a pet without it) is not tried again (`refused`, casters.py `engorge`), and the buff
# for its own sake (buffs.py ENGORGE_PACK_FIRST, `engorge_due`) is not cast while every pet alive shows the state
# (`buffed`); a pet in danger still gets its heal. False: every corpse and every cadence, as before.
# The arena, 20 seeds a scene off -> on (the 13 danger fights, both Fane cuts, the canyon, Dominus, the revivers'
# scenes and the cuts of 15:07 and 15:59-16:01; the arena plays no Engorge heal or state, so there every corpse is
# refused after one key): no new death (the canyon 22 of 60 either way), no scene's least or median lowest life lower;
# strikes in the 60 s cut of 15:07 87.3 -> 87.9, of 16:00 78.0 -> 81.2. Since 2026-10-23 ~17:10 a corpse under an
# object or an item's label is refused too (casters.py STILL_COVERS).
ENGORGE_LEARNS = True
ENGORGE_STATE = 211  # states.txt `engorge` (skills.txt 379 aurastate): on a pet while the buff lasts
REFUSED_MOST = 400  # corpses remembered refused at most (a game's unit ids: one set a watch)


@dataclass
class Pet:
    """One pet as the watch remembers it."""

    unit: int
    txt: int
    seen: deque[tuple[float, int]] = field(default_factory=deque)  # (clock, life in 128ths), the last PET_HISTORY s
    whole: int = LIFE_SHARE  # its life at full, in the read's units (128ths)
    last_at: float = -math.inf  # clock it was last seen at
    said_at: float = -math.inf  # clock its danger was last said at
    endangered: bool = False  # in danger at its last look
    danger_since: float = math.inf  # clock its danger began at (inf: not in danger)
    lost: bool = False  # said lost

    @property
    def bound(self) -> bool:
        """The bound demon (Bind Demon's petmax 1): none of the Warlock's summons (bind.py SUMMONED)."""
        return self.txt not in SUMMONED

    @property
    def life(self) -> int:
        return self.seen[-1][1] if self.seen else 0


@dataclass(frozen=True)
class Trial:
    """One Engorge key whose corpse is judged (ENGORGE_LEARNS): its clock, the corpse, the pets' life with room for
    a heal at the key, and the pets whose state words showed no ENGORGE_STATE then."""

    at: float
    corpse: int
    room: dict[int, int]
    bare: frozenset[int]


def shows(words: bytes | None) -> bool | None:
    """Whether a unit's state words show ENGORGE_STATE (32 states to a little-endian word); None unread."""
    if not words:
        return None
    word, bit = divmod(ENGORGE_STATE, 32)
    if len(words) < (word + 1) * 4:
        return None
    return bool(int.from_bytes(words[word * 4 : word * 4 + 4], 'little') >> bit & 1)


States = Callable[[Monster], bytes | None]


def buffed(world: World, states: States | None) -> bool | None:
    """Whether every pet alive shows Engorge's state (ENGORGE_STATE); None with no pet, no reader or one unread."""
    live = alive(world)
    if states is None or not live:
        return None
    found = [shows(states(m)) for m in live]
    if any(seen is None for seen in found):
        return None
    return all(found)


def bare(world: World, states: States | None) -> frozenset[int]:
    """The pets alive whose state words read without Engorge's state (`shows` False; unread ones left out)."""
    if states is None:
        return frozenset()
    return frozenset(m.unit_id for m in alive(world) if shows(states(m)) is False)


@dataclass(frozen=True)
class Peril:
    """A pet in danger at a look: the pet, why in words ("-55 in 1.4s", "under 70%")."""

    unit: int
    name: str
    life: int
    why: str
    fresh: bool  # its danger began at this look


def name_of(txt: int, bound: bool) -> str:
    """A pet's name for the log: 'bound Urdar', 'Defiler', a summon's own name (terror/data/threats.json)."""
    if txt == DEFILER_CLASS:
        return 'Defiler'
    row = threat_table().monsters.get(txt)
    found = row.name if row is not None else f'monster {txt}'
    return f'bound {found}' if bound else found


def pets(world: World) -> list[Monster]:
    """The character's pets in the look (mark.py `sends`)."""
    return [m for m in world.monsters if sends(world, m)]


def dead(monster: Monster) -> bool:
    """Whether a pet is dead in the look: a dead mode, or no life left of a life that reads."""
    return monster.mode in DEAD_MODES or (monster.max_life > 0 and monster.life <= 0)


def alive(world: World) -> list[Monster]:
    """The pets alive in the look."""
    return [m for m in pets(world) if not dead(m)]


class PetWatch:
    """The pets' life over the last seconds, for one buff executor (`watch_of`)."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Nothing remembered."""
        self.pets: dict[int, Pet] = {}
        self.at = -math.inf  # clock of the last look
        self.perils: tuple[Peril, ...] = ()  # the pets in danger at the last look
        self.keyed_at: float | None = None  # clock of the last Engorge key not judged yet
        self.keyed_life: dict[int, int] = {}  # unit -> its life at that key, for the pets with room for a heal
        self.last_key = -math.inf  # clock of the last Engorge key
        self.unhealed = 0  # Engorges in a row that brought no heal
        self.pack_said = -math.inf
        self.pack_at = -math.inf  # clock of the last look the pack's Engorge was due at (buffs.py `engorge_first`)
        self.trial: Trial | None = None  # the last key whose corpse is not judged yet (ENGORGE_LEARNS)
        self.refused: set[int] = set()  # corpses whose key showed no effect: not tried again (ENGORGE_LEARNS)
        self.seen_as: dict[int, Monster] = {}  # unit -> the pet as the last look read it, for its state words
        self.states: States | None = None  # the last look's reader of state words (None: none)

    def look(self, world: World, now: float, below: float, states: States | None = None) -> tuple[Peril, ...]:
        """Take the look's pets in; the ones in danger (under `below` of their life, or PET_FALL lost within
        PET_FALL_SECONDS). A pet dead in it is said lost once (PET_LINES). `states` reads a pet's state words, for
        the judgement of the last key's corpse (`settle`)."""
        if now < self.at:  # the clock went back: another game's or another test's
            self.reset()
        if now == self.at:
            return self.perils
        self.at = now
        self.states = states
        for monster in pets(world):
            self.seen_as[monster.unit_id] = monster
            pet = self.pets.get(monster.unit_id)
            if pet is None:
                pet = self.pets[monster.unit_id] = Pet(monster.unit_id, monster.txt_id)
            pet.last_at = now
            if dead(monster):
                if not pet.lost:
                    pet.lost = True
                    self.say_lost(pet, monster, now)
                continue
            if monster.max_life <= 0:
                continue  # its stats unread
            pet.whole = min(monster.max_life, LIFE_SHARE)
            pet.seen.append((now, monster.life))
            while pet.seen and now - pet.seen[0][0] > PET_HISTORY:
                pet.seen.popleft()
        for unit in [u for u, pet in self.pets.items() if now - pet.last_at > PET_FORGET]:
            del self.pets[unit]
            self.seen_as.pop(unit, None)
        self.settle(now)
        self.judge(now)
        found = []
        for pet in self.pets.values():
            if pet.lost or pet.last_at != now or not pet.seen:
                continue
            why = self.danger(pet, now, below)
            if why is not None:
                found.append(Peril(pet.unit, name_of(pet.txt, pet.bound), pet.life, why, not pet.endangered))
            pet.endangered = why is not None
            pet.danger_since = min(pet.danger_since, now) if why is not None else math.inf
        self.perils = tuple(found)
        return self.perils

    @staticmethod
    def danger(pet: Pet, now: float, below: float) -> str | None:
        """Why a pet is in danger now, in words; None when it is not."""
        recent = [life for at, life in pet.seen if now - at <= PET_FALL_SECONDS]
        falling = max(recent) - pet.life >= PET_FALL
        under = pet.life < below * pet.whole
        if not (falling or under):
            return None
        parts = []
        if falling:
            peak = max(life for _, life in pet.seen)
            since = max(at for at, life in pet.seen if life == peak)
            parts.append(f'-{peak - pet.life} in {now - since:.1f}s')
        if under:
            parts.append(f'under {below:.0%}')
        return ', '.join(parts)

    def packed(self, now: float, within: float = 0.5) -> bool:
        """Whether the pack's Engorge was due at a look within `within` s (casters.py `engorge`)."""
        return now - self.pack_at <= within

    def perilous(self, now: float, within: float = 0.5) -> bool:
        """Whether a pet was in danger at a look within `within` s."""
        return bool(self.perils) and now - self.at <= within

    def tell(self, perils: tuple[Peril, ...], now: float, then: str) -> None:
        """Say the pets in danger (PET_LINES): at its onset, then every PET_SAY_SECONDS while it lasts."""
        if not PET_LINES:
            return
        for peril in perils:
            pet = self.pets.get(peril.unit)
            if pet is None or not (peril.fresh or now - pet.said_at >= PET_SAY_SECONDS):
                continue
            pet.said_at = now
            LOG.info('Macro: pet: %s %d/%d, %s: %s', peril.name, peril.life, LIFE_SHARE, peril.why, then)

    def tell_pack(self, world: World, why: str, now: float) -> None:
        """Say the pack's danger to the pets (PET_LINES), at most every PACK_SAY_SECONDS."""
        if not PET_LINES or now - self.pack_said < PACK_SAY_SECONDS:
            return
        self.pack_said = now
        named = ', '.join(f'{name_of(m.txt_id, m.txt_id not in SUMMONED)} {m.life}/{LIFE_SHARE}' for m in alive(world))
        LOG.info('Macro: pet: %s by %s: Engorge first', named or 'the pets', why)

    def say_lost(self, pet: Pet, monster: Monster, now: float) -> None:
        """A pet dead (PET_LINES): the bound demon always; a summon only when it was hurt before, not one taken at full
        life (Consume takes a Defiler so: one look 128, the next 0)."""
        if not PET_LINES:
            return
        before = pet.life if pet.seen else LIFE_SHARE
        if not pet.bound and before >= pet.whole - 8:
            return
        engorged = f'; the last Engorge {now - self.last_key:.1f}s before' if self.last_key > -math.inf else ''
        LOG.info(
            'Macro: pet: %s (%d) lost at %d/%d, %d/%d before%s',
            name_of(pet.txt, pet.bound), pet.unit, max(monster.life, 0), LIFE_SHARE, before, LIFE_SHARE, engorged,
        )  # fmt: skip

    def keyed(self, at: float, corpse: int | None = None, without: frozenset[int] = frozenset()) -> None:
        """An Engorge key went at `at`: its heal is judged ENGORGE_HEAL_SHOWS later on the pets with room for one. One
        not judged yet is judged now by the looks since it. With ENGORGE_LEARNS the key's `corpse` is judged too
        (`settle`): `without`, the pets whose state words showed no ENGORGE_STATE at the key."""
        self.settle(at, early=True)
        self.judge(at, early=True)
        self.last_key = at
        room = {u: p.life for u, p in self.pets.items() if p.seen and not p.lost and p.life <= p.whole - PET_HEALED}
        self.keyed_at, self.keyed_life = (at, room) if room else (None, {})
        if ENGORGE_LEARNS and corpse is not None and (room or without):
            self.trial = Trial(at, corpse, dict(room), frozenset(without))

    def refuse(self, corpse: int) -> None:
        """`corpse` not tried again (ENGORGE_LEARNS): its key showed nothing, or something that stays covers it."""
        if len(self.refused) >= REFUSED_MOST:
            self.refused.clear()
        self.refused.add(corpse)

    def settle(self, now: float, *, early: bool = False) -> None:
        """Whether the last key's corpse showed an effect, once ENGORGE_HEAL_SHOWS has passed (ENGORGE_LEARNS): a heal
        on a pet with room for one, or ENGORGE_STATE on a pet that lacked it. None of either where one could show: the
        corpse is `refused`. `early` (another key is going): by the heal alone, and no verdict without a look since."""
        trial = self.trial
        if trial is None or (not early and now - trial.at < ENGORGE_HEAL_SHOWS - TICK):
            return
        self.trial = None
        healed, looked = False, False
        for unit, life in trial.room.items():
            pet = self.pets.get(unit)
            after = [seen for t, seen in pet.seen if t > trial.at] if pet is not None else []
            looked = looked or bool(after)
            healed = healed or (bool(after) and max(after) - life >= PET_HEALED)
        read = [] if early or self.states is None else [
            shows(self.states(self.seen_as[unit])) for unit in trial.bare if unit in self.seen_as
        ]  # fmt: skip
        if healed or any(read):
            return
        if not (looked or any(seen is False for seen in read)):
            return  # nothing could show either way: no verdict
        self.refuse(trial.corpse)
        if PET_LINES:
            LOG.info(
                'Macro: pet: the Engorge on the corpse %d %.1fs ago showed nothing (no heal%s): not tried again',
                trial.corpse, now - trial.at, ', no Engorge state on the pets' if read else '',
            )  # fmt: skip

    def judge(self, now: float, *, early: bool = False) -> None:
        """Whether the last Engorge key brought a heal, once ENGORGE_HEAL_SHOWS has passed (`unhealed`); `early`: now,
        by the looks since it (another key is going), and not at all with none."""
        if self.keyed_at is None or (not early and now - self.keyed_at < ENGORGE_HEAL_SHOWS - TICK):
            return
        at, before = self.keyed_at, self.keyed_life
        self.keyed_at, self.keyed_life = None, {}
        rose, looked = False, False
        for unit, life in before.items():
            pet = self.pets.get(unit)
            after = [seen for t, seen in pet.seen if t > at] if pet is not None else []
            looked = looked or bool(after)
            rose = rose or (bool(after) and max(after) - life >= PET_HEALED)
        if early and not looked:
            return
        if rose:
            self.unhealed = 0
            return
        self.unhealed += 1
        if PET_LINES:
            hurt = ', '.join(
                f'{name_of(p.txt, p.bound)} {before[u]}/{LIFE_SHARE} -> {p.life}/{LIFE_SHARE}'
                for u, p in self.pets.items() if u in before
            )  # fmt: skip
            LOG.info(
                'Macro: pet: the Engorge %.1fs ago brought no heal (%s): %d in a row', now - at, hurt, self.unhealed
            )


def pull_wanted(watch: PetWatch, now: float) -> str | None:
    """Why the fight is pulled off the bound demon now (PET_PULL), None when it is not: the demon under PULL_BELOW of
    its life, and the last PULL_UNHEALED Engorges brought no heal or none was keyed in PULL_DRY s of its danger."""
    for pet in watch.pets.values():
        if not pet.bound or pet.lost or not pet.seen or pet.last_at != watch.at or pet.life >= PULL_BELOW * pet.whole:
            continue
        dry = now - max(watch.last_key, pet.danger_since)
        if watch.unhealed >= PULL_UNHEALED:
            return f'{name_of(pet.txt, True)} at {pet.life}/{LIFE_SHARE}, {watch.unhealed} Engorges with no heal'
        if dry >= PULL_DRY:
            return f'{name_of(pet.txt, True)} at {pet.life}/{LIFE_SHARE}, no Engorge for {dry:.1f}s'
    return None


def out_with(watch: PetWatch, world: World | None, now: float) -> bool:
    """Whether every bound demon the watch sees stands within PULL_OUT of the character in `world` under PULL_REST s
    after a hop landed (PULL_ONCE_OUT): taken out with it already. False with no world, no character or none seen."""
    if not PULL_ONCE_OUT or world is None or world.player is None or since_hop(now) > PULL_REST:
        return False
    here = (world.player.x, world.player.y)
    bound = {p.unit for p in watch.pets.values() if p.bound and not p.lost}
    found = [m for m in world.monsters if m.unit_id in bound]
    return bool(found) and all(math.dist(here, (m.x, m.y)) <= PULL_OUT for m in found)


def pull(watch: PetWatch, now: float, world: World | None = None) -> str | None:
    """Ask the pack's hop for the bound demon (PET_PULL, `pull_wanted`), said once an ask; why, or None. None while
    the demon was taken out with the character by a hop just now (`out_with`, PULL_ONCE_OUT)."""
    why = pull_wanted(watch, now) if PET_PULL else None
    if why is None or out_with(watch, world, now):
        return None
    if PET_LINES and pulled(now) is None:
        LOG.info('Macro: pet: %s: the fight pulled off it (the pack hop asked)', why)
    ask_pull(why, now + PULL_HOLD)
    return why


@dataclass
class Slot:
    """The one watch kept, and the executor memory it belongs to."""

    owner: object = None
    watch: PetWatch = field(default_factory=PetWatch)


SLOT = Slot()


def watch_of(owner: object) -> PetWatch:
    """The watch of one buff executor, named by its memory of casts (`Buffs.cast_at`, the same dict in every look's
    facts): another executor's first ask starts a new one (one hunt runs at a time)."""
    if SLOT.owner is not owner:
        SLOT.owner, SLOT.watch = owner, PetWatch()
    return SLOT.watch
