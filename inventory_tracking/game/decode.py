"""Pure readers of the game's memory: each takes a `read` and gives records (moved from macros/world.py)."""

import contextlib
import functools
import json
import re
import struct
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import replace
from pathlib import Path

from inventory_tracking.collection.capture import is_shared_candidate, read_owner_grids
from inventory_tracking.common import LOG
from inventory_tracking.game.layout import (
    ALIGNMENT_STAT,
    BANK,
    BASE_STATS,
    BATTLE_ORDERS_BIT,
    COOLDOWN_BIT,
    CURSOR_MODE,
    DAMAGE_PERCENT,
    DAMAGE_PERCENT_STAT,
    DEFENSE_PERCENT,
    DEFILER_CLASS,
    EMPTY_SLOT,
    FULL_STATS,
    GOLD_STAT,
    HERALD_TIER_STAT,
    HEX_PURGE_BIT,
    IDENTIFY_TOME,
    KEY_STACK,
    KEY_STATS,
    LAYERED_SKILLS,
    LEFT_SKILL,
    LOW_STATES,
    LYING_DEAD,
    MAGIC_ROLLED_TYPES,
    MISSILE_DATA,
    MISSILE_OWNER,
    MISSILE_PATH,
    MISSILE_RECORD,
    MISSILE_SLOTS,
    MISSILE_UNIT,
    MODIFIER_LEVEL_STAT,
    MODIFIER_SKILL_STAT,
    MODIFIERS,
    MONSTER_DATA,
    MONSTER_OWNER,
    MONSTER_RESISTS,
    MONSTER_UNIT,
    NAME_WRAP,
    NO_OWNER,
    OBJECT_PATH,
    OBJECT_UNIT,
    PATH_RECORD,
    PORTAL_STATS,
    PSYCHIC_WARD_BIT,
    QUALITIES,
    RESISTS,
    RIGHT_SKILL,
    ROLLED_QUALITIES,
    ROLLED_TYPES,
    SELECTABLE_FLAG,
    SHARED_PAGES,
    SHOP_GRIDS,
    SKILL_IN_USE,
    SKILL_LIST,
    SKILL_RECORD,
    SKILL_SLOT_SIZE,
    SKILL_SLOTS,
    STASH_ITEM_PAGE,
    STATE_RUN,
    STRIKING_MODES,
    TILE_UNIT,
    TYPE_FLAGS,
    UNIT_FLAGS,
    UNIT_SLOTS,
    WHITE_QUALITIES,
)
from inventory_tracking.game.records import (
    VALUABLE,
    Carried,
    Drop,
    Monster,
    Pack,
    Page,
    Player,
    Rolls,
    StashView,
    Stocked,
    Thing,
    Warp,
    _rows,
)
from inventory_tracking.items.grid import CUBE_GRID, INVENTORY_GRID, STASH_GRID, STASH_SIZE, Grid
from inventory_tracking.items.identity import (
    ETHEREAL_FLAG,
    FLAGS_OFFSET,
    IDENTIFIED_FLAG,
    IDENTITY_OFFSET,
    ITEM_DATA_SIZE,
    QUALITY_OFFSET,
    SOCKETED_FLAG,
)
from inventory_tracking.items.metadata import item_base, metadata
from inventory_tracking.items.modifiers import owned_chain
from inventory_tracking.items.stat_constants import SKILL_TABS, StatId
from inventory_tracking.levels.doors import Door, door_sizes
from inventory_tracking.levels.memory import WAYPOINT_CLASSES, pointer
from inventory_tracking.levels.model import CLICKED, DURIEL_PORTAL, PORTAL, TOWN_PORTAL, WIRTS_BODY
from inventory_tracking.native.item_diagnostics import capture_stat_candidates
from inventory_tracking.native.layout import (
    DEAD_MODES,
    KEY_CLASS_ID,
    LEVEL_AREA_ID,
    LIFE_STAT,
    MAX_LIFE_STAT,
    PATH_ROOM1,
    PLAYER_DEAD_MODES,
    QUANTITY_STAT,
    ROOM1_ROOM2,
    ROOM2_LEVEL,
    TOME_CLASS_ID,
)
from inventory_tracking.native.memory import game_read
from inventory_tracking.native.units import read_stats, walk_units
from inventory_tracking.tracking.consume import read_consume


GOLD_SEEN: dict[int, int] = {}  # unit id -> amount, of the piles read


def decode_slots(raw: bytes) -> tuple[int | None, ...]:
    if len(raw) != SKILL_SLOTS * SKILL_SLOT_SIZE:
        raise ValueError('Short skill slot table')
    ids = [struct.unpack_from('<I', raw, slot * SKILL_SLOT_SIZE)[0] for slot in range(SKILL_SLOTS)]
    if any(skill != EMPTY_SLOT and skill >= 1024 for skill in ids):
        raise ValueError('Skill slot table does not hold skill ids')
    return tuple(None if skill == EMPTY_SLOT else skill for skill in ids)


def decode_name(raw: bytes) -> str:
    return raw.split(b'\0', 1)[0].decode('ascii', errors='replace')


def next_name(name: str) -> str:
    """cyber32 -> cyber33, cyber99 -> cyber1; only names a macro can type (lower-case letters, digits, a number
    last)."""
    found = re.fullmatch(r'([a-z0-9]*?)(\d+)', name)
    if not found:
        raise ValueError(f'game name {name!r} does not end in a number')
    number = int(found[2])
    return f'{found[1]}{1 if number >= NAME_WRAP else number + 1}'


