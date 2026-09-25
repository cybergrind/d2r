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

    def __call__(self):
        now = self.clock()
        if 0 <= now - self.checked_at < 0.5:
            return self.output
        self.checked_at = now
        self.output = None
        try:
            window = self.read('focused-window')
            if not isinstance(window, dict) or window.get('app_id') != INPUT.game_app_id:
                return None
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


def place_assessment(window, label, monitor, layer_shell, font_size):
    window.set_visible(False)
    layer_shell.set_monitor(window, monitor)
    geometry = monitor.get_geometry()
    width = max(200, geometry.width // 2 - 40)
    label.set_size_request(width, -1)
    label.set_max_width_chars(max(20, int(width / (font_size * 0.65))))
    label.set_lines(max(5, int((geometry.height - 80) / (font_size * 1.5))))
