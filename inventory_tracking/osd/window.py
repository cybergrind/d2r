"""Wayland layer-shell window. Import GTK only when a window is requested."""

import ctypes
import math
import signal
import time

from inventory_tracking.common import LOG
from inventory_tracking.config import OSD
from inventory_tracking.osd.monitor import GameOutput, choose_monitor, place_mark
from inventory_tracking.presentation import StyledLine, render_markup


def load_toolkit():
    # Upstream requires layer-shell to load before libwayland-client/GTK.
    ctypes.CDLL('libgtk4-layer-shell.so.0')
    import gi

    gi.require_version('Gtk', '4.0')
    gi.require_version('Gdk', '4.0')
    gi.require_version('Gtk4LayerShell', '1.0')
    gi.require_foreign('cairo')
    import cairo
    from gi.repository import Gdk, Gio, GLib, Gtk, Gtk4LayerShell

    return Gtk, Gdk, Gio, GLib, Gtk4LayerShell, cairo


def apply_display(window, label, lines):
    """Unmap empty overlays so the compositor cannot retain the last alert."""
    if any(isinstance(line, StyledLine) for line in lines):
        label.set_markup(render_markup(line if isinstance(line, StyledLine) else StyledLine(line) for line in lines))
    else:
        label.set_text(' · '.join(lines))
    window.set_visible(bool(lines))


def parse_color(value):
    """'#rrggbb' → (r, g, b) in 0..1; anything else is a configuration error."""
    if len(value) != 7 or value[0] != '#':
        raise ValueError(f'Mark color must be #rrggbb, not {value!r}')
    return tuple(int(value[i : i + 2], 16) / 255 for i in (1, 3, 5))


def pulse(now, period):
    """0..1 triangle-ish sine pulse so the mark breathes instead of blinking off."""
    return 0.5 + 0.5 * math.sin(2 * math.pi * (now % period) / period)


def draw_mark(cr, size, mark, now):
    """A glowing rounded square outline filling `size` pixels, pulsing in alpha and width."""
    red, green, blue = parse_color(mark.color)
    level = pulse(now, mark.pulse_seconds)
    line = max(2.0, size * 0.06)
    inset = line * 1.6
    radius = size * 0.12
    x0, y0, x1, y1 = inset, inset, size - inset, size - inset
    cr.new_sub_path()
    cr.arc(x1 - radius, y0 + radius, radius, -math.pi / 2, 0)
    cr.arc(x1 - radius, y1 - radius, radius, 0, math.pi / 2)
    cr.arc(x0 + radius, y1 - radius, radius, math.pi / 2, math.pi)
    cr.arc(x0 + radius, y0 + radius, radius, math.pi, 3 * math.pi / 2)
    cr.close_path()
    cr.set_source_rgba(red, green, blue, 0.2 + 0.3 * level)
    cr.set_line_width(line * (2.0 + level))
    cr.stroke_preserve()
    cr.set_source_rgba(red, green, blue, 0.75 + 0.25 * level)
    cr.set_line_width(line)
    cr.stroke()


