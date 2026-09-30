"""Widget renderers: measure(payload, scale) → (w, h) and draw(cr, w, h, payload, scale), pure cairo.

Text uses PangoCairo markup from presentation.render_markup (the OSD palette); sizes are logical
pixels at scale 1.0 (the reference game-window height, see hud/plan.md). Composite widgets draw
their sub-widgets inside their own box. Everything renders to an image surface in tests.
"""

import math
from functools import cache

import cairo
import gi


gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo  # noqa: E402

from inventory_tracking.common import LOG  # noqa: E402
from inventory_tracking.config import OSD  # noqa: E402
from inventory_tracking.hud.payloads import card_lines  # noqa: E402
from inventory_tracking.osd.direction import MAP_SIZE, draw_indicator  # noqa: E402
from inventory_tracking.osd.level_map import MapCard, draw_map  # noqa: E402
from inventory_tracking.presentation import StyledLine, render_markup, tone_rgb  # noqa: E402


CARD_BACKGROUND = (0.06, 0.06, 0.08, 0.92)
CARD_BORDER = (0.70, 0.61, 0.38, 1.0)


@cache
def _measuring_context():
    return cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))


def text_layout(cr, markup: str, scale: float):
    layout = PangoCairo.create_layout(cr)
    font = Pango.FontDescription(f'{OSD.font_family} {OSD.font_weight} {max(6, round(OSD.font_size * scale))}')
    layout.set_font_description(font)
    layout.set_markup(markup, -1)
    return layout


def card_background(cr, width, height, scale):
    radius = 4 * scale
    cr.new_sub_path()
    cr.arc(width - radius, radius, radius, -math.pi / 2, 0)
    cr.arc(width - radius, height - radius, radius, 0, math.pi / 2)
    cr.arc(radius, height - radius, radius, math.pi / 2, math.pi)
    cr.arc(radius, radius, radius, math.pi, 3 * math.pi / 2)
    cr.close_path()
    cr.set_source_rgba(*CARD_BACKGROUND)
    cr.fill_preserve()
    cr.set_source_rgba(*CARD_BORDER)
    cr.set_line_width(1)
    cr.stroke()


class GuideCard:
    """Level guide: one row per POI (framed vector arrow or arrival dot, with text) and the map."""

    ARROW_WIDTH, ARROW_HEIGHT = 64, 52
    PAD, GAP, SLACK = 8, 8, 4  # SLACK: hinting differs slightly between measure and draw
    HERE = '•'  # "you are here" rows (no arrow) get a dot in the arrow column

    def decode(self, payload):
        lines = [StyledLine.from_payload(line) for line in payload.get('lines', [])]
        card = MapCard.from_payload(payload['map']) if payload.get('map') else None
        return lines, card

    def _rows(self, lines, scale):
        rows = []
        for line in lines:
            mark = line.arrow or (self.HERE if line.text.startswith(self.HERE) else None)
            text = line.text.removeprefix(mark).lstrip() if mark else line.text
            layout = text_layout(_measuring_context(), render_markup([StyledLine(text, line.tone)]), scale)
            width, height = layout.get_pixel_size()
            rows.append((line, text, width + self.SLACK * scale, max(height, round(self.ARROW_HEIGHT * scale))))
        return rows

    def measure(self, payload, scale, limit=None):
        lines, card = self.decode(payload)
        pad, gap, arrow = self.PAD * scale, self.GAP * scale, self.ARROW_WIDTH * scale
        rows = self._rows(lines, scale)
        width = max([arrow + gap + w for _, _, w, _ in rows] + [0])
        height = sum(h for *_, h in rows) + gap * max(0, len(rows) - 1)
        if card is not None:
            width = max(width, MAP_SIZE[0] * scale)
            height += (gap if rows else 0) + MAP_SIZE[1] * scale
        return math.ceil(width + 2 * pad), math.ceil(height + 2 * pad)

    def draw(self, cr, width, height, payload, scale):
        lines, card = self.decode(payload)
        pad, gap, arrow = self.PAD * scale, self.GAP * scale, self.ARROW_WIDTH * scale
        rows = self._rows(lines, scale)
        if rows:  # the text rows get a card; the map below them has no box (user, 2026-09-30)
            text_height = sum(h for *_, h in rows) + gap * (len(rows) - 1)
            card_background(cr, width, text_height + 2 * pad, scale)
        y = pad
        for line, text, _, row_height in rows:
            if line.arrow or line.text.startswith(self.HERE):
                cr.save()
                tile_height = self.ARROW_HEIGHT * scale
                cr.translate(pad, y + (row_height - tile_height) / 2)
                draw_indicator(cr, arrow, tile_height, line.arrow, tone_rgb(line.tone))
                cr.restore()
            layout = text_layout(cr, render_markup([StyledLine(text, line.tone)]), scale)
            cr.move_to(pad + arrow + gap, y + (row_height - layout.get_pixel_size()[1]) / 2)
            PangoCairo.show_layout(cr, layout)
            y += row_height + gap
        if card is not None:
            cr.save()
            cr.translate(pad, y if lines else pad)
            draw_map(cr, MAP_SIZE[0] * scale, MAP_SIZE[1] * scale, card)
            cr.restore()


