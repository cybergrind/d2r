# One memory-checked wrapper for the cube, the inventory and the stash: design and migration

Asked by the player, 2026-10-18 14:28 (verbatim):

> create sub-agent that will design cube wrapper that will use memory backed synchronizatin and will allow easier way
> to perform some activities:
> - different modes, cube can be opened in two ways
>   * opened with hotkey `v`: we have cube and inventory on another side
>   * opened inside tab in shared stash: gems, materials, runes - have the access to cube
> - cube that is opened in shared stash has some additional hotkeys:
>   * move to the inventory with ctrl-shift + click
>   * move gems/runes/other things with ctrl + shift + right click on resource => move 3 of item to the cube
> we need to analyze what we're doing with cube:
> - move between cube-inventory with ctrl-click in regular mode
> - move to shared stash: ctrl-click when stash is opened
> and implement all required high level inetrfaces, so script don't use anything hardcoded in business logic and use
> well designed interfaces.
> tests and everything must be done in a systematic and careful way

Then, the same day: "design first": this file is the design; no code is changed until the player has reviewed it.
It serves the town visit ([town-plan.md](town-plan.md), steps 0-3 implemented, not yet run live) and the loop's field
moves (`make_room`, `drop_room`, the transmutes). Written 2026-10-18 from the code in the tree at that time
(cube.py, stash.py, visit.py, charms.py, runner.py, shop.py, junk.py, loop.py), the game's layout and string files, the
player's key files, the RE notes (rca/2026-10-13/pickup-cube.md, re-findings.md, re/names.md) and the serve logs
(`runs/alt-d/*/probe.log`, 2026-10-16 to 2026-10-18 14:31).

## 1. What the macros do with the cube, the inventory and the stash today

Every routine opens its own panels, clicks its own points and waits in its own loop. Seven copies of "close the panels if
open", three of "open the inventory, right click the cube", five of "take up with a click, put down with a click,
else put back", two `_until`, one `_sent`, one `_now`. The checks are all memory reads (`run.carried()` → `Pack`:
`items`, `in_cube`, `cube_items`, `cube` rows, `pointer`, `stashed`/`stash`; `run.stash_view()` → `StashView`:
pages, their items and rows, `stacks`), which is the part worth keeping and sharing.

