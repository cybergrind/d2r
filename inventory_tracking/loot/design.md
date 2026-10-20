# Loot: one abstraction for pickup, appraisal, keeping and the town routine (design, 2026-10-20)

Status: **design only, nothing built**. Asked by the player at 08:42 on 2026-10-20 ("we need to build a single
abstraction that will do everything regarding appraisals"). It replaces decisions spread over a dozen modules
(§1.2) with five layers and one small API (§2). Every number here is dated; prices are scoped asks in Ist
(SC / NL / PC / RotW) from the repo only.

Contents: §0 the player's rules · §1 layers and the module map · §2 the API · §3 the value model · §4 pickup
classes · §5 identify scrolls · §6 test plan · §7 migration · §8 open questions.

---

## 0. The rules this design implements

New, from the request (2026-10-20 08:42):

| # | Rule | Where it lives |
|---|---|---|
| N1 | Duplicates are kept **only for expensive items** | `keep.decide` K5 (§3.3) |
| N2 | A cheap item (e.g. 0.6 Ist) is kept **only if it beats what we already have** | `keep.decide` K6, `value.better_than` (§3.2) |
| N3 | Every kept item knows **which rolls make it valuable** (ethereal, ED, +level, sockets…) | `value.Value.matters` (§3.1) |
| N4 | White/grey bases with good rolls or open sockets are picked up; bad unused bases are not | `ground.judge` (§4) |
| N5 | +3 staff-mod 3os daggers ("+3 Apocalypse"), the best 4os eth merc bases, expensive blues, Monarch of Deflecting 4os (always kept) | §4 classes G4–G8 |
| N6 | No money is needed from sales: an item that fails is **dropped in the field** after a scroll identify, never carried to town | `Item.drop`, `Loot.settle` (§2.4) |
| N7 | Identify scrolls are restocked, used in the field, counted | §5 |
| N8 | A named acceptance test for every very valuable item | §6 |

Standing rules the layers must keep (AGENTS.md; d2-loop-watch SKILL.md "Hard rules"; the loop journal; memory):

| # | Rule | Enforced by |
|---|---|---|
| S1 | Never sell, drop or move the player's items: only the loop's (volatile cells, `macros/volatile-cells.json`, and the cube) | `facts.Owner`, `keep.decide` K0, and again in every `LootHands` action (`engine.protected`) |
| S2 | Never sell runes, gems, potions, set/unique charms (Gheed's, Torch, Anni, Sunders); never a Ber Rune in a transmute | `keep.decide` K1 (NEVER_SELL classes) |
| S3 | Keep one copy of each unique and set ("never drop the last copy") | `keep.decide` K4 |
| S4 | Repairs and purchases from carried gold only, never the stash's | unchanged: `repair.py`, `shop.py` behind `TownHands` |
| S5 | Never leave a game while a valuable lies on the ground | unchanged guard (`lootpolicy.verdict` GUARD, sightings); its "valuable" now comes from `ground.judge` |
| S6 | Labels on before a run | unchanged (`routines.show_items_on`) |
| S7 | Prices only from the repo (`pricing/`), never the web | `value.KnowledgeAppraiser` reads only `pricing.knowledge` / triage data |
| S8 | Unknown is kept: an unread stat, an unreadable collection, no price → keep, never sell or drop | `keep.decide` K2, K7 |

---

## 1. Layers

Five layers, each a package module under `inventory_tracking/loot/` (the package already holds the ground
classifiers, `ground.py`, `shown.py`, `materials.py`…). Each depends only on the layers above it in this table;
layers 1–4 are pure (no input, no memory reads, no clock); only layer 5 touches the game, behind narrow protocols.

| Layer | Module | One-line responsibility | Pure? |
|---|---|---|---|
| 1. Facts | `loot/facts.py` | **What an item is**: base, quality, ethereal, sockets, its rolls (stat id/layer → value), identified or not, where it is, whose it is | yes (adapters from game records) |
| 2. Value | `loot/value.py`, `loot/wants.py` (+ `loot/data/wants.json`) | **What the market and the build say**: price band by its own rolls, demand (build/merc BiS, own-use rows), **which rolls matter** and their good ranges | yes (data + a lookup protocol) |
| 3. Keep decision | `loot/keep.py`, `loot/ground_judge.py` | **What to do with it**: KEEP / KEEP_IF_BETTER→KEEP or DROP / IDENTIFY / DROP / NEVER_TOUCH, with the reason; on the ground: PICK / PICK_TO_IDENTIFY / LEAVE | yes |
| 4. Storage | `loot/storage.py` | **Where things go**: inventory, cube, stash pages, resource tabs; occupancy, room for a size, compaction and stash plans | yes |
| 5. Actions | `loot/hands.py` (protocols), `loot/api.py` (facade), `loot/town.py` (`TownRoutine`) | **Doing it in the world**: pick up, drop (and do-not-pick-again), identify with a scroll, into the cube, stash, sell, restock, repair | no — the only layer with input; behind `LootHands` / `TownHands` |

```
             game memory / identify reads / collection.sqlite (read-only)
                                   │
  1 facts      ItemFacts  ◄── from_drop · from_carried · from_observation · from_collection
                                   │
  2 value      Value      ◄── Appraiser.appraise(facts)   (pricing.knowledge, triage bands, wants.json)
                                   │
  3 decision   Decision   ◄── keep.decide(facts, value, owned)      GroundVerdict ◄── ground_judge.judge(facts, value)
                                   │
  4 storage    StoragePlan ◄── storage.compact / storage.stash_plan / storage.occupied
                                   │
  5 actions    Loot · Item · TownRoutine  ──►  LootHands / TownHands  ──► pickup.py · cube.py · junk.identify · visit.py · shop.py · repair.py
```

### 1.1 Layer types (the plain data that crosses layers)

```python
# loot/facts.py
class Where(StrEnum):
    GROUND = 'ground'; INVENTORY = 'inventory'; CUBE = 'cube'; STASH = 'stash'; EQUIPPED = 'equipped'

class Owner(StrEnum):
    LOOP = 'loop'        # a volatile cell or the cube (macros/volatile.py); the only items any action may touch
    PLAYER = 'player'    # a protected cell, a print match, equipment, the stash
    UNKNOWN = 'unknown'  # not told yet: treated as PLAYER (S1)

@dataclass(frozen=True)
class ItemFacts:
    """What an item is, as read. Unread fields are None, never a guess."""
    unit_id: int
    code: str                      # items.txt code ('uit'), from items/metadata.py, never written from memory
    base_type: str                 # itemtypes code ('shie', 'knif', 'pole'…)
    size: tuple[int, int]
    quality: int                   # ItemData quality: 1 low … 8 crafted
    identified: bool
    ethereal: bool | None
    sockets: int | None            # stat 194; None unread
    rolls: Mapping[str, int]       # 'id:layer' → raw value (the identify read's keys, appraisal/owned.py stat_key)
    name: str | None = None        # unique/set/rare name once identified
    row: int | None = None         # uniqueitems/setitems row (ItemData +0x34) once identified
    where: Where = Where.GROUND
    owner: Owner = Owner.UNKNOWN
    cell: tuple[int, int] | None = None
    page: int | None = None        # stash page (0 personal, 1..5 shared)
    observation: Mapping | None = None  # the identify watcher's full read, when there is one
```

```python
# loot/value.py
@dataclass(frozen=True)
class RollSpec:
    """One roll that decides the price or the use: its stat key, the direction that is better, the range it rolls in
    and the value from which it is 'good' (paid). `facet` rolls (ethereal, sockets) are matched, not ranked."""
    key: str                  # 'id:layer', or a facet: 'ethereal', 'sockets'
    label: str                # 'Enhanced Defense', '+3 Apocalypse'
    low: int; high: int
    better: Literal['higher', 'lower', 'match'] = 'higher'
    good: int | None = None   # the paid floor (Shaftstop 218 ED; Sacred Targe 45 all-res)
    source: str = ''          # file#anchor or file:line

@dataclass(frozen=True)
class Want:
    """A demand row: who uses it (build slot, merc slot, runeword base, trade) and what it must have."""
    who: Literal['warlock', 'merc', 'runeword-base', 'trade']
    label: str                # 'Echoing Strike ring', 'Insight base (merc)', 'Monarch of Deflecting'
    must: tuple[RollSpec, ...]
    always_keep: bool = False # BiS rows (Monarch of Deflecting 4os…): kept whatever the copies
    source: str = ''

@dataclass(frozen=True)
class Value:
    worth_ist: float | None          # the price by its own rolls (identify/service.py value_ist), None unknown
    band: Band | None                # q1/median asks, sellers, observed date
    verdict: str | None              # the triage verdict (sell/slow/check/self/vendor), for the log only
    wants: tuple[Want, ...]          # matched demand rows
    matters: tuple[RollSpec, ...]    # the rolls that decide it (§3.1); () = none known
    tier: Literal['expensive', 'cheap', 'worthless', 'unknown']
    reason: str
```

```python
# loot/keep.py
class Action(StrEnum):
    KEEP = 'keep'               # stash it
    IDENTIFY = 'identify'       # its value needs the identified read: a scroll in the field, Cain in town
    DROP = 'drop'               # loop's item that fails: on the ground, remembered for the game (N6)
    SELL = 'sell'               # only an item already in town whose drop would be the same; see §8 Q4
    NEVER_TOUCH = 'never-touch' # the player's (S1), or a never-sell class carried by the loop: kept as is

@dataclass(frozen=True)
class Decision:
    action: Action
    rule: str                   # 'K5 expensive duplicate', 'K6 not better than 2 owned (ED 50 vs 53, 56)'
    reason: str                 # for the log and the HUD
    compared: tuple[Comparison, ...] = ()  # the owned copies it was compared with, roll by roll
```

```python
# loot/storage.py
@dataclass(frozen=True)
class Storage:
    inventory: Grid; volatile: frozenset[tuple[int, int]]   # the loop's cells of the inventory
    cube: Grid | None; pages: tuple[Page, ...]; stacks: Mapping[int, int]
```

### 1.2 Who decides what today, and where it goes

"Decides" = owns a keep/pickup/sell judgement. Each row says what moves, what stays and what is deleted at the end
of the migration (§7 gives the order).

| Today | What it decides | Layer | Fate |
|---|---|---|---|
| `game/decode.py` `base_rolls`, `rolled`; `game/records.py` `Rolls`, `Drop.rolls` | sockets, staff mods, ED, least res, eth off the ground — only for `knif`, `shie`, `ashd` (`game/layout.py:105-108`) | 1 facts | **stays** as the reader; widened to every base type a §4 class names and to all stats (§4.3); `facts.from_drop` adapts |
| `game/records.py` `Carried`, `Pack`; `engine` `item_stats` | carried items, their stats | 1 facts | stays; `facts.from_carried` adapts |
| `identify/service.py` `_read`/`appraise`, `corpus` `identified/*.json` | the full identified read | 1 facts | stays; `facts.from_observation` adapts |
| `macros/volatile.py` `is_players`, `cube.py` `loot`/`KEPT` | the loop's vs the player's | 1 facts (`Owner`) | stays; its answer becomes `ItemFacts.owner` |
| `appraisal/owned.py` (`match_kind`, `same_item`, `variable_rolls`, `compare_rolls`, `overall`), `macros/copies.py` `owned_copies` | owned copies, roll comparison | 2 value (`OwnedCopies`) + 3 | `owned.py` **stays** (Alt+D uses it); `copies.owned_copies` moves to `loot/value.py` `CollectionCopies`; comparison narrowed to `matters` (§3.2) |
| `identify/service.py` `assessed_verdict`, `value_ist`, `trade_reason`, `KEEP_IST` | price, triage verdict | 2 value | `value_ist` **moves** to `loot/value.py` (service imports it back); `assessed_verdict` stays for the OSD card only |
| `identify/service.py` `owned_verdict` | duplicates by owned copies (1+ Ist rule of 2026-10-19) | 3 keep | **deleted** from the loop's path (`keep.decide` K4–K6); the card shows `keep.decide`'s reason instead |
| `macros/copies.py` `keep_copy`, `sold` | best copy of a `vendor` unique/set | 3 keep | **deleted** (K4–K6 cover every rarity, not only `vendor`) — the Goblin Toe gap (§3.4) |
| `macros/keepers.py` `amulet_keeper` | rare/crafted amulet FCR/life/+2 | 2 value (`wants.json` row) + 3 | **deleted**; becomes the `rare-amulet` want (§4 G9) |
| `macros/junk.py` `junk`, `junk_of`, `JUNK_QUALITIES`; `pickmode.sellable` | what is junk, what may be sold | 3 keep | **deleted**; `Decision.action in (DROP, SELL)`; `sellable`'s exclusions become K1 |
| `macros/junk.py` `identify` (tome clicks) | — (an action) | 5 actions | **moves** to `loot/hands.py` `GameHands.identify` |
| `macros/pickmode.py` `sure`, `judged_base`, `void_base`, `shield_base`, `candidate`, `identified_for`, `SKILLED`, `VOID_*`, `MONARCH…` | what the ground pickup takes, what is an identify candidate | 3 decision (`ground_judge`) | **deleted**; replaced by `ground_judge.judge` and the §4 classes; `pickmode.MODES`/`next_mode`/`kept` stay (GOOD/MOST is a user switch: GOOD = `GroundVerdict.pick`, MOST = today's regular pickup) |
| `game/records.py` `prized`, `NAMED`; `loot/uniques.py`, `materials.py`, `runes.py`, `shown.py` | what the marks point at; what the filter shows | 1 facts (classifiers) | **stay** (they find candidates and draw the HUD); `Drop.prized` is set from `GroundVerdict.must_have` |
| `macros/lootpolicy.py` `verdict`, `trip_for`, `disputed` | per site: take now / hold / trip | 5 (site behaviour) | **stays** (site logic is not appraisal); its inputs `prized`, `is_candidate` come from `GroundVerdict` |
| `macros/sightings.py`, `running/valuables.py` `_picked`/`_valuable_left` | remembered valuables, the guard | 5 | stay; `_picked` calls `ground_judge` instead of `pickmode.kept` |
| `game/kept.py` `PutDown` | items put down this game are not picked again | 5 (do-not-pick memory) | **stays**, gains `reject(unit, code, place, why)` for the loop's own drops (today it logs them as "the player put it down") |
| `macros/cube.py` `plan`, `overflow`, `droppable`, `keys_move`, `BIG_BLOCK`, `SURE_BLOCK` | cube placement, room, what to drop for room | 4 storage | pure parts **move** to `loot/storage.py` (re-exported from `cube.py` during the migration); `droppable` (drops an *unidentified* candidate for room) is **deleted**: identify-then-decide replaces it |
| `macros/town.py` `stash_stop`, `place`, `_make_way`, `surplus`, `sold_full`, `kept_gem`, `TRADE_ROOM`, `Needs`, `contract` | the stash plan, room trigger, the visit's contract | 4 storage (plans) + 5 (`TownRoutine`) | pure planning **moves** to `loot/storage.py`; `contract` and `Needs` stay with the town routine (`loot/town.py`) |
| `macros/loop.py` `free`, `room_low`, `carrying`, `visit_due` | when to go to town | 4 (`occupied`, `room_low`) + 5 | the cell arithmetic moves to `storage.occupied`; `visit_due` stays in the loop and asks `Loot.room_low()` |
| `macros/visit.py` `visit`, `Hands` | the town visit's walk and stops | 5 (`TownRoutine`) | **stays** as the executor; `Hands.judge` becomes `TownRoutine`'s decisions; `copies.sold` call deleted |
| `macros/shop.py` `restock`, `BUYS`, `short`; `repair.py`; `cain.py` | buy keys/TP/identify, repair, Cain | 5 (`TownHands`) | stay; `short` learns the identify reserve (§5) |

---

## 2. The high-level API

Close to the player's sketch. One facade per scope: `Loot` (the loop's items and the ground, anywhere) and
`TownRoutine` (one town visit). `Item` and `GroundItem` are thin views: facts + value + decision, plus the
actions bound to the hands. All decisions are computed by the pure layers; the facade only reads and acts.

### 2.1 `loot/api.py`

```python
class Loot:
    """The loop's loot: the items it carries, the drops near it, the room it has. Reads through `world`, decides
    through the pure layers, acts through `hands`. One instance per run (`Run`), cheap to make."""

    def __init__(self, world: LootWorld, hands: LootHands, appraiser: Appraiser, owned: OwnedCopies,
                 rules: KeepRules = RULES) -> None: ...

    def items(self, *, where: Iterable[Where] = (Where.INVENTORY, Where.CUBE),
              identified: bool | None = None) -> list[Item]:
        """The loop's own items (Owner.LOOP) in `where`, each with its value and decision; never the player's.
        `identified`: only identified (True) or unidentified (False) ones. Ordered: the best rolled first, so that two
        copies carried in one visit are judged in that order and the first counts as owned for the second."""

    def ground(self) -> list[GroundItem]:
        """The drops near the character worth a look (the loot marks, the filter's Show rules, potions, gold), each
        with its `GroundVerdict`; what the player or the loop put down this game is left out (PutDown)."""

    def occupied(self) -> float:
        """The share (0..1) of the loop's room — its volatile inventory cells and the cube — that its items take."""

    def room_low(self) -> bool:
        """Whether a town visit is due for room (storage.room_low: under TRADE_ROOM free cells, or no SURE_BLOCK
        free, or no free BIG_BLOCK after a compaction). The loop's `visit_due` asks this."""

    def optimize_space(self) -> Compacted:
        """Compact the loop's room without leaving the level: the identified items that fail dropped first, then the
        cube filled (storage.compact), then the keys arranged out of the BIG_BLOCK. Never moves the player's items.
        Returns what moved and the room left."""

    def identify_pending(self, *, most: int | None = None) -> list[Item]:
        """Identify with the Tome the loop's unidentified items whose decision is IDENTIFY (best expected value first,
        at most `most` and the tome's charges); each verified in memory and appraised at once
        (IdentifyWorker.appraise). Returns them re-judged. Nothing when the tome is empty: Cain will do them."""

    def settle(self) -> Settled:
        """The field routine, the player's sketch as one call (§2.4): identify what waits, drop what fails, then
        compact or ask for town. Safe to call again: it does only what is left."""
```

```python
class Item:
    """One of the loop's carried items: what it is, what it is worth, what to do with it."""
    facts: ItemFacts
    value: Value
    decision: Decision

    def is_keep(self) -> bool:
        """True for KEEP and NEVER_TOUCH (kept as it is); False for DROP and SELL. IDENTIFY is kept until identified
        (an unidentified item is never dropped: S8)."""

    def needs_identify(self) -> bool:
        """Whether its decision waits for the identified read (Action.IDENTIFY)."""

    def why(self) -> str:
        """'Goblin Toe (Light Plated Boots): drop — K6 cheap (0.65 Ist), not better than the 2 owned: ED 50 vs 53, 56'."""

    def identify(self) -> 'Item':
        """Identify it with a scroll from the Tome (hands.identify), re-read and re-judged. Raises NoScroll."""

    def drop(self) -> bool:
        """Drop it at the feet (hands.drop) and remember it for the game so no pickup takes it again
        (PutDown.reject). Refused (False, logged) for anything is_keep(), the player's, or protected (S1)."""
```

```python
class GroundItem:
    facts: ItemFacts
    verdict: GroundVerdict      # pick, must_have, then (KEEP | IDENTIFY | JUDGE_IN_TOWN), class name, reason

    def is_pick(self) -> bool: ...
    def pick_up(self) -> Item | None:
        """Pick it up (hands.pick_up: pickup.py's aimed clicks) and return it as an Item, judged again from the
        carried read (more stats are readable carried than on the ground)."""
```

```python
# loot/town.py
class TownRoutine:
    """One town visit by the player's order: identify (Cain, free) → keep good (stash) → sell trash → restock (keys,
    Town Portal, Identify scrolls) → repair → leave. Wraps macros/visit.py `visit`; the judgement is `keep.decide`."""

    def __init__(self, loot: Loot, hands: TownHands, needs: Needs) -> None: ...

    def plan(self) -> TownPlan:
        """Pure: what this visit will do from what is read now — the unidentified for Cain, keepers and their pages,
        the sales, the drops, the buys, whether to repair (storage.stash_plan, shop.buys, repair.due)."""

    def run(self) -> TownReport:
        """Make the visit (`plan`, then each stop that has work) and check its contract (town.contract): cube empty,
        a BIG_BLOCK free, keepers stashed, no junk carried, keys/portals/identifies stocked. Abort-safe: a visit cut
        and made again does only what is left."""
```

### 2.2 The narrow interfaces (where the game is)

```python
class LootWorld(Protocol):
    """Reads. The live one wraps GameMemory/Run.reads; tests give plain data."""
    def carried(self) -> Sequence[ItemFacts]: ...     # the loop's and the player's, with Owner set
    def ground(self) -> Sequence[ItemFacts]: ...
    def storage(self) -> Storage: ...
    def tome(self) -> int | None: ...                  # Identify charges (Pack.identifies); None: no tome / unread

class Appraiser(Protocol):
    def appraise(self, facts: ItemFacts) -> Value: ...  # live: KnowledgeAppraiser; ground: WantsAppraiser; tests: table

class OwnedCopies(Protocol):
    def copies(self, facts: ItemFacts) -> Sequence[ItemFacts] | None: ...  # None: cannot be told (S8)

class LootHands(Protocol):
    """Every game action the loot layer takes. Each verifies its effect in memory and returns whether it took;
    each refuses the player's items itself (S1) — a second guard below the decision."""
    def pick_up(self, item: ItemFacts) -> bool: ...
    def drop(self, item: ItemFacts, why: str) -> bool: ...
    def identify(self, item: ItemFacts) -> ItemFacts | None: ...
    def to_cube(self, moves: Sequence[Move]) -> int: ...
    def arrange_keys(self) -> bool: ...

class TownHands(LootHands, Protocol):
    def cain(self, items: Sequence[ItemFacts]) -> int: ...
    def stash(self, plan: StashPlan) -> StashDone: ...
    def sell(self, items: Sequence[ItemFacts]) -> int: ...
    def buy(self, buys: Sequence[Buy]) -> Pack: ...
    def repair(self) -> bool: ...
```

The live implementations are adapters over code that exists: `GameHands.pick_up` → `pickup.pick_up`/`take`;
`drop` → `cube.drop_item` + `PutDown.reject`; `identify` → `junk.identify`'s tome clicks + `IdentifyWorker.appraise`;
`to_cube` → `cube.stash`; `cain` → `cain.identify_all`; `stash` → `visit.stash_stop`; `sell`/`buy` → `shop.restock`;
`repair` → `repair.repair`. Tests use `FakeHands` (records calls, mutates a fake `LootWorld`).

### 2.3 Pure functions (the tested core)

```python
def ground_judge.judge(facts: ItemFacts, value: Value, rules: GroundRules = GROUND) -> GroundVerdict
def keep.decide(facts: ItemFacts, value: Value, owned: Sequence[ItemFacts] | None, rules: KeepRules = RULES) -> Decision
def value.better_than(new: ItemFacts, copies: Sequence[ItemFacts], matters: Sequence[RollSpec]) -> Comparison
def value.matters_for(facts: ItemFacts, triage: Mapping | None, wants: Sequence[Want]) -> tuple[RollSpec, ...]
def storage.occupied(storage: Storage, loop_items: Sequence[ItemFacts]) -> float
def storage.room_low(storage: Storage) -> bool
def storage.compact(storage: Storage, items: Sequence[ItemFacts]) -> tuple[Move, ...]
def storage.stash_plan(storage: Storage, keepers: Sequence[ItemFacts], junk: Sequence[ItemFacts]) -> StashPlan
def identify.order(items: Sequence[Item], charges: int) -> list[Item]     # §5
```

### 2.4 How the loop's legs call it

The player's sketch, as the loop's field routine (`Loot.settle`), called at three points: after each pickup press
that took an IDENTIFY item **and** no hostile is within `SIGHT`; at the level's end (the "what is left" leg, before
the waypoint or the portal); and before a no-room trip (`running/room.py`), so a trip is never made for junk.

```python
def settle(self) -> Settled:
    for item in self.identify_pending():          # scroll identify, verified, appraised (§5)
        pass
    for item in self.items(identified=True):
        if not item.is_keep():
            item.drop()                           # on the ground; PutDown.reject: not picked again this game
    if self.room_low():
        return Settled(town=True)                 # the loop's visit_due → TownRoutine.run() at the next town leg
    self.optimize_space()                         # cube, keys out of the 2x4 block
    return Settled(town=False)
```

Note on the sketch's `occupied() < 0.5`: today the visit waits until fewer than `TRADE_ROOM` (8) cells of the
inventory and cube are free (`town.py:72`, `loop.py:608`), because a town walk is the slow leg (memory, 2026-10-16).
`room_low()` keeps that rule; `occupied()` is still exposed (HUD, logs). Q3 asks whether the player wants the 0.5.

| Leg | Today | With the API |
|---|---|---|
| Level run / sweep / press: what to take | `running/valuables.py` `_picked` → `pickmode.kept` → `sure` | `_picked` keeps drops whose `GroundItem.is_pick()`; `Drop.prized = verdict.must_have`; `lootpolicy.verdict` unchanged |
| The guard (no game left with a valuable) | `lootpolicy.verdict(GUARD)` skips identify candidates | same; "identify candidate" = `verdict.then == IDENTIFY and not must_have` |
| No room in the field | `running/room.py`: cube, then a trip; `cube.drop_for` drops an *unidentified* candidate | `Loot.settle()` first (identify + drop the failures), then the cube, then the trip |
| Level end ("what is left") | sightings fetch | + `Loot.settle()` |
| Town leg | `legs._shared_town_visit` → `visit.visit(Hands(judge=junk_of…))` + `copies.sold` | `TownRoutine(loot, hands, needs).run()` → `visit.visit` with `judge = [i for i in loot.items() if not i.is_keep()]` |
| HUD / Alt+D card | `identify/service.py` verdict | the card adds `Item.why()` (the same sentence the loop logs) |

Logging: one line per decision, `Macro: loot: <name>: <action> — <rule> <reason>`; one per action
(`Macro: loot: dropped …`, `identified …`); `settle` one summary line. The d2-loop-finds skill reads these.

---


## 3. Value model per item

### 3.1 Which rolls matter (`Value.matters`)

Every kept item carries the rolls that make it worth something, as `RollSpec`s. `value.matters_for` takes the first
source that has them, in this order (all already in the repo):

| # | Source | What it gives | Shape |
|---|---|---|---|
| 1 | `loot/data/wants.json` (new, §4.4) — the BiS / pickup rows from the guides | facets that must match (ethereal, sockets, superior) and the paid floors (ED ≥ 15, all-res 45, +3 staff mod) | `Want.must` |
| 2 | `inventory_tracking/corpus/data/score-roll-models.json` (30 models; built by `pricing/triage/analyze_rolls.py:187`, compiled by `compiled_rolls.py`) | the **deciding stats** of a unique/set by the market: `deciding {prop: {min, max, better, native_key, observed_min/max}}` | already read by `appraisal/price_rolls.py` `deciding_specs` |
| 3 | `pricing/triage/named-roll-placements.json` | a single paid roll with `valuable_min` (Shaftstop ED 180–220, paid from 218) | one spec |
| 4 | `pricing/data/triage/rules.json` row `pattern.properties` + `conditions` (1970 rows; e.g. Andariel's Visage "eth & 30 str & 10 LL") | the bucket's paid properties and facets | specs + facets |
| 5 | `pricing/data/wp-i-uniques-misc.json` `roll_bucket` | the hand-researched "one roll that matters" (Arachnid "ED% (425); max 120") | one spec |
| 6 | fallback: every variable stat of the read (`appraisal/owned.py` `variable_rolls`, ranges from `pricing/data/appraisal-definitions.json`) | all variable rolls, equal weight | today's comparison |

Facets are part of an item's identity, not ranked: an ethereal copy and a non-ethereal one are different items
(`owned.py` `match_kind` already splits on ethereal), and for bases the socket count and superior/normal split too
(rules.json `policies` for `base`: rarity, ethereal, sockets, socket_contents, base_ed_grade).

Stat ids used by the specs (verified in `third-parties/d2data/json/itemstatcost.json`): maxhp 7 (×256), ED on armor 16,
max-damage % 17, to-block 20, life leech 60, mana leech 62, MF 80, class skills 83 (layer = class: Warlock 7), FRW 96,
FHR 99, faster block 102, FCR 105, single skill (staff mod) 107 (layer = skill), all skills 127, skill tab 188 (layer
56 Demon / 57 Eldritch / 58 Chaos, `items/stat_constants.py:57-67`), sockets 194; resists 39/41/43/45.

Examples, as `matters` would read:

| Item | Rolls that matter | Source |
|---|---|---|
| Goblin Toe | ED 50–60 (the only variable stat) | fallback 6 (appraisal-definitions) |
| Shaftstop | ED 180–220, paid ≥ 218; or ethereal | named-roll-placements.json |
| Andariel's Visage | ethereal (facet); +Str 25–30; LL 8–10 | rules.json row 0 ("eth & 30 str & 10 LL") |
| Arachnid Mesh | ED 90–120 | wp-i `roll_bucket` |
| Monarch (white) | sockets ∈ {0, 4}; superior ED ≥ 15 | wants `monarch-*` (PK-monarch, `guides/pindle-anya.html:288`) |
| Giant Thresher (merc) | ethereal (must); sockets = 4 (or 0 with superior ED 15); superior ED | wants `merc-polearm-*` (PK-merc-polearms, `:291`) |
| 3os elite dagger | sockets = 3; staff mod (107) level 3 on Abyss 402 / Hex: Purge 389 / Apocalypse 401 | wants `void-*` (PK-rotw-daggers-grimoires, `:294`) |
| Rare ring | FCR 10; life leech; mana leech; res; life | wants `rare-ring-*` (`guides/pricing.html:238-259`) |
| Rare circlet | +2 class (83:7) or +3 tab (188:57); FCR 20; sockets | wants `rare-circlet-*` (PK-blue-circlet, `:297`; `pricing.html:233`) |

### 3.2 "Better than what we already have" (`value.better_than`)

Owned copies: `CollectionCopies.copies(facts)` = today's `macros/copies.py` `owned_copies` (collection DB read-only,
open placements, less the playing character's inventory and cube, offline characters' items counted as owned only per
`owned.py` `online_only`), plus the copies kept earlier in the same visit (`copies.sold`'s `held`). `None` when the
collection cannot be read or the item has no match rule → S8 keeps it.

Comparison, one copy at a time, **only on `matters`** (not every variable stat as today):

1. facets differ (eth vs non-eth, 3os vs 4os) → not the same item: that copy is ignored;
2. each ranked spec both items have: `better` / `worse` / `equal` by its direction;
3. relation to the copy: better (≥ on all, > on one), worse, equal, mixed;
4. **mixed** is decided by worth: `value_ist` of each (its place in the band by its own rolls,
   `identify/service.py:167-183`) when a band exists; else by the summed roll positions over `matters` with the `good`
   specs counted twice; a tie is *not better*;
5. over all copies: **better only when better than every copy** (as `owned.overall` today).

`Comparison` keeps every per-roll line ("ED 50 vs 53, 56"), so `Item.why()` names them.

### 3.3 Expensive vs cheap: the duplicate threshold

Proposal (needs the player's ruling, Q1): **`DUPLICATE_IST = 1.0`** — an item worth **≥ 1 Ist by its own rolls**
(`value_ist`) is kept as a duplicate; under it, only when better than every owned copy.

| Evidence | Says |
|---|---|
| The player, 2026-10-19 (in `identify/service.py:201-207` `owned_verdict`): "we keep all expensive items 1+ ist value" | 1 Ist is already the ruled line |
| `identify/service.py:93` `KEEP_IST = 1.0` | same |
| `loot/build_filter.py:43-45` `SLOW_MINIMUM = 1.0` ("a dear item that sells only now and then is still worth the pickup") | 1 Ist separates "worth a slow sale" |
| `pricing/triage/market_demand.py:20-25`: under 1 Ist with no measured demand → `slow`, not `sell` | sub-1-Ist is where `slow` piles up — the Goblin Toe |
| Rune ladder `pricing/data/wp-f-ladder.json` (2026-09-18): Pul 0.568, Um 0.674, Mal 0.789, **Ist 1.0**, Gul 1.431, Vex 2.585 | the player's "0.6 Ist" example is an Um |
| Recent Trades 2026-10-09 over 543 uniques/sets (`guides/warlock.html:262`): 182 < 0.1, 120 at 0.1–0.25, 92 at 0.25–1, 49 at 1–5, 15 > 5 | 1 Ist keeps duplicates of 64 items (e.g. BK 2.585, Mara's 3.7, Arachnid 2.29, Entropy Locket 2.2); 2 Ist would also drop Wraithstep and Hellwarden's (~1.0) — nothing in the repo supports 2 |
| `pricing/data/triage/rules.json:3` `keep_ist = 0.25`; guide tiers `guides/pricing.html:289-293` (Low 0.2–0.8 "sell only in bulk… or use") | below 0.25 an item is `worthless` unless a want names it |

Tiers in `Value.tier`: `expensive` ≥ 1.0; `cheap` 0.25–1.0; `worthless` < 0.25 with a supported band and no want;
`unknown` no band and no estimate.

### 3.4 The keep decision (`keep.decide`), rule by rule

Rules in order; the first that applies decides. Each test in §6 names its rule.

| Rule | When | Action |
|---|---|---|
| K0 | `owner` is not LOOP (the player's, a print match, unknown) | NEVER_TOUCH (S1) |
| K1 | a never-sell class: rune, gem, potion, key, tome, cube, set/unique charm; a rune or gem goes to its resource tab by the stack rules (`town.py` RUNES_AIM, GEMS_*) | KEEP (S2) |
| K2 | unidentified, and the value needs the read (any magic+ that is not judged by its ground facts alone) | IDENTIFY — never dropped unidentified (S8) |
| K3 | a want with `always_keep` matches (the BiS rows of §4; Monarch of Deflecting, eth 4os Giant Thresher…) | KEEP, duplicates included |
| K4 | unique or set with no owned copy, or owned copies cannot be told (`None`) | KEEP (S3, S8) |
| K5 | `worth_ist ≥ DUPLICATE_IST` | KEEP (expensive: duplicates kept) |
| K6 | owned copies exist and `worth_ist < DUPLICATE_IST` (or unknown with a want) | KEEP if `better_than` every copy, else DROP |
| K7 | multiples-use items (charms, jewels: `owned.py` MULTIPLE_COPY_BASES): no copy comparison | KEEP if worth ≥ `keep_ist` 0.25 or a want matches, else DROP |
| K8 | `tier == 'worthless'` (triage `vendor` on a supported band) and no want | DROP |
| K9 | `tier == 'unknown'`, no want, not unique/set (the KB cannot price it) | KEEP the first, logged `unknown` for the update-kb skill; later copies by K6 on the fallback rolls |

The Goblin Toe of tonight under these rules: worth 0.65 Ist (asks q1 0.647, 3 sellers, 2026-10-04 — the figure the
loop used; the KB's Recent Trades fills say q1 = median 0.061, 20 trades, 2026-10-09, `pricing/data/named-trades.json:3284`),
so cheap → K6; owned 53 % and 56 % ED (`collection.sqlite`: MUniqAA stash and shared tab 5; the 50 % one now sits on
shared tab 4) → its 50 % is worse than both → **DROP**. Today's path kept it because `owned_verdict`
(`identify/service.py:212-218`) leaves a `slow` verdict alone when `value_ist` is None and `trade_reason` holds, and
`copies.keep_copy` looks only at `vendor` items (`macros/copies.py:56`).

---

## 4. New pickup classes

### 4.1 What can be judged on the ground

`ground_judge.judge(facts, value)` answers `GroundVerdict(pick, must_have, then, klass, reason)`; `then` is KEEP
(ground facts decide), IDENTIFY (the value needs the identified read: field identify, §5), or JUDGE_IN_TOWN (no
tome charge: Cain). Read before identification (`items/identity.py:15-23`, `game/decode.py:610-633`): quality, the
ethereal and socketed flags, and from the full stat list sockets (194), staff mods (107), ED (16), least res — today
**only for `knif`, `shie`, `ashd`** and qualities normal/superior/magic (`game/layout.py:105-108`). The ground read
of sockets and staff mods is new since 2026-10-17 and **not yet confirmed in play** (journal
`routes/lower-kurast-loop-journal.md:722-728, 768-774`) — research R2 below.

Research needed before the field-identify classes are sized (M0):

- **R1** — whether an *unidentified* magic/rare item's full stat list already holds its affixes in memory (block 20
  and faster block 102 of "of Deflecting", FCR, +skills). If yes, most magic classes become ground-judged and the
  scroll is only for rares and uniques. One Win+C next to an unidentified magic Monarch answers it.
- **R2** — confirm `base_rolls` on the ground (sockets, ED, staff mods) against the tooltip for three items; then
  widen `ROLLED_TYPES` to `pole`, `spea`, `tors`, `helm`, `circ`, `grim` (types from `third-parties/d2data/json/itemtypes.json`).
- **R3** — whether ItemData +0x34 (unique/set row) is filled before identification (`loot/ground.py:13-14` UNCONFIRMED);
  if yes, a unique's name is known on the ground and K5/K6 can run before pickup.

### 4.2 The classes

Item codes are quoted from `third-parties/d2data/json/` (weapons.json, armor.json, misc.json) with line numbers;
names not followed by a code are to be resolved by `items/metadata.py` at build time, never typed. "Ground" =
decided from ground facts; "ID" = needs the identified read.

| Class | Items (codes) | Pick when (ground) | Then | Keep when | Source |
|---|---|---|---|---|---|
| G1 sure valuables (today's GOOD) | runes, gems, charms, jewels, rings `rin` (misc:9727), amulets `amu` (misc:89) | always | KEEP / ID | K1, K7 | PK-runes `guides/pindle-anya.html:307`, PK-gems `:308`, PK-charm-* `:303-304`, PK-jewel `:305`; `macros/pickmode.py` `sure` |
| G2 uniques & sets | every gold/green item the filter shows | always | ID | K3–K6 (first copy; duplicates only ≥ 1 Ist or better) | PK-unique-set `:301`; S3 |
| G3 **merc eth polearms** | Thresher `7s8` (weapons:5499), Giant Thresher `7wc` (:6822), Cryptic Axe `7pa` (:5078), Great Poleaxe `7h7` (:4007), Colossus Voulge `7vo` (:6577); Mancatcher, Matriarchal Spear (codes to resolve) | white/superior, **ethereal**, sockets 4; or 0 with superior ED ≥ 15 (GT, GPA only) | KEEP | eth 4os Superior of any: always_keep; eth 4os plain GT: always_keep (merc Insight/Infinity BiS); others by K5/K6 | PK-merc-polearms `:291`, PK-eth `:285`; `guides/warlock.html:135-142, 166` ("Eth 4os Giant Thresher is the single most valuable gray base Pindle drops"); asks wp-b `pricing/data/wp-b-prices.json:10884` (GT eth 4os 5.9→11.4 n20; superior 57→86; eth 15ED 126→799) |
| G4 merc / runeword armor | Dusk Shroud `uui` (armor:12748), Archon Plate `utp` (:12406), Sacred Armor `uar` (:9393), Mage Plate `xtp` (:17408), Wire Fleece `utu` | eth 4os Dusk / Archon (merc Fortitude, CoH); superior ≥ 15 ED 3/4/0os Archon; superior ≥ 15 ED Mage Plate 3/0os (Enigma); eth Sacred Armor 4/0os | KEEP | always_keep: eth 4os Dusk (merc fix #1, `warlock.html:135-142`), eth 4os Archon (CoH eth Archon, `wp-a-builds.json` merc blocks :3711–:3956); rest K5/K6 | PK-elite-armor `:286`, PK-mage-plate `:287` |
| G5 white Monarch `uit` (armor:10235) | | superior ED ≥ 15 with 4 or 0 sockets; plain 4os only while no Spirit base is owned (self-use floor) | KEEP | sup 15 ED 4os 9.3→17.1, 0os 2.6→11.4; plain 4os 0.42→0.79 (q1 0.674/15, 2026-10-04) → cheap: K6 | PK-monarch `:288`; `wp-b-prices.json:3399`; `warlock.html:156` (Spirit 4os Monarch off-hand) |
| G6 **magic Monarch** | `uit`, magic | **every** magic Monarch (2x3) — today only 4os ones | **ID in the field** | 4os (Jeweler's, any affix: 9.3→71.5 n50) KEEP; **of Deflecting** (block 20 + faster block 30, `magicsuffix.json:2990`) at 4os: always_keep (74.6→114 n17); 3os of Deflecting: KEEP (q1 6, 20 sellers, 2026-10-08); anything else DROP in the field | PK-blue-jeweler `:296`; `guides/pricing-primer.html:479`; `pricing.html:199, 331` |
| G7 Paladin shields | Sacred Targe / Rondache (classes 498, 499, `pickmode.py:69`) | today's `shield_base` (all-res 45; 40–44 with 3+os) | KEEP | as today | PK-pala-shields `:289`; history/pickmode.md |
| G8 **Void daggers (staff mods)** | Kriss `kri` (weapons:19962), Blade `bld` (:16353), Cinquedeas `9kr` (:11504), Stilleto `9bl` (:9532), Fanged Knife `7kr` (:4257), Legend Spike `7bl` (:2270) — the only daggers with 3 sockets | white/superior with **3 sockets and a +3 staff mod** of a paid skill — Abyss 402, Hex: Purge 389, **Apocalypse 401** (new: the player's "+3 apocalypse", `shop/skills.json:929`) — or 0 sockets with +3 Abyss (Larzuk); not a 3os dagger without one (the player, 2026-10-17 17:45: "we're storing every 3os dagger, while in reality we need something that is really good for void", history/pickmode.md), although the guide prices plain 3os elite daggers at mid (`pricing.html:352`): Q9 | KEEP | 3os elite: Legend Spike 4.05→17.3 (n37), Fanged Knife 0.67→22.8 (n42); +3 Abyss / Hex: Purge fills 8.2 / 17.5; +3 Apocalypse ~5 (n24, `pricing.html:346-348`); K5/K6 | PK-rotw-daggers-grimoires `:294`; `warlock.html:155, 220, 263-264`; `pricing.html:352-353`; daggers 1os elsewhere (Dirk, Poignard, Rondel, Bone Knife, Mithral Point): never |
| G9 magic/rare Warlock class items | daggers (`knif`), grimoires (`grim`, wa1–waf, armor:13437–14585) | magic or rare | ID | +2 Warlock (Arch-Devil's, `magicprefix.json:13176`), +3 tree (Torrid 23 / Forbidden 22 / Malevolent 21, `:12997, :13068, :13137`) with a companion; rare +2 Warlock (q1 4, median 15); magic grimoire +3 tree + all-res (~51); "+3 staff mod without a class or tree prefix stays vendor" → DROP | PK-blue-class-items `:298`; `pricing.html:202, 238, 346-349` |
| G10 **circlets** | Circlet `ci0`, Coronet `ci1`, Tiara `ci2`, Diadem `ci3` (armor:1897–2143) | magic or rare | ID | **rare 20 FCR + +2 Warlock (or +3 Eldritch)**: always_keep (Warlock helm, `warlock.html:158`); magic "of the Magus" + class prefix; Artisan's Tiara of Speed; rares with 2 of skills/FCR/FRW/res/sockets | PK-blue-circlet `:297`; `pricing.html:200, 233`; primer `:481-485` (rare +2/20 FCR/2os Tiara 34→143) |
| G11 **rare rings & amulets** | `rin`, `amu` | rare/crafted (today: taken, judged in town) | ID | ring: **10 FCR + life leech + mana leech** (the player's "dual leech FCR ring"): always_keep; 10 FCR + res + life (Warlock ring, `warlock.html:164`); AR ≥ 100 + LL ≥ 5 (melee, Ohm–2 Jah); amulet: +2 class + 10 FCR (+2 Warlock / 10 FCR ≈ Ist); any FCR, life or +2 skills (the player's ruling of 2026-10-18, today `macros/keepers.py`) | PK-blue-jewelry-gloves `:299`; `pricing.html:228-259`; `warlock.html:163-164, 192-193` |
| G12 expensive blues (others) | magic Archon/Dusk/Sacred Armor 4os (11.4→148), Jeweler's Archon of the Whale (merc, 57→343), magic Diadem/Tiara 2–3os, GC skillers, Shimmering SC of Vita | as the classes above / G1 | ID | the primer §3.3 patterns (`pricing-primer.html:476-488`, charms `:496-515`) | `wp-b-prices.json` `_blues` (:30082) |
| G13 rare elite misc | rare gloves / boots / belts (filter's Rare ARMOR rule); rare elite armor/weapons | as the filter shows | ID | 2+ of ED/IAS/skills/FCR/res/life (boots FRW/res/FHR) | PK-rare-misc `:300` |
| — leave | white non-gray non-superior, low quality, bases no row names, 1os daggers, plain 5/6os eth polearms, non-eth polearms | never picked | — | — | PK-leave-white `:310`, PK-leave-blue-misc `:311` |

"Bad bases we don't use" (the request): a base is picked only when a class above names it **and** its ground facts
meet the row; no base is carried to town to be sold. Bases no build or merc uses but the market pays (Phase Blade /
Berserker Axe / Colossus Blade, `PK-elite-weapons :290`; Grand Matron Bow, `PK-bows`) are left until the player rules
on Q7.

### 4.3 Size and the filter

- Polearms and some armors exceed `pickup_shown_cells = 6` (`config.py:417`; a polearm is 2x4). Wanted-base rows
  bypass the cell cap; the cap stays for everything else.
- The loot filter must show what is picked (labels on, S6; the HUD marks): each new class gets a Show rule built by
  `loot/build_filter.py` from the same `wants.json`, so the filter and the pickup cannot drift (as `loot/shown.py`
  already guarantees for the rest). Codes in the filter are taken from the d2data dump (lootfilter skill), never typed.
- Ground facts for G3/G4/G10 need `ROLLED_TYPES` widened (R2).

### 4.4 `loot/data/wants.json` (new data, built, sourced)

Built by `loot/build_wants.py` (like `build_filter.py`, `build_uniques.py`) from the guides' PK rows, `wp-b` buckets
and `own.json` (`pricing/data/triage/own.json`, 110 own-use rows: "Echoing Strike ring", "…helm"…). Each row:

```json
{"id": "merc-insight-gt-eth-4os", "class": "G3", "who": "merc", "label": "Insight base: eth 4os Giant Thresher",
 "codes": ["7wc"], "qualities": ["normal", "superior"], "must": {"ethereal": true, "sockets": [4]},
 "matters": [{"key": "17:0", "label": "Enhanced Damage (superior)", "low": 1, "high": 15, "good": 15}],
 "always_keep": true, "asks": {"q1": 5.9, "median": 11.4, "sellers": 20, "observed": "2026-09-18", "kind": "asks"},
 "source": "guides/pindle-anya.html:291; guides/warlock.html:166; pricing/data/wp-b-prices.json:10884"}
```

A row without a `source` fails the build. The test plan's fixtures (§6) are generated from the same rows, so every
want has an acceptance test.

---

## 5. Identify scrolls

Facts (verified): Scroll of Identify `isc` (`third-parties/d2data/json/misc.json:5486`, cost 80 gold), class 545
(`macros/shop.py:39`); Tome of Identify `ibk` (`misc.json:5320`, maxstack 20), class 534 (`game/layout.py:126`),
carried in the inventory (`cube.py:53` KEPT), charges read as stat 70 into `Pack.identifies`
(`game/decode.py:386-389`; None = unread or no tome). Sold by Jamella (405, `shop.py:37`); `shop.BUYS` fills the tome
to 20 by Shift + right click only when a visit happens anyway (`shop.py:377-380`); `town.Needs.identifies = 20`
(`town.py:104`) is not yet a reason to visit.

| Question | Design |
|---|---|
| How many to carry | One tome, **20** charges (its maximum; a loose scroll would take a cell) |
| When to restock | Every Jamella visit tops it to 20 (as today). New: charges **< 5** (`IDENTIFY_RESERVE`) makes `shop.short` true, so the game-start town step visits Jamella (she is on the waypoint walk in Pandemonium Fortress; the cost is a menu, not a walk). The contract (`town.contract`) gains `identifies < 5` as a miss |
| When the field identify runs | `Loot.settle()` (§2.4): at the level's end; after a pickup press that took a G6/G9–G11 item when no hostile is within `SIGHT` (`hunting/base.py`); before a no-room trip. Never in a fight, never with a panel the player opened, never in controller mode (`run.pad`: Cain later) |
| Which items, in what order | `identify.order`: always_keep candidates first (a 4os magic Monarch), then by expected worth (the class's band median), then by cells (big first: they cost room). Capped by the charges; the rest wait for Cain (free) |
| Whether to spend a scroll on every rare | Recommended: yes for G6, G9–G11 and any item ≥ 4 cells; small identify-class items (rings, amulets, jewels, charms: 1 cell) also, since the sale gold is not needed and a dropped junk ring is a cell back. With R1 = yes, magic items are judged without a scroll |
| How it is performed | `GameHands.identify` = `junk.identify`'s clicks (open inventory, right click the tome, click the item, `CURSOR_SETTLE` 0.15 s), one panel opening for the whole batch |
| How it is verified | the item's identified flag in memory within `IDENTIFY_SECONDS` 1.0 s (`junk.py:82-87`), then the full read and appraisal **synchronously** (`IdentifyWorker.appraise`, `identify/service.py:677`, extended to return the observation, not only the verdict), then `keep.decide`. A charge spent and no flag: stop the batch, log, Cain later |
| What a failure leads to | DROP at once (`Item.drop` → `cube.drop_item` + `PutDown.reject`): the item lies at the feet, is never picked again this game and does not hold the guard (S5 counts only what the loop would pick) |

Shadow-mode measurement (M1) logs, per game, how many items each class would send to the scroll, so the reserve
of 5 and the order are tuned on data (30+ cycles, per the loop's steering rule).

---

## 6. Test plan

All tests are pure: `ItemFacts` fixtures + a table `Appraiser` + a list `OwnedCopies` → `keep.decide` /
`ground_judge.judge`; no game, no collection, no KB. Files mirror the modules:
`tests/inventory_tracking/loot/test_keep.py`, `test_ground_judge.py`, `test_value.py`, `test_storage.py`,
`test_api.py` (FakeHands), and **`test_valuables.py`** — the named acceptance table the player asked for, one
parametrized case per row, each row's fixture in `tests/inventory_tracking/loot/fixtures/valuables.json` with its
source line. A case fails with the item's `why()`.

### 6.1 Very valuable items (must be picked and kept; duplicates kept)

| Test id | Fixture (facts) | Expected ground → decision | Rule |
|---|---|---|---|
| `monarch_of_deflecting_4os` | magic `uit`, sockets 4, stats 20=20, 102=30, identified | PICK/ID → **KEEP** (dup kept) | K3 (G6) |
| `monarch_of_deflecting_4os_unidentified` | magic `uit`, sockets 4, unidentified | PICK, then IDENTIFY; never DROP | K2 |
| `jewelers_monarch_other_suffix` | magic `uit` 4os, no Deflecting | KEEP (9.3→71.5) | K5 |
| `monarch_of_deflecting_3os` | magic `uit` 3os, Deflecting | KEEP | K5 |
| `magic_monarch_2os_plain_dropped_in_field` | magic `uit` 2os, of the Fox | ID → **DROP in the field** | K8 |
| `merc_gt_eth_4os` | white `7wc`, eth, 4os | PICK (cell cap bypassed) → KEEP (dup kept) | K3 |
| `merc_gt_eth_4os_superior` / `merc_thresher_eth_4os_superior` / `merc_cryptic_axe_eth_4os_superior` / `merc_great_poleaxe_eth_4os_superior` / `merc_colossus_voulge_eth_4os_superior` | superior, eth, 4os | KEEP | K3 |
| `merc_gt_eth_0os_superior_15ed` | superior `7wc` eth 0os ED 15 | KEEP (126→799) | K5 |
| `merc_dusk_eth_4os` (Fortitude) / `merc_archon_eth_4os` (CoH) | white `uui` / `utp`, eth, 4os | KEEP | K3 |
| `merc_andariels_visage_first` | unique Andariel's Visage, no owned | KEEP | K4 |
| `warlock_void_legend_spike_3os_plus3_hex_purge` / `_fanged_knife_3os_plus3_abyss` / `_kriss_3os_plus3_abyss` | white `7bl` / `7kr` / `kri`, 3os, 107:389 or 402 = 3 | PICK → KEEP | K5 (G8) |
| `dagger_3os_without_paid_staffmod_left` | white `7bl` 3os, 107:401 = 1 | LEAVE (the 2026-10-17 ruling) | G8 |
| `warlock_dagger_3os_plus3_apocalypse` | white `9kr` 3os, 107:401 = 3 | PICK → KEEP | K5 (G8) |
| `warlock_dagger_0os_elite_plus3_abyss` | white `7bl` 0os, 107:402 = 3 | PICK → KEEP | G8 |
| `warlock_spirit_monarch_superior_15ed_4os` | superior `uit` 4os ED 15 | KEEP | K5 |
| `warlock_enigma_mage_plate_superior_15ed_3os` / `warlock_coh_archon_superior_15ed_4os` | superior `xtp` 3os ED 15 / `utp` 4os ED 15 | KEEP | K5 |
| `rare_ring_dual_leech_fcr` | rare `rin`, 105=10, 60=5, 62=5 | ID → KEEP (dup kept) | K3 |
| `rare_ring_fcr_res_life` | rare `rin`, 105=10, res 15, life 30 | KEEP | K3 |
| `rare_tiara_fcr_plus2_warlock` | rare `ci2`, 105=20, 83:7=2, 2os | KEEP (dup kept) | K3 |
| `rare_diadem_fcr_plus3_eldritch` | rare `ci3`, 105=20, 188:57=3 | KEEP | K3 |
| `magic_diadem_arch_devils_of_the_magus` | magic `ci3`, 83:7=2, 105=20 | KEEP | K3 |
| `amulet_plus2_warlock_10fcr` | rare/magic `amu`, 83:7=2, 105=10 | KEEP | K3 |
| `rare_amulet_any_fcr_life_or_2_skills` | rare `amu`, 105=10 only / life 40 only / 127=2 only | KEEP each (the 2026-10-18 ruling) | K3 |
| `rare_grimoire_plus2_warlock` / `magic_grimoire_plus3_tree_all_res` | rare/magic `grim` | KEEP | K5 |
| `gc_eldritch_skiller_life` | magic GC, 188:57=1, life 30 | KEEP | K7 |
| `jewelers_archon_of_the_whale` | magic `utp` 4os, life 95 | KEEP | K5 |
| `sacred_targe_45_res` | white class 498, res 45 | KEEP | G7 |

### 6.2 Duplicates and better copies

| Test id | New | Owned | Expected | Rule |
|---|---|---|---|---|
| `goblin_toe_third_copy_worse_is_dropped` | Goblin Toe ED 50, worth 0.65 | ED 53, 56 | **DROP** "not better than 2 owned: ED 50 vs 53, 56" | K6 |
| `goblin_toe_equal_is_dropped` | ED 53 | 53, 56 | DROP (equal is not better) | K6 |
| `goblin_toe_better_than_all_is_kept` | ED 58 | 53, 56 | KEEP | K6 |
| `goblin_toe_first_copy_is_kept` | ED 50 | none | KEEP | K4 |
| `goblin_toe_owned_unreadable_is_kept` | ED 50 | None | KEEP | K4 (S8) |
| `expensive_duplicate_worse_is_kept` | Arachnid Mesh ED 95, worth 2.3 | ED 110 | KEEP | K5 |
| `cheap_mixed_decided_by_worth` | Andariel's Visage non-eth, Str 30 LL 8 | Str 25 LL 10 | by `value_ist` / score; tie → DROP | K6 step 4 |
| `eth_and_non_eth_are_different_items` | eth Andariel's | non-eth owned only | KEEP (first eth copy) | K4 |
| `two_copies_in_one_visit_best_first` | 56 % and 50 % carried, 53 % owned | — | keep 56, drop 50 | K6 + `items()` order |
| `charms_are_not_compared_as_copies` | second +1 Eldritch GC, same rolls | one owned | KEEP | K7 |
| `cheap_unknown_price_first_kept_logged` | unpriced magic boots | none | KEEP, logged `unknown` | K9 |
| `vendor_band_item_dropped` | magic Sash of the Fox, triage vendor | — | DROP | K8 |

### 6.3 Never touch / never drop

| Test id | Fixture | Expected | Rule |
|---|---|---|---|
| `players_item_on_protected_cell` | a junk-looking item, `owner=PLAYER` | NEVER_TOUCH; `Item.drop()` refuses | K0, S1 |
| `players_item_by_print_in_cube` | print match in the cube | NEVER_TOUCH | K0 |
| `owner_unknown_is_the_players` | `owner=UNKNOWN` | NEVER_TOUCH | K0 |
| `gheeds_fortune_duplicate` / `annihilus` / `torch` / `sunder` | unique charms | KEEP, never sold | K1 |
| `ber_rune_never_transmuted` | Ber in the Runes tab over 80 | not in `rune_transmutes` | S2 (town.py) |
| `cheap_rune_and_gem_kept` | Hel rune; chipped gem | KEEP | K1 |
| `unidentified_never_dropped` | any unidentified magic+ | IDENTIFY, never DROP | K2 |
| `tome_keys_cube_never_moved` | classes 533, 534, 558, 564 | NEVER_TOUCH | K1 |

### 6.4 Ground judgement and leave cases

| Test id | Fixture | Expected |
|---|---|---|
| `white_plain_0os_monarch_left` | normal `uit` 0os | LEAVE (PK-leave-white) |
| `monarch_3os_white_left` | normal `uit` 3os | LEAVE (PK-monarch: 3os = vendor) |
| `merc_polearm_non_eth_left` / `merc_polearm_eth_6os_plain_left` | `7wc` non-eth 4os / eth 6os | LEAVE |
| `one_socket_dagger_left` | Mithral Point, Bone Knife | LEAVE |
| `rare_non_elite_armor_left` | rare non-elite chest | LEAVE (PK-rare-misc) |
| `unread_rolls_not_taken` | wanted base, `rolls=None` | LEAVE (today's rule: unread bases filled the stash) |
| `put_down_not_picked_again` | a dropped DROP item back on the ground | not in `Loot.ground()` (PutDown.reject) |

### 6.5 Storage, identify and the API

`test_storage.py`: `occupied` over volatile cells only; `room_low` matches today's `loop.py:1025-1063` cell rules on
the recorded packs of `tests/inventory_tracking/macros/fixtures`; `compact` equals `cube.plan`. `test_identify.py`:
order and the charge cap; tome empty → nothing identified, Cain later; flag not set → batch stops. `test_api.py`
(FakeHands): `settle` identifies, drops the failures, and asks for town at room low; `Item.drop()` on a keeper or the
player's item does nothing; `TownRoutine.plan` on the Goblin Toe trio sells/drops the 50 %. The golden table of
`tests/…/macros/test_lootpolicy.py` keeps passing (site logic unchanged).

---

## 7. Migration

Each step ships alone, behind a module switch (as `tzloop.ENABLED`), with its tests, the routine suite
(`-m "not slow" -n 6` while the game is not running) and a restart only through the loop-watch tools. Measure 30+
clean cycles before the next step (the loop's steering rule).

| Step | Change | Switch | What the live loop does differently | Retires |
|---|---|---|---|---|
| **M0** | Research R1–R3 (one Win+C each); acceptance fixtures `fixtures/valuables.json` and `test_valuables.py` run against a first pure `keep.decide` + `ground_judge.judge` stub that wraps today's functions (`owned_verdict`, `keep_copy`, `pickmode.sure`) — cases today's code fails are `xfail(strict=True)` with the reason (the Goblin Toe, +3 Apocalypse, magic non-4os Monarch) | — | nothing | — |
| **M1** | `loot/facts.py`, `loot/value.py` (value_ist moved, CollectionCopies, matters_for), `loot/keep.py`, `loot/data/wants.json` + `build_wants.py`; **shadow mode**: at each town visit and each ground look, log the new decision beside the old one (`Macro: loot: shadow: …: new drop K6 / old keep slow`) | `loot.keep.SHADOW = True` | log lines only | — |
| **M2** | The town judge is `keep.decide`: `Hands.judge` returns the loop's items whose decision is DROP/SELL; they are sold at Jamella as today (still in town) | `keep.DECIDES` | cheap duplicates that are not better are sold (the Goblin Toe case); expensive duplicates and BiS rows always kept; amulet/ring rows from wants | `copies.keep_copy`, `copies.sold`, `keepers.amulet_keeper`, `junk.junk_of`/`junk`/`JUNK_QUALITIES`, `pickmode.sellable`; `owned_verdict` off the loop path |
| **M3** | `loot/storage.py`: the pure planning of `cube.py` (`plan`, `overflow`, `keys_move`) and `town.py` (`stash_stop`, `place`, `_make_way`, `surplus`) moved and re-exported; `occupied`, `room_low` | — | nothing (byte-equal plans; the recorded visit snapshots `visitlog` replay equal) | the duplicated cell arithmetic in `loop.py` |
| **M4** | Field identify and drop: `Loot.settle()` at level end and before a no-room trip; `PutDown.reject`; `IDENTIFY_RESERVE` in `shop.short` and the contract; G6 first (every magic Monarch), then G9–G11 | `loot.api.FIELD_IDENTIFY` (+ the class list) | magic Monarchs picked, identified in the field, failures dropped at the feet; tome kept stocked | `cube.droppable`, `cube.drop_for` (drop-unidentified-for-room) |
| **M5** | `ground_judge` replaces `pickmode.sure`: G3, G4, G8 with Apocalypse, G10; `ROLLED_TYPES` widened (after R2); cell-cap exception; filter Show rules built from wants.json (lootfilter skill, codes from d2data) | `loot.ground_judge.CLASSES` | eth 4os merc polearms/armor, +3 Apocalypse daggers, more circlets picked; bad bases still left | `pickmode.void_base`, `shield_base`, `judged_base`, `candidate`, `identified_for`, `SKILLED`, `VOID_*`, `MONARCH…` |
| **M6** | Facade wiring: `Loot`, `Item`, `TownRoutine` in `running/legs.py` and `running/room.py`; HUD/Alt+D card shows `Item.why()` | — | same behaviour, one code path | `junk.py` (identify moved to hands), `copies.py`, `keepers.py`; `lootpolicy.is_candidate` reads `GroundVerdict` |
| M7 (optional) | A read-only "surplus owned copies" report for the mules skill (e.g. the 50 % Goblin Toe on shared tab 4) | — | nothing | — |

**Recommended first step: M0 + M1 together** — the acceptance table and the pure `keep.decide` in shadow mode. No
live behaviour changes; it shows on real visits how often the new rules disagree with today's (and which way), and it
sizes the scroll use before M4. M2 (the Goblin Toe fix) follows once the shadow log of ~30 cycles shows no keeper
the new rules would drop.

---

## 8. Open questions for the player (each with a recommended answer)

| # | Question | Recommended answer |
|---|---|---|
| Q1 | The expensive line for keeping duplicates | **1.0 Ist by the item's own rolls** (§3.3: the 2026-10-19 "1+ ist" ruling, KEEP_IST, SLOW_MINIMUM; 2 Ist has no support) |
| Q2 | "Better" when one paid roll is better and another worse (mixed) | Decide by worth (`value_ist` in its band); with no band, by the summed roll positions of the rolls that matter; a tie is *not better* → drop |
| Q3 | The sketch's `occupied() < 0.5` vs today's rule (town when < 8 cells free, or no 1x3 free) | Keep today's rule (`room_low`): with field drops the inventory holds only keepers, and a town walk is the slow leg; 0.5 would roughly double the visits. `occupied()` is shown on the HUD |
| Q4 | Junk in town: sell or drop? | Drop in the field (no gold needed since Enigma); sell only what is still carried when Jamella is visited anyway (repairs need carried gold, S4) |
| Q5 | How long the do-not-pick-again memory lasts | The game (PutDown's scope: the item is gone with the game); by unit id, then class and place (PutDown.NEAR) when the unit id changes |
| Q6 | Spend a scroll on every rare / magic candidate? | Yes for G6, G9–G11 and every item ≥ 4 cells; rings/amulets too (a cell back is worth 80 gold). If R1 shows magic affixes readable unidentified, magic items need no scroll |
| Q7 | Bases nobody in the build or merc uses but the market pays for (Phase Blade / Berserker Axe / Colossus Blade, Grand Matron Bow, Sacred Rondache) | Pick only rows ≥ 1 Ist with the exact socket count (superior ≥ 15 ED); never plain ones; never carried to town to be sold |
| Q8 | Plain 4os white Monarch (Spirit base, 0.42→0.79) | Keep one (self-use Spirit base) while none is owned; later copies left on the ground |
| Q9 | +3 staff-mod 3os daggers are ≥ 1 Ist, so duplicates are kept: cap them? And plain 3os elite daggers (guide: "any mods: mid", Legend Spike 4→17) stay left per the 2026-10-17 ruling? | Keep the ruling (only +3 Abyss / Hex: Purge / Apocalypse); keep at most 3 per skill unless better (higher superior ED); they fill the shared stash fast |
| Q10 | Worse copies already in the stash (the 50 % Goblin Toe) | Never touched by the loop; listed by M7's report for the mules skill (the player's cleanup) |
| Q11 | The guide's "Forbidden Diadem of the Magus (+2 Warlock skills)" (`guides/warlock.html:158`; `wp-a-builds.json` note "mp713 assumed = 'Forbidden'") — d2data says Forbidden is **+3 Eldritch** (`magicprefix.json:13068`), +2 Warlock is Arch-Devil's (`:13176, :13211`) | Keep both as BiS circlet rows (+3 Eldritch covers Echoing Strike and Hex: Purge); fix the guide line through the warlock-build skill with a dated review pass |
| Q12 | Field identify while monsters are near | Never within `SIGHT` of a hostile; the batch waits for the level end |
| Q13 | Unpriced items (KB `unresolved`, e.g. Goblin Toe in the KB lookup) | Keep the first copy, log `unknown`, and queue them for the update-kb skill; never sold on no evidence |

### Side findings (for the caller)

- The loop's Goblin Toe price (asks q1 0.647, 3 sellers, 2026-10-04) and the KB's Recent Trades fills (q1 = median
  0.061, 20 trades in 2 days, 2026-10-09, `pricing/data/named-trades.json:3284`) disagree by 10×; under either
  number the third copy is cheap and worse, so K6 drops it.
- "Monarch of Deflection" is the suffix **of Deflecting** in the game data (`magicsuffix.json:2990`: +20 % block,
  +30 % faster block); tests and wants use the data's name.
- "+3 Apocalypse" is a Chaos-tree **staff mod** (stat 107, skill 401), not a tab; today's `VOID_STAFFMODS` lacks it
  (`pickmode.py:63`), so in the default GOOD pickup level a 3os dagger with +3 Apocalypse is not taken (only the MOST level takes it,
  through the filter's base rule).

---

## 9. M0 + M1 done (2026-10-20, the player's "start M0+M1", 09:33; Q1-Q13 as recommended)

Built (log only; the loop's behaviour is unchanged):

- `loot/facts.py` (`ItemFacts`, `from_drop` / `from_carried` / `from_observation`), `loot/wants.py` +
  `loot/data/wants.json` (built by `loot/build_wants.py`: every row sourced and its guide quote checked, codes
  resolved from the game data and checked in d2data, asks from `pricing/data/wp-b-prices.json`, the triage own-use
  uniques/sets imported), `loot/value.py` (`value_ist` moved here, identify/service.py imports it back; `assess`,
  `appraise_result`, `matters_for`, `better_than`, `CollectionCopies`), `loot/keep.py` (`decide`, `decide_all`,
  `SHADOW = True`), `loot/ground_judge.py` (`judge`), `loot/today.py` (today's judgements in the new types, for the
  acceptance table only), `loot/shadow.py` (the two hooks: `macros/visit.py` after the junk is judged, and
  `macros/pickmode.py` `kept`; the identify worker notes its KB results for it).
- Acceptance: `tests/inventory_tracking/loot/test_valuables.py` over `fixtures/valuables.json` (72 cases, §6.1-6.4),
  each against the new layers and against today's code; today's failures are strict xfails with the reason.
- Research R1-R3: `rca/2026-10-20/loot-m0-research.md`. R1 no (an unidentified item holds no affix and no socket
  count), R2 sockets/staff mods/eth yes, ED never read (stat 16 is in the +0xD0 chain), R3 no (+0x34 is 0 until
  identified). Consequences taken into the layers: magic rows have no ground conditions; ED is unread on the ground.

Deviations from the text above, on purpose: K7 runs before K5 (a charm is never a duplicate) and K8 before K6 (a
worthless item is not "cheap"); a fallback K10 keeps a cheap first copy; Matriarchal Spear (`amd`, type `aspe`) is
not in the merc polearm rows yet; Jeweler's Archon of the Whale is an always-keep row (K3, not K5).

Shadow lines: `Macro: loot: shadow: <item>: new <action> <rule> <reason> / old <keep|sell> <verdict> [(differ)]`,
`Macro: loot: shadow: town: N items, D differ (...)`, `Macro: loot: shadow: ground: <item>: new <pick|leave> ... /
old <pick|leave> [(differ)]`, and once per error kind `Macro: loot: shadow: <town|ground> failed (...)`.

Two live fixes outside the shadow period (2026-10-20, the player's 08:42 "+3os daggers with +3 apocalypse",
"superior bases"; each made an existing rule never fire):

- `macros/pickmode.py` `VOID_STAFFMODS` takes Apocalypse 401 (`third-parties/d2data/json/skills.json`) beside
  Abyss 402 and Hex: Purge 389 (Q9: only those three at +3): the GOOD level now picks a white or superior 3os
  Void-line dagger with +3 Apocalypse. `loot/build_wants.py` already had it; `test_wants.py` keeps the two equal.
  The fixture case `warlock_dagger_3os_plus3_apocalypse` passes today's code too (its strict xfail removed).
- `game/decode.py` `base_rolls` reads the enhanced defense (16) from the item's +0xD0 modifier chain
  (`chain_defense`, `items/modifiers.py` `owned_chain`; a socket filler's list passed over); `Rolls.defense` is None
  while the chain is not read whole (not cached, read again). The superior 15 % ED Monarch rule (`shield_base`) can
  fire, and `loot/facts.py` `GROUND_STATS` holds 16 for white and superior bases. `ROLLED_TYPES` is unchanged (M5).

### M3 done (2026-10-20, the game closed; no behaviour change)

- `loot/storage.py` holds the pure planning, moved verbatim: from `macros/cube.py` `loot`, `roomed`, `plan`,
  `overflow`, `keys_move`, `KEPT`, `SURE_BLOCK`, `BIG_BLOCK`, `perfect_of`, `rune_recipe`/`RuneRecipe`; from
  `macros/town.py` the stash stop (`stash_stop`, `place`, `_make_way`, `_opening`, `_settled`, the parks, `after`,
  `out_now`, `unread_way_for_cube`, the rune transmutes), `surplus` and their types (`Holdings`, `Put`, `StashStop`,
  `RuneCube`) and constants (`TRADE_ROOM`, `PARK_JUNK`, `RUNES_AIM`, `GEMS_*`, `BER`); and, to keep the layer free of
  an import cycle (`macros/stash.py` imports the cube), the stash's page order and resource tabs (`PAGE_PRIORITY`,
  `SHARED_PRIORITY`, `RESOURCES`, `resource_tabs`, `MATERIALS_TAB`, `is_potion`, `INVENTORY_CELLS`). Every name is
  re-exported from its old module; `town.stash_stop` (NEEDS, PARK_JUNK), `town.rune_transmutes` and `town.uncubed`
  (`rune_recipe`) stay thin wrappers so the tests that patch those module names keep working. `storage.stash_stop`
  takes the block to leave free (`Needs.block`), not `Needs`, which stays with the town routine (`contract`, `Exit`,
  `Needs`, `deposit_to`, `sold_full`, `kept_gem` stay in town.py).
- New: `Storage(pack, own)`, `room(storage) -> Room(inventory, cube, free, rows)` (the count `Loop.look` computed
  inline, the duplicated arithmetic now gone from `loop.py`), `room_low(storage)` = `cells_low(free)` = today's rule
  (Q3: under TRADE_ROOM free cells, the inventory's alone when the cube's room fits no loop item, no SURE_BLOCK free
  → low), `occupied(storage)` (the loop's items' share of its inventory and cube room; HUD/log only). Deviation:
  `occupied`/`room_low` take `Storage` (pack + the player's cells) instead of §1.1's grids + volatile cells, since the
  loop tells the player's items by `own`; a `view`/pages field waits for M6.
- Proof: `tests/inventory_tracking/loot/test_storage_replay.py` replays 13 recorded visits (52 stops, kept in
  `fixtures/visits`, chosen to cover each planning path) against golden plans written by the code before the move
  (SHA-256 of each plan's canonical text, through the re-exports and through storage directly), and, opt-in (`slow`),
  every visit recorded on the host (184 files, 714 stops on 2026-10-20) plus the macros fixtures through the code of
  commit 8c7b1c3 loaded from git: all equal. `test_storage.py`: `room`, `room_low`, `occupied`.

### M4 field identify (2026-10-20, the player's "also start M4 field identify"; Q5, Q6, Q12 as recommended)

Built, behind `loot.api.FIELD_IDENTIFY = True` and `loot.api.CLASSES = {'G6'}` (G9 magic/rare daggers and grimoires,
G10 magic/rare circlets, G11 magic rings and amulets are built and tested — `IMPLEMENTED` — and off until the player
rules). Only in the KP_6 loop (`FIELD.looping`, set by `running/execution.py`); KP_1, attack mode and the other keys by
hand pick and carry as before.

- Pickup: `macros/pickmode.py` `kept` (GOOD level) also takes a drop `Field.pick` names — magic or rare, filter-shown,
  not prized, a ground verdict of IDENTIFY in a class of `CLASSES` (loot/ground_judge.py over loot/data/wants.json) —
  and remembers its unit id for the game as picked for the field identify. `is_candidate` says such a drop is an
  identify candidate: the guard keeps no game and the room routine makes no trip for it (S5 counts must-haves only).
  `pickmode.sure` and `loot/today.py` are unchanged (the acceptance table's today xfails stay).
- Routine (`loot/api.py` `Field.settle`, live hands `loot/hands.py` `GameHands`): only the items picked for it, still
  in the inventory (the cube's wait for Cain), are identified with the Tome (`junk.identify`: one inventory opening,
  the identified flag checked in memory), read and appraised now (the worker's `appraise`, its read and KB result from
  the shadow's `BOOK`), decided (`keep.decide_all` with the collection's copies), and the DROP ones put down at the
  feet (`cube.drop_item`, refused for protected items there too) and remembered (`game/kept.py` `PutDown.reject`: not
  picked, stood by or warned about again this game, logged as the loop's own put-down). A second guard below the
  decision (`api.droppable`) refuses the player's, unidentified, set/unique items, runes, gems, potions, charms,
  jewels, the loop's tools, any item a want row names (a 4os magic Monarch, of Deflecting 3os/4os) and anything worth
  1 Ist or more. No identified read or no appraisal: kept (S8), Cain and today's town path decide.
- When: `api.settle(run, site)`, one call at each site — `macros/portal.py` `to_town` before the cast (Lower Kurast's
  and the terror zones' level end, every trip for room), `macros/loop.py` `Loop.leave` before Save and Exit (not a
  game given up), `running/execution.py` before the loop's `make_room` cube. Never: within SIGHT of a hostile, life
  under the healer's floor, a valuable the loop could pick up now on the ground (one with no room does not hold it:
  the routine may make that room), in town, dead, in controller mode, a panel open. Bounded: 2 identifies of an item a
  game (`MOST_TRIES`), 8 a batch, the tome's charges. The player's hand and a cancel go on up, counted as no failure;
  anything else is logged and the leg goes on.
- Reserve: `IDENTIFY_RESERVE = 5`; `shop.short` is true under it (a visit for the tome alone: superseding the
  2026-10-17 "only on a visit made anyway" for the field identify's tome; `test_shop.py` updated), and the visit's
  contract misses `identifies N` (`town.contract`). Purchases as before: Jamella, carried gold only.
- Logs: `Macro: loot: field: <item> (unit N): <decision>`, `Macro: inventory: <class> (<unit>) at (x, y) dropped in
  the field: <rule> <reason>` (d2-loop-watch `logwords.FIELD_DROP`: games.py and watch.py count it no MISSED, the
  census seeing it after the line), `Macro: loot: field: <site>: N identified, D dropped, K kept[, W wait (Cain in
  town)]` (`FIELD_SETTLED`), `Macro: loot: field: <site>: N to identify wait: <why>` (once a game and site), `Macro:
  put down: ... the loop's own field drop (...)`.
- Tests: `tests/inventory_tracking/loot/test_api.py` (the routine on fake hands; the real unit 1728653239 read
  dropped; every magic Monarch case of `fixtures/valuables.json` kept or dropped as `keep.decide` says; the 4os and
  Deflecting reads kept even when appraised vendor), `test_hands.py` (the fake game's tome clicks and drop),
  `test_field_hooks.py` (the hooks), `tests/skills/test_loop_watch_lines.py` (the lines).
- Not in this step: `cube.droppable` / `drop_for` stay (M3 moves cube.py); M2 (town sales by `keep.decide`) waits for
  the shadow log. Side finding: R1's unit 1728653239 (chain 20:10, 102:15, native suffix 172) is a Monarch **of
  Blocking** (magicsuffix.json "172": block 10, faster block 15), not of Deflecting (row 173: 20 and 30).