def position(path: bytes) -> tuple[float, float]:
    x_fraction, x, y_fraction, y = struct.unpack_from('<HHHH', path)
    return x + x_fraction / 65536, y + y_fraction / 65536


def plausible_life(read, stats_pointer: int) -> bool:
    """Whether the unit's full stat list holds a life within a positive maximum (tracking/state.py)."""
    try:
        stats = read_stats(read, stats_pointer + FULL_STATS)
    except OSError, ValueError, struct.error:
        return False
    life = [s['raw'] for s in stats if s['layer'] == 0 and s['id'] == LIFE_STAT]
    most = [s['raw'] for s in stats if s['layer'] == 0 and s['id'] == MAX_LIFE_STAT]
    return len(life) == len(most) == 1 and 0 <= life[0] <= most[0] and most[0] > 0


def skill_in_use(read, record: bytes) -> bytes:
    """The skill a unit is using, raw: the two bytes its skills.txt row begins with (the skill id) and
    the skill record's first SKILL_RECORD bytes. From the client's code (rca/2026-10-13/re-findings.md),
    not yet seen to hold in a game: kept raw for that reason. Empty when any of the three reads fails."""
    try:
        skills = struct.unpack_from('<Q', record, SKILL_LIST)[0]
        used = struct.unpack('<Q', read(skills + SKILL_IN_USE, 8))[0] if skills else 0
        if not used:
            return b''
        kept = read(used, SKILL_RECORD)
        row = struct.unpack_from('<Q', kept)[0]
        return (read(row, 2) if row else b'\0\0') + kept
    except OSError, ValueError, struct.error:
        return b''


def monster_table(read, table: int, *, records: bool = False) -> dict:
    """The monster slot of the unit table walked (native/units.py `walk_units`: 'units', 'complete'): where every
    reader of monsters starts, the look's (`monsters_and_dead`, `corpses`) and the Terror Zone probe's
    (terror/monsters.py `monster_units`), which read different parts of each unit (game/records.py `Monster`)."""
    heads = struct.unpack('<128Q', read(table + MONSTER_UNIT * 1024, 1024))
    return walk_units(read, heads, MONSTER_UNIT, records=records)


def monsters(
    read, table: int, *, dead: bool = False, paths: bool = False, records: bool = False
) -> tuple[Monster, ...]:
    """The live monsters with a position: type flags and owner from the monster data, ally by the
    alignment stat (unreadable stats: not an ally). Dead ones (unless `dead`) and those without a
    path are left out. `paths`: each with its whole path record, where it can be read to its end."""
    return monsters_and_dead(read, table, dead=dead, paths=paths, records=records)[0]


def monsters_and_dead(
    read, table: int, *, dead: bool = False, paths: bool = False, records: bool = False
) -> tuple[tuple[Monster, ...], frozenset[int]]:
    """`monsters`, and the unit ids of the monsters lying dead (from the same walk of the unit table)."""
    found = []
    corpses = set()
    for unit in monster_table(read, table, records=records)['units']:
        if unit['mode'] in DEAD_MODES:
            corpses.add(unit['unit_id'])
        if (unit['mode'] in DEAD_MODES and not dead) or not unit['path_pointer'] or not unit['data_pointer']:
            continue
        record = b''
        if paths:
            with contextlib.suppress(OSError, ValueError):
                record = read(unit['path_pointer'], PATH_RECORD)
        try:
            path = record[:8] or read(unit['path_pointer'], 8)
            data = read(unit['data_pointer'], MONSTER_DATA)
        except OSError, ValueError:
            continue
        owner = struct.unpack_from('<I', data, MONSTER_OWNER)[0]
        ally, life, max_life, tier, resists, aura, raised = False, 0, 0, 0, (), None, None
        if unit['stats_pointer']:
            with contextlib.suppress(OSError, ValueError, struct.error):
                full = read_stats(read, unit['stats_pointer'] + FULL_STATS)
                stats = {s['id']: s['raw'] for s in full if s['layer'] == 0}
                ally = bool(stats.get(ALIGNMENT_STAT))
                tier = stats.get(HERALD_TIER_STAT, 0)
                life, max_life = stats.get(LIFE_STAT, 0) >> 8, stats.get(MAX_LIFE_STAT, 0) >> 8
                resists = tuple((stat, stats[stat]) for stat in MONSTER_RESISTS if stat in stats)
                if stats.get(MODIFIER_SKILL_STAT):
                    aura = (stats[MODIFIER_SKILL_STAT], stats.get(MODIFIER_LEVEL_STAT, 0))
                raised = stats.get(DAMAGE_PERCENT_STAT, 0)
        raw = b''
        if unit['txt_id'] == DEFILER_CLASS:
            with contextlib.suppress(OSError, ValueError):
                raw = read(unit['address'], 0x160) + read(unit['data_pointer'], 0x80)
        monster = Monster(unit['unit_id'], unit['txt_id'], unit['mode'], *position(path), owner, data[TYPE_FLAGS])
        monster = replace(
            monster,
            ally=ally,
            life=life,
            max_life=max_life,
            raw=raw,
            stats_at=unit['stats_pointer'],
            unit_flags=unit.get('flags'),
        )
        whole = states = skill = b''
        if records:
            whole = unit.get('record', b'') + data
            if unit['stats_pointer']:
                with contextlib.suppress(OSError, ValueError):
                    states = read(unit['stats_pointer'] + STATE_RUN[0], STATE_RUN[1])
            if unit['mode'] in STRIKING_MODES:
                skill = skill_in_use(read, unit.get('record', b''))
        monster = replace(
            monster,
            path=record,
            modifiers=tuple(mod for mod in data[MODIFIERS] if mod),
            tier=tier,
            resists=resists,
            aura=aura,
            damage_percent=raised,
        )
        found.append(replace(monster, record=whole, states=states, skill=skill))
    return tuple(found), frozenset(corpses)


