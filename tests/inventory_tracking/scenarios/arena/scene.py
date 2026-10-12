"""The records of one arena scene and their JSON form.

A scene is a fight cut from a recorded battle or built by hand (framework-plan.md, Task 1.1).
"""

import dataclasses
import json
import typing
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from types import UnionType
from typing import Union


Point = tuple[float, float]


@dataclass
class Mob:
    """One monster in the scene."""

    unit: int
    txt: int  # monstats id
    at: Point  # world units
    level: int
    life: float  # points left
    full: float  # points at full life
    flags: int = 0  # the monster's type flags (rank)
    mods: tuple[int, ...] = ()  # enchantments, monumod ids
    tier: int = 0  # Herald tier, 0: none
    mode: int = 1  # monmode; 12 is a corpse
    owner: int | None = None  # unit id of its owner when it is a companion of the character's
    ally: bool = False
    immune: bool = False  # the strike takes nothing off it


@dataclass
class WeaponSet:
    """One of the two weapon sets the hero can switch between."""

    codes: tuple[str, ...]  # base codes of what is held
    resist: dict[str, float]  # 'fire','cold','lightning','physical' -> share of damage let through
    teleport_charges: int | None = None  # None: no Teleport staff in this set


@dataclass
class Hero:
    """The character at the time of the scene."""

    name: str
    at: Point
    area: int
    life: float
    max_life: float
    mana: float
    max_mana: float
    belt: tuple[int | None, ...]  # item class id by belt cell, 16 cells, None empty (as Loot.belt)
    sets: tuple[WeaponSet, WeaponSet]
    hand: int = 0  # index into sets of the set in hand
    slots: tuple[int | None, ...] = ()  # skill id on each skill key
    hex_purge: bool | None = None  # buff states as macros/world.py Player reads them; None: unknown
    ward: bool | None = None
    consume: bool | None = None
    # the skill on each mouse button (macros/world.py Player); None: not known, the arena's default holds
    left_skill: int | None = None
    right_skill: int | None = None


@dataclass
class Drop:
    """An item on the ground in the scene."""

    unit: int
    code: str
    at: Point
    quality: int = 0
    gold: int = 0


@dataclass
class Prop:
    """An object that can be operated in the scene (a chest, a body): macros/world.py `Thing`."""

    unit: int
    txt: int  # objects.txt id
    at: Point
    mode: int = 0  # 0 until it is operated


@dataclass
class Scene:
    """A whole arena scene: the hero, the monsters, the walkable grids and the doors."""

    name: str
    hero: Hero
    mobs: list[Mob]
    ground: list[dict]  # walkable grids, kept as plain dicts exactly as loaded
    doors: list[list]  # raw door rows, kept as plain lists exactly as loaded
    rooms: list[dict] = field(default_factory=list)
    drops: list[Drop] = field(default_factory=list)
    assumed: tuple[str, ...] = ()  # names of fields the source did not hold
    source: dict | None = None  # {'take': str, 'frame': int, 't': float} when cut from a recording
    things: list[Prop] = field(default_factory=list)  # no take holds them: put there by hand (incident.py)

    def copy(self) -> Scene:
        """A deep, independent copy of the scene."""
        return deepcopy(self)


def _plain(value: object) -> object:
    """The JSON-ready form of a record, with tuples as lists."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: _plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


def _build(tp: object, value: object, where: str) -> object:
    """Rebuild a JSON value as the annotated type tp (records, tuples, lists, dicts, optionals)."""
    if dataclasses.is_dataclass(tp):
        return _record(tp, value)
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if origin is UnionType or origin is Union:
        if value is None:
            return None
        return _build(next(a for a in args if a is not type(None)), value, where)
    if origin is tuple:
        if not isinstance(value, list):
            raise ValueError(f'{where} must be a list, got {type(value).__name__}')
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_build(args[0], v, where) for v in value)
        if len(value) != len(args):
            raise ValueError(f'{where} needs {len(args)} items, got {len(value)}')
        return tuple(_build(a, v, where) for a, v in zip(args, value, strict=True))
    if origin is list:
        if not isinstance(value, list):
            raise ValueError(f'{where} must be a list, got {type(value).__name__}')
        return [_build(args[0], v, where) for v in value]
    if origin is dict:
        if not isinstance(value, dict):
            raise ValueError(f'{where} must be an object, got {type(value).__name__}')
        return {k: _build(args[1], v, where) for k, v in value.items()}
    return value


def _record(cls: type, data: object) -> object:
    """Rebuild a record from its JSON object, refusing unknown and missing keys by name."""
    if not isinstance(data, dict):
        raise ValueError(f'{cls.__name__} must be an object, got {type(data).__name__}')
    fields = {f.name: f for f in dataclasses.fields(cls)}
    for key in data:
        if key not in fields:
            raise ValueError(f'unknown key {key!r} in {cls.__name__}')
    hints = typing.get_type_hints(cls)
    kwargs: dict[str, object] = {}
    for name, f in fields.items():
        if name not in data:
            if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING:
                raise ValueError(f'missing field {name!r} in {cls.__name__}')
            continue
        kwargs[name] = _build(hints[name], data[name], f'{cls.__name__}.{name}')
    return cls(**kwargs)


def dump(scene: Scene, path: Path) -> None:
    """Write the scene to path as JSON."""
    text = json.dumps(_plain(scene), indent=1, sort_keys=False, ensure_ascii=False)
    path.write_text(text + '\n', encoding='utf-8')


def load(path: Path) -> Scene:
    """Read a scene back from a JSON file written by dump."""
    data = json.loads(path.read_text(encoding='utf-8'))
    return _record(Scene, data)  # type: ignore[return-value]
