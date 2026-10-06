"""Slots in game-window fractions → canvas pixel boxes.

The canvas covers the working area (niri's workspace view), so its coordinates are the ones
niri reports for floating windows. Tiled windows have no reported position; like the
live-accepted repair mark, a tiled game is taken to sit at the working area's bottom-left.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GameRect:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class Slot:
    """Top-left of the slot's widget stack, as fractions of the game window (x from left, y from top);
    a centred slot's x is the middle of its widgets instead."""

    x: float
    y: float
    max_width: float = 1.0  # widest widget, as a fraction of the game window width
    centered: bool = False
    upward: bool = False  # y is the bottom of the stack, which grows up


def slot_limit(slot: Slot, rect: GameRect) -> tuple[int, int]:
    """(width, height) a widget may take: the game window's room right of (or around, centred) and
    below the slot (above it when it grows up)."""
    room = 2 * min(slot.x, 1 - slot.x) if slot.centered else 1 - slot.x
    width = min(rect.width * room, rect.width * slot.max_width)
    return round(width), round(rect.height * (slot.y if slot.upward else 1 - slot.y))


def game_rect(canvas_size, *, window_size, position) -> GameRect | None:
    if window_size is None:
        return None
    width, height = window_size
    if position is not None:
        return GameRect(int(position[0]), int(position[1]), width, height)
    return GameRect(0, canvas_size[1] - height, width, height)


def scale_for(height: float, *, reference_height: float) -> float:
    return min(2.0, max(0.6, height / reference_height))


def place(widgets, sizes, slots, rect: GameRect, *, gap: int = 8):
    """[(widget, (x, y, w, h))]: each slot stacks its widgets downward, kept inside the game window."""
    cursors: dict[str, float] = {}
    boxes = []
    for widget in widgets:
        slot = slots.get(widget.slot)
        if slot is None:
            continue
        width, height = sizes[widget.id]
        edge = cursors.get(widget.slot, rect.y + slot.y * rect.height)
        top = edge - height if slot.upward else edge
        left = rect.x + slot.x * rect.width - (width / 2 if slot.centered else 0)
        x = min(left, rect.x + rect.width - width)
        y = min(top, rect.y + rect.height - height)
        x, y = max(rect.x, round(x)), max(rect.y, round(y))
        boxes.append((widget, (x, y, width, height)))
        cursors[widget.slot] = y - gap if slot.upward else y + height + gap
    return boxes