| Where | Panels it assumes | Input | Memory check | Waits, failure | Live (logs to 14:31 on 10-18) | Incidents its comments cite |
| --- | --- | --- | --- | --- | --- | --- |
| cube.py `stash` (loop items into the cube; runner `make_room`, `_room_in_cube`, `transmute_gems`) | none → inventory (key, action 1) → cube (right click on the cube item) | Ctrl + left click, inventory item | unit in `cube_items` | `ITEM_SECONDS` 1.0; not in: put back if on the pointer, `Abort`; Escape in `finally` | 516 "moved in" | takes 20261016T180313Z/181510Z (the gesture); 22:50 10-16 (say why nothing moved); 16:39:01 10-17 (larger first, `plan`) |
| cube.py `unpack` (cube → inventory; visit, runner `bring`, stash `unload`) | as above | Ctrl + left click, cube item | unit not in `cube_items`; `room_for` checked before each | two tries, `RETRY_PAUSE` 0.3; one that stays is passed over | 462 "taken out", 35 "did not come out" | 13:11:52 10-17 (tallest first); 14:51:04 (no block, no click); 12:54:10 (passed over, not the end) |
| cube.py `transmute` (+ `_park`) | as above | Ctrl + left click both ways; `_park`: plain click cube item → pointer, click `PARK_POINT` → ground; click Transmute | exactly the three units in `cube_items` before the button; one perfect gem the only item after (`TRANSMUTE_SECONDS` 1.5) | `Abort` caught and logged unless `run.stops`; `park(unit)` told before the drop (world.py `PutDown`) | 21 made, 62 not; `_park` never yet (0 "put down for the transmute") | 09:53 10-18 (park ruling); 09:22-09:58 (the full-stack jam) |
| cube.py `arrange_keys` (keys out of the 2 x 4 block; visit, `make_room`) | none → inventory | click key → pointer; click new cell; else click old cell | `pointer == key`; then unit at the cell, pointer empty | warning if still on the pointer | 14 moved | 19:10 10-17; 12:36 10-18 (2 x 4 before larger) |
| cube.py `drop_item` / `drop_for` (visit's full materials; `drop_room`) | none → inventory | click item → pointer; click `DROP_POINT` → ground; else put back | pointer, then unit gone and pointer empty | returns False | 2 dropped | 21:00:03 10-17 (Grand Charm, `SURE_BLOCK`) |
| stash.py `open_stash` / `close_stash` | none → stash + inventory (walk, click the `Bank` object) | `walk_until`, `use_thing` | `{'stash', 'inventory'}` open | `PANEL_SECONDS`; `Abort` | every stash stop | 01:07:41, 01:28:48, 01:35:40 10-17 (walk until drawn, stand still) |
| stash.py `unload` (the scan; visit fallback with the stash unread) | stash; a resource tab shown (the cube's grid at (431, 784)); Personal / Shared + arrows | Ctrl + Shift + left click cube resource → its stack; Ctrl + left click inventory item → its stack (any tab) or the page shown | unit left `cube_items` / `items`; `_sent`: on the pointer → put back, `Abort` | refusal → own tab shown again → `full` learned; page + 1 | 355 "items put in" | 01:28:34 10-17 (a charm stays on Ctrl + Shift); 01:31:48, 09:23:12-21 10-18 (full flawless stacks: each stayed in the cube, nothing else happened); 06:08:50 (a refused kind not tried again); 17:52 (`Pages.first`) |
| stash.py `deposit` | stash open (else the button drops the gold) | click gold button, BackSpace x 8, digits, Return | carried gold falls by the amount | Escape, `pause('key')` | 3 | 16:02:26 10-17 (the dialog sets no panel flag) |
| visit.py `stash_stop` (`_tabs`, `_pages`, `_show`, `_drops`, `_scan`) | stash; tabs; shared page by arrows, remembered across stops (`Remembered.shared`) | as `unload`; `_drops`: click → pointer, click `PARK_POINT` | as `unload`, and the view read again after each page put (`page_of`) | a refused remembered page: from the first page; else `_scan`; P1 unknown → close, `unpack`, reopen in place | 8 "by the view"; 14:21:23 and 14:31:48 made 2 openings (the P1 fallback, ~0.9 s each: closed 14:31:42.03, open again 42.89) | town-plan §5 |
| charms.py `park`, `choose` (`_onto_shared`, `_take`, `settle`) | stash; a shared page | Ctrl + left click inventory → page; Ctrl + left click page item (`STASH_PAGE`) → inventory; `settle`: click / click within the inventory | view `page_of`; landing on page 0 → taken back, `Abort` | `Abort` with where it lies | 2 parks (13:57:40, 14:01:40) | 13:39-13:41 10-18 (the swap rulings) |
| shop.py `restock` (sales) | npc_shop + inventory | Ctrl + left click inventory item = **sell**; Shift + right click stock = buy | unit gone; no other unit gone (`Abort`) | gold cap stops sales | every visit | 10-17 "never sell our own equipment" |
| junk.py `identify` (tome) | inventory | right click tome, click item | identified flag | | rare (Cain first) | |
| runner.py closures | — | `inventory_key()` = `action_key(saved_games, name, INVENTORY)` per call | — | — | — | — |

loop.py uses only the pure helpers (`loot`, `overflow`, `roomed`, `own_of`, `room_for`, `inventory_rows`): it is not
touched by this design.

## 2. What the game and memory give

### 2.1 Panels (memory: `world.open_panels`, native/layout.py PANEL_FLAGS)

`inventory` 0x01, `npc_interact` 0x08, `npc_shop` 0x0B, `stash` 0x18, `cube` 0x19. Read every look, all panels closed or
not. **Not in memory as far as is known:** which stash tab or shared page is shown (the code tracks what it clicked:
`Tally.shown`, `Remembered.shared`); whether the gold dialog is up. **Not yet seen:** which flags the cube key sets
(`cube` alone, or `cube` and `inventory`), and whether `cube` is set while a resource tab shows the cube's grid (probe
P0). The design never relies on either: the mode a session is in is the memory's panels plus the tab the session
itself showed.

### 2.2 Keys

`input/keybindings.py` `action_key(saved_games, name, action)` reads the character's own key file. Action 1 is the
Inventory (`i`, `b`). **Action 60 is `CfgOpenCube`, "Horadric Cube"** (`ai_d2_keybind_action_name` 0x140cfea60,
rca/2026-10-13/re/names.md; stringsui.json `CfgOpenCube`). Read today from the player's files: `0x56` (`v`) primary in
CybergrindAA194867311.keyo, EchoingStrike.key, Warlock.key and Custom.key; **unbound (0xFFFF) in the untouched files**
(AmazonAA, JewelAA, CybergrindAB), so the inventory key and a right click on the cube stay the fallback. Actions 61/62
are `CfgCycleStashLeft`/`Right` ("Previous/Next Stash Page", stringskeybinds.json): unbound in the player's files,
`0x1009` (Tab with a modifier flag) in the untouched ones; not used (the arrows are clicked), noted for later. The key
file is read by the client at launch only (memory: d2r-online-and-loot-to-cube), so a key the file names may not be
the one the running client has: every open is checked in memory and falls back.

### 2.3 Grids and places to click (the game's layout files; 1 unit = 1/2160 of the window's height, 98 a cell)

| Grid / place | Panel | Layout | Today's name |
| --- | --- | --- | --- |
| Inventory 10 x 4 (grid 2) | right `(1.0, 0.397)`, `(-1394, -651)` | (93, 897) | cube.py `INVENTORY` |
| Cube 3 x 4 (grid 5), cube mode | left `(0.0, 0.397)`, `(236, -651)` | (431, 534) | cube.py `CUBE` |
| Cube 3 x 4 on a resource tab | left | (431, 784) `advancedstash_horadriccube/horadriccube_grid` | stash.py `STASH_CUBE` |
| Stash page 10 x 10 (grid 6) | left | (89, 219) `basicstash_container/grid` | stash.py `STASH_PAGE` |
| Stash tabs (0 Personal, 1 Shared, 2 Gems, 3 Materials, 4 Runes) | left | `BankTabs` (82, 146), 195 x 72 each | stash.py `tab_point` |
| Shared page arrows | left | `StashNavigation` (369, 1211) + (29/327, 13), 64 x 64 | `SHARED_LEFT` / `SHARED_RIGHT` |
| **Resource stack slots** (one per item code; gems 98 x 98 from (164, 232), materials pk1-ua5 98 x 196, runes from (114, 268)) | left | `advancedstash_gems|materials|runes/<code>` `AdvancedStashSlotWidget` rects (read 2026-10-18) | none yet: needed for a right click on a stack |
| Transmute button | left (cube mode) | (520, 969) + 35 | cube.py `TRANSMUTE` |
| Gold button | right | (429, 1347) + (27, 24) | stash.py `GOLD_BUTTON` |
| The ground between the panels / left of the inventory | window fractions | — | `PARK_POINT` (0.5, 0.7) / `DROP_POINT` (0.3, 0.5) |

### 2.4 The gestures, by panel (the game's own words, stringsui.json, read 2026-10-18)

The item tooltip says what a click does: `InventoryItemTooltipAppenderMove` "Ctrl + Left Click to Move",
`…Sell` "Ctrl + Left Click to Sell", **`…Drop` "Ctrl + Left Click to Drop"**, `…Give`, `…MoveCube` "%s to Move to
Horadric Cube", `…MoveAdvStash` "%s to Move to Stack Tab", `…KeyComboCtrlShiftLC` "Ctrl + Shift + Left Click",
**`…BulkMovePostfix` " (Right Click to Move %u)"**. Code picks the string by the panels open
(rca/2026-10-13/pickup-cube.md §2.2 b, b', b''). So one physical gesture means different things in different panels,
and two are dangerous: **Ctrl + click with only the inventory open drops the item; with a vendor open it sells it.**

| Panels (mode) | Source → destination | Gesture | Evidence |
| --- | --- | --- | --- |
| cube + inventory (CUBE) | inventory → cube (the game finds the cell) | Ctrl + left click | **proven** (516 live) |
| CUBE | cube → inventory | Ctrl + left click | **proven** (462 live) |
| CUBE | cube → pointer → ground | click, click on the ground | in code (`_park`), never run live |
| CUBE | Transmute | click the button | **proven** (21 made) |
| CUBE | pointer → a cube cell | click on the cell | fake only |
| inventory alone | inventory → pointer → cell / ground | click, click | **proven** (keys 14, drops 2) |
| inventory alone | inventory item | Ctrl + left click | **drops it** (game string); never used, must never be |
| stash + inventory, Personal/Shared (STASH) | inventory → the page shown (first fit) | Ctrl + left click | **proven** (355 live) |
| STASH (any tab) | inventory resource → its own stack | Ctrl + left click | **proven** (the player, 10-18; live); a full stack refuses, nothing moves |
| STASH | page item → inventory | Ctrl + left click | in code (charms `_take`); tests only |
| STASH | inventory → cube | Ctrl + Shift + left click | game string ("to Move to Horadric Cube"); unproven |
| stash on a resource tab (STASH_CUBE) | cube resource → its stack | Ctrl + Shift + left click | **proven** (live); a full stack refuses, nothing moves (09:23:12-21 10-18) |
| STASH_CUBE | cube non-resource → ? | Ctrl + Shift + left click | **conflict**: stayed at 01:28:34 10-17; the player 10-18 14:28: "move to the inventory with ctrl-shift + click". Probe P1 |
| STASH_CUBE | cube item → ? | Ctrl + left click | unknown (town-plan P1) |
| STASH_CUBE | stack → cube, 3 of it | Ctrl + Shift + right click on the stack's slot | the player 14:28; the string "(Right Click to Move %u)". Probe P3 |
| STASH_CUBE | stack → cube, 1 / stack → inventory | Ctrl + Shift + left / Ctrl + left click on the slot | inferred from the strings; probe P3 |
| npc_shop + inventory (SHOP) | inventory item → sold | Ctrl + left click | **proven**; out of this wrapper's verbs, inside its guard |

### 2.5 Where an item is, from memory alone

`Pack.items` (inventory, top-left cell), `Pack.in_cube` / `cube_items` (cube), `Pack.pointer` (on the pointer),
`Pack.stashed` (personal page), `StashView.pages[n].items` (shared pages), `StashView.stacks` (resource counts: a unit
put onto a stack disappears into the stack's count). An item that is in none of them after a drop is on the ground
(the ground reads, loot/ground.py, can confirm it; `PutDown` keeps the macro's own from being read as the player's).

## 3. Interfaces

Two modules, the pure one testable without a game, the executor the only place that clicks an item.

### 3.1 `macros/containers.py` (pure: no input, no reads)

```python
Cell = tuple[int, int]

class Box(Enum):                      # where an item is
    INVENTORY = 'inventory'
    CUBE = 'cube'
    PAGE = 'stash page'               # with `page`: 0 personal, 1..5 shared
    STACK = 'stack'                   # a resource tab's stack (the unit is gone into the count)
    POINTER = 'pointer'
    GROUND = 'ground'                 # carried nowhere any more
    UNKNOWN = 'unknown'               # unread

@dataclass(frozen=True)
class Where:
    box: Box
    page: int | None = None
    cell: Cell | None = None
    count: int | None = None          # STACK: the stack's count as read

def where(unit_id: int, pack: Pack | None, view: StashView | None = None) -> Where
def stack_of(txt: int, view: StashView | None) -> Where           # Box.STACK with its count

class Mode(Enum):                     # what is open, as the session knows it (2.1)
    CLOSED = 'closed'
    INVENTORY = 'inventory'           # alone: Ctrl + click drops
    CUBE = 'cube'                     # cube + inventory: the cube key, or the inventory key and a right click
    STASH = 'stash'                   # stash + inventory, the Personal or the Shared tab shown
    STASH_CUBE = 'stash cube'         # stash + inventory, a resource tab shown: the stacks and the cube's grid
    SHOP = 'shop'                     # a vendor's trade window: Ctrl + click sells

def mode_of(open_panels: Sequence[str], resource_tab: bool) -> Mode   # the memory's flags + the tab the session showed

@dataclass(frozen=True)
class Grid:                           # one drawn grid: its panel anchor, panel origin, grid origin, size
    name: str
    anchor: tuple[float, float]
    panel: tuple[int, int]
    origin: tuple[int, int]
    size: tuple[int, int]

INVENTORY_GRID, CUBE_GRID, STASH_CUBE_GRID, PAGE_GRID: Grid           # the values of 2.3, from today's constants

def grid_of(box: Box, mode: Mode) -> Grid | None                      # the one answer to "where is this box drawn now"
def cell_point(rect: Rect, grid: Grid, at: Cell, size: Cell = (1, 1)) -> Point   # today's cube.cell_point
def slot_point(rect: Rect, txt: int) -> Point                         # a resource stack's slot (data/stash_tabs.json `slots`)
def tab_point(rect: Rect, tab: Tab) -> Point
def place_point(rect: Rect, place: Place) -> Point                    # TRANSMUTE, GOLD, SHARED_LEFT/RIGHT, PARK, DROP

class Tab(IntEnum): PERSONAL = 0; SHARED = 1; GEMS = 2; MATERIALS = 3; RUNES = 4
def resource_tab(txt: int) -> Tab | None                              # today's stash.resource_tabs

class Gesture(Enum):
    CTRL_CLICK = ('Control_L',), 'Button1'
    CTRL_SHIFT_CLICK = ('Control_L', 'Shift_L'), 'Button1'
    CTRL_SHIFT_RIGHT = ('Control_L', 'Shift_L'), 'Button3'
    LIFT = (), 'Button1'              # take onto the pointer / put down from it

class Evidence(Enum): PROVEN = 'proven'; SAID = 'the player said'; STRINGS = 'the game strings'; UNKNOWN = 'unknown'

@dataclass(frozen=True)
class Way:
    mode: Mode
    source: Box
    dest: Box
    gesture: Gesture
    evidence: Evidence
    note: str                          # the incident or the probe that proved it

WAYS: tuple[Way, ...]                  # the table of 2.4, one row a way
def way(mode: Mode, source: Box, dest: Box, *, trying: frozenset[str] = frozenset()) -> Way | None
    # the PROVEN way; an unproven one only when its probe is in `trying` (3.3)
def forbidden(mode: Mode, gesture: Gesture, source: Box) -> str | None
    # why this gesture must not be made here: INVENTORY + CTRL_* on an inventory item ("drops it"), SHOP + CTRL_* ("sells it")
```

The geometry moves here unchanged (same numbers, same `cell_point` arithmetic); cube.py and stash.py keep their old
names as aliases until their callers are gone, so no import breaks in between. `data/stash_tabs.json` gains a `slots`
key (code → rect) from a small builder (`macros/build_stash_tabs.py <install>`, as build_containers.py), `tabs`
unchanged.

### 3.2 `macros/panels.py` (the executor: the only module that clicks an item)

```python
@dataclass(frozen=True)
class Keys:                            # resolved by the runner from the character's key file, never in business logic
    inventory: str | None              # action 1
    cube: str | None                   # action 60, CfgOpenCube (keybindings.HORADRIC_CUBE, new)

def keys_of(saved_games: Path, name: str) -> Keys

@dataclass(frozen=True)
class Moved:                           # a verb's result: what moved, from where to where, how, how long
    item: Carried
    source: Where
    dest: Where
    gesture: Gesture
    seconds: float

@dataclass(frozen=True)
class Taken:                           # take_resource's result
    txt: int
    count: int                         # how many arrived in the cube
    units: tuple[int, ...]
    stack_left: int | None

class Refused(Abort): ...              # nothing changed; the item is where it was (what, where, why in the message)
class Elsewhere(Abort): ...            # it moved, but not where meant: `.now` says where (still carried or stashed)
class Stuck(Abort): ...                # an item stays on the pointer after the put-back: the leg must stop
class WrongMode(Abort): ...            # the verb is not made in this mode; raised before any input

class Containers:
    """One per run: the run's reads and input, the keys, the player's items (never dropped or sold)."""
    def __init__(self, run: Run, keys: Keys, *, own: frozenset[tuple[int, int, int]] = frozenset(),
                 trying: frozenset[str] = frozenset(), topic: str = 'cube') -> None
    def pack(self) -> Pack                                   # `Abort('the inventory is not read')` when unread
    def view(self) -> StashView | None
    def open(self, mode: Mode) -> AbstractContextManager[Opened]
        # Mode.CUBE: the cube key, checked in memory, else the inventory key and a right click on the cube
        # Mode.INVENTORY: the inventory key
        # Mode.STASH: walk to the stash and click it (today's open_stash)
        # reuses what is open already; on exit closes only what it opened, puts any pointer item back first

class Opened:
    mode: Mode                                               # as the session knows it (2.1)
    rect: Rect
    def show(self, tab: Tab, page: int | None = None) -> None    # STASH/STASH_CUBE: a tab, a shared page (arrows),
                                                                 # remembered across openings (today's Remembered)
    # cube <-> inventory
    def to_cube(self, item: Carried) -> Moved                # CUBE: Ctrl + click; STASH: Ctrl + Shift + click (if tried)
    def to_inventory(self, item: Carried) -> Moved           # from the cube (CUBE: Ctrl + click; STASH_CUBE: P1 if tried)
                                                             # or a stash page (STASH: Ctrl + click on its cell)
    # into and out of the stash
    def to_stash(self, item: Carried, page: int | None = None) -> Moved
        # inventory resource → its stack (any tab); cube resource → its stack (a resource tab shown first);
        # inventory item → `page` (shown first; None: the page shown); the landing page read back from the view
    def take_resource(self, txt: int, count: int = 3) -> Taken   # STASH_CUBE, P3 only: Ctrl + Shift + right click
    # by the pointer
    def place(self, item: Carried, cell: Cell) -> Moved      # within its grid (keys, the Gheed's cell)
    def drop(self, item: Carried, why: str, *, park: Callable[[int], None] | None = None) -> Moved
        # onto the ground (DROP_POINT, PARK_POINT with the left panel open); never an `own` item; `park` told first
    # the cube's button and the gold
    def transmute(self, expect: Callable[[Pack], bool]) -> bool  # CUBE: the cube must hold what `expect` accepts
    def deposit(self, down_to: int) -> int                   # STASH: today's deposit
```

Legacy entry points keep their signatures and returns while callers move (`cube.stash(run, key, own) -> int`,
`cube.unpack`, `cube.transmute`, `cube.arrange_keys`, `cube.drop_item`, `cube.drop_for`, `stash.unload`,
`visit.stash_stop`, `charms.park`/`choose`): each becomes a few lines over `Containers`, with the same log lines.

Business logic after the migration speaks only these verbs: `visit.py` (the stash stop, the drops, the keys),
`charms.py`, runner.py's closures (`make_room`, `drop_room`, `transmute_gems`, `bring`, `_room_in_cube`), all given
one `Containers` built by the runner (`keys_of`, `Loop.own`). No `cell_point`, modifier name or panel name outside
`containers.py`, `panels.py` and shop.py (the vendor's own windows stay shop.py's; its sale click goes through
`forbidden` too).

### 3.3 Unproven gestures

`trying` names the probes the run may make: `'stash-cube-out'` (P1), `'take-three'` (P3), `'inventory-to-cube-in-stash'`
(P5). Off by default. With one on, the verb makes the new gesture, checks the result in memory, logs
`Macro: probe: <gesture> on <item> in <mode>: <where it went>`, and on a refusal makes the proven way in the same verb
(P1: close, `to_inventory` in CUBE mode, reopen the stash in place: today's fallback). After a probe has been seen to work in the
logs, its row's evidence becomes PROVEN in `WAYS` (a dated note) and it leaves `trying`.

## 4. Verification rules (one helper, `Opened._move`)

1. **Pointer empty before every gesture** (`pack.pointer is None`), except the second half of a pick and put. A held
   item at the start: `Stuck`, no input.
2. **The panels read just before a Ctrl gesture**, not believed: `forbidden(mode_of(world.open_panels, …), gesture,
   source)` must be None. Inventory alone → no Ctrl + click on an inventory item (it drops); a vendor open → none
   (it sells).
3. **The verb's mode is checked before any input**: `WrongMode` (e.g. `to_stash` with only the cube open,
   `take_resource` without a resource tab shown).
4. **One settle wait for every move**: poll `run.carried()` (and `run.stash_view()` only when the destination is a
   page or a stack and the caller needs the landing page) every 0.05 s up to `ITEM_SECONDS` 1.0 for `where(unit)` to
   change from the source. Then, in this order:
   - arrived (the destination box; the planned page where one was asked): `Moved`;
   - on the pointer: put back with a click on its source cell, wait for the pointer to empty, then `Refused` (still
     held: `Stuck`). This is today's `_sent`, `_park` and `drop_item` behaviour in one place;
   - unchanged: `Refused`. The callers that pass over a refusal today (`unpack`, the scan's refused page) catch it;
   - somewhere else (another page, the inventory instead of the stash): `Elsewhere` with `.now`; the stash stop
     treats a page other than planned as today (the page shown is learned).
5. **Resources by count**: a unit put onto a stack is gone from the pack; with the view read, its stack's count rose
   by one. `take_resource`: the cube's units of `txt` rose by n and the stack fell by n (n ≤ count asked).
6. **Panels**: an open is checked in memory within `PANEL_SECONDS` 1.5; `rebase()` after every open, close and tab
   click (the 471 px pointer jump, 01:33:52 10-17); Escape only with a panel open (with none it opens the game's
   menu); the context manager puts a pointer item back before it closes; Escape closes everything, so a session never
   closes a panel the player opened before it began unless the verb needed it closed (today's behaviour).
7. **The player's items**: `drop` refuses an item whose (class, cell) is in `own` or whose class is KEPT (the cube, the
   tomes, the keys): `Refused` before any input.
8. **Mouse mode only**: `open` raises `Abort('… needs mouse mode')` with a pad, as today.
9. **No bool verbs**: a verb returns its result or raises. The legacy entry points turn that into their old returns.
10. **Logs**: one line per verb outcome under the caller's topic. Every line the tools parse is kept verbatim:
    `Macro: stash: the <name> stack is full` (d2-loop-watch games.py), `Macro: trade session done` (andy.py,
    trade.py), `Macro: cube: N of M … moved in` / `taken out`, `put down for the transmute` / `picked up again`.

## 5. Migration (each step leaves the loop as it plays now; the suite green after each)

**C0, the pure model (no caller).** `containers.py` as 3.1; `WAYS` filled from 2.4; `build_stash_tabs.py` and the
`slots` in stash_tabs.json; `keybindings.HORADRIC_CUBE = 60`. cube.py/stash.py import their constants from it (aliases
kept). Tests `test_containers.py`: every cell of the four grids gives the same point as today's `cell_point` with the
old constants (exact); `slot_point` of `gcw`, `pk1`, `r01` against the layout numbers; `where` for each box (inventory,
cube, page 0, shared page 3, stack, pointer, ground, unread); `way` returns only PROVEN rows unless the probe is tried;
`forbidden` for inventory alone and the shop; `mode_of` for each panel set. Live: nothing changes.

**C1, the executor (no caller).** `panels.py` as 3.2 with rules 1-10. Fakes (tests/…/macros/fakes.py): the cube key
(`v` opens `('inventory', 'cube')`, a flag `cube_key_opens` to model a key that does nothing); **Ctrl + click with only
the inventory open drops the item** (as the game's string says; today's fake picks it up); a flag for each unknown way:
`stash_cube_ctrl` (P1: 'nothing' | 'inventory' | 'stash'), `stash_cube_shift` ('stays' today's `cube_spill`, or
'inventory'), `take_three` (P3: None | n); a right click with Ctrl + Shift on a slot. Tests `test_panels.py`: each verb's
happy path in each mode it allows; `WrongMode` before input; a refusal leaves the item and raises `Refused`; an item
taken onto the pointer is put back and `Refused`; still held → `Stuck`; `Elsewhere` on another page; no Ctrl gesture
with the inventory alone (no press reaches the fake) and with the shop open; the context manager closes only with a
panel open and puts a pointer item back first; the cube key falls back to the inventory key and a right click when it
opens nothing (and is not tried again that run); an unbound cube key goes straight to the fallback; `drop` refuses an
own item; probes off: no unproven gesture is pressed. Live: nothing changes.

**C2, cube.py over the executor.** `stash`, `unpack`, `transmute` (+ `_park` → `drop(park=…)`), `arrange_keys`
(`place`), `drop_item`/`drop_for` (`drop`) become wrappers; signatures, returns and log lines unchanged; `Keys(inventory=key,
cube=None)` so the same inputs are pressed. test_cube.py unchanged and green (any edit deliberate and named in the
change). Live: the same lines; nothing else.

**C3, the stash's routines over the executor.** `stash.unload`, `deposit`, `open_stash`/`close_stash`; visit.py
`stash_stop` (`_tabs`, `_pages`, `_show`, `_drops`; `Tally.shown`/`guessed` and `Remembered.shared` become the
session's), charms.py `_onto_shared`/`_take`/`settle`. test_stash.py, test_visit.py, test_charms.py unchanged and green.
Done after the town visit (town-plan step 3) has played live, so an RCA of its first sessions is not mixed with this
refactor. Live: the same lines.

**C4, the cube key.** The runner builds one `Containers` per loop leg with `keys_of(...)` (action 1 and 60); visit's
`Hands.inventory_key` becomes `Hands.keys`; cube.py's legacy wrappers take `Keys`. `open(CUBE)` presses `v`, checks
`cube` in memory, else falls back (the fallback logged once a run). Tests: test_runner/test_visit with `v` opening the
cube (one key, no right click); with `cube_key_opens = False` the old way after `PANEL_SECONDS`, once. Live:
`Macro: cube: opened by the cube key (v)` once a run, then no right click on the cube before each Ctrl + click series;
the cube's openings a little shorter (a panel wait less each; measure from the press traces, latency.py).

**C5, callers speak verbs only.** runner.py closures (`make_room`, `drop_room`, `transmute_gems`, `bring`,
`_room_in_cube`), visit.py's drops and keys, charms.py: `Containers` passed in, no `inventory_key` strings, no
`cell_point`. The duplicates go (`_until` x2, `_sent`, `_now`, `_gone`, seven panel-closing blocks). A ratchet test (as
builds/test_ratchet.py): no `click('Control_L'`, `cell_point(` or `'Button3'` outside containers.py, panels.py, shop.py
and junk.py's tome. Live: the same lines.

**C6, the probes, one at a time, when the player says.** With `trying={'stash-cube-out'}` for a watched session: a
cube keeper with no room before the stash's keepers left goes out in the stash's cube view (no close, no reopen: ~0.9 s
and a collection pass less a stop that needs it; "2 openings" → 1). With `'take-three'`: the stash stop can take three
flawless gems of a full stack straight into the cube for a transmute (town-plan step 5: stack room ≥ 20, no gem carried
for it). Each probe's log lines read by the RCA before its row becomes PROVEN and the default.

## 6. Risks and what each step keeps

- **A Ctrl + click that drops or sells** (C1-C5): the panels are read before every Ctrl gesture (rule 2), not trusted
  from the session; the fake now drops on it, so a test that would drop fails.
- **Escape with an item on the pointer** (C1): what it does is not known; the session puts the item back first and
  never closes with one held.
- **Behaviour drift in the refactor** (C2, C3): the old tests unchanged; the same inputs (C2-C3 press exactly what they
  press today, the cube key only from C4); the same log lines (the tools parse them).
- **The tab shown is not in memory** (C3): kept as today, by what the session clicked, remembered across openings
  (`Remembered.shared`); a restart forgets it (the first-page walk, as today).
- **A key file that is not the client's** (C4): the cube key's open is checked; the fallback is today's way.
- **Parked items** (C2): `_park` never ran live; its `PutDown.park` before the drop and the pick-up after
  (`transmute_gems`) stay exactly as they are; covered by test_cube's park test.
- **Reads per move** (C1): a pack read every 0.05 s as now; the stash view only where a page or stack must be
  confirmed (as `_pages` reads it today), not on every put.
- **The player's hand mid-verb** (all): `Hand` from the actuator still ends the verb; the context manager still puts
  back and closes in `finally`; the leg is made again and re-plans from memory (town-plan §2.2).
- **The in-flight town visit** (C3, C5): visit.py and town.py are new and not yet run live; C3/C5 wait for its first
  live sessions and touch only its click layer, not its plan.
- **Concurrent edits** (all): the tree is shared with the live loop and other sessions; each step is one small change
  with its tests, never a long-lived half state.

## 7. Probes needed in the game

| # | What | How it is seen | Needed by |
| --- | --- | --- | --- |
| P0 | The panel flags the cube key sets (`cube` alone or with `inventory`); whether `cube` is set while a resource tab shows the cube's grid | `world.open_panels` logged at each open (C1 logs it, no extra input) | C4 (mode_of), C6 |
| Pv | The cube key `v` opens the cube with the inventory (the player says so) | memory check at the open; fallback otherwise | C4 |
| P1 | In the stash's cube view: Ctrl + Shift + left click on a non-resource cube item → the inventory (the player, 14:28) or nothing (01:28:34 10-17; that inventory may have been full); Ctrl + left click on a cube item → ? | `where(unit)` after the click (C6, `trying`) | C6: the reopen goes |
| P3 | Ctrl + Shift + right click on a stack's slot → 3 of it into the cube (fewer with fewer? with the cube holding something? its own tab shown?); Ctrl + Shift + left click → 1? Ctrl + left click → 1 into the inventory? | cube units of the class and the stack's count before and after | C6, town-plan step 5 |
| P4 | Where a Ctrl + click puts an item on a page (the first free cell row by row, or column by column) | the view after the put | town-plan's `place` (assumed first fit) |
| P5 | Ctrl + Shift + left click on an inventory item with the stash open → the cube (the game string) | `where(unit)` | optional: loop items into the cube without the cube panel |
| P6 | `CfgCycleStashLeft/Right` (61/62) with a key bound: page changes without arrow clicks | the page the next put lands on | optional |

None needs a memory write; each is an input the loop can make in a normal stash stop with the proven way as the
fallback, so each can run in a watched loop session once the player turns its flag on.

## 8. What the live log shows after each step

C0-C3, C5: nothing different (the same lines, the same inputs). C4: one `Macro: cube: opened by the cube key (v)` (or
`… the cube key opened nothing: the inventory and a right click`) per run; the right click on the cube item is gone from
the press traces. C6: `Macro: probe: …` lines in the sessions the player turns a probe on, and "2 openings" in
`Macro: stash: by the view` going to 1.

## Status

- 2026-10-18: design written for review; no code changed. Next: the player's review, then C0.
