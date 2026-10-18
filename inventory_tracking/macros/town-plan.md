# One planned town visit for the KP_6 loop: design and migration

Asked by the player, 2026-10-18 12:55 (verbatim):

> we need to get a proper ARCHITECTURAL solution to the town visit
> 1. right now when we're doing our town visit with identifying and refilling the stock we're doing back-and-forwards
> 2. when we're putting items to shared stash, we just brute forcing each tab, despite we could exactly know where we
>    can put items
>
> what we need to change: wire together stash reading logic and town visit logic; implement proper module that will
> handle and not forget any step; after the loop we must have: empty cube, all designated free space cells are free in
> the inventory (eg. for warlock: this is 2x4 continuous space); we visit the stash only ONE time, no running back and
> forward
>
> principal architecture: identify everything with cain; move to the shared stash; put all items that we need to keep
> in stash; if we need to get space for runes/gems: we cube them several times to have at least 20 free slots. if we
> have 99pgems - we can stop colleting this type of gems; if we need free space for cubing, we can drop some of
> runes/gems that cannot be stored on the ground in town, but we need to pick and put them into stash when finished;
> after stash visit we should carry only junk/sell items in our inventory or cube; visit store and sell junk items from
> inventory and cube; refill the consumables; if we need to repair things - repair things; go to waypoint; continue
> activity. this is should be generalized and reused. during the loop - we can move items to cube, but if there is no
> free space at all, we just visit town and do routine; after that, we return to our previous location and continue the
> loop (probably with picking up remaining loot)

Design by a read-only planning study (2026-10-18 13:10). Status per step at the end.

## 1. The visit as it runs today (evidence)

Places in Pandemonium Fortress (`shop.USUAL`, `stash.USUAL`; arrival at the waypoint ~(5044, 5019)): waypoint→Cain
(5022.8, 5032.7) 25 units; Cain→stash (5019, 5040) 8; stash→Jamella (5083.5, 5058.5) 67; Jamella→waypoint 56;
Jamella→Halbu (5089.5, 5024.5) 34.5; Halbu→waypoint 46; stash→waypoint 33. One pass waypoint→Cain→stash→Jamella→waypoint
is 156 units; today's with the second stash visit ~200 units, plus a second stash opening and an extra cube opening.

Legs today (`next_leg` Fortress branch, `Loop.leg`): IDENTIFY (Cain; `bring`/`unpack` cube items out; `stash(own, keep,
True)`: runner `stash_loot` = `unload` resource tabs, personal page, shared pages one by one; transmutes; `cube.stash`),
SHOP (`bring` cube junk, `discard` materials, `restock(back=...)`, up to SELL_PASSES more cube passes), STASH (a second
walk to the stash when the cube still holds keepers after the sales), REPAIR (Halbu, `back()`), then the exit leg with
`arrange` and `report`.

12:48 session (`20261018T094616Z-7115ca0e`): Cain 2.6 s; appraisal 0.6; cube out (Linked Mail found no room) 1.8;
stash 2.5; essence drop 1.0; Jamella 7.0; walk toward the waypoint 2.8; STASH leg: cube again 1.1, walk back 1.7,
**pages 0→5 tried 15.4 s** for one item; waypoint 2.2. **Arrival→waypoint 38.6 s.**

Others: 11:46 22.3 s (2.3 s on the full essence refusal, Jamella 7.6 s to fail selling it); 11:50 20.6 s (cube opened
twice, keys in a third opening); 11:55 32.1 s (pages 0→5 13.2 s); 12:42 40.0 s (pages 13 s, second STASH 9.0 s for one
item); 13:00 37.5 s (pages 12.2 s); 11:14 trip 49.6 s whole.

Why pages are brute-forced: a full page costs ~2.25 s (arrow, TAB_SETTLE 0.4, Ctrl+click, `_sent` waits ITEM_SECONDS
1.0); the first switch ~4.2 s. `Pages.first` lives only for the service's lifetime, and restarts are frequent. Every page
but shared page 5 is full, which the service already knows (`Collection …: 298 items … (6 shared tabs` at 12:42:57).

