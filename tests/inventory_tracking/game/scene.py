"""A stand-in game in real memory: the unit tables of a Chaos Sanctuary look, read through /proc/<pid>/mem by the
macro's own `GameMemory`, and a game clock ticking every 40 ms (2026-10-23, game/frames.py's tests and
rca/2026-10-23/scripts/realtime_bench.py).

The population follows the census of 2026-10-13 (rca/2026-10-23/scripts/lag_reads_bench.py, from which this is
taken): 7 player units, `monsters` monsters, 18 objects, 300 items, 22 missiles. `run_scene` is a process's body: it
builds the scene, sends (pid, base, table) on its pipe and ticks until told to stop; with `moving` the character's x is
5000 + the tick's number, the tick's time (monotonic s) kept in `times[n % len(times)]`.
"""

import ctypes
import os
import struct
import time
from dataclasses import dataclass

from inventory_tracking.collection.capture import INVENTORY_MAGIC
from inventory_tracking.game.layout import (
    BASE_STATS,
    FULL_STATS,
    GAME_NAME_RVA,
    IN_GAME,
    ITEM_BODY_LOCATION,
    ITEM_OWNER,
    LEFT_SKILL,
    MISSILE_DATA,
    MISSILE_PATH,
    MONSTER_OWNER,
    NO_OWNER,
    OBJECT_PATH,
    PATH_RECORD,
    RIGHT_SKILL,
    SKILL_IN_USE,
    SKILL_LIST,
    SKILL_RECORD,
    TICK_HEAD,
    UNIT_SLOTS,
    VIEW_RVA,
)
from inventory_tracking.native.layout import (
    CHARGED_SKILL_STAT,
    LEVEL_AREA_ID,
    PATH_ROOM1,
    ROOM1_ROOM2,
    ROOM2_LEVEL,
    TERROR_SERVICE_RVA,
    UI_PANELS_RVA,
)


KEEP: list = []
TICK_SECONDS = 0.04
PR_SET_PTRACER, PTRACER_ANY = 0x59616D61, ctypes.c_ulong(-1).value


def alloc(size: int) -> int:
    buffer = ctypes.create_string_buffer(size)
    KEEP.append(buffer)
    return ctypes.addressof(buffer)


def put(address: int, fmt: str, *values) -> None:
    struct.pack_into(fmt, (ctypes.c_char * struct.calcsize(fmt)).from_address(address), 0, *values)


def stat_list(holder: int, offset: int, stats: list[tuple[int, int]]) -> None:
    array = alloc(max(8, 8 * len(stats)))
    put(holder + offset, '<QQ', array, len(stats))
    for index, (stat, value) in enumerate(stats):
        put(array + 8 * index, '<HHi', 0, stat, value)


def skill_list(unit: int, skill: int) -> None:
    row = alloc(0x10)
    put(row, '<H', skill)
    record = alloc(SKILL_RECORD)
    put(record, '<Q', row)
    skills = alloc(0x40)
    put(skills + LEFT_SKILL, '<Q', record)
    put(skills + RIGHT_SKILL, '<Q', record)
    put(skills + SKILL_IN_USE, '<Q', record)
    put(unit + SKILL_LIST, '<Q', skills)


@dataclass
class Scene:
    base: int
    table: int
    clock: int  # the game's clock object (TICK_HEAD bytes): +0x08 now, +0x0C the last whole tick (ms)
    player_path: int  # the character's path record (x at +2, y at +6)
    monster_paths: tuple[int, ...]


