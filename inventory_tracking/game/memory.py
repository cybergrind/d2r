"""The game's memory as the macros read it in one pass: `GameMemory` (moved from macros/world.py).

Image addresses found with the record probe on 2026-10-06 (plan.md, findings): the skill slot
table, the game name and the in-game byte. The unit table is the one the service attached to;
it stays at the same address through the lobby and into the next game.
"""

import struct
import time
from contextlib import suppress
from dataclasses import replace

from inventory_tracking.collection.capture import STASH_ORDER_OFFSET, is_shared_candidate, read_owner_grids
from inventory_tracking.common import LOG
from inventory_tracking.game.decode import (
    CENSUS_KEPT,
    CENSUS_SKIPPED,
    USED,
    carried_items,
    carried_rows,
    census,
    containers,
    corpses,
    decode_name,
    decode_slots,
    doors,
    flights,
    gold_amount,
    item_size,
    item_values,
    missiles,
    monsters,
    monsters_and_dead,
    player_among,
    rolled,
    rolls,
    stash_view_of,
    stock_of,
    things,
    unit_census,
    unit_stats,
    warps,
)
from inventory_tracking.game.layout import (
    DATA_RVA,
    DATA_SIZE,
    EQUIPPED_MODE,
    FULL_REJUVENATION,
    FULL_STATS,
    GAME_NAME_RVA,
    GAME_NAME_SIZE,
    GOLD_CLASS,
    GOLD_PER_LEVEL,
    GOLD_STAT,
    HANDS,
    HOVER_RVA,
    IN_GAME,
    ITEM_BODY_LOCATION,
    ITEM_OWNER,
    ITEM_PAGE,
    ITEM_UNIT,
    LEVEL_STAT,
    MONSTER_UNIT,
    NO_OWNER,
    OBJECT_PATH,
    OBJECT_UNIT,
    OPEN_PANELS,
    SHOP_GRIDS,
    SHOW_ITEMS,
    SKILL_SLOT_SIZE,
    SKILL_SLOTS,
    SKILL_SLOTS_RVA,
    STASH_ITEM_PAGE,
    STATE_RUN,
    SUPER_HEALING,
    SWAP_SET,
    TELEPORT_STATS,
    TICK_HEAD,
    TRACE_RVAS,
    VIEW_RVA,
)
from inventory_tracking.game.records import (
    GOLD,
    HEALING,
    REJUVENATION,
    VALUABLE,
    Drop,
    Loot,
    Monster,
    Pack,
    Player,
    StashView,
    Stocked,
    Teleport,
    Thing,
    Warp,
    Wear,
    World,
    given_skills,
    gives_orders,
    least_worn,
    prized,
    shown_source,
)
from inventory_tracking.game.units import walked
from inventory_tracking.items.identity import (
    FLAGS_OFFSET,
    IDENTIFIED_FLAG,
    IDENTITY_OFFSET,
    ITEM_DATA_SIZE,
    QUALITY_OFFSET,
)
from inventory_tracking.items.metadata import item_base
from inventory_tracking.levels.doors import Door
from inventory_tracking.loot.ground import (
    GroundItem,
    GroundMaterial,
    materials_among,
    on_ground,
    runes_among,
    shown_among,
    sightings_among,
    uniques_among,
)
from inventory_tracking.loot.materials import appraised_classes
from inventory_tracking.loot.runes import is_valuable_rune, rune_name
from inventory_tracking.loot.shown import ShownRule
from inventory_tracking.native.layout import (
    BELT_ITEM_MODE,
    BELT_SIZE,
    CHARGED_SKILL_STAT,
    LIFE_STAT,
    MAX_LIFE_STAT,
    STAFF_CLASS_IDS,
    TELEPORT_SKILL,
    TERROR_SERVICE_RVA,
    UI_PANELS_RVA,
    UI_PANELS_SIZE,
    WEAPON_SLOTS,
)
from inventory_tracking.native.memory import ProcessMemory
from inventory_tracking.native.stack_items import read_stack_count
from inventory_tracking.native.units import read_stats, walk_units


# What `GameMemory.hands` calls a Call to Arms, the weapon that gives Battle Orders: no base code (d2data weapons, armor
# and misc hold no `cta`). CybergrindAA's is a Flail like his Heart of the Oak (`fla`), Spirit in both sets (22:58 on
# 2026-10-17): by base codes alone the two sets read the same
CTA_CODE = 'cta'
CTA_SECONDS = 10.0  # between two reads of whether a Call to Arms is worn (`GameMemory.cta`)
UNPLACED_GOLD: set[int] = set()  # gold piles `loot` said it left out for an unread place: said once a pile
CAPPED_GOLD: set[int] = set()  # gold piles `loot` said it left out for the gold cap: said once a pile


