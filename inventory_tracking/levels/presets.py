"""Bundled level tables under data/: preset and level names (build_presets.py), warp and waypoint spots
(build_warps.py), door click boxes (build_warp_boxes.py), placed objects (build_objects.py)."""

import json
from pathlib import Path


_TABLE = json.loads((Path(__file__).parent / 'data' / 'level_presets.json').read_text())
PRESET_NAMES: dict[int, str] = {int(k): v for k, v in _TABLE['presets'].items()}
LEVEL_NAMES: dict[int, str] = {int(k): v for k, v in _TABLE['levels'].items()}
DISPLAY_NAMES: dict[int, str] = {int(k): v for k, v in _TABLE['names'].items()}
LEVEL_LINKS: dict[int, tuple[int, ...]] = {int(k): tuple(v) for k, v in _TABLE['links'].items()}
LEVEL_WARPS: dict[int, tuple[int, ...]] = {int(k): tuple(v) for k, v in _TABLE['warps'].items()}
_SPOTS = json.loads((Path(__file__).parent / 'data' / 'preset_warps.json').read_text())
_WARPS = _SPOTS['warps']
_WAYPOINTS = _SPOTS['waypoints']
_BOXES = json.loads((Path(__file__).parent / 'data' / 'warp_boxes.json').read_text())['boxes']


def preset_name(preset: int) -> str:
    return PRESET_NAMES.get(preset, f'preset {preset}')


def level_name(area: int) -> str:
    return LEVEL_NAMES.get(area, f'area {area}')


def display_name(area: int) -> str:
    """The name the game shows ('Halls of Pain'); level_name is the older table name."""
    return DISPLAY_NAMES.get(area) or level_name(area)


def linked_level(area: int, slot: int) -> int | None:
    """The level behind warp slot `slot` of `area` (levels.txt Vis0..7); None when there is none."""
    links = LEVEL_LINKS.get(area, ())
    return links[slot] or None if slot < len(links) else None


def open_passage(area: int, to: int) -> bool:
    """Whether `to` is entered from `area` by walking across (levels.txt): a Vis slot naming it with Warp -1
    (River of Flame to Chaos Sanctuary), or no slot naming it (a border of touching rooms)."""
    links, warps = LEVEL_LINKS.get(area, ()), LEVEL_WARPS.get(area, ())
    slots = [slot for slot, linked in enumerate(links) if linked == to]
    return all(slot >= len(warps) or warps[slot] < 0 for slot in slots)


def warp_spots(preset: int, variant: int | None) -> dict[int, tuple[float, float]]:
    """Warp slot -> centre of its tiles from the preset origin, for one DS1 variant; {} unknown."""
    slots = _WARPS.get(str(preset), {}).get(str(variant), {}) if variant is not None else {}
    return {int(slot): (x, y) for slot, (x, y) in slots.items()}


def has_warps(preset: int) -> bool:
    """Whether any layout of the preset holds a warp tile: a door, not an open edge."""
    return any(_WARPS.get(str(preset), {}).values())


def waypoint_spot(preset: int, variant: int | None) -> tuple[float, float] | None:
    """The preset's waypoint from its origin, in tiles, for one DS1 variant; None unknown. An unread
    variant answers when every variant agrees."""
    variants = _WAYPOINTS.get(str(preset), {})
    known = variants.values() if variant is None else [variants[str(variant)]] if str(variant) in variants else []
    spots = {(x, y) for x, y in known}
    return next(iter(spots)) if len(spots) == 1 else None


def warp_box(warp: int) -> tuple[int, int, int, int] | None:
    """(left, top, right, bottom) click box of a lvlwarp Id `warp` door, classic pixels from the door's
    screen place; None unknown."""
    box = _BOXES.get(str(warp))
    return (box[0], box[1], box[2], box[3]) if box else None


_PLACED = json.loads((Path(__file__).parent / 'data' / 'preset_objects.json').read_text())


def object_spots(preset: int, variant: int | None, thing: int) -> tuple[tuple[int, int], ...]:
    """Where one DS1 variant places objects.txt id `thing`, world units from the preset origin; () when none
    or unread (a one-layout preset answers unread too)."""
    if variant is None and object_variants(preset) == 1:
        variant = 0
    placed = _PLACED['objects'].get(str(preset), {}).get(str(variant), ()) if variant is not None else ()
    return tuple((x, y) for found, x, y in placed if found == thing)


def object_variants(preset: int) -> int:
    """How many DS1 variants the preset has; 0 when none of them places an object a mark sits on."""
    return _PLACED['variants'].get(str(preset), 0)
