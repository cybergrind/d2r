"""The canvas: one transparent, click-through layer-shell surface over the game's working area.

Anchored to all edges (exclusive zone 0), it covers niri's workspace view, so niri's window positions are canvas
coordinates. Each refresh it reads the scene, lays widgets out in game-window slots, redraws only on a layout change,
and unmaps when empty, so a fullscreen game keeps direct scanout. `desktop_slots` get a second surface on
`desktop_output`, shown whatever has the focus (no such output: this canvas). Open item panels dim `dim_slots`;
controller mode swaps in `controller_slots` (hud/live.py).
"""

import signal
import time
from typing import Any

from inventory_tracking.common import LOG
from inventory_tracking.config import HUD, OSD
from inventory_tracking.hud.dots import LiveDots
from inventory_tracking.hud.layout import Slot, desktop_rect, game_rect, place, scale_for, slot_limit
from inventory_tracking.hud.live import (
    Entrance,
    InputModeByte,
    LiveUnits,
    OpenPanels,
    follow,
    ground_payload_of,
    map_card_of,
    mode_source,
    panel_source,
)
from inventory_tracking.hud.scene import read_scene
from inventory_tracking.hud.widgets import draw_scene, measure
from inventory_tracking.osd.monitor import FocusedOutput, GameOutput, choose_monitor
from inventory_tracking.osd.window import load_toolkit


# Seconds between redraws for the monster dots alone (hud/dots.py): a map card redraw costs ~4.5 ms, and the dots
# move every frame in a fight; the player's own move still redraws every frame.
DOT_REDRAW = 0.05


