"""Vector direction arrows (drawn by the HUD guide card); shapes do not depend on the desktop font."""

import math


ARROWS = ('→', '↗', '↑', '↖', '←', '↙', '↓', '↘')
# Logical pixels (260x180 x1.5, user 2026-10-02); a level is scaled to fit, down to level_map.WHOLE_SCALE.
MAP_SIZE = (390, 270)


def arrow_polygon(glyph, width, height):
    """Seven-vertex filled arrow, rotated in screen space and inset from its box."""
    angle = -ARROWS.index(glyph) * math.pi / 4
    scale = min(width, height) * 0.36
    vertices = ((-1, -0.22), (0.15, -0.22), (0.15, -0.65), (1, 0), (0.15, 0.65), (0.15, 0.22), (-1, 0.22))
    return tuple(
        (
            width / 2 + scale * (x * math.cos(angle) - y * math.sin(angle)),
            height / 2 + scale * (x * math.sin(angle) + y * math.cos(angle)),
        )
        for x, y in vertices
    )


ARROW_COLOUR = (0.93, 0.79, 0.40)


def draw_arrow(cr, width, height, glyph, colour=ARROW_COLOUR):
    points = arrow_polygon(glyph, width, height)
    cr.move_to(*points[0])
    for point in points[1:]:
        cr.line_to(*point)
    cr.close_path()
    cr.set_source_rgba(*colour, 1)
    cr.fill_preserve()
    cr.set_source_rgba(*(0.5 + c / 2 for c in colour), 1)  # lighter outline
    cr.set_line_width(1.5)
    cr.stroke()


def draw_indicator(cr, width, height, glyph, colour=ARROW_COLOUR):
    """Framed direction tile; None marks arrival without suggesting further travel."""
    cr.save()
    cr.rectangle(1, 1, width - 2, height - 2)
    cr.set_source_rgba(0.025, 0.03, 0.04, 0.96)
    cr.fill_preserve()
    cr.set_source_rgba(*colour, 0.65)
    cr.set_line_width(1.5)
    cr.stroke()
    if glyph is None:
        cr.arc(width / 2, height / 2, min(width, height) * 0.12, 0, 2 * math.pi)
        cr.set_source_rgba(*colour, 1)
        cr.fill()
    else:
        draw_arrow(cr, width, height, glyph, colour)
    cr.restore()
