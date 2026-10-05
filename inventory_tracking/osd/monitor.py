"""Resolve the game's Niri workspace to a GDK connector, independent of monitor order."""

import json
import subprocess
import time

from inventory_tracking.config import INPUT


class GameOutput:
    def __init__(self, *, query=subprocess.check_output, clock=time.monotonic):
        self.query, self.clock = query, clock
        self.checked_at = -float('inf')
        self.output: str | None = None
        self.focused = False
        self.window_size: tuple[int, int] | None = None
        # Workspace-view position of the game's visual geometry; niri reports it for floating
        # windows only (tiled ones have tile_pos_in_workspace_view = null).
        self.window_position: tuple[float, float] | None = None

    def __call__(self):
        now = self.clock()
        if 0 <= now - self.checked_at < 0.5:
            return self.output
        self.checked_at = now
        self.output = self.window_size = self.window_position = None
        self.focused = False
        try:
            window = self.read('focused-window')
            if not isinstance(window, dict) or window.get('app_id') != INPUT.game_app_id:
                return None
            self.focused = True
            layout = window.get('layout') or {}
            size = layout.get('window_size')
            if isinstance(size, list) and len(size) == 2 and all(type(v) is int and v > 0 for v in size):
                self.window_size = (size[0], size[1])
            tile, offset = layout.get('tile_pos_in_workspace_view'), layout.get('window_offset_in_tile') or [0, 0]
            if isinstance(tile, list) and len(tile) == 2 and isinstance(offset, list) and len(offset) == 2:
                self.window_position = (float(tile[0]) + float(offset[0]), float(tile[1]) + float(offset[1]))
            workspace_id = window.get('workspace_id')
            workspaces = self.read('workspaces')
            if workspace_id is not None and isinstance(workspaces, list):
                for workspace in workspaces:
                    if isinstance(workspace, dict) and workspace.get('id') == workspace_id:
                        name = workspace.get('output')
                        self.output = name if isinstance(name, str) and name else None
                        break
        except OSError, ValueError, subprocess.SubprocessError:
            pass
        return self.output

    def read(self, command):
        return json.loads(self.query(['niri', 'msg', '--json', command], timeout=INPUT.focus_timeout, text=True))


def choose_monitor(monitors, index, output):
    if index is not None:
        return monitors.get_item(index) if 0 <= index < monitors.get_n_items() else None
    if output is not None:
        for position in range(monitors.get_n_items()):
            monitor = monitors.get_item(position)
            if monitor.get_connector() == output:
                return monitor
    return None


def place_mark(window, area, monitor, layer_shell, window_size, mark):
    """Anchor the highlight to the output's bottom-left corner, where a tiled game window under a top bar sits.

    Mark units are fractions of the game window height; the returned pixel square is what was requested.
    """
    _, height = window_size
    size = max(8, round(mark.size * height))
    left = round(mark.center_x * height - size / 2)
    bottom = round(mark.center_y * height - size / 2)
    layer_shell.set_monitor(window, monitor)
    layer_shell.set_margin(window, layer_shell.Edge.LEFT, max(0, left))
    layer_shell.set_margin(window, layer_shell.Edge.BOTTOM, max(0, bottom))
    area.set_size_request(size, size)
    window.set_default_size(size, size)
    return size
