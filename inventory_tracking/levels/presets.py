"""Bundled LvlPrest Def and level names (data/level_presets.json, built by build_presets.py) and
preset warp and waypoint spots (data/preset_warps.json, built by build_warps.py), and the boxes
doors take clicks in (data/warp_boxes.json, built by build_warp_boxes.py)."""

import json
from pathlib import Path


_TABLE = json.loads((Path(__file__).parent / 'data' / 'level_presets.json').read_text())
PRESET_NAMES: dict[int, str] = {int(k): v for k, v in _TABLE['presets'].items()}
LEVEL_NAMES: dict[int, str] = {int(k): v for k, v in _TABLE['levels'].items()}
DISPLAY_NAMES: dict[int, str] = {int(k): v for k, v in _TABLE['names'].items()}
LEVEL_LINKS: dict[int, tuple[int, ...]] = {int(k): tuple(v) for k, v in _TABLE['links'].items()}
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


def warp_spots(preset: int, variant: int | None) -> dict[int, tuple[float, float]]:
    """Warp slot -> centre of its tiles from the preset origin, for one DS1 variant; {} unknown."""
    slots = _WARPS.get(str(preset), {}).get(str(variant), {}) if variant is not None else {}
    return {int(slot): (x, y) for slot, (x, y) in slots.items()}


def waypoint_spot(preset: int, variant: int | None) -> tuple[float, float] | None:
    """The preset's waypoint from the preset origin, in tiles, for one DS1 variant; None unknown.
    An unread variant still answers when every variant puts it in the same place (Lut Gholein)."""
    variants = _WAYPOINTS.get(str(preset), {})
    known = variants.values() if variant is None else [variants[str(variant)]] if str(variant) in variants else []
    spots = {(x, y) for x, y in known}
    return next(iter(spots)) if len(spots) == 1 else None


def warp_box(warp: int) -> tuple[int, int, int, int] | None:
    """(left, top, right, bottom) of the box a door of lvlwarp Id `warp` takes clicks in, classic
    pixels from the door unit's place on screen; None when unknown."""
    box = _BOXES.get(str(warp))
    return (box[0], box[1], box[2], box[3]) if box else None