def build(*, monsters: int = 60, objects: int = 18, items: int = 300, missiles: int = 22) -> Scene:
    base = alloc(0x25A6000)  # the image: panels, game name, skill slots, trace bytes, hover, clock pointer
    put(base + UI_PANELS_RVA + IN_GAME, '<B', 1)
    put(base + VIEW_RVA, '<B', 255)
    put(base + GAME_NAME_RVA, '8s', b'cyber32')
    clock = alloc(TICK_HEAD)
    put(base + TERROR_SERVICE_RVA, '<Q', clock)
    table = alloc(UNIT_SLOTS * 1024)
    level = alloc(0x200)
    put(level + LEVEL_AREA_ID, '<I', 108)
    room2 = alloc(0xA0)
    put(room2 + ROOM2_LEVEL, '<Q', level)
    room1 = alloc(0x50)
    put(room1 + ROOM1_ROOM2, '<Q', room2)
    heads: dict[int, list[int]] = {}

    def link(slot: int, unit_id: int, address: int) -> None:
        heads.setdefault(slot * 128 + unit_id % 128, []).append(address)

    def unit(kind: int, txt: int, unit_id: int, mode: int, *, path=0, data=0, stats=0, inventory=0) -> int:
        address = alloc(0x1C0)
        put(address, '<IIII', kind, txt, unit_id, mode)
        put(address + 0x10, '<Q', data)
        put(address + 0x38, '<Q', path)
        put(address + 0x88, '<QQ', stats, inventory)
        return address

    character, player_path = 1, 0
    for index in range(7):  # the character and six stash tabs
        unit_id = index + 1
        path = alloc(0x28)
        put(path, '<HHHH', 0, 5000, 0, 5000)
        put(path + PATH_ROOM1, '<Q', room1)
        player_path = player_path or path
        data = alloc(16)
        put(data, '16s', b'CybergrindAA')
        stats = alloc(0xC00)
        life = [(6, 900 << 8), (7, 1000 << 8)] if index == 0 else []
        stat_list(stats, FULL_STATS, life + [(100 + i, i) for i in range(72 - len(life) if index == 0 else 4)])
        inventory = 0
        if index == 0:
            inventory = alloc(0x78)
            put(inventory, '<IIQ', INVENTORY_MAGIC, 0, 0)
            grids = alloc(32 * 4)
            put(inventory + 0x20, '<QQ', grids, 4)
            for grid in range(4):
                cells = alloc(10 * 8 * 8)
                put(grids + 32 * grid + 0x10, '<BB', 10, 4)
                put(grids + 32 * grid + 0x18, '<Q', cells)
        address = unit(0, 7, unit_id, 1, path=path, data=data, stats=stats, inventory=inventory)
        if inventory:
            put(inventory + 8, '<Q', address)
        skill_list(address, 388)
        link(0, unit_id, address)
    monster_paths = []
    for index in range(monsters):
        unit_id = 1000 + index
        path = alloc(PATH_RECORD)
        put(path, '<HHHH', 0, 5010 + index % 40, 0, 5020 + index // 40)
        monster_paths.append(path)
        data = alloc(0x80)
        put(data + MONSTER_OWNER, '<I', NO_OWNER)
        stats = alloc(0xC00)
        stat_list(stats, FULL_STATS, [(6, 90 << 8), (7, 128 << 8)] + [(20 + i, i) for i in range(13)])
        mode = 4 if index % 3 == 0 else (12 if index % 10 == 9 else 1)
        address = unit(1, 19, unit_id, mode, path=path, data=data, stats=stats)
        skill_list(address, 0)
        link(1, unit_id, address)
    for index in range(objects):
        unit_id = 2000 + index
        link(2, unit_id, unit(2, 100 + index, unit_id, 0, path=alloc(OBJECT_PATH), data=alloc(0x40)))
    for index in range(missiles):
        unit_id = 3000 + index
        link(9, unit_id, unit(3, 750, unit_id, 0, path=alloc(MISSILE_PATH), data=alloc(MISSILE_DATA)))
    for index in range(items):  # carried and stored, 12 worn (one a Teleport staff), 8 in the belt, 10 on the ground
        unit_id = 128 * (index // 112) + index % 112
        mode = 3 if index >= items - 10 else (2 if index >= items - 18 else (1 if index >= items - 30 else 0))
        txt = 63 if index == items - 30 else (531 if mode == 2 else (538 if index == items - 1 else 200 + index % 300))
        path = alloc(0x20)
        put(path + 0x10, '<II', index % 4 if mode == 2 else 5005, 5005)
        data = alloc(0x60)
        put(data + ITEM_OWNER, '<I', character)
        put(data + ITEM_BODY_LOCATION, '<B', 4 if mode == 1 else 0)
        stats = alloc(0x100)
        stat_list(stats, FULL_STATS, [(CHARGED_SKILL_STAT, 0x1414)] if txt == 63 else [(14, 9000)])
        stat_list(stats, BASE_STATS, [(14, 9000)])
        link(4, unit_id, unit(4, txt, unit_id, mode, path=path, data=data, stats=stats))
    for key, chain in heads.items():
        previous = 0
        for address in reversed(chain):
            put(address + 0x158, '<Q', previous)
            previous = address
        put(table + 8 * key, '<Q', previous)
    return Scene(base, table, clock, player_path, tuple(monster_paths))


def tick(scene: Scene, number: int, now: float, *, moving: bool) -> None:
    """The game's tick `number` made at `now` (monotonic s): the clock's fields, and with `moving` the character at
    x = 5000 + number % 20000 and the monsters a unit on."""
    ms = int(now * 1000) & 0xFFFFFFFF
    if moving:
        put(scene.player_path + 2, '<H', 5000 + number % 20000)
        for index, path in enumerate(scene.monster_paths):
            put(path + 2, '<H', 5010 + (index + number) % 40)
    put(scene.clock + 0x08, '<II', ms, ms)


def run_scene(conn, moving: bool = False, times=None, monsters: int = 60) -> None:
    """A stand-in game process: the scene built, (pid, base, table) sent, a tick every 40 ms until a word on `conn`
    (or its end). Any process of this user may read it (PR_SET_PTRACER), as the game lets the service."""
    ctypes.CDLL(None, use_errno=True).prctl(PR_SET_PTRACER, PTRACER_ANY, 0, 0, 0)
    scene = build(monsters=monsters)
    begun = time.monotonic()
    tick(scene, 0, begun, moving=moving)
    if times is not None:
        times[0] = begun
    conn.send((os.getpid(), scene.base, scene.table))
    number = 0
    while True:
        number += 1
        due = begun + number * TICK_SECONDS
        if conn.poll(max(0.0, due - time.monotonic())):
            break
        now = time.monotonic()
        tick(scene, number, now, moving=moving)
        if times is not None:
            times[number % len(times)] = now
    conn.close()