def gold_room(stats: dict[int, int]) -> int | None:
    """The gold the character can still take (its level x GOLD_PER_LEVEL less the gold carried); None unread."""
    level = stats.get(LEVEL_STAT)
    return max(0, level * GOLD_PER_LEVEL - stats.get(GOLD_STAT, 0)) if level else None


def belt_cells(read, items: list[dict], owner: int) -> tuple[tuple[int | None, ...], bool]:
    """The item class in each belt cell of `owner`'s (None: empty), and whether every belt item was read. One that
    is not is left out and the belt is unknown for the look (the player, 2026-10-19: "skip the bad potion, keep
    the ground drops, and mark the belt as 'unread'"): it used to empty the whole look."""
    cells: list[int | None] = [None] * BELT_SIZE
    whole = True
    for unit in items:
        if unit['mode'] != BELT_ITEM_MODE or not unit['data_pointer'] or not unit['path_pointer']:
            continue
        try:
            if struct.unpack_from('<I', read(unit['data_pointer'], 0x60), ITEM_OWNER)[0] != owner:
                continue
            cell = struct.unpack_from('<H', read(unit['path_pointer'], 0x18), 0x10)[0]
        except OSError, ValueError, struct.error:
            if whole:
                LOG.info('Macro: belt: item %d unread: the belt is unread this look', unit['unit_id'])
            whole = False
            continue
        if cell < BELT_SIZE:
            cells[cell] = unit['txt_id']
    return tuple(cells), whole


def _unit_of(walk: dict, player: Player) -> dict | None:
    """The character's unit among the walked player units; None when the walk did not find it."""
    return next((unit for unit in walk['units'] if unit['unit_id'] == player.unit_id), None)