Why back and forth: (1) cube keepers go through an inventory too full before the stash; the stash closes before room is
made, so a second STASH leg follows Jamella; (2) `restock(back=True)` walks toward the waypoint, then STASH walks back;
(3) the cube/inventory panels open 2-4 times a session; (4) Jamella visited only for an essence no vendor buys.

What the stash read knows (`collection/capture.py`, `collection/research.md` R1/R2): shared pages are player units
(type 0) with the local player's name and no level or life stats (`is_shared_candidate`), ordered by the u64 at +0xD8
(`read_stash_meta`); each owns grid 6, 10 x 10 (`read_owner_grids`, `grid_space`, `fits`). "6 shared tabs" = 5 shared
pages + one same-name unit owning the Gems/Materials/Runes tabs (its grid 6 always empty). Resource stacks are
owner-less item units (owner 0xFFFFFFFF, page 4, mode 0, cell (0,0)), one per type held; count = u32 at item data +0x9C
(`native/stack_items.read_stack_count`, checked against 43 counts); a type not held has no unit (count 0). All readable
in town with the stash panel closed (R2). The macros today read only the personal page (`Pack.stash`/`stashed`).

## 2. Design

### 2.1 Modules

`inventory_tracking/macros/town.py`: pure (types, trigger, planner, contract; no input, no reads).

```python
Cell = tuple[int, int, int]
STACK_MOST = 99
STACK_ROOM = 20          # the player 2026-10-18: "at least 20 free slots"

@dataclass(frozen=True)
class Page:                      # 0 personal, 1..5 shared (by the +0xD8 order)
    index: int
    rows: tuple[str, ...]        # 10 x 10, '.' free
    owner: int | None = None

@dataclass(frozen=True)
class StashView:
    pages: tuple[Page, ...]
    stacks: Mapping[int, int]    # resource class -> count on its tab (absent: 0)
    def room(self, txt: int) -> int: ...      # STACK_MOST - count
    def full(self) -> frozenset[int]: ...

@dataclass(frozen=True)
class Needs:                     # from the build and the run kind
    block: tuple[int, int]       # BuildSettings.free_block, Warlock (2, 4)
    keys: int                    # Kind.keys: LK 24, Andariel 12
    portals: PortalSource
    identifies: int = 20
    stack_room: int = STACK_ROOM

@dataclass(frozen=True)
class Holdings:
    pack: Pack
    own: frozenset[Cell]
    junk: frozenset[int]         # unit ids judged `vendor` (after Cain)
    unknown: frozenset[int]

class Exit(Enum): WAYPOINT, LEAVE, PORTAL

@dataclass(frozen=True)
class Put:
    item: Carried
    source: Literal['inventory', 'cube']
    to: int                      # page index, or -tab for a resource tab

@dataclass(frozen=True)
class Transmute:
    txt: int
    gems: tuple[int, ...]
    park: tuple[int, ...]        # units put on the ground meanwhile (resources only)

@dataclass(frozen=True)
class StashStop:
    puts: tuple[Put, ...]                 # grouped: resource tabs, then pages 3, 4, 5, 2, 1, 0
    out_for_sale: tuple[Carried, ...]     # cube junk to the inventory while the stash is open
    drops: tuple[Carried, ...]            # full-stack materials no vendor buys
    transmutes: tuple[Transmute, ...]
    deposit_to: int | None
    keys_to: Move | None                  # cube.keys_move for Needs.block

@dataclass(frozen=True)
class ShopStop:
    sell: tuple[Carried, ...]
    from_cube: tuple[Carried, ...]
    buys: tuple[Buy, ...]

@dataclass(frozen=True)
class Itinerary:
    identify: tuple[Carried, ...]
    stash: StashStop | None
    shop: ShopStop | None
    repair: bool
    exit: Exit
    why: tuple[str, ...]

@dataclass(frozen=True)
class Contract:
    cube: int
    block_free: bool
    loop_items: int
    junk_left: int
    keys: int | None
    portals: str
    parked_on_ground: int
    misses: tuple[str, ...]

def due(h, view, needs, *, game_end, short, repair, trip) -> str | None   # the trigger (TRADE_ROOM, SURE_BLOCK, ...)
def place(pages: Sequence[Page], items: Sequence[Carried]) -> dict[int, int]  # unit -> page, largest first, first fit
def plan(h, view, needs, *, gold, cap, repair, exit, full_fallback) -> Itinerary
def after(pack: Pack, stop: StashStop) -> Pack                             # simulated result of the stop
def contract(pack, own, needs, parked_left) -> Contract
```

