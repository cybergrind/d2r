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
from gi.repository import Pango, PangoCairo  # ruff: ignore[module-import-not-at-top-of-file]

from inventory_tracking.common import LOG  # ruff: ignore[module-import-not-at-top-of-file]
from inventory_tracking.config import HUD, OSD  # ruff: ignore[module-import-not-at-top-of-file]
from inventory_tracking.hud.direction import MAP_SIZE, draw_indicator  # ruff: ignore[module-import-not-at-top-of-file]
from inventory_tracking.hud.ground import arrow_reach, arrow_shown, ground_marks, place_mark  # ruff: ignore[module-import-not-at-top-of-file]
from inventory_tracking.hud.map import KIND_COLOURS, LOCAL_SCALE, WHOLE_SCALE, draw_map  # ruff: ignore[module-import-not-at-top-of-file]
from inventory_tracking.hud.payloads import card_lines  # ruff: ignore[module-import-not-at-top-of-file]
from inventory_tracking.levels.map_card import MapCard  # ruff: ignore[module-import-not-at-top-of-file]
from inventory_tracking.presentation import StyledLine, Tone, render_markup, tone_rgb  # ruff: ignore[module-import-not-at-top-of-file]


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
    OUTLINE = 3.5  # the dark line around the rows' text

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
        y = pad
        for line, text, _, row_height in rows:
            if line.arrow or line.text.startswith(self.HERE):
                cr.save()
                tile_height = self.ARROW_HEIGHT * scale
                cr.translate(pad, y + (row_height - tile_height) / 2)
                draw_indicator(cr, arrow, tile_height, line.arrow, tone_rgb(line.tone))
                cr.restore()
            layout = text_layout(cr, render_markup([StyledLine(text, line.tone)]), scale)
            # No box behind the rows (user, 2026-10-06: it hid the game): the text is outlined instead.
            left, top = pad + arrow + gap, y + (row_height - layout.get_pixel_size()[1]) / 2
            cr.move_to(left, top)
            PangoCairo.layout_path(cr, layout)
            cr.set_source_rgba(0, 0, 0, 0.9)
            cr.set_line_width(self.OUTLINE * scale)
            cr.set_line_join(cairo.LINE_JOIN_ROUND)
            cr.stroke()
            cr.move_to(left, top)
            PangoCairo.show_layout(cr, layout)
            y += row_height + gap
        if card is not None:
            cr.save()
            cr.translate(pad, y if lines else pad)
            draw_map(
                cr,
                MAP_SIZE[0] * scale,
                MAP_SIZE[1] * scale,
                card,
                min_scale=WHOLE_SCALE * scale,
                local_scale=LOCAL_SCALE * scale,
            )
            cr.restore()


class TextCard:
    """Assessment / shop / identify card: styled lines, word-wrapped to the slot's width and ellipsized at its
    height."""

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


class GroundMarks:
    """Translucent marks on the game view at map positions (hud/ground.py). In view: a floor
    ellipse around the spot; beyond it: an arrow towards the spot, on a ring around the player."""

    # Logical pixels; the radii are half the ellipse's width (a monster's is smaller than a way on).
    RADIUS, LEADER_RADIUS, LINE = 44, 30, 3
    ELITE_RADIUS, ELITE_LINE = 38, 5  # a deadly pack's leader: wider and bolder than its pack's marks
    ARROW, ARROW_OUTLINE = 28, 2.5  # the arrow reaches this far from its centre, either way
    # Pointing along +x: head, then the shaft, as fractions of ARROW.
    ARROW_SHAPE = ((1, 0), (0.05, -0.8), (0.05, -0.3), (-1, -0.3), (-1, 0.3), (0.05, 0.3), (0.05, 0.8))
    FILL = 0.3  # of the outline's alpha
    DANGER_FILL = 0.8  # a deadly pack's monsters stand on a filled mark (user, 2026-10-06)

    def measure(self, payload, scale, limit=None):
        return limit or (0, 0)  # the whole game window; nothing without one

    def draw(self, cr, width, height, payload, scale, config=None):
        config = config or HUD.ground
        (px, py), marks = ground_marks(payload)
        reach = arrow_reach(payload.get('age'), config)
        origin_x, origin_y, _ = place_mark(0, 0, width, height, config)
        for kind, x, y in marks:
            colour = KIND_COLOURS.get(kind, KIND_COLOURS['target'])
            sx, sy, on_screen = place_mark(x - px, y - py, width, height, config, reach)
            if not (on_screen or arrow_shown(kind, x - px, y - py, config)):
                continue
            if on_screen and kind == 'pack':
                continue  # its monsters carry their own marks; the pack is only an arrow from afar
            cr.save()
            cr.translate(sx, sy)
            if not on_screen:
                cr.rotate(math.atan2(sy - origin_y, sx - origin_x))
                size = self.ARROW * scale
                for index, (ax, ay) in enumerate(self.ARROW_SHAPE):
                    (cr.line_to if index else cr.move_to)(ax * size, ay * size)
                cr.close_path()
                cr.restore()
                cr.set_source_rgba(*colour, config.arrow_alpha)
                cr.fill_preserve()
                cr.set_source_rgba(0, 0, 0, config.arrow_alpha)  # readable on fire and snow alike
                cr.set_line_width(self.ARROW_OUTLINE * scale)
                cr.stroke()
                continue
            cr.scale(1, 0.5)  # a circle on the floor, seen isometrically
            radius = {'leader': self.LEADER_RADIUS, 'danger': self.LEADER_RADIUS, 'elite': self.ELITE_RADIUS}
            cr.arc(0, 0, radius.get(kind, self.RADIUS) * scale, 0, 2 * math.pi)
            cr.restore()
            fill = KIND_COLOURS['danger'] if kind == 'elite' else colour  # the pack's fill, the leader's outline
            cr.set_source_rgba(*fill, config.alpha * (self.DANGER_FILL if kind in ('danger', 'elite') else self.FILL))
            cr.fill_preserve()
            cr.set_source_rgba(*colour, config.alpha)
            cr.set_line_width((self.ELITE_LINE if kind == 'elite' else self.LINE) * scale)
            cr.stroke()


