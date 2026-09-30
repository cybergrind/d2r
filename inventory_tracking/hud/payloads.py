"""Widget payloads, built by producers. Pure data: no GTK/Pango, so producers never import renderers."""

from inventory_tracking.osd.level_map import MapCard
from inventory_tracking.presentation import StyledLine


def guide_payload(lines, card: MapCard | None) -> dict:
    """Level guide card: styled rows (arrow or "here") and the level map."""
    return {'lines': [line.to_payload() for line in lines], 'map': card.to_payload() if card else None}


def card_payload(lines) -> dict:
    """Text card (Alt+D assessment, shop, identify): styled lines; plain strings become default-tone lines."""
    return {'lines': [(line if isinstance(line, StyledLine) else StyledLine(line)).to_payload() for line in lines]}


def card_lines(payload) -> list[StyledLine]:
    return [StyledLine.from_payload(line) for line in payload.get('lines', [])]