Moves into town.py: `surplus`, GEMS_A_KIND, GEMS_KEPT, TRADE_ROOM, `deposit_to`, `tops_up` (loop.py); TRANSMUTES,
PICK_SLACK (runner.py).

`inventory_tracking/macros/visit.py`: the executor, one call walks the itinerary once and checks the contract.

```python
@dataclass
class Hands:                                      # the runner's closures, one object
    inventory_key: Callable[[], str | None]
    identify: Callable[[Sequence[Carried]], int]
    judge: Callable[[list[Carried]], list[Carried]]
    park: Callable[[int], None]
    pick_parked: Callable[[frozenset[int]], int]
    view: Callable[[], StashView | None]

@dataclass(frozen=True)
class TownMap:
    area: int
    waypoint: tuple[float, float]
    stash: tuple[float, float]
    cain: int
    vendor: int
    repairer: int

FORTRESS_MAP = TownMap(103, (5044.0, 5019.0), stash.USUAL, CAIN, JAMELLA, HALBU)

def visit(run, hands, needs, own, exit, town=FORTRESS_MAP) -> Contract
```

`world.py`: `stash_view_of(players, grids_by_owner, items) -> StashView` (pure) and `GameMemory.stash_view()`, wired
as `run.stash_view`; reuses `collection.capture.read_owner_grids`, `is_shared_candidate`, STASH_ORDER_OFFSET,
`read_stack_count`; drops the resource-tab owner (always-empty grid); the personal page from `Pack.stash`.

`build.py`: `BuildSettings.free_block = (2, 4)` (Warlock); `cube.BIG_BLOCK` becomes the default.

### 2.2 The planner, in order

1. Cain: every unidentified magic-or-better item, inventory and cube; skipped with none; wait for verdicts, `judge`,
   plan again from a fresh read (every stop re-plans from memory: idempotent).
2. Stash stop (one walk; opened once, twice only for a transmute): (i) inventory resources to their tab by Ctrl+click
   only where `view.room(txt) > 0` (no full-stack click); (ii) cube resources by Ctrl+Shift on STASH_CUBE likewise;
   (iii) inventory keepers to the page `place()` chose (Shared 3, 4, 5, 2, 1, then Personal; no refused click);
   (iv) cube keepers cube→inventory→page in the room (iii) made (probe P1; fallback close, unpack,
   reopen standing at the stash); (v) cube junk to the inventory as the simulated room allows; (vi) full-stack
   materials dropped at `cube.PARK_POINT`; (vii) keys `keys_move(pack, needs.block)`; (viii) gold `deposit`;
   (ix) close; (x) transmutes (`cube.transmute(..., park)`, resources only parked, `pick_parked`), reopen and stash the
   perfect gems.
3. Jamella: `restock(sell, back=False, keys=needs.keys)`; a cube pass only for `from_cube`; skipped with nothing to
   sell and nothing short.
