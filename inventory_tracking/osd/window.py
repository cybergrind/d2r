"""Wayland layer-shell window. Import GTK only when a window is requested."""

import ctypes
import signal
import time

from inventory_tracking.common import LOG
from inventory_tracking.config import OSD
from inventory_tracking.osd.monitor import GameOutput, choose_monitor, place_assessment
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


def apply_display(window, label, lines, *, multiline=False):
    """Unmap empty overlays so the compositor cannot retain the last alert."""
    if any(isinstance(line, StyledLine) for line in lines):
        label.set_markup(render_markup(line if isinstance(line, StyledLine) else StyledLine(line) for line in lines))
    else:
        label.set_text(('\n' if multiline else ' · ').join(lines))
    window.set_visible(bool(lines))


def show(render, config=OSD, *, demo=False, assessment=False):
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
        LayerShell.set_namespace(window, 'd2r-appraisal-osd' if assessment else 'd2r-inventory-osd')
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
        label = Gtk.Label(xalign=0 if assessment else 0.5)
        game_output = GameOutput()
        assessment_monitor = None
        if assessment:
            # Center a half-output-wide card in the right half, vertically centered.
            LayerShell.set_anchor(window, LayerShell.Edge.RIGHT, True)
            label.set_wrap(True)
            LayerShell.set_margin(window, LayerShell.Edge.RIGHT, 10)
            # Long assessments remain bounded and explicitly ellipsized.
            from gi.repository import Pango

            label.set_ellipsize(Pango.EllipsizeMode.END)
        # Transparent widget margins shift the label inside the centered window.
        # Twice the requested offset compensates for centering the whole window.
        label.set_margin_start(max(0, 2 * config.x))
        label.set_margin_end(max(0, -2 * config.x))
        label.set_margin_top(max(0, 2 * config.y))
        label.set_margin_bottom(max(0, -2 * config.y))
        label.set_selectable(False)
        window.set_child(label)
        css = Gtk.CssProvider()
        background = 'rgba(15, 15, 20, 0.88)' if assessment else 'transparent'
        css.load_from_string(f"""
            window {{ background: transparent; }}
            label {{ color: {config.color}; background: {background};
                     border-radius: 6px; padding: 6px 10px;
                     font-family: {config.font_family}; font-size: {config.font_size}px;
                     font-weight: {config.font_weight}; }}
        """)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        def refresh():
            nonlocal assessment_monitor
            lines = render(now=time.monotonic())
            if demo:
                lines.insert(0, 'PREVIEW')
            if assessment and lines:
                monitor = choose_monitor(monitors, config.monitor, game_output() if config.monitor is None else None)
                if monitor is None:
                    lines = []
                    assessment_monitor = None
                elif monitor != assessment_monitor:
                    place_assessment(window, label, monitor, LayerShell, config.font_size)
                    assessment_monitor = monitor
            apply_display(window, label, lines, multiline=assessment)
            surface = window.get_surface()
            if surface is not None:
                surface.set_input_region(cairo.Region())
            return GLib.SOURCE_CONTINUE

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