class GameMemory:
    """Keeps /proc/<pid>/mem open for one macro run."""

    def __init__(self, pid: int, base: int, table: int) -> None:
        self.base, self.table = base, table
        self.memory = ProcessMemory(pid)
        self.hover_raw: tuple[int, int, int, int] | None = None  # the last record read whole (`hovered`)
        self.stock_note: dict | None = None  # what the last vendor's stock read found (`stock`), logged when it changes
        self.where: tuple[float, float] | None = None  # where the character was at the last `place` or `loot`
        self.mode: int | None = None  # the character's mode at the last `place` (runner.py `_dead`)
        self.life: tuple[int, int] | None = None  # (life, max life) at the last `place` (runner.py `poll`)
        self.where_area: int | None = None  # and in which level (`loot`)
        # (character, item) unit ids the ground census said (`census`): the runner gives the one set its GameMemory
        # objects share, so an item is said once whatever reads it (a set of each said it 2-4 times, 2026-10-17)
        self.ground_seen: set[tuple[int, int]] = set()
        # The worn items (unit id, body location) `worn_skills` last read, and the skills they give (`given_skills`)
        self.worn_held: frozenset[tuple[int, int]] | None = None
        self.worn_skills_of: frozenset[int] = frozenset()
        self.orders_of: dict[int, bool] = {}  # item unit id -> whether it gives Battle Orders (`_orders`)
        self.cta_seen: tuple[float, bool] | None = None  # (monotonic time, a Call to Arms worn) at `cta`

    def close(self) -> None:
        self.memory.close()

    def read(self, address: int, size: int) -> bytes:
        return self.memory.read(address, size)

    def _player(self) -> Player | None:
        return self._players()[0]

    def _players(self) -> tuple[Player | None, dict]:
        """(the character, `local_player`; the walk of the player units it was told among, records read)."""
        walk = walked(self.read, self.table, 0, records=True)
        return player_among(self.read, walk['units']), walk

    def _monsters(self) -> tuple[tuple[Monster, ...], frozenset[int]]:
        return monsters_and_dead(self.read, self.table)

    def _doors(self) -> tuple[Door, ...]:
        return doors(self.read, self.table)

    def all_monsters(self, *, paths: bool = False, records: bool = False) -> tuple[Monster, ...]:
        """Live and dead monsters with a position (the recorder tells a death from an unload)."""
        return monsters(self.read, self.table, dead=True, paths=paths, records=records)

    def missiles(self) -> list[dict]:
        return missiles(self.read, self.table)

    def flights(self, kinds: frozenset[int]) -> tuple[tuple[int, int, float, float], ...]:
        return flights(self.read, self.table, kinds)

    def corpses(self) -> tuple[tuple[int, float, float], ...]:
        try:
            return corpses(self.read, self.table)
        except OSError, ValueError, struct.error:
            return ()

    def warps(self) -> tuple[Warp, ...]:
        try:
            return warps(self.read, self.table)
        except OSError, ValueError, struct.error:
            return ()

    def things(self) -> tuple[Thing, ...]:
        try:
            return things(self.read, self.table)
        except OSError, ValueError, struct.error:
            return ()

    def operated(self) -> tuple[Thing, ...]:
        """Everything a mark may name for a click and every container, opened or not: what the combat
        recorder writes as the level's objects (a seal's mode says when it was opened)."""
        try:
            return things(self.read, self.table, USED | containers())
        except OSError, ValueError, struct.error:
            return ()

    def tick(self) -> bytes | None:
        """The head of the client's clock object, raw: by the client's code the time of the last whole
        tick in ms is the u32 at +0x0C (40 a tick) and the part of the tick under way the float at +0x18
        (rca/2026-10-13/re-findings.md; not yet seen to hold in a game). None when unread."""
        try:
            clock = struct.unpack('<Q', self.read(self.base + TERROR_SERVICE_RVA, 8))[0]
            return self.read(clock, TICK_HEAD) if clock else None
        except OSError, ValueError, struct.error:
            return None

    def states(self, stats_at: int) -> bytes | None:
        """The unit's state words raw (STATE_RUN); None when unread."""
        try:
            return self.read(stats_at + STATE_RUN[0], STATE_RUN[1]) if stats_at else None
        except OSError, ValueError, struct.error:
            return None

    def belt(self) -> tuple[int | None, ...] | None:
        """The item class in each belt cell of the character's (None: empty); None when unread."""
        try:
            player = self._player()
            if player is None:
                return None
            heads = struct.unpack('<128Q', self.read(self.table + ITEM_UNIT * 1024, 1024))
            cells, whole = belt_cells(self.read, walk_units(self.read, heads, ITEM_UNIT)['units'], player.unit_id)
            return cells if whole else None
        except OSError, ValueError, struct.error:
            return None

    def stock(self, vendor: int) -> tuple[Stocked, ...]:
        """What the vendor of monstats class `vendor` sells (`stock_of`); () unread or not loaded: the game has the
        stock in memory once its trade window has been opened."""
        try:
            heads = struct.unpack('<128Q', self.read(self.table + MONSTER_UNIT * 1024, 1024))
            unit = next((u for u in walk_units(self.read, heads, MONSTER_UNIT)['units'] if u['txt_id'] == vendor), None)
            if unit is None:
                return ()
            grids = read_owner_grids(self.read, unit)
            item_heads = struct.unpack('<128Q', self.read(self.table + ITEM_UNIT * 1024, 1024))
            by_address = {u['address']: u for u in walk_units(self.read, item_heads, ITEM_UNIT)['units']}
        except OSError, ValueError, struct.error:
            return ()
        # What the read found, for the log when it changes (the shop's stock read 14 items, none on its Misc tab, at
        # 00:37 on 2026-10-17 where the shop's own capture reads 69): each grid's taken cells, how many resolved
        note = {
            'grids': {
                index: (
                    len({c for c in grids[index]['cells'] if c}),
                    len({c for c in grids[index]['cells'] if c in by_address}),
                )
                for index in SHOP_GRIDS
                if index in grids
            },
            'items walked': len(by_address),
        }
        if note != self.stock_note:
            self.stock_note = note
            LOG.info('Macro: stock of %d: grid index -> (items, resolved): %s', vendor, note)
        return stock_of(grids, by_address)

    def carried(self) -> Pack | None:
        """The carried inventory's items and the cube's rows (`carried_items`); None when unread."""
        try:
            player, players = self._players()
            if player is None:
                return None
            items = walked(self.read, self.table, ITEM_UNIT)['units']
            return carried_items(self.read, _unit_of(players, player), items)
        except OSError, ValueError, struct.error:
            return None

    def stash_view(self) -> StashView | None:
        """The stash's pages and resource stacks (`stash_view_of`), read whatever panel is open; None when the read is
        not whole or the pages cannot be told (macros/town-plan.md step 0)."""
        read = self.read
        try:
            player, player_walk = self._players()
            if player is None:
                return None
            item_walk = walked(read, self.table, ITEM_UNIT)
            if not player_walk['complete'] or not item_walk['complete']:
                return None
            main, players = None, []
            for unit in player_walk['units']:
                if not unit['data_pointer']:
                    continue
                stats = read_stats(read, unit['stats_pointer'] + FULL_STATS) if unit['stats_pointer'] else []
                order = struct.unpack('<Q', read(unit['address'] + STASH_ORDER_OFFSET, 8))[0]
                name = decode_name(read(unit['data_pointer'], 16))
                entry = unit | {'details': {'name': name, 'full_stats': stats}, 'order': order}
                if unit['unit_id'] == player.unit_id:
                    main = entry
                else:
                    players.append(entry)
            if main is None:
                return None
            owners = [main, *(unit for unit in players if is_shared_candidate(unit, main))]
            grids_by_owner = {unit['unit_id']: read_owner_grids(read, unit) for unit in owners}
            items = []
            for unit in item_walk['units']:
                entry = {key: unit[key] for key in ('unit_id', 'address', 'txt_id', 'mode')}
                entry |= {'owner': None, 'page': None}
                if unit['mode'] == 0 and unit['data_pointer']:
                    data = read(unit['data_pointer'], ITEM_DATA_SIZE)
                    entry |= {'owner': struct.unpack_from('<I', data, ITEM_OWNER)[0], 'page': data[ITEM_PAGE]}
                    entry |= {
                        'quality': struct.unpack_from('<I', data, QUALITY_OFFSET)[0],
                        'identified': bool(struct.unpack_from('<I', data, FLAGS_OFFSET)[0] & IDENTIFIED_FLAG),
                        'unique': struct.unpack_from('<I', data, IDENTITY_OFFSET)[0],
                    }
                    if entry['owner'] == NO_OWNER and entry['page'] == STASH_ITEM_PAGE:
                        entry['count'] = read_stack_count(read, unit)
                items.append(entry)
        except OSError, ValueError, struct.error:
            return None
        return stash_view_of(main, players, grids_by_owner, items)

    def item_stats(self, unit_id: int) -> dict[int, int]:
        """An item unit's full stat list (+0xE8, the item's totals: items/decode.py) as {stat id: raw value}, layer 0,
        wherever it lies (the inventory, the cube, a stash page); {} when it is not found or unreadable: a Gheed's
        Fortune's Magic Find (macros/charms.py)."""
        try:
            heads = struct.unpack('<128Q', self.read(self.table + ITEM_UNIT * 1024, 1024))
            unit = next((u for u in walk_units(self.read, heads, ITEM_UNIT)['units'] if u['unit_id'] == unit_id), None)
        except OSError, ValueError, struct.error:
            return {}
        if unit is None or not unit['stats_pointer']:
            return {}
        try:
            return item_values(read_stats(self.read, unit['stats_pointer'] + FULL_STATS))
        except OSError, ValueError, struct.error:
            return {}

    def containers(self) -> tuple[Thing, ...]:
        """The chests and the like the game shows now, opened or not (the pickup step opens them)."""
        try:
            return things(self.read, self.table, containers())
        except OSError, ValueError, struct.error:
            return ()

    def objects(self) -> list[dict]:
        """Research: every object unit the game shows, with its unit record and the head of its object
        data raw (which bytes say that it can be used is not known yet, 2026-10-12)."""
        found = []
        with suppress(OSError, ValueError, struct.error):
            heads = struct.unpack('<128Q', self.read(self.table + OBJECT_UNIT * 1024, 1024))
            for unit in walk_units(self.read, heads, OBJECT_UNIT)['units']:
                row = {key: unit[key] for key in ('unit_id', 'txt_id', 'mode')}
                with suppress(OSError, ValueError, struct.error):
                    path = self.read(unit['path_pointer'], OBJECT_PATH)
                    row['x'] = struct.unpack_from('<I', path, 0x10)[0] & 0xFFFF
                    row['y'] = struct.unpack_from('<I', path, 0x14)[0] & 0xFFFF
                    row['unit'] = self.read(unit['address'], 0x160).hex()
                    row['data'] = self.read(unit['data_pointer'], 0x40).hex()
                found.append(row)
        return found

    def census(self) -> list[dict]:
        return unit_census(self.read, self.table)

    def stats(self, stats_at: int) -> dict[int, int]:
        return unit_stats(self.read, stats_at)

    def loot(
        self,
        *,
        rune_minimum: str,
        unique_minimum: float | None,
        materials: dict[int, str],
        gold_minimum: int | None = None,
        shown: tuple[ShownRule, ...] = (),
        prized_rune_minimum: str | None = None,
        prized_materials: frozenset[int] | None = None,
    ) -> Loot:
        """The drops the loot marks would show (loot/ground.py, the same rules), the potions on the
        ground, the character's belt and life. An empty Loot when the character cannot be read.

        One walk of the player units and one of the item units for the whole look: the ground's classifiers,
        the census, the gold, the potions, the belt and the grids all take their rows (game/units.py)."""
        try:
            player, players = self._players()
            if player is None:
                return Loot()
            self.where, self.where_area = (
                (player.x, player.y),
                player.area,
            )  # the loop's sightings (macros/sightings.py)
            read = self.read
            items = walked(read, self.table, ITEM_UNIT)['units']
            ground = on_ground(read, items)
            # Without the marks' own settings every rune and material counts as one of theirs (`prized`).
            drops = [
                Drop(
                    rune.unit_id, rune.x, rune.y, rune_name(rune.class_id), VALUABLE,
                    prized=prized(
                        'rune',
                        marked=prized_rune_minimum is None
                        or is_valuable_rune(rune.class_id, minimum=prized_rune_minimum),
                    ),
                    source='rune',
                )
                for rune in runes_among(ground, minimum=rune_minimum)
            ]  # fmt: skip
            marked = [*materials_among(ground, materials, appraised_classes())] if materials else []
            sources = dict.fromkeys((item.unit_id for item in marked), 'material')
            if shown:
                found = shown_among(ground, shown)
                marked += found
                sources.update({item.unit_id: shown_source(item.quality) for item in found})
            if unique_minimum is not None:
                found = uniques_among(ground, minimum=unique_minimum)
                marked += found
                sources.update(dict.fromkeys((item.unit_id for item in found), 'unique'))
            # One drop per unit: a unique ring is both a ring and a marked unique (the unique's label wins,
            # as it does over the label of a base the filter shows).
            labelled = {item.unit_id: item for item in marked}
            drops += [
                Drop(
                    item.unit_id, item.x, item.y, item.label, VALUABLE, source=sources.get(item.unit_id, ''),
                    quality=item.quality if isinstance(item, GroundMaterial) else 0,
                )
                for item in labelled.values()
            ]  # fmt: skip
            classes = {unit['unit_id']: unit['txt_id'] for unit in items}
            drops = [
                replace(
                    drop,
                    size=item_size(classes.get(drop.unit_id)),
                    txt=classes.get(drop.unit_id, 0),
                    prized=drop.prized
                    if drop.unit_id not in sources
                    else prized(
                        sources[drop.unit_id],
                        marked=prized_materials is None or classes.get(drop.unit_id) in prized_materials,
                    ),
                )
                for drop in drops
            ]
            units = {unit['unit_id']: unit for unit in items}
            drops = [rolled(read, drop, units.get(drop.unit_id)) for drop in drops]
            self._census(ground, drops, player.unit_id)
            stats = unit_stats(read, player.stats_at) if player.stats_at else {}
            room_for = gold_room(stats)
            for item in ground:
                if gold_minimum is None or item.txt != GOLD_CLASS or not item.unit['path_pointer']:
                    continue
                amount = gold_amount(read, item.unit)
                if amount < gold_minimum:
                    continue
                if room_for is not None and amount > room_for:
                    # At the cap the game puts a click's pile back down under a new unit id: 45 s of clicks on one
                    # 7679 gold pile at 920k+ of 940k ended game 5 at 09:22:12 on 2026-10-20
                    if item.unit_id not in CAPPED_GOLD:
                        if len(CAPPED_GOLD) > CENSUS_KEPT:
                            CAPPED_GOLD.clear()
                        CAPPED_GOLD.add(item.unit_id)
                        LOG.info(
                            'Macro: gold pile %d: %d gold over the cap (room for %d): left',
                            item.unit_id,
                            amount,
                            room_for,
                        )
                    continue
                if item.at is None:
                    # Left out alone: it used to empty the whole look, every other drop unseen (2026-10-19)
                    if item.unit_id not in UNPLACED_GOLD:
                        if len(UNPLACED_GOLD) > CENSUS_KEPT:
                            UNPLACED_GOLD.clear()
                        UNPLACED_GOLD.add(item.unit_id)
                        LOG.info('Macro: gold pile %d: its place is unread: left out of this look', item.unit_id)
                    continue
                drops.append(Drop(item.unit_id, *item.at, f'{amount} gold', GOLD, (0, 0)))
            for potion in sightings_among(ground, {SUPER_HEALING, FULL_REJUVENATION}):
                kind = REJUVENATION if potion.class_id == FULL_REJUVENATION else HEALING
                drops.append(
                    Drop(
                        potion.unit_id,
                        potion.x,
                        potion.y,
                        f'a {"full rejuvenation" if kind == REJUVENATION else "super healing"} potion',
                        kind,
                    )
                )
            belt, belt_read = belt_cells(read, items, player.unit_id)
            room, cube, held = carried_rows(read, _unit_of(players, player))
            carried = frozenset(unit['unit_id'] for unit in items if unit['address'] in held)
            return Loot(
                tuple(drops),
                belt,
                stats.get(LIFE_STAT, 0) >> 8,
                stats.get(MAX_LIFE_STAT, 0) >> 8,
                room,
                tuple(sorted(stats.items())),
                (decode_name(read(self.base + GAME_NAME_RVA, GAME_NAME_SIZE)), player.unit_id),
                cube=cube,
                shown=frozenset(unit for unit, source in sources.items() if source == 'shown'),
                carried=carried,
                classes=tuple((drop.unit_id, classes[drop.unit_id]) for drop in drops if drop.unit_id in classes),
                belt_read=belt_read,
            )
        except OSError, ValueError, struct.error:
            return Loot()

    def _census(self, ground: list[GroundItem], drops: list[Drop], character: int) -> None:
        """Say each item on the ground once (`census`): what it is and which pickup rule takes it, if any. The
        player, 2026-10-17: "maybe we need to log drops in case if we're missing something right now, we would be
        able to pickup something valuable"."""
        if len(self.ground_seen) > CENSUS_KEPT:
            self.ground_seen.clear()
        taken = {drop.unit_id: drop.source or drop.kind for drop in drops}
        labels = {drop.unit_id: drop.label for drop in drops}
        dropped = {drop.unit_id: drop for drop in drops}
        for item in ground:
            key = (character, item.unit_id)
            if key in self.ground_seen or not item.unit['data_pointer']:
                continue
            self.ground_seen.add(key)
            base = item_base(item.txt)
            if base is None or base.get('type') in CENSUS_SKIPPED or item.data is None or item.at is None:
                continue
            quality, flags, _ = item.data
            unit_id, rolled = item.unit_id, rolls(dropped.get(item.unit_id))
            line = census(base['name'], quality, flags, item.at, taken.get(unit_id), labels.get(unit_id), rolled)
            LOG.info('Macro: ground: %s', line)

    def _equipped(self):
        """(unit, item data) of what the character wears; ValueError/OSError when unreadable."""
        player = self._player()
        if player is None:
            return
        heads = struct.unpack('<128Q', self.read(self.table + ITEM_UNIT * 1024, 1024))
        for unit in walk_units(self.read, heads, ITEM_UNIT)['units']:
            if unit['mode'] != EQUIPPED_MODE or not unit['data_pointer']:
                continue
            data = self.read(unit['data_pointer'], 0x60)
            if struct.unpack_from('<I', data, ITEM_OWNER)[0] == player.unit_id:
                yield unit, data

    def hands(self) -> tuple[str, ...]:
        """Base codes of what the character holds in the weapon set in hand, a Call to Arms as CTA_CODE; () when
        unreadable."""
        try:
            held = []
            for unit, data in self._equipped():
                base = item_base(unit['txt_id']) if data[ITEM_BODY_LOCATION] in HANDS else None
                if base is not None:
                    held.append(CTA_CODE if self._orders(unit) else base['code'])
            return tuple(sorted(held))
        except OSError, ValueError, struct.error:
            return ()

    def cta(self) -> bool | None:
        """Whether a Call to Arms (`gives_orders`) is worn in either weapon set, read again every CTA_SECONDS; None when
        unreadable. Its skills are on keys only while it is in hand (the player, 23:40 on 2026-10-17: "swap weapon and
        there are 7 and 8 bound to skills"), so the keys tell nothing of it from the other set."""
        now = time.monotonic()
        if self.cta_seen is not None and now - self.cta_seen[0] < CTA_SECONDS:
            return self.cta_seen[1]
        try:
            found = any(
                data[ITEM_BODY_LOCATION] in WEAPON_SLOTS and self._orders(unit) for unit, data in self._equipped()
            )
        except OSError, ValueError, struct.error:
            return None
        self.cta_seen = (now, found)
        return found

    def _orders(self, unit) -> bool:
        """Whether a worn item gives Battle Orders (`gives_orders`), read once for each item."""
        found = self.orders_of.get(unit['unit_id'])
        if found is None:
            stats = read_stats(self.read, unit['stats_pointer'] + TELEPORT_STATS) if TELEPORT_STATS is not None else ()
            found = self.orders_of[unit['unit_id']] = gives_orders(stats)
        return found

    def teleport(self) -> Teleport | None:
        """The worn staff with Teleport charges, in either weapon set; None without one, when unreadable, and when
        Teleport is a skill of the character's own (`own_teleport`): a staff in the other set is not swapped in for it
        then, nor are its charges spent (the player wears Enigma and Naj's Puzzler on the swap, 22:26 on 2026-10-17)."""
        if TELEPORT_STATS is None:
            return None
        try:
            worn = list(self._equipped())
            if TELEPORT_SKILL in self._worn_skills(worn):
                return None
            for unit, data in worn:
                if unit['txt_id'] not in STAFF_CLASS_IDS or data[ITEM_BODY_LOCATION] not in WEAPON_SLOTS:
                    continue
                for stat in read_stats(self.read, unit['stats_pointer'] + TELEPORT_STATS):
                    if stat['id'] == CHARGED_SKILL_STAT and stat['layer'] >> 6 == TELEPORT_SKILL:
                        raw = stat['raw'] & 0xFFFF
                        return Teleport(raw & 0xFF, raw >> 8, data[ITEM_BODY_LOCATION] in HANDS)
        except OSError, ValueError, struct.error:
            return None
        return None

    def own_teleport(self) -> bool | None:
        """Whether Teleport is a skill of the character's own: a worn item outside the other weapon set gives it
        (Enigma's "+1 to Teleport"), not charges; None when unreadable."""
        if TELEPORT_STATS is None:
            return None
        try:
            return TELEPORT_SKILL in self._worn_skills(list(self._equipped()))
        except OSError, ValueError, struct.error:
            return None

    def worn_skills(self) -> frozenset[int] | None:
        """The skills of the character's own the worn items outside the other weapon set give (`given_skills`): Teleport
        (54) from Enigma, Town Portal (411) from the Sling (macros/portal.py `portal_source`). An unreadable look gives
        the last read: a lost read must not take the Sling off and send the loop to buy scrolls it has no tome for.
        None when never read."""
        if TELEPORT_STATS is None:
            return None
        try:
            return self._worn_skills(list(self._equipped()))
        except OSError, ValueError, struct.error:
            return self.worn_skills_of if self.worn_held is not None else None

    def wear(self) -> Wear | None:
        """The worn item with the least of its durability left (`least_worn`); None with none, or when unreadable."""
        if TELEPORT_STATS is None:
            return None
        try:
            return least_worn(
                (
                    unit['txt_id'],
                    struct.unpack_from('<I', data, FLAGS_OFFSET)[0],
                    read_stats(self.read, unit['stats_pointer'] + TELEPORT_STATS),
                )
                for unit, data in self._equipped()
            )
        except OSError, ValueError, struct.error:
            return None

    def _worn_skills(self, worn) -> frozenset[int]:
        """`worn_skills` of the items worn, read once for each set of them: their stats change only with them."""
        held = frozenset((unit['unit_id'], data[ITEM_BODY_LOCATION]) for unit, data in worn)
        if held != self.worn_held:
            stats = [
                read_stats(self.read, unit['stats_pointer'] + TELEPORT_STATS)
                for unit, data in worn
                if data[ITEM_BODY_LOCATION] not in SWAP_SET
            ]
            self.worn_held, self.worn_skills_of = held, given_skills(stats)
        return self.worn_skills_of

    def hovered(self) -> tuple[int, int] | None:
        """(unit type, unit id) the game holds for the unit under the pointer (HOVER_RVA); None when
        unreadable, and when the record is known to be a leftover.

        The record keeps the last unit after the pointer has left it: of the pickup clicks made with
        the item "under the pointer" up to 2026-10-11, 87 of 130 took it at the aim 14 pixels above
        its ground and none of 21 at 6 (the pointer crosses the label on its way and stops on the
        ground below; the click then walks the character there). The record is 16 bytes in a table
        (hover/legacy.py: active, type, id; the three memory images in pricing/raw/re hold 0 in the
        first word with a unit in the next two). Confirmed in game, the Tower, 17:21 on 2026-10-11:
        the word read 0x101 at each of the 5 aims whose click took the item and 0 at the 7 aims that
        still named an item picked up before. The whole record is kept for the log (`hover_note`)."""
        try:
            flag, unit_type, unit_id, tail = struct.unpack('<IIII', self.read(self.base + HOVER_RVA - 4, 16))
        except OSError, ValueError, struct.error:
            return None
        self.hover_raw = (flag, unit_type, unit_id, tail)
        return (unit_type, unit_id) if flag else None

    def hover_note(self) -> str:
        """The record `hovered` read last, whole, for a log line."""
        if self.hover_raw is None:
            return 'unread'
        flag, unit_type, unit_id, tail = self.hover_raw
        return f'flag {flag:#x} type {unit_type} id {unit_id} tail {tail:#x}'

    def hover_candidates(self, unit_id: int, unit_type: int = MONSTER_UNIT) -> list[str]:
        """Research: image addresses holding (unit type, this unit id), as the record of the
        unit under the pointer would while the pointer is on it. Never raises."""
        try:
            data = b''.join(
                self.memory.pread(self.base + DATA_RVA + offset, 0x100000).ljust(0x100000, b'\0')
                for offset in range(0, DATA_SIZE, 0x100000)
            )
        except OSError:
            return []
        wanted, found, at = struct.pack('<II', unit_type, unit_id), [], -1
        while len(found) < 8 and (at := data.find(wanted, at + 1)) >= 0:
            found.append(hex(DATA_RVA + at))
        return found

    def place(self) -> tuple[str | None, int | None]:
        """(game name, level) for the journey: no name out of a game, no level when unreadable."""
        if self.read(self.base + UI_PANELS_RVA, UI_PANELS_SIZE)[IN_GAME] != 1:
            return None, None
        name = decode_name(self.read(self.base + GAME_NAME_RVA, GAME_NAME_SIZE))
        try:
            player = self._player()
        except OSError, ValueError, struct.error:
            player = None
        self.where = (player.x, player.y) if player is not None else None
        self.mode = player.mode if player is not None else None
        stats = unit_stats(self.read, player.stats_at) if player is not None and player.stats_at else {}
        self.life = (stats.get(LIFE_STAT, 0) >> 8, stats[MAX_LIFE_STAT] >> 8) if MAX_LIFE_STAT in stats else None
        return name, player.area if player is not None else None

    def world(self, light: bool = False) -> World:
        """The game as it is now. `light`: without the monsters and the doors, for a step that only
        asks where the character is and what it does. A teleport step looked at the game about six
        times before its key, 54 to 96 ms in all with nothing else in the way (22:11 on 2026-10-11),
        and every look walked all the monsters."""
        panels = self.read(self.base + UI_PANELS_RVA, UI_PANELS_SIZE)
        in_game = panels[IN_GAME] == 1
        player, monsters, doors, dead = None, (), (), frozenset()
        if in_game:
            try:
                player = self._player()
                if not light:
                    monsters, dead = self._monsters() if player is not None else ((), frozenset())
                    doors = self._doors() if player is not None else ()
            except OSError, ValueError, struct.error:
                player, monsters, doors, dead = None, (), (), frozenset()
        return World(
            in_game=in_game,
            open_panels=tuple(name for name, offset in OPEN_PANELS.items() if panels[offset] == 1),
            game_name=decode_name(self.read(self.base + GAME_NAME_RVA, GAME_NAME_SIZE)),
            slots=decode_slots(self.read(self.base + SKILL_SLOTS_RVA, SKILL_SLOTS * SKILL_SLOT_SIZE)),
            trace=b''.join(self.read(self.base + rva, 1) for rva in TRACE_RVAS),
            view=self.read(self.base + VIEW_RVA, 1)[0],
            player=player,
            monsters=monsters,
            doors=doors,
            dead=dead,
            show_items=panels[SHOW_ITEMS] == 1,
        )