def corpses(read, table: int) -> tuple[tuple[int, float, float], ...]:
    """The monsters lying dead (mode 12, the death animation over) as (unit id, x, y), world units.
    Its own walk of the unit table: asked for now and then (Engorge), not at every look at the world."""
    found = []
    for unit in monster_table(read, table)['units']:
        if unit['mode'] != LYING_DEAD or not unit['path_pointer']:
            continue
        with contextlib.suppress(OSError, ValueError):
            found.append((unit['unit_id'], *position(read(unit['path_pointer'], 8))))
    return tuple(found)


@functools.cache
def item_sizes() -> dict[int, tuple[int, int]]:
    table = json.loads((Path(__file__).parents[1] / 'loot' / 'data' / 'sizes.json').read_text())
    return {int(class_id): (size[0], size[1]) for class_id, size in table['sizes'].items()}


def item_size(class_id: int | None) -> tuple[int, int]:
    """Inventory cells (across, down) of an item class; one cell when the class is not known."""
    return item_sizes().get(class_id, (1, 1)) if class_id is not None else (1, 1)


def carried_rows(read, unit: dict | None) -> tuple[tuple[str, ...] | None, tuple[str, ...] | None, frozenset[int]]:
    """The rows of the carried inventory and of the Horadric Cube, '.' a free cell, and the item pointers of all
    the character's grids (`held_items`), from one read of them; the rows None when they cannot be read (no cube:
    no grid of it). `unit`: the character's walked player unit; None when the walk did not find it."""
    try:
        grids = read_owner_grids(read, unit) if unit is not None else {}
    except OSError, ValueError, struct.error:
        return None, None, frozenset()
    return _rows(grids.get(INVENTORY_GRID)), _rows(grids.get(CUBE_GRID)), held_items(grids)


def stash_view_of(
    main: dict, players: Sequence[dict], grids_by_owner: Mapping[int, dict], items: Sequence[dict]
) -> StashView | None:
    """The stash from one read (`GameMemory.read_stash`, reached only through game/stash.py `Stash.read`): `main` the
    character's player unit, `players` the other player units (each with its `details` name and full stats, as
    collection/capture.py `is_shared_candidate` reads them, and its `order`, the u64 at STASH_ORDER_OFFSET),
    `grids_by_owner` their grids by unit id (`read_owner_grids`), `items` the item units (`unit_id`, `address`,
    `txt_id`, `mode`, `owner`, `page`, `count`).

    The personal page is the character's grid 6; the shared pages are the same-name units with no level or life, in
    their order. One more such unit owns the Gems, Materials and Runes tabs, its grid 6 always empty, and orders last
    (research.md R1): dropped. Any other count of such units than SHARED_PAGES + 1, or a last one holding items, is no
    view (None): a page told wrong would misplace. The stacks are the owner-less stash units, one a class held, each
    with its count."""
    by_address = {item['address']: item['unit_id'] for item in items}
    entries = {item['address']: item for item in items}
    by_unit = {item['unit_id']: item for item in items}

    def state(item: Carried) -> Carried:
        entry = by_unit.get(item.unit_id)
        if entry is None or 'quality' not in entry:
            return item
        return replace(item, quality=entry['quality'], identified=entry['identified'], unique=entry['unique'])

    def page(index: int, owner: int, grid: dict | None) -> Page | None:
        if grid is None and index > 0:
            # A shared page with no item has no grid allocated, as an empty cube has none (65cfebc): an empty page.
            # Read as no view, it left the stash unread at every visit from 20:18 on 2026-10-18 (the player emptied
            # shared page 5 for the mules), and the scan's guesses marked the Deep Worldstone Shards full
            return Page(index, Grid.empty(STASH_SIZE), owner)
        if grid is None:
            return None
        units = frozenset(by_address[cell] for cell in grid['cells'] if cell in by_address)
        return Page(index, Grid.from_cells(grid), owner, units, tuple(map(state, _held(grid, entries))))

    personal = page(0, main['unit_id'], grids_by_owner.get(main['unit_id'], {}).get(STASH_GRID))
    if personal is None:
        return None
    shared = sorted(
        (unit for unit in players if is_shared_candidate(unit, main) and unit['unit_id'] in grids_by_owner),
        key=lambda unit: unit['order'],
    )
    # Exactly one unit more than the pages, the last in order with an empty grid: any other count is no view
    if len(shared) != SHARED_PAGES + 1:
        return None
    if any(grids_by_owner[shared[-1]['unit_id']].get(STASH_GRID, {}).get('cells', ())):
        return None
    shared.pop()  # the resource tabs' owner
    pages = [personal]
    for index, unit in enumerate(shared, 1):
        found = page(index, unit['unit_id'], grids_by_owner[unit['unit_id']].get(STASH_GRID))
        if found is None:
            return None
        pages.append(found)
    stacks: dict[int, int] = {}
    for item in items:
        if item['mode'] == 0 and item['page'] == STASH_ITEM_PAGE and item['owner'] == NO_OWNER:
            stacks[item['txt_id']] = stacks.get(item['txt_id'], 0) + item.get('count', 0)
    return StashView(tuple(pages), tuple(sorted(stacks.items())))