4. Halbu only if planned; order Jamella then Halbu (Halbu first only if the gold is still capped after the deposit).
5. Exit: WAYPOINT one walk; LEAVE none; PORTAL the trip's way back.
6. Contract: `pack.in_cube == ()`, `room_for(inventory_rows(pack), needs.block)`, no loop item but unsold junk, keys
   and portals at target, every parked unit carried again; log `Macro: trade session done[ (short of the contract:
   …)]: cube N items, block 2x4 free|taken, …, ground clear, 19.4 s (cain 2.6, stash 4.1, jamella 6.0, halbu -,
   walk 6.7)` (the prefix kept for andy.py, trade.py, SKILL 3b).

Expected: 12:48 ~19 s (38.6), 12:42 ~18 s (40.0), 13:00 ~24 s (37.5), 11:55 ~13 s (32.1).

### 2.3 Rulings encoded

Sell only `loot()` items appraised `vendor`; never `own`, never a set/unique charm; `restock` keeps its per-item cell
check and its Abort if another item left. Repairs from carried gold only; the deposit never below
`max(cap - DEPOSIT_ROOM, 1.2 × expected repair)`. Gems: a full flawless kind cubed 3→1 while its perfect stack < 99
(counts from `view.stacks`); `surplus` sells a kind only at perfect 99; new (12:55): perfect at 99 → the kind is no
longer collected (`sold_full` gains its flawless and perfect classes). Full runes sold; full materials dropped; a potion
is never full. Keys LK 24, Andariel 12; Sling → no scrolls. Nothing valuable left on the ground (parked units picked
up before the contract; `_valuable_left` unchanged). `full` still learned from a refusal as a fallback; FULL_FILE keeps
the last read for pickups out of town.

### 2.4 loop.py / runner.py

Delete from loop.py: legs IDENTIFY, SHOP, REPAIR, STASH; fields identified, shopped, restashed, cubed, reported,
arranged, stash_now, junk, unknown, selling, capped, carrying; methods walks_back, shop_next, report; the session logic
in `next_leg`. Add one leg `TOWN = 'town visit'` and `visited: str | None`:

```python
if loop.visit_due and loop.visited != game: return TOWN
if loop.done == game: return LEAVE
kind == ANDARIEL: TO_THE_ENCAMPMENT if trip else TO_THE_CATACOMBS
else: TO_THE_CHESTS
```

`Loop.leg(..., visit: Callable[[Exit], Contract] | None)` replaces stash, identify, judge, bring, arrange, discard.
runner.py: one `town_visit` closure building `Hands`; `gems_tried`, `stash_pages` go; make_room/drop_room stay (field
policy). Re-entry: a Hand or Abort mid-visit re-runs the leg, which re-plans and does only what is left; REPEATS TOWN 2.

Flows: LK game end: LK → portal → Docks → TO_THE_FORTRESS → TOWN(LEAVE) → LEAVE. LK game start: TOWN(WAYPOINT) →
TO_THE_CHESTS. Andariel game start: RE → TO_THE_FORTRESS → TOWN(WAYPOINT) → TO_THE_CATACOMBS. Andariel trip: TRIP →
TO_THE_FORTRESS → TOWN(PORTAL) → TO_THE_ENCAMPMENT → THROUGH_PORTAL → PICK_UP (TRIP resets `fortressed`, `visited`).

## 3. During the loop

