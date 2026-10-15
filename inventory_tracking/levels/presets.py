"""Bundled LvlPrest Def and level names (data/level_presets.json, built by build_presets.py) and
preset warp and waypoint spots (data/preset_warps.json, built by build_warps.py), and the boxes
doors take clicks in (data/warp_boxes.json, built by build_warp_boxes.py), and the objects a
preset's files place (data/preset_objects.json, built by build_objects.py)."""

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
    """Whether level `to` is entered from `area` by walking across, with no warp to click (levels.txt): a Vis slot
    that names it with no warp behind it (Warp -1: the River of Flame's bridge into the Chaos Sanctuary, the Outer
    Cloister's gate into the Barracks), or none that names it, as levels joined by touching rooms are (a border:
    the Cold Plains and the Burial Grounds, the Outer Steppes and the Plains of Despair). A level behind a warp
    (stairs, a cave's mouth, a door) is not; an object used to go (a portal, a waypoint) is no level link at all."""
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


_PLACED = json.loads((Path(__file__).parent / 'data' / 'preset_objects.json').read_text())


def object_spots(preset: int, variant: int | None, thing: int) -> tuple[tuple[int, int], ...]:
    """Where one DS1 variant of the preset places objects of objects.txt id `thing`, in world units
    from the preset origin; () when it places none or the variant is unread. A preset with one
    layout answers unread too (Durance of Hate 3, the Throne)."""
    if variant is None and object_variants(preset) == 1:
        variant = 0
    placed = _PLACED['objects'].get(str(preset), {}).get(str(variant), ()) if variant is not None else ()
    return tuple((x, y) for found, x, y in placed if found == thing)


def object_variants(preset: int) -> int:
    """How many DS1 variants the preset has; 0 when none of them places an object a mark sits on."""
    return _PLACED['variants'].get(str(preset), 0)
