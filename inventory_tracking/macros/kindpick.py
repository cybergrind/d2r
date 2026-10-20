"""The KP_6 kind picker (the player, 2026-10-20 ~19:25: "we are adding a lot of modes, probably we need to pop some
kind of dialogue to chose the mode on 3 clicks: shard act 4 as an entry").

Three KP_6 presses open it on the HUD (runner.py `_judge_loop_taps`): the loop's kinds, the one running marked, the
next one highlighted. While it is open one press moves the highlight, two choose the highlighted kind, three close it,
and PICK_SECONDS with no press close it with nothing changed. The entries are `loop_kinds()` then the announced kinds
not built yet (loop.py COMING), shown but not choosable: a kind registered later appears by itself.
Pure state: the runner keeps it under its lock and publishes `widgets()`.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from inventory_tracking.hud.payloads import picker_payload
from inventory_tracking.hud.scene import Widget
from inventory_tracking.macros.loop import Kind, coming_kinds, loop_kinds


PICK_SECONDS = 6.0  # no press for this long: closed, nothing changed
PICKER_TICK = 0.5  # republished this often while open: inside the HUD's lease (hud/scene.py LEASE_SECONDS)
PRODUCER = 'picker'  # the HUD scene's layer (appraisal/service.py) and the slot (config.HUD.slots)
COMING_NOTE = 'coming'
HINT = 'KP_6: next · twice: choose · 3 times: close'


@dataclass(frozen=True)
class Entry:
    """A row of the picker: a kind to choose, or one announced (`kind` None)."""

    key: str
    name: str
    word: str
    metric: str
    kind: Kind | None = None

    @property
    def enabled(self) -> bool:
        return self.kind is not None


def entries(offered: Mapping[str, Kind] | None = None) -> tuple[Entry, ...]:
    """The kinds offered (`loop_kinds()` by default) in their order, then the coming ones."""
    kinds = loop_kinds() if offered is None else offered
    chosen = tuple(Entry(kind.key, kind.name, kind.word, kind.metric, kind) for kind in kinds.values())
    return chosen + tuple(Entry(c.key, c.name, c.word, c.metric) for c in coming_kinds(kinds))


class KindPicker:
    """The open picker: its rows, the kind running (and the one asked from the next game), the highlight, the clock of
    its last press."""

    def __init__(self, rows: tuple[Entry, ...], current: Kind, now: float, *, pending: Kind | None = None) -> None:
        if not any(row.enabled for row in rows):
            raise ValueError('a picker needs a kind to choose')
        self.rows, self.current, self.pending = rows, current, pending
        self.pressed = now
        here = next((i for i, row in enumerate(rows) if row.kind == current), len(rows) - 1)
        self.highlight = self._after(here)  # the next kind: two presses once open make the old cycle's switch

    def _after(self, index: int) -> int:
        """The next choosable row after `index`, round the end (the coming rows are skipped)."""
        count = len(self.rows)
        return next(i % count for i in range(index + 1, index + 1 + count) if self.rows[i % count].enabled)

    @property
    def highlighted(self) -> Entry:
        return self.rows[self.highlight]

    def move(self, now: float) -> Entry:
        self.highlight, self.pressed = self._after(self.highlight), now
        return self.highlighted

    def touch(self, now: float) -> None:
        """A press that changed nothing still keeps it open."""
        self.pressed = now

    def expired(self, now: float) -> bool:
        return now - self.pressed >= PICK_SECONDS

    def widgets(self, now: float) -> list[Widget]:
        rows = [
            {
                'name': row.name,
                'word': row.word,
                'metric': row.metric,
                'current': row.kind is not None and row.kind == self.current,
                'pending': row.kind is not None and row.kind == self.pending,
                'highlighted': index == self.highlight,
                'enabled': row.enabled,
                'note': '' if row.enabled else COMING_NOTE,
            }
            for index, row in enumerate(self.rows)
        ]
        left = max(0, PICK_SECONDS - (now - self.pressed))
        payload = picker_payload('Loop kind', rows, f'{HINT} · {left:.0f} s')
        return [Widget(PRODUCER, 'picker', PRODUCER, payload)]