class PickerCard:
    """The KP_6 kind picker (macros/kindpick.py, the player 2026-10-20): a title, a row per kind in columns (the
    highlight's arrow, name, HUD word, metric, a tag: now / next game / coming), the highlighted row on a bar, and
    the keys' hint."""

    PAD, GAP, ROW_GAP, SLACK = 10, 14, 4, 4
    ARROW = '▶'
    HIGHLIGHT = (0.70, 0.61, 0.38, 0.30)  # CARD_BORDER, faint

    def _cell(self, text, tone, scale):
        return text_layout(_measuring_context(), render_markup([StyledLine(text, tone)]), scale)

    def _cells(self, row, scale):
        enabled, lit = bool(row.get('enabled')), bool(row.get('highlighted'))
        name_tone = Tone.METADATA if not enabled else Tone.VALUABLE if lit else Tone.DEFAULT
        tag = 'now' if row.get('current') else 'next game' if row.get('pending') else row.get('note') or ''
        return [
            (self.ARROW if lit else '', Tone.VALUABLE),
            (str(row.get('name') or ''), name_tone),
            (str(row.get('word') or ''), Tone.SET if enabled else Tone.METADATA),
            (str(row.get('metric') or ''), Tone.METADATA),
            (tag, Tone.SET if row.get('current') else Tone.METADATA),
        ]

    def _plan(self, payload, scale):
        """(title, rows of cells, column widths, row heights, hint) at `scale`; the text sizes measured once."""
        title = self._cell(str(payload.get('title') or ''), Tone.HEADING, scale).get_pixel_size()
        hint = self._cell(str(payload.get('hint') or ''), Tone.METADATA, scale).get_pixel_size()
        rows = [self._cells(row, scale) for row in payload.get('rows', [])]
        sizes = [[self._cell(text, tone, scale).get_pixel_size() if text else (0, 0) for text, tone in r] for r in rows]
        widths = [max((size[i][0] for size in sizes), default=0) for i in range(5)]
        heights = [max(h for _, h in size) for size in sizes]
        return title, rows, widths, heights, hint

    def measure(self, payload, scale, limit=None):
        pad, gap, row_gap, slack = self.PAD * scale, self.GAP * scale, self.ROW_GAP * scale, self.SLACK * scale
        title, _, widths, heights, hint = self._plan(payload, scale)
        columns = sum(w + slack + (gap if w else 0) for w in widths)  # as `draw` steps across
        width = max(title[0], hint[0], columns) + slack
        height = title[1] + hint[1] + sum(h + row_gap for h in heights) + 2 * row_gap
        return math.ceil(width + 2 * pad), math.ceil(height + 2 * pad)

    def draw(self, cr, width, height, payload, scale):
        pad, gap, row_gap, slack = self.PAD * scale, self.GAP * scale, self.ROW_GAP * scale, self.SLACK * scale
        title, rows, widths, heights, _ = self._plan(payload, scale)
        card_background(cr, width, height, scale)

        def show(text, tone, x, y):
            cr.move_to(x, y)
            PangoCairo.show_layout(cr, text_layout(cr, render_markup([StyledLine(text, tone)]), scale))

        show(str(payload.get('title') or ''), Tone.HEADING, pad, pad)
        y = pad + title[1] + row_gap
        for row, cells, row_height in zip(payload.get('rows', []), rows, heights, strict=True):
            if row.get('highlighted'):
                cr.rectangle(pad / 2, y - row_gap / 2, width - pad, row_height + row_gap)
                cr.set_source_rgba(*self.HIGHLIGHT)
                cr.fill()
            x = pad
            for (text, tone), column in zip(cells, widths, strict=True):
                if text:
                    show(text, tone, x, y)
                x += column + slack + (gap if column else 0)
            y += row_height + row_gap
        show(str(payload.get('hint') or ''), Tone.METADATA, pad, y + row_gap)


RENDERERS = {'guide': GuideCard(), 'text': TextCard(), 'ground': GroundMarks(), 'picker': PickerCard()}


def measure(widget, *, scale: float, limit: tuple[int, int] | None = None) -> tuple[int, int]:
    """Size at `scale`, fitting `limit` (the slot's free width/height) when the widget can wrap."""
    renderer = RENDERERS.get(widget.kind)
    return renderer.measure(widget.payload, scale, limit) if renderer else (0, 0)


def draw_scene(cr, boxes, *, scale: float, dimmed=(), dim_alpha: float = 1.0):
    """Widgets in the slots `dimmed` are drawn at `dim_alpha` of their own opacity."""
    for widget, (x, y, width, height) in boxes:
        renderer = RENDERERS.get(widget.kind)
        if renderer is None:
            continue
        faint = widget.slot in dimmed
        cr.save()
        try:
            cr.new_path()  # save/restore keeps the path: the last widget's pen position would join this one's shapes
            cr.translate(x, y)
            if faint:
                cr.push_group()
            try:
                renderer.draw(cr, width, height, widget.payload, scale)
            finally:
                if faint:
                    cr.pop_group_to_source()
                    cr.paint_with_alpha(dim_alpha)
        except Exception:  # one broken widget never blanks the rest of the HUD
            LOG.exception('HUD widget %s (%s) failed to draw', widget.id, widget.kind)
        finally:
            cr.restore()