def run(scene_dir, config=HUD, *, monitor_index=OSD.monitor):
    Gtk, Gdk, Gio, GLib, LayerShell, cairo = load_toolkit()
    app = Gtk.Application(application_id='local.d2r.Hud', flags=Gio.ApplicationFlags.NON_UNIQUE)
    slots = {
        name: Slot(slot.x, slot.y, slot.max_width, slot.centered, slot.upward) for name, slot in config.slots.items()
    }
    controller_slots = slots | {
        name: Slot(slot.x, slot.y, slot.max_width, slot.centered, slot.upward)
        for name, slot in config.controller_slots.items()
    }
    failure = []

    def activate(application):
        if not LayerShell.is_supported():
            failure.append('Wayland layer-shell is unavailable; run from your Niri desktop terminal')
            application.quit()
            return

        def overlay(title, namespace):
            """A click-through layer-shell surface over one output's working area, and its drawing area."""
            surface_window = Gtk.ApplicationWindow(application=application, title=title)
            surface_window.set_decorated(False)
            surface_window.set_focusable(False)
            LayerShell.init_for_window(surface_window)
            LayerShell.set_namespace(surface_window, namespace)
            LayerShell.set_layer(surface_window, LayerShell.Layer.OVERLAY)
            LayerShell.set_keyboard_mode(surface_window, LayerShell.KeyboardMode.NONE)
            LayerShell.set_exclusive_zone(surface_window, 0)
            for edge in (LayerShell.Edge.TOP, LayerShell.Edge.BOTTOM, LayerShell.Edge.LEFT, LayerShell.Edge.RIGHT):
                LayerShell.set_anchor(surface_window, edge, True)
            drawing = Gtk.DrawingArea()
            surface_window.set_child(drawing)
            surface_window.connect('realize', lambda *_: surface_window.get_surface().set_input_region(cairo.Region()))
            return surface_window, drawing

        window, area = overlay('D2R HUD', 'd2r-hud')
        # The desktop slots' own surface on `desktop_output` (the game's canvas is bound to its output).
        desk_window, desk_area = overlay('D2R HUD desktop', 'd2r-hud-desktop')
        desk: dict[str, Any] = {'boxes': [], 'scale': 1.0, 'key': None, 'monitor': None}
        desk_area.set_draw_func(lambda _a, cr, _w, _h: draw_scene(cr, desk['boxes'], scale=desk['scale']))
        css = Gtk.CssProvider()
        css.load_from_string('window, drawingarea { background: transparent; }')
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        monitors = Gdk.Display.get_default().get_monitors()
        game_output, desktop_output = GameOutput(), FocusedOutput()
        state: dict[str, Any] = {'boxes': [], 'scale': 1.0, 'key': None, 'monitor': None, 'ground': None}
        state.update(panels=None, dim=False, moved=None, drawn=0.0)
        live, entrance, panels = LiveUnits(), Entrance(), OpenPanels(config.dim_panels)
        dots = LiveDots()
        input_mode = InputModeByte()

        def draw(_a, cr, _w, _h):
            started = time.perf_counter()
            draw_scene(
                cr,
                follow(state['boxes'], state['ground'], state['moved']),
                scale=state['scale'],
                dimmed=config.dim_slots if state['dim'] else (),
                dim_alpha=config.dim_alpha,
            )
            dots.stats.drew(time.monotonic(), 1000 * (time.perf_counter() - started))

        area.set_draw_func(draw)

        def follow_units(*_):
            """Every frame: the player and every monster dot where they are now (hud/live.py, hud/dots.py)."""
            now = time.monotonic()
            payload = ground_payload_of(state['boxes'])
            ground = live.locate(payload) if payload else None
            age = entrance.age(payload, now)
            if payload is not None and age is not None and age < config.ground.arrow_seconds:
                ground = {**(ground or payload), 'age': age}  # the arrows are still moving out
            moved = dots.frame(map_card_of(state['boxes']), payload, now)
            dim = panels.reading(state['panels'])
            if ground != state['ground'] or dim != state['dim']:
                state.update(ground=ground, dim=dim, moved=moved, drawn=now)
                area.queue_draw()
            elif moved != state['moved'] and now - state['drawn'] >= DOT_REDRAW:
                state.update(moved=moved, drawn=now)
                area.queue_draw()
            return GLib.SOURCE_CONTINUE

        area.add_tick_callback(follow_units)

        def canvas_size(monitor, drawing=area):
            if drawing.get_width() > 0 and drawing.get_height() > 0:
                return drawing.get_width(), drawing.get_height()
            geometry = monitor.get_geometry()
            return geometry.width, geometry.height

        def lay_out(widgets, rect, chosen=slots):
            scale = scale_for(rect.height, reference_height=config.reference_height)
            sizes = {
                w.id: measure(w, scale=scale, limit=slot_limit(chosen[w.slot], rect) if w.slot in chosen else None)
                for w in widgets
            }
            return place(widgets, sizes, chosen, rect, gap=round(config.gap * scale)), scale

        def refresh_desktop(widgets, monitor):
            """The desktop slots on their own output, whatever has the focus."""
            boxes, scale = [], desk['scale']
            if widgets:
                if monitor != desk['monitor']:
                    desk_window.set_visible(False)
                    LayerShell.set_monitor(desk_window, monitor)
                    desk['monitor'] = monitor
                boxes, scale = lay_out(widgets, desktop_rect(canvas_size(monitor, desk_area)))
            key = repr((boxes, scale))
            if key != desk['key']:
                desk.update(boxes=boxes, scale=scale, key=key)
                desk_area.queue_draw()
            desk_window.set_visible(bool(boxes))
            surface = desk_window.get_surface()
            if surface is not None:
                surface.set_input_region(cairo.Region())

        def refresh():
            scene = read_scene(scene_dir, now=time.monotonic())
            chosen = controller_slots if input_mode.reading(mode_source(scene)) else slots
            state['panels'], widgets = panel_source(scene)
            # With `desktop_output` connected its slots are drawn there only; without it (laptop
            # panel off) they fall back to this canvas.
            desk_monitor = choose_monitor(monitors, None, config.desktop_output)

            def on_desk(w):
                return desk_monitor is not None and w.slot in config.desktop_slots

            refresh_desktop([w for w in widgets if on_desk(w)], desk_monitor)
            widgets = [w for w in widgets if not on_desk(w)]
            boxes, scale = [], state['scale']
            if widgets:
                output = game_output()
                if not game_output.focused:
                    # Without the game only the desktop slots show. They stay on the output the
                    # canvas is on (moving it remaps the surface, which flickers as the focus moves
                    # between outputs); a canvas not placed yet takes the focused output.
                    widgets = [w for w in widgets if w.slot in config.desktop_slots]
                    output = desktop_output() if widgets and state['monitor'] is None else None
                monitor = choose_monitor(monitors, monitor_index, output if monitor_index is None else None)
                if monitor is None and widgets and not game_output.focused:
                    monitor = state['monitor']
                if monitor is not None:
                    if monitor != state['monitor']:
                        window.set_visible(False)
                        LayerShell.set_monitor(window, monitor)
                        state['monitor'] = monitor
                    rect = (
                        game_rect(
                            canvas_size(monitor),
                            window_size=game_output.window_size,
                            position=game_output.window_position,
                        )
                        if game_output.focused
                        else desktop_rect(canvas_size(monitor))
                    )
                    if rect is not None:
                        boxes, scale = lay_out(widgets, rect, chosen if game_output.focused else slots)
            key = repr((boxes, scale))
            if key != state['key']:
                state.update(boxes=boxes, scale=scale, key=key)
                area.queue_draw()
            window.set_visible(bool(boxes))
            surface = window.get_surface()
            if surface is not None:
                surface.set_input_region(cairo.Region())
            return GLib.SOURCE_CONTINUE

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