class TextCard:
    """Assessment / shop / identify card: styled lines, word-wrapped to the slot's width and
    ellipsized at its height (what the old assessment label did with its width/line caps)."""

    PAD_X, PAD_Y, SLACK = 10, 6, 4

    def _layout(self, cr, payload, scale, width=None, height=None):
        layout = text_layout(cr, render_markup(card_lines(payload)), scale)
        if width is not None:
            layout.set_wrap(Pango.WrapMode.WORD_CHAR)
            layout.set_width(max(1, round(width)) * Pango.SCALE)
        if height is not None:
            layout.set_ellipsize(Pango.EllipsizeMode.END)
            layout.set_height(max(1, round(height)) * Pango.SCALE)
        return layout

    def measure(self, payload, scale, limit=None):
        pad_x, pad_y, slack = self.PAD_X * scale, self.PAD_Y * scale, self.SLACK * scale
        inner = (None, None) if limit is None else (limit[0] - 2 * pad_x - slack, limit[1] - 2 * pad_y)
        width, height = self._layout(_measuring_context(), payload, scale, *inner).get_pixel_size()
        return math.ceil(width + slack + 2 * pad_x), math.ceil(height + 2 * pad_y)

    def draw(self, cr, width, height, payload, scale):
        pad_x, pad_y, slack = self.PAD_X * scale, self.PAD_Y * scale, self.SLACK * scale
        card_background(cr, width, height, scale)
        layout = self._layout(cr, payload, scale, width - 2 * pad_x - slack, height - 2 * pad_y)
        cr.move_to(pad_x, pad_y)
        PangoCairo.show_layout(cr, layout)


RENDERERS = {'guide': GuideCard(), 'text': TextCard()}


def measure(widget, *, scale: float, limit: tuple[int, int] | None = None) -> tuple[int, int]:
    """Size at `scale`, fitting `limit` (the slot's free width/height) when the widget can wrap."""
    renderer = RENDERERS.get(widget.kind)
    return renderer.measure(widget.payload, scale, limit) if renderer else (0, 0)


def draw_scene(cr, boxes, *, scale: float):
    for widget, (x, y, width, height) in boxes:
        renderer = RENDERERS.get(widget.kind)
        if renderer is None:
            continue
        cr.save()
        try:
            cr.translate(x, y)
            renderer.draw(cr, width, height, widget.payload, scale)
        except Exception:  # one broken widget never blanks the rest of the HUD
            LOG.exception('HUD widget %s (%s) failed to draw', widget.id, widget.kind)
        finally:
            cr.restore()