def show(render, config=OSD, *, demo=False, marks=None):
    """The inventory OSD label (centred) and the repair mark. Cards and the level guide are on the
    HUD canvas (inventory_tracking/hud); this window moves there in HUD Phase 3."""
    Gtk, Gdk, Gio, GLib, LayerShell, cairo = load_toolkit()
    app = Gtk.Application(application_id='local.d2r.InventoryOSD', flags=Gio.ApplicationFlags.NON_UNIQUE)
    failure = []

    def activate(application):
        if not LayerShell.is_supported():
            failure.append('Wayland layer-shell is unavailable; run from your Niri desktop terminal')
            application.quit()
            return
        window = Gtk.ApplicationWindow(application=application, title='D2R inventory OSD')
        window.set_decorated(False)
        window.set_resizable(False)
        window.set_focusable(False)
        LayerShell.init_for_window(window)
        LayerShell.set_namespace(window, 'd2r-inventory-osd')
        LayerShell.set_layer(window, LayerShell.Layer.OVERLAY)
        LayerShell.set_keyboard_mode(window, LayerShell.KeyboardMode.NONE)
        LayerShell.set_exclusive_zone(window, -1)
        # No edge anchors: the compositor centers the window on its output.
        for edge in (LayerShell.Edge.TOP, LayerShell.Edge.BOTTOM, LayerShell.Edge.LEFT, LayerShell.Edge.RIGHT):
            LayerShell.set_anchor(window, edge, False)
        monitors = Gdk.Display.get_default().get_monitors()
        if config.monitor is not None:
            if config.monitor >= monitors.get_n_items():
                failure.append(f'Monitor {config.monitor} does not exist ({monitors.get_n_items()} available)')
                application.quit()
                return
            LayerShell.set_monitor(window, monitors.get_item(config.monitor))
        label = Gtk.Label(xalign=0.5)
        game_output = GameOutput()
        label.set_margin_start(max(0, 2 * config.x))
        label.set_margin_end(max(0, -2 * config.x))
        # Transparent widget margins shift the label inside the centered window.
        # Twice the requested offset compensates for centering the whole window.
        label.set_margin_top(max(0, 2 * config.y))
        label.set_margin_bottom(max(0, -2 * config.y))
        label.set_selectable(False)
        window.set_child(label)
        marker = area = None
        shown_mark = [None]
        if marks is not None:
            # A second click-through surface anchored to the output's bottom-left corner; place_mark
            # moves it over the button from the game window's size (see design.md, repair mark).
            marker = Gtk.ApplicationWindow(application=application, title='D2R inventory OSD mark')
            marker.set_decorated(False)
            marker.set_resizable(False)
            marker.set_focusable(False)
            LayerShell.init_for_window(marker)
            LayerShell.set_namespace(marker, 'd2r-inventory-osd-mark')
            LayerShell.set_layer(marker, LayerShell.Layer.OVERLAY)
            LayerShell.set_keyboard_mode(marker, LayerShell.KeyboardMode.NONE)
            LayerShell.set_exclusive_zone(marker, -1)
            for edge in (LayerShell.Edge.TOP, LayerShell.Edge.RIGHT):
                LayerShell.set_anchor(marker, edge, False)
            for edge in (LayerShell.Edge.LEFT, LayerShell.Edge.BOTTOM):
                LayerShell.set_anchor(marker, edge, True)
            area = Gtk.DrawingArea()
            area.set_draw_func(
                lambda _area, cr, width, height: (
                    shown_mark[0] is not None and draw_mark(cr, min(width, height), shown_mark[0], time.monotonic())
                )
            )
            marker.set_child(area)
            marker.connect('realize', lambda *_: marker.get_surface().set_input_region(cairo.Region()))
        css = Gtk.CssProvider()
        css.load_from_string(f"""
            window {{ background: transparent; }}
            drawingarea {{ background: transparent; }}
            label {{ color: {config.color}; background: transparent;
                     border-radius: 6px; padding: 6px 10px;
                     font-family: {config.font_family}; font-size: {config.font_size}px;
                     font-weight: {config.font_weight}; }}
        """)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        def refresh():
            lines = render(now=time.monotonic())
            if demo:
                lines.insert(0, 'PREVIEW')
            apply_display(window, label, lines)
            surface = window.get_surface()
            if surface is not None:
                surface.set_input_region(cairo.Region())
            if marker is not None and area is not None and marks is not None:
                refresh_mark(marker, area, marks)
            return GLib.SOURCE_CONTINUE

        def refresh_mark(marker, area, marks):
            current = marks(now=time.monotonic())
            shown_mark[0] = None
            if current:
                output = game_output()
                monitor = choose_monitor(monitors, config.monitor, output if config.monitor is None else None)
                size = game_output.window_size
                if demo and (monitor is None or size is None) and monitors.get_n_items():
                    # Preview without a focused game: treat the first output as the game window.
                    monitor = monitors.get_item(0)
                    geometry = monitor.get_geometry()
                    size = (geometry.width, geometry.height)
                if monitor is not None and size is not None:
                    place_mark(marker, area, monitor, LayerShell, size, current[0])
                    shown_mark[0] = current[0]
            marker.set_visible(shown_mark[0] is not None)
            if shown_mark[0] is not None:
                area.queue_draw()
                surface = marker.get_surface()
                if surface is not None:
                    surface.set_input_region(cairo.Region())

        window.connect('realize', lambda *_: window.get_surface().set_input_region(cairo.Region()))
        refresh()
        GLib.timeout_add(max(1, round(config.refresh_interval * 1000)), refresh)
        LOG.info('OSD window ready; stop with Ctrl+C in the launching terminal')

    app.connect('activate', activate)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, lambda: app.quit() or GLib.SOURCE_REMOVE)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: app.quit() or GLib.SOURCE_REMOVE)
    code = app.run([])
    if failure:
        raise RuntimeError(failure[0])
    return code