`town.field_room(pack, own, needs) -> 'ok' | 'cube' | 'keys' | 'trip' | 'drop' | 'stop'`: (1) loop items into the cube
while it has room, proactively when `needs.block` is not free; (2) keys out of the block (`keys_move`); (3) no room
and a valuable waiting → a trip, both kinds (`Kind.portal_town`: Docks / RE; TO_THE_ENCAMPMENT generalizes to
`travel(kind.portal_town)`; LK's TO_THE_FORTRESS must not set `done` on a trip; once a game); (4) `drop_for`; (5) stop
with the valuable stood by (the only stop besides death).

## 4. Migration (each step keeps the live loop working)

- Step 0, read and log only: `world.stash_view_of` / `GameMemory.stash_view`; log `Macro: stash view: pages free 0:n
  1:n …; full stacks …` at each town look; `trade.py --sessions`. Tests test_world.py. Measure: the view's page with room
  = the page `unload` lands on; its full stacks = the refusals. Probes P1 (Ctrl+click a cube item in the stash's
  resource view → inventory?), P2 (cube inside Jamella's window?), P3 (gems out of a resource stack).
- Step 1, town.py planner, pure, no caller; tests test_town.py (12:48 Linked Mail cube→inventory→page 5 in one stop;
  12:42 items to page 5 with no other page; no full-stack Put; cube junk fits after keepers; block free; surplus and
  perfect-99 gate; deposit floor; exit per flow).
- Step 2, the stash stop by plan inside today's legs: IDENTIFY's and STASH's `stash(...)` call
  `visit.stash_stop(plan.stash)` when `stash_view()` reads, else `unload` as today. Fakes: `stash_pages` rows, `stacks`,
  `cube_spill`. Tests: `test_a_visit_clicks_only_the_page_with_room`, `test_a_full_stacks_item_is_never_clicked`,
  `test_a_cube_keeper_goes_through_the_room_the_inventory_keepers_left_in_one_opening`. Measure: `page N is full` → 0;
  stash ≤ 5 s; STASH legs → ~0; session median ~32-40 → ~22 s.
- Step 3, the TOWN leg (`visit.visit` Cain → stash → Jamella → Halbu → exit); delete the old legs; andy.py TRADE_LEGS,
  trade.py, SKILL 3b in the same change; fakes with several NPCs; test_visit.py (order [Cain, stash, Jamella,
  waypoint], one stash walk; Halbu after Jamella; LEAVE no walk back; contract holds; a Hand mid-visit re-plans with
  nothing done twice). Measure: arrival→waypoint median ≤ 22 s; no "short of the contract"; no `the stash` leg.
- Step 4, transmutes and parking inside the stash stop by stack counts; perfect-99 stop-collecting. Measure: "put down
  for the transmute" = "picked up again"; "stack is full" → 0.
- Step 5, stack room ≥ 20 (gated on P3): 3 at a time from a full flawless stack, ≤ TRANSMUTES_A_VISIT 2.
- Step 6, field policy and trips for LK. Measure: "the loop stops here" → 0.
- Step 7 (optional), the portal town's own services (RE / Docks TownMap; vendor ids Akara 148, Charsi 154, Ormus 255,
  Hratli 253; keys in stock; Cain per act).

## 5. Risks and what each step keeps

- Page mapping (0, 2): the sixth unit is the resource owner; a wrong order misplaces. After each Put read where it
  landed; learn the page on a mismatch; a refused target falls back to `unload`'s scan for that item only.
- Clicks and panels: `_sent` (an item on the pointer put back, the leg aborts); Escape only with a panel open; mouse
  mode only.
- Selling and gold (3): "we shouldn't sell our own equipment" (2026-10-17), "do not sell own equipment or valuable
  items" (11:10 2026-10-18); the 10:28 hand-moved fix (`sort(loose)`); `_potion` (a Full Rejuvenation Potion sold at
  03:35:18); `deposit_to`/`capped` (15:33); carried-only repairs (9M stash gold).
- Cube and transmutes (4): exactly three gems before Transmute; only resources parked and picked up before the
  contract; the 09:22-09:58 jam cannot recur (counts are read).
- Watchdogs (3): the visit under STILL_SECONDS 45 / GAME_SECONDS 240; `tops_up` only until done (15:48:43);
  `kind.keys`; the Sling's no-scroll rule.
- Trips (6): `fortressed`/`visited` reset on TRIP (11:56:48, 12:36); LK `done` untouched on a trip; never Save and
  Exit with a valuable on the ground.
- Report consumers (3): andy.py TRADE_LEGS/TRIP_LEGS, trade.py, SKILL 3b; keep the `trade session done` prefix.