def carried_items(read, unit: dict | None, items: Sequence[dict]) -> Pack | None:
    """The carried inventory's items, each at the first cell (row by row) its pointer lies on, and the cube's rows,
    from one read of the character's grids (`carried_rows`); None when they cannot be read. `unit`: the character's
    walked player unit (None: not found), `items`: the walked item units."""
    try:
        grids = read_owner_grids(read, unit) if unit is not None else {}
    except OSError, ValueError, struct.error:
        return None
    by_address = {u['address']: u for u in items}
    pack = pack_of(grids, by_address)
    if pack is None:
        return None
    units = {u['unit_id']: u for u in by_address.values()}

    def quantity(item: Carried, offset: int | None, empty: int | None = None) -> int | None:
        """The item's quantity stat; None unread, `empty` with its stat list read and no quantity in it."""
        unit = units.get(item.unit_id)
        if offset is None or unit is None or not unit['stats_pointer']:
            return None
        try:
            stats = read_stats(read, unit['stats_pointer'] + offset)
        except OSError, ValueError, struct.error:
            return None
        return next((s['raw'] for s in stats if s['id'] == QUANTITY_STAT and s['layer'] == 0), empty)

    def state(item: Carried) -> Carried:
        unit = units.get(item.unit_id)
        if unit is None or not unit['data_pointer']:
            return item
        try:
            data = read(unit['data_pointer'], ITEM_DATA_SIZE)
            quality, flags, unique = (
                struct.unpack_from('<I', data, QUALITY_OFFSET)[0],
                struct.unpack_from('<I', data, FLAGS_OFFSET)[0],
                struct.unpack_from('<I', data, IDENTITY_OFFSET)[0],
            )
        except OSError, ValueError, struct.error:
            return item
        return replace(item, quality=quality, identified=bool(flags & IDENTIFIED_FLAG), unique=unique)

    pack = replace(
        pack,
        items=tuple(map(state, pack.items)),
        in_cube=tuple(map(state, pack.in_cube)),
        stashed=tuple(map(state, pack.stashed)),
    )
    keys = [quantity(item, KEY_STATS) for item in pack.items if item.txt == KEY_CLASS_ID]
    tomes = [quantity(item, PORTAL_STATS) for item in pack.items if item.txt == TOME_CLASS_ID]
    # An empty Tome of Identify holds no quantity stat: 0 charges, not unread (2026-10-20: read None from 15:12 to the
    # player's refill at 20:05, so the field identified nothing and the shop never filled it). The Town Portal tome's
    # is left as it was: the loop casts Town Portal from the Sling
    identifies = [quantity(item, PORTAL_STATS, 0) for item in pack.items if item.txt == IDENTIFY_TOME]
    return replace(
        pack,
        identifies=identifies[0] if identifies else None,
        keys=None if None in keys else sum(k for k in keys if k is not None),
        portals=0 if not tomes else tomes[0],
        key_room=None if None in keys else not keys or any(k is not None and k < KEY_STACK for k in keys),
        pointer=next((u['unit_id'] for u in by_address.values() if u['mode'] == CURSOR_MODE), None),
    )


def pack_of(grids: dict, by_address: dict[int, dict]) -> Pack | None:
    """The carried items of a character's grids (`read_owner_grids`), each at the first cell (row by row) its item
    pointer lies on, and the cube's rows; `by_address`: the item units by their address. None with no inventory."""
    grid = grids.get(INVENTORY_GRID)
    if grid is None:
        return None
    cube = grids.get(CUBE_GRID)
    held = _held(cube, by_address) if cube is not None else ()
    page = grids.get(STASH_GRID)
    return Pack(
        _held(grid, by_address),
        _rows(cube),
        frozenset(item.unit_id for item in held),
        held,
        stashed=_held(page, by_address) if page is not None else (),
        stash=_rows(page),
    )


