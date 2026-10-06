"""The canvas: one transparent, click-through layer-shell surface over the game's working area.

Anchored to all edges with exclusive zone 0, it covers exactly niri's workspace view, so niri's
window positions are canvas coordinates. It reads the scene every refresh, lays widgets out in
game-window slots, redraws only when the layout changes, and unmaps when there is nothing to
show (or the game is not focused), so a fullscreen game keeps direct scanout.
"""

import signal
import time

from inventory_tracking.common import LOG
from inventory_tracking.config import HUD, OSD
from inventory_tracking.hud.layout import Slot, game_rect, place, scale_for, slot_limit
from inventory_tracking.hud.live import Entrance, LiveUnits, follow, ground_payload_of
from inventory_tracking.hud.scene import read_scene
from inventory_tracking.hud.widgets import draw_scene, measure
from inventory_tracking.osd.monitor import GameOutput, choose_monitor
from inventory_tracking.osd.window import load_toolkit


def run(scene_dir, config=HUD, *, monitor_index=OSD.monitor):
    Gtk, Gdk, Gio, GLib, LayerShell, cairo = load_toolkit()
    app = Gtk.Application(application_id='local.d2r.Hud', flags=Gio.ApplicationFlags.NON_UNIQUE)
    slots = {
        name: Slot(slot.x, slot.y, slot.max_width, slot.centered, slot.upward) for name, slot in config.slots.items()
    }
    failure = []

    def activate(application):
        if not LayerShell.is_supported():
            failure.append('Wayland layer-shell is unavailable; run from your Niri desktop terminal')
            application.quit()
            return
        window = Gtk.ApplicationWindow(application=application, title='D2R HUD')
        window.set_decorated(False)
        window.set_focusable(False)
        LayerShell.init_for_window(window)
        LayerShell.set_namespace(window, 'd2r-hud')
        LayerShell.set_layer(window, LayerShell.Layer.OVERLAY)
        LayerShell.set_keyboard_mode(window, LayerShell.KeyboardMode.NONE)
        LayerShell.set_exclusive_zone(window, 0)
        for edge in (LayerShell.Edge.TOP, LayerShell.Edge.BOTTOM, LayerShell.Edge.LEFT, LayerShell.Edge.RIGHT):
            LayerShell.set_anchor(window, edge, True)
        area = Gtk.DrawingArea()
        window.set_child(area)
        css = Gtk.CssProvider()
        css.load_from_string('window, drawingarea { background: transparent; }')
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        monitors = Gdk.Display.get_default().get_monitors()
        game_output = GameOutput()
        state = {'boxes': [], 'scale': 1.0, 'key': None, 'monitor': None, 'ground': None}
        live, entrance = LiveUnits(), Entrance()
        area.set_draw_func(
            lambda _a, cr, _w, _h: draw_scene(cr, follow(state['boxes'], state['ground']), scale=state['scale'])
        )

        def follow_units(*_):
            """Every frame: the player and the marked monsters where they are now (hud/live.py)."""
            payload = ground_payload_of(state['boxes'])
            ground = live.locate(payload) if payload else None
            age = entrance.age(payload, time.monotonic())
            if age is not None and age < config.ground.arrow_seconds:  # the arrows are still moving out
                ground = {**(ground or payload), 'age': age}
            if ground != state['ground']:
                state['ground'] = ground
                area.queue_draw()
            return GLib.SOURCE_CONTINUE

        area.add_tick_callback(follow_units)

        def canvas_size(monitor):
            if area.get_width() > 0 and area.get_height() > 0:
                return area.get_width(), area.get_height()
            geometry = monitor.get_geometry()
            return geometry.width, geometry.height

        def refresh():
            widgets = read_scene(scene_dir, now=time.monotonic())
            boxes, scale = [], state['scale']
            if widgets:
                output = game_output()
                monitor = choose_monitor(monitors, monitor_index, output if monitor_index is None else None)
                if monitor is not None:
                    if monitor != state['monitor']:
                        window.set_visible(False)
                        LayerShell.set_monitor(window, monitor)
                        state['monitor'] = monitor
                    rect = game_rect(
                        canvas_size(monitor), window_size=game_output.window_size, position=game_output.window_position
                    )
                    if rect is not None:
                        scale = scale_for(rect.height, reference_height=config.reference_height)
                        sizes = {
                            w.id: measure(
                                w, scale=scale, limit=slot_limit(slots[w.slot], rect) if w.slot in slots else None
                            )
                            for w in widgets
                        }
                        boxes = place(widgets, sizes, slots, rect, gap=round(config.gap * scale))
            key = repr((boxes, scale))
            if key != state['key']:
                state.update(boxes=boxes, scale=scale, key=key)
                area.queue_draw()
            window.set_visible(bool(boxes))
            surface = window.get_surface()
            if surface is not None:
                surface.set_input_region(cairo.Region())
            return GLib.SOURCE_CONTINUE

        window.connect('realize', lambda *_: window.get_surface().set_input_region(cairo.Region()))
        refresh()
        GLib.timeout_add(max(1, round(config.refresh_interval * 1000)), refresh)
        LOG.info('HUD canvas ready for scene %s', scene_dir)

    app.connect('activate', activate)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, lambda: app.quit() or GLib.SOURCE_REMOVE)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: app.quit() or GLib.SOURCE_REMOVE)
    code = app.run([])
    if failure:
        raise RuntimeError(failure[0])
    return code