## Status

- 2026-10-18 20:18: the player changed the storage order to shared 3 > 4 > 5 > 2 > 1 > personal. The planner,
  fallback scan, temporary shared parking and Gheed's storage now use that order. Resource items still go to their
  dedicated tabs. Earlier step notes below describe the implementation at their recorded time.
- 2026-10-18 13:15: plan written. Steps 0-2 in progress.
- 2026-10-18 (steps 0-2 implemented, not yet run live; the service not restarted):
  - Step 0: `world.Page`, `world.StashView` (`room`, `full`, `page_of`, `said`), `world.stash_view_of` (pure: the
    personal page from the character's grid 6; the shared candidates (`is_shared_candidate`) by +0xD8; exactly
    SHARED_PAGES + 1 of them, the last with an empty grid dropped as the resource tabs' owner, else no view; the
    owner-less page-4 units' counts) and `GameMemory.stash_view`, wired as `run.stash_view` (engine `Run.stash_view`,
    runner `_execute`). `visit.note_view` logs `Macro: stash view: pages free 0:n …; full stacks …` once a game in the
    Fortress (runner LOOP branch, before `Loop.leg`; loop.py untouched). Checked offline on the 10:27 collection capture
    (`20261018T102718Z-d143b59c`): six candidates, the empty last one dropped, `pages free 0:7 1:5 2:16 3:2 4:16 5:62;
    full stacks Full Rejuvenation Potion, Twisted Essence of Suffering`. Tests: test_world.py.
  - Step 1: `town.py` with the types (Needs, Holdings, Exit, Put, Transmute, StashStop, Buy, ShopStop, Itinerary,
    Contract; Page and StashView re-exported from world.py, which cannot import town.py), `place`, `out_now`,
    `stash_stop` (the stash-stop part of `plan`), `after`, `stop_collecting` (perfect 99), `surplus` by the view's
    counts, `deposit_to` with the repair floor. GEMS_A_KIND, GEMS_KEPT, DEPOSIT_* are duplicated from loop.py until
    step 3 moves the session (loop.py untouched). `due`, `plan`, `contract`, the transmutes' plan: not yet (steps 3-4).
    Tests: test_town.py.
  - Step 2: `visit.stash_stop` executes the plan from runner `stash_loot` (IDENTIFY and STASH legs) when
    `run.stash_view()` reads, else `unload` as before. One walk; the cube's keepers that fit come out first; tabs, the
    personal page, the shared pages straight to the planned one (`_shared` the first time, the arrows after; the page
    the Shared tab showed last kept in `visit.Remembered` across stops: no arrow from 5 to 5); the full stacks'
    materials put down between the panels; the deposit. P1 unknown: the fallback (close, `unpack`, reopen in place)
    for a cube keeper that needs the room the inventory's keepers leave. After each put the view is read again: a page
    other than planned is learned as the one shown; a refusal on a remembered page is retried from the first page, else
    that item alone goes to `unload`'s scan. After the stop `Loop.full` = the view's full stacks (no potion), so the
    pickups and the SHOP leg's sales/drops follow the read. Tests: test_visit.py (`test_a_visit_clicks_only_the_page_
    with_room`, `test_a_full_stacks_item_is_never_clicked`, `test_a_cube_keeper_goes_through_the_room_the_inventory_
    keepers_left_in_one_walk`, the material drop, the refused put's scan, the remembered page). Not verified in the
    game: P1, the shared pages' order as the UI numbers them (R1's 2026-09-25 check only), where a Ctrl + click on a
    page puts an item (the plan assumes the first fit), the Shared tab showing the page last looked at after a reopen,
    a drop at PARK_POINT with the stash open.
- 2026-10-18 (step 3 implemented, not yet run live; the service not restarted):
  - `visit.visit(run, hands, needs, own, exit, town=FORTRESS_MAP, *, full, waited, memory) -> Visited` (contract,
    the full stacks as read, `repair_failed`, each stop's seconds): Cain only with an unidentified item (inventory and
    cube); the verdicts (`Hands.judge`) and `town.surplus` make the junk; one stash stop (`_stash`: `stash_stop` by the
    view, else `unload`'s scan for what is not junk, unidentified or a full gem stack's; non-hand Aborts logged and the
    visit goes on); the full gem stacks' transmutes standing there (`Hands.transmute`, runner `transmute_gems`: only kinds
    whose perfect stack is not full), the stop planned again for the perfect gems with no walk; the full materials put
    down (`drop_item`); Jamella only with something to sell (junk by unit, full runes) or `short`: the cube's junk the
    stop left out first, `restock(sell, back=False, keys=needs.keys)`, up to SELL_PASSES more passes while the cube
    holds junk and a pass sold something; Halbu after her when `repair.due` (any missing charge in a visit:
    `town.tops_up`), before her only if a sale would still pass the gold cap; a key stack moved when the build's block is
    taken and `keys_move` frees it; the walk to the waypoint only after Jamella or Halbu and never for `Exit.LEAVE`.
    Then `town.contract` and `Macro: trade session done[ (short of the contract: …)]: cube N items, block 2x4
    free|taken, N inventory cells free, junk left N, keys K, portals P, staff C, ground clear, T s (cain …, stash …,
    jamella …, halbu …, walk …)`.
  - town.py: TRADE_ROOM, GEMS_A_KIND, GEMS_KEPT, DEPOSIT_* (only here now), `sold_full`, `surplus` (a view or the
    classes), `deposit_to` (repair floor), `tops_up`, `contract`. repair.py: `due` (the loop's repair rule, shared).
  - loop.py: legs IDENTIFY, SHOP, REPAIR, STASH gone, TOWN = 'town visit' added; fields identified, shopped, restashed,
    cubed, reported, arranged, stash_now, junk, unknown, selling, capped gone (`free`, `carrying` kept for the trigger),
    `visiting`/`visited` added (TRIP resets both); `Loop.visit_due(game)` (the old errand rule; a begun, cut visit made
    again), `exit_of(game)` (LEAVE at a game's end, PORTAL on a trip, else WAYPOINT), `repair_waited()`; methods
    walks_back, shop_next, report and the module's surplus/deposit_to/tops_up gone. `Loop.leg(..., visit=, identify=,
    bring=, ...)`: stash, judge, arrange, discard gone (identify and bring stay for GHEED_CHOOSE). The dead
    `stash(own, keep, False)` calls at TO_THE_CHESTS/LEAVE gone (the runner's returned 0 without force).
  - runner.py: `town_visit(exit)` builds `Hands` and `Needs(keys=kind.keys, portals=loop.portal)`, keeps the full
    stacks (FULL_FILE) and `repair_failed`; `stash_loot`, `arrange`, `discard`, `gems_tried`, `stash_pages` gone.
  - Tools: andy.py TRADE_LEGS has 'town visit' (the old four kept for older logs); trade.py takes the Cain and Jamella
    seconds of a `town visit` leg from its done line; SKILL.md rule 3b says the one leg and its line.
  - Tests: test_visit.py (order [cain, stash, jamella, waypoint] with one stash opening; Halbu after Jamella and LEAVE
    with no walk; the cube's Long Battle Bow in the same stop; a Hand at Jamella then the visit again with neither Cain
    nor the stash; the full material put down, not offered; junk unsold is short of the contract); test_loop.py's
    session tests replaced (TOWN, visited, exit_of, repair.due).
  - Not verified in the game: the whole visit's order and timing; `drop_item` with the stash closed beside it; the
    exit walk from Halbu (repair.py's WAYPOINT_SEEN); a transmute's re-planned stop; Halbu first at the cap (the deposit
    usually prevents it). Measure: arrival→waypoint median ≤ 22 s; no "short of the contract"; no `the stash` leg.