def _held(grid: dict, by_address: dict[int, dict]) -> tuple[Carried, ...]:
    """A grid's items, each at the first cell (row by row) its item pointer lies on."""
    width, found, seen = grid['width'], [], set()
    for index, cell in enumerate(grid['cells']):
        if not cell or cell in seen or cell not in by_address:
            continue
        seen.add(cell)
        item = by_address[cell]
        found.append(Carried(item['unit_id'], item['txt_id'], index % width, index // width, item_size(item['txt_id'])))
    return tuple(found)


# The ground census (`GameMemory._census`): the item types not said (misc.txt's type column, from the bundled
# metadata on 2026-10-17): potions, scrolls, keys, ammunition, gold; and the unit ids kept at most before forgetting
CENSUS_SKIPPED = frozenset(
    ('hpot', 'mpot', 'rpot', 'apot', 'spot', 'wpot', 'tpot', 'scro', 'key', 'bowq', 'xboq', 'gold')
)
CENSUS_KEPT = 20000


def rolls(drop: Drop | None) -> str:
    """A base's rolls for the census (`rolled`): ' 3os +3 Abyss', ' 4os 15% ED 45 all res'; '' unread."""
    if drop is None or drop.rolls is None:
        return ''
    found, skills = drop.rolls, metadata()['skills']
    named = ''.join(f' +{level} {skills.get(str(skill), {}).get("name", skill)}' for skill, level in found.skills)
    tabs = ''.join(f' +{value} {tab_name(layer)}' for layer, value in found.tabs)
    defense = f' {found.defense}% ED' if found.defense else ''
    damage = f' {found.damage}% ED' if found.damage else ''  # a weapon's: an item has one or the other
    resists = f' {found.resists} all res' if found.resists else ''
    return f' {found.sockets}os{named}{tabs}{defense}{damage}{resists}'


def tab_name(layer: int) -> str:
    """A skill tab's name by its stat 188 layer (class * 8 + tab, items/stat_constants.py SKILL_TABS)."""
    group, tab = divmod(layer, 8)
    if group < len(SKILL_TABS) and tab < len(SKILL_TABS[group]):
        return SKILL_TABS[group][tab]
    return f'skill tab {layer}'


def census(
    name: str,
    quality: int,
    flags: int,
    at: tuple[float, float],
    taken: str | None,
    label: str | None,
    rolled: str = '',
) -> str:
    """The ground census's line for an item: its quality and base, eth and socketed, a dagger's sockets and staff mods
    (`rolls`), where, and the rule that takes it ('left' for none)."""
    marks = ''.join((' eth' if flags & ETHEREAL_FLAG else '', ' socketed' if flags & SOCKETED_FLAG else '', rolled))
    shown = f' "{label}"' if label and label != name else ''
    return (
        f'{QUALITIES.get(quality, f"quality {quality}")} {name}{marks}{shown} at ({at[0]:.0f}, {at[1]:.0f}): '
        f'{f"taken ({taken})" if taken else "left"}'
    )


def stock_of(grids: dict, by_address: dict[int, dict]) -> tuple[Stocked, ...]:
    """A vendor's stock from its grids (`read_owner_grids`), each item at the first cell its pointer lies on."""
    found, seen = [], set()
    for index in SHOP_GRIDS:
        grid = grids.get(index)
        if grid is None:
            continue
        for cell_index, cell in enumerate(grid['cells']):
            if not cell or cell in seen or cell not in by_address:
                continue
            seen.add(cell)
            x, y = cell_index % grid['width'], cell_index // grid['width']
            unit = by_address[cell]
            found.append(Stocked(unit['txt_id'], index - SHOP_GRIDS[0], x, y, unit.get('unit_id', 0)))
    return tuple(found)


def held_items(grids: dict) -> frozenset[int]:
    """The item pointers in a unit's grids (collection/capture.py `read_owner_grids`: a cell holds the item lying
    on it): what the character carries in its inventory, its cube and its stash tabs."""
    return frozenset(cell for grid in grids.values() for cell in grid['cells'] if cell)


def doors(read, table: int) -> tuple[Door, ...]:
    """The door objects among the streamed object units, with their mode (closed or opened)."""
    heads = struct.unpack('<128Q', read(table + OBJECT_UNIT * 1024, 1024))
    sizes = door_sizes()
    found = []
    for unit in walk_units(read, heads, OBJECT_UNIT)['units']:
        if unit['txt_id'] not in sizes or not unit['path_pointer']:
            continue
        try:
            path = read(unit['path_pointer'], OBJECT_PATH)
        except OSError, ValueError:
            continue
        x, y = struct.unpack_from('<I', path, 0x10)[0] & 0xFFFF, struct.unpack_from('<I', path, 0x14)[0] & 0xFFFF
        found.append(Door(unit['unit_id'], unit['txt_id'], unit['mode'], float(x), float(y)))
    return tuple(found)


def warps(read, table: int) -> tuple[Warp, ...]:
    """The doors among the streamed units. Seen on 2026-10-10 in the Forgotten Tower: the way out
    (Id 11) and the stairs down (Id 12), with the two doors of the levels just left still listed."""
    heads = struct.unpack('<128Q', read(table + TILE_UNIT * 1024, 1024))
    found = []
    for unit in walk_units(read, heads, TILE_UNIT)['units']:
        if not unit['path_pointer']:
            continue
        try:
            path = read(unit['path_pointer'], OBJECT_PATH)
        except OSError, ValueError:
            continue
        x, y = struct.unpack_from('<I', path, 0x10)[0] & 0xFFFF, struct.unpack_from('<I', path, 0x14)[0] & 0xFFFF
        found.append(Warp(unit['unit_id'], unit['txt_id'], float(x), float(y)))
    return tuple(found)


@functools.cache
def glowing_chests() -> dict[int, str]:
    """Object class id -> objects.txt Class of the glowing chests: drawn with an overlay over a chest's drops, the
    quest chests among them (data/glowing_chests.json, macros/superchests.py `build_glowing`)."""
    data = json.loads((Path(__file__).parents[1] / 'macros' / 'data' / 'glowing_chests.json').read_text())
    return {int(txt): name for txt, name in data['chests'].items()}


@functools.cache
def container_table() -> dict[int, tuple[str, frozenset[int]]]:
    """Object class id -> (objects.txt Class, the modes it can be clicked or struck in) of what is opened
    for what it holds: chests, caskets, urns, corpses and the like (data/containers.json,
    macros/build_containers.py), and the glowing chests, opened in mode 0 (`Selectable0` in each row): the quest
    chests build_containers.py leaves out drop a chest's items too (the player, 2026-10-20: "we always should try to
    open such chests whenever we encountered them"; macros/superchests.py)."""
    data = json.loads((Path(__file__).parents[1] / 'macros' / 'data' / 'containers.json').read_text())
    table = {int(txt): (row['class'], frozenset(row['modes'])) for txt, row in data['containers'].items()}
    return {**{txt: (name, frozenset((0,))) for txt, name in glowing_chests().items()}, **table}


def container_names() -> dict[int, str]:
    return {txt: name for txt, (name, _modes) in container_table().items()}


def usable(thing: Thing) -> bool:
    """Whether the game lets the container be used as it stands: its own "can be selected" flag
    (UNIT_FLAGS), and when that is unread objects.txt's word on its mode (`Selectable0..7`,
    `IsAttackable0`). A chest is until it is opened."""
    row = container_table().get(thing.txt_id)
    if row is None:
        return False
    return thing.mode in row[1] if thing.selectable is None else thing.selectable


def containers() -> frozenset[int]:
    return frozenset(container_names())


# Doors too: a closed one across an open passage's walk is clicked open (macros/hunting/moves.py `door_across`; the
# Outer Cloister's gate into the Barracks, 04:00:40 on 2026-10-20)
# The Duriel's Lair portal the true tomb's Orifice mark clicks (macros/teleport.py USES, 2026-10-21)
USED = (
    frozenset((PORTAL, TOWN_PORTAL, WIRTS_BODY, DURIEL_PORTAL, BANK, *CLICKED, *WAYPOINT_CLASSES))
    | containers()
    | frozenset(door_sizes())
)


def things(read, table: int, classes: frozenset[int] = USED) -> tuple[Thing, ...]:
    """The objects of `classes` among the streamed object units: by default those a mark may name."""
    heads = struct.unpack('<128Q', read(table + OBJECT_UNIT * 1024, 1024))
    found = []
    for unit in walk_units(read, heads, OBJECT_UNIT)['units']:
        if unit['txt_id'] not in classes or not unit['path_pointer']:
            continue
        try:
            path = read(unit['path_pointer'], OBJECT_PATH)
        except OSError, ValueError:
            continue
        x, y = struct.unpack_from('<I', path, 0x10)[0] & 0xFFFF, struct.unpack_from('<I', path, 0x14)[0] & 0xFFFF
        selectable = None
        with suppress(OSError, ValueError):
            selectable = bool(read(unit['address'] + UNIT_FLAGS, 1)[0] & SELECTABLE_FLAG)
        found.append(Thing(unit['unit_id'], unit['txt_id'], unit['mode'], float(x), float(y), selectable))
    return tuple(found)


def observe_things(pid, images, capture, classes: frozenset[int]) -> tuple[Thing, ...]:
    """The objects of `classes` near the player, opened read-only for this one read (the level guide's poll:
    a `use` mark's object operated by anyone, macros/card_goal.py)."""
    with game_read(pid, images, capture, changed='Game process changed during the object read') as (read, table):
        found = things(read, table, classes)
    return found


def gold_amount(read, unit: dict) -> int:
    """The gold in a pile on the ground; 0 when it cannot be read. Which of the unit's two stat lists
    holds it is not known yet (2026-10-11), so both are read and the first sight of a pile is logged."""
    if unit['unit_id'] in GOLD_SEEN:
        return GOLD_SEEN[unit['unit_id']]  # a pile's amount does not change, and the loot is read often
    for name, offset in (('full', FULL_STATS), ('base', BASE_STATS)):
        try:
            stats = read_stats(read, unit['stats_pointer'] + offset) if unit['stats_pointer'] else []
        except OSError, ValueError, struct.error:
            continue
        amount = next((s['raw'] for s in stats if s['id'] == GOLD_STAT and s['layer'] == 0), 0)
        if amount:
            if len(GOLD_SEEN) > 500:
                GOLD_SEEN.clear()
            GOLD_SEEN[unit['unit_id']] = amount
            if amount >= 1000:
                LOG.info('Macro: gold pile %d: %d gold (the %s stat list)', unit['unit_id'], amount, name)
            return amount
    return 0


BASE_ROLLS_SEEN: dict[int, Rolls] = {}  # unit id -> `base_rolls`, of the items read


def chain_defense(read, unit: dict) -> int | None:
    """An item's enhanced defense (16, layer 0) from its own +0xD0 modifier chain (`chain_sums`)."""
    found = chain_sums(read, unit, (DEFENSE_PERCENT,))
    return found[DEFENSE_PERCENT] if found is not None else None


def chain_sums(read, unit: dict, ids: Sequence[int]) -> dict[int, int] | None:
    """The sums of the stats `ids` (layer 0) in an item's own +0xD0 modifier chain, one walk; 0 for one the chain
    holds none of; None when the chain is not read whole (items/modifiers.py `owned_chain`: owner and links checked;
    a socket filler's list passed over). This build keeps a superior armor's local ED there and never in the +0xE8
    totals ([verified] 0 of 5,610 captured white, superior or magic units have 16 in the totals, 720 in the chain:
    rca/2026-10-20/loot-m0-research.md R2). The chain walk is the collection and Alt+D captures' (`owned_defense_
    modifiers`); [verified] 2026-10-20 by replaying the bytes of 600 collection captures (106,658 white, superior and
    magic item reads) through `base_rolls`: every ED equals the capture's own, e.g. a superior Tome's 8 and a superior
    Grimoire's 12. On the ground the same unit structure is [inferred]: no superior shield lay in a capture.
    Read only. A superior weapon's enhanced damage (17) is kept in the same chain (items/modifiers.py
    `owned_damage_modifiers`, the collection and Alt+D captures' read), [inferred] on the ground as the ED is."""
    diagnostics = capture_stat_candidates(read, unit['stats_pointer'])
    chain = owned_chain(diagnostics, unit, fillers=True)
    if chain is None:
        return None
    return {stat: sum(s['raw'] for s in chain if s['id'] == stat and s['layer'] == 0) for stat in ids}


def base_rolls(read, unit: dict) -> Rolls | None:
    """An item's `Rolls` from its full stat list, its +0xD0 modifier chain (the ED, `chain_defense`) and its data's
    flags; None unreadable. An item's rolls do not change: read once a unit, unless its chain was not read whole
    (`Rolls.defense` None: read again at the next look)."""
    if unit['unit_id'] in BASE_ROLLS_SEEN:
        return BASE_ROLLS_SEEN[unit['unit_id']]
    try:
        stats = read_stats(read, unit['stats_pointer'] + FULL_STATS) if unit['stats_pointer'] else None
        data = read(unit['data_pointer'], ITEM_DATA_SIZE) if unit['data_pointer'] else None
    except OSError, ValueError, struct.error:
        stats = data = None
    if stats is None or data is None:
        return None
    plain = {s['id']: s['raw'] for s in stats if s['layer'] == 0}
    # The totals' 16 and 17 first, should a build keep them there; else the chain's (2026-10-20: the superior Monarch
    # rule, "superior bases" the player asked for at 08:42, never fired on a ground ED read always 0). One chain walk
    defense, damage = plain.get(DEFENSE_PERCENT), plain.get(DAMAGE_PERCENT)
    resists = min(plain.get(stat, 0) for stat in RESISTS)
    chain = None
    if not defense or not damage or not resists:
        chain = chain_sums(read, unit, (DEFENSE_PERCENT, DAMAGE_PERCENT, *RESISTS))
        defense = defense or (chain[DEFENSE_PERCENT] if chain is not None else None)
        damage = damage or (chain[DAMAGE_PERCENT] if chain is not None else None)
    if not resists and chain is not None:
        # A Paladin shield's all-res automod off the totals: the chain's, should it be kept there as a superior's
        # ED is ([inferred]: the ground census read 9-32 all res on 12 normal Sacred Targe / Rondache lines and none
        # on 6 superior Rondache lines, 2026-10-17 to 10-20; a carried superior Ancient Shield holds its 13 in the
        # totals). Read for the Exile base (the player, 2026-10-20 ~12:15)
        resists = min(chain[stat] for stat in RESISTS)
    rolls = Rolls(
        plain.get(StatId.SOCKETS, 0),
        tuple((s['layer'], s['raw']) for s in stats if s['id'] == StatId.CLASS_SINGLE_SKILL),
        defense,
        resists,
        bool(struct.unpack_from('<I', data, FLAGS_OFFSET)[0] & ETHEREAL_FLAG),
        damage,
        # A white bow's +3 Bow and Crossbow Skills automod: in the totals ([verified] 2026-10-20: 96 of 96 captured
        # superior Amazon bows hold 188 there, e.g. a superior Grand Matron Bow 188:0 = 3 with 194 = 5)
        tuple((s['layer'], s['raw']) for s in stats if s['id'] == StatId.SKILL_TAB),
    )
    if defense is None or damage is None:
        return rolls
    if len(BASE_ROLLS_SEEN) > 500:
        BASE_ROLLS_SEEN.clear()
    BASE_ROLLS_SEEN[unit['unit_id']] = rolls
    return rolls


def rolled(read, drop: Drop, unit: dict | None) -> Drop:
    """`drop` with its `Rolls` when it is a base the loop judges off the ground (pickmode.py `void_base`,
    `shield_base`, `ground_base`): a white, superior or magic dagger, shield or Paladin shield, or a white or superior
    base of BASE_ROLLED_TYPES (every weapon and armor type since 2026-10-20 ~18:45); as it is otherwise."""
    base = item_base(drop.txt) if drop.txt else None
    if unit is None or drop.kind != VALUABLE or drop.quality not in ROLLED_QUALITIES or base is None:
        return drop
    if base['type'] not in ROLLED_TYPES:
        return drop
    if base['type'] not in MAGIC_ROLLED_TYPES and drop.quality not in WHITE_QUALITIES:
        return drop  # a magic one's ground read holds no socket count and no affix (R1): nothing to judge by
    return replace(drop, rolls=base_rolls(read, unit))


def item_values(stats: Sequence[Mapping]) -> dict[int, int]:
    """An item's read stats as {stat id: raw value}: layer 0, and LAYERED_SKILLS at the most of any layer."""
    values = {s['id']: s['raw'] for s in stats if s['layer'] == 0}
    for s in stats:
        if s['id'] in LAYERED_SKILLS:
            values[s['id']] = max(values.get(s['id'], 0), s['raw'])
    return values


def unit_stats(read, stats_at: int) -> dict[int, int]:
    """A unit's full stat list as {stat id: raw value} (layer 0 only); {} when unreadable."""
    try:
        return {s['id']: s['raw'] for s in read_stats(read, stats_at + FULL_STATS) if s['layer'] == 0}
    except OSError, ValueError, struct.error:
        return {}


def missiles(read, table: int) -> list[dict]:
    """Research (combat/plan.md stage 1): every missile unit of MISSILE_SLOTS as raw bytes: the
    unit record, its path record and the u16 pair at 0xC4 MapAssist calls X/Y, with the slot it
    hangs off. Nothing is interpreted yet."""
    found = []
    for slot in MISSILE_SLOTS:
        heads = struct.unpack('<128Q', read(table + slot * 1024, 1024))
        for unit in walk_units(read, heads, MISSILE_UNIT)['units']:
            try:
                record = read(unit['address'], MISSILE_RECORD)
                path = read(unit['path_pointer'], MISSILE_PATH) if unit['path_pointer'] else b''
            except OSError, ValueError:
                continue
            data = b''
            if unit['data_pointer']:
                with contextlib.suppress(OSError, ValueError):
                    data = read(unit['data_pointer'], MISSILE_DATA)
            found.append(
                {
                    'unit_id': unit['unit_id'],
                    'txt_id': unit['txt_id'],
                    'mode': unit['mode'],
                    'slot': slot,
                    'xy': list(struct.unpack_from('<HH', record, 0xC4)),
                    'path': path.hex(),
                    'record': record.hex(),
                    'data': data.hex(),
                }
            )
    return found


def flights(read, table: int, kinds: frozenset[int]) -> tuple[tuple[int, int, float, float], ...]:
    """The missiles in flight of the classes `kinds`, light: (owner unit id, class, x, y) from the unit record's
    owner (MISSILE_OWNER) and the head of its path record; the others are passed over after the unit header.
    What a read threat model prices (combat/threats; macros/safety.py `in_flight`)."""
    found = []
    for slot in MISSILE_SLOTS:
        heads = struct.unpack('<128Q', read(table + slot * 1024, 1024))
        for unit in walk_units(read, heads, MISSILE_UNIT, records=True)['units']:
            if unit['txt_id'] not in kinds or not unit['path_pointer']:
                continue
            record = unit.get('record', b'')
            if len(record) < MISSILE_OWNER + 8:
                continue
            _kind, owner = struct.unpack_from('<II', record, MISSILE_OWNER)
            try:
                x, y = position(read(unit['path_pointer'], 8))
            except OSError, ValueError, struct.error:
                continue
            found.append((owner, unit['txt_id'], x, y))
    return tuple(found)


def unit_census(read, table: int) -> list[dict]:
    """Research: per slot of the unit hash table, how many heads are set and what the first unit
    says of itself (type, txt id, unit id, mode), the walk's unit count and its first error."""
    census = []
    for slot in range(UNIT_SLOTS):
        try:
            heads = struct.unpack('<128Q', read(table + slot * 1024, 1024))
        except OSError, ValueError:
            census.append({'slot': slot, 'unreadable': True})
            continue
        first = next((head for head in heads if head), 0)
        entry: dict = {'slot': slot, 'heads': sum(1 for head in heads if head)}
        if first:
            try:
                entry['first'] = list(struct.unpack('<IIII', read(first, 16)))
            except OSError, ValueError:
                entry['first'] = None
            walked = walk_units(read, heads, entry['first'][0] if entry.get('first') else slot % 6)
            entry['units'] = len(walked['units'])
            if walked['errors']:
                entry['error'] = walked['errors'][0]['error']
        census.append(entry)
    return census


def mouse_skills(read, unit_address: int) -> tuple[int | None, int | None]:
    """(left, right) skill ids on the mouse buttons of the unit; None for a side that cannot be read."""
    try:
        skills = pointer(read, unit_address + SKILL_LIST)
    except OSError, ValueError, struct.error:
        return None, None
    if not skills:
        return None, None
    found = []
    for offset in (LEFT_SKILL, RIGHT_SKILL):
        try:
            record = pointer(read, skills + offset)
            found.append(struct.unpack('<H', read(pointer(read, record), 2))[0] if record else None)
        except OSError, ValueError, struct.error:
            found.append(None)
    return found[0], found[1]


def local_player(read, table: int) -> Player | None:
    """The character played, among the player units; None in menus or when it cannot be told."""
    heads = struct.unpack('<128Q', read(table, 1024))
    return player_among(read, walk_units(read, heads, 0, records=True)['units'])


def player_among(read, units: Sequence[dict]) -> Player | None:
    """`local_player` of the walked player units (their records read: `walk_units` records=True)."""
    found = []
    for unit in units:
        if not unit['path_pointer']:
            continue
        try:
            path = read(unit['path_pointer'], 0x28)
            room1 = struct.unpack_from('<Q', path, PATH_ROOM1)[0]
            level = pointer(read, pointer(read, room1 + ROOM1_ROOM2) + ROOM2_LEVEL)
            area = struct.unpack('<I', read(level + LEVEL_AREA_ID, 4))[0]
            name = decode_name(read(unit['data_pointer'], 16))
        except OSError, ValueError, struct.error:
            continue
        consume, node = None, b''
        try:
            buff = read_consume(read, unit['stats_pointer'])
            consume = buff.active
            if buff.effect_id:
                node = read(buff.effect_id, 0x80)
        except OSError, ValueError, struct.error:
            pass
        left, right = mouse_skills(read, unit['address'])
        purge = ward = cooldown = orders = None
        with suppress(OSError, ValueError, struct.error):
            low, *_, delays, states = struct.unpack('<6I', read(unit['stats_pointer'] + LOW_STATES, 24))
            purge, ward = bool(states & HEX_PURGE_BIT), bool(states & PSYCHIC_WARD_BIT)
            cooldown = bool(delays & COOLDOWN_BIT)
            orders = bool(low & BATTLE_ORDERS_BIT)
        player = Player(
            unit['unit_id'],
            name,
            unit['mode'],
            area,
            *position(path),
            consume,
            node,
            left,
            right,
            unit['stats_pointer'],
            purge,
            ward,
            unit.get('record', b''),
            skill_in_use(read, unit.get('record', b'')),
            cooldown,
            orders,
        )
        found.append((player, unit['stats_pointer']))
    # Several player units may stand for the one character: the shared stash tabs carry its name
    # and no life (collection/research.md). With other players in the game (user, 2026-10-08)
    # the character is the one unit with a plausible life; another player's unit has none.
    # A corpse left on the level also carries the name, dead and without life, and may have the
    # lowest unit id (2026-10-11): with a dead unit among them the ones with a life go first.
    if len({player.name for player, _ in found}) == 1:
        if any(player.mode in PLAYER_DEAD_MODES for player, _ in found):
            found = [(player, stats) for player, stats in found if plausible_life(read, stats)] or found
        return min((player for player, _ in found), key=lambda p: p.unit_id)
    alive = [player for player, stats in found if plausible_life(read, stats)]
    return alive[0] if len(alive) == 1 else None
