"""The strike's pointer off items' labels, one shift a look of the bout (LABEL_CLEAR_AIM).

The game casts at the unit under the pointer, so with an item's label there the blades would fly to the item
(hunt.py `off_labels`, 2026-10-12, Drifter Cavern). The pointer is tried LABEL_SHIFTS units along the line to the
focal point; along the line the blades keep their way (game/view.py).

`off_labels` tries all the shifts in one call, HOVER_SECONDS a look, with the bout's loop held for it, and tries
them all again at the next look while the label stays. Here each look of the bout tries one shift and returns:
the bout goes on between two (the prey's death, the next choice, the safety's step, the build's casts), and a
line under every shift of which a label lay is not tried again while it stays (`covered`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from inventory_tracking.combat.controller import REAIM_UNITS, Pixel
from inventory_tracking.combat.policy import MIN_FOCAL
from inventory_tracking.common import LOG
from inventory_tracking.game.layout import ITEM_UNIT
from inventory_tracking.game.view import Viewport
from inventory_tracking.macros.hunting.base import LABEL_SHIFTS


if TYPE_CHECKING:
    from inventory_tracking.macros.engine import Run
    from inventory_tracking.macros.travel import Point

# 2026-10-23: one shift a look of the bout, a covered line left as it is (rca/2026-10-23/label-aim-findings.md).
# Session 01:35-02:56 on 2026-10-23: 100 "under every aim" calls held the bout 0.88 s each (87.8 s), the prey died
# during 63 of them and its line was struck 42.6 s after the death; 32 were the same line again within 1.6 s. The
# blades after a covered line flew as after a clear one (median 18.1 against 18.4 degrees off the line, 523 against
# 20899 blades): the label of an item lying on the line turns no blade. False: hunt.py `off_labels`, as before.
LABEL_CLEAR_AIM = True
COVERED_UNITS = 2.0  # a covered line's focal point within this of a new one: the same line, not tried again


Line = tuple[int, 'Point', 'Point']  # (the prey, the focal point, the character's place)


def same_line(line: Line | None, unit: int, focal: Point, here: Point, within: float) -> bool:
    return line is not None and line[0] == unit and line[2] == here and math.dist(line[1], focal) <= within


@dataclass
class LabelLook:
    """The shifts tried for the line the pointer was put on while the hover names an item, one a look."""

    line: Line | None = None  # the line the shifts are tried for
    shift: int = 0  # index in LABEL_SHIFTS of the shift the pointer stands at
    put: Pixel | None = None  # where the last shift put the pointer
    tried: list[str] = field(default_factory=list)
    covered: Line | None = None  # the last line under every shift of which an item's label lay

    def look(
        self, run: Run, view: Viewport, here: Point, focal: Point, unit: int, over: tuple[int, int] | None
    ) -> bool:
        """A look at the standing pointer, `over` the unit under it: whether the pointer was moved to the next
        shift (the caller looks again HOVER_SECONDS later). False with no item under it, and on a covered line."""
        pointer = run.actuator.keys.pointer()
        going = same_line(self.line, unit, focal, here, REAIM_UNITS) and pointer == self.put
        if over is None or over[0] != ITEM_UNIT:
            if going and self.tried:
                LOG.info(
                    "Macro: an item's label under the aim at (%.1f, %.1f) (%s): the pointer %+.0f units along the "
                    'line instead',
                    *focal, ', '.join(self.tried), LABEL_SHIFTS[self.shift],
                )  # fmt: skip
            self.line, self.tried = None, []
            return False
        if same_line(self.covered, unit, focal, here, COVERED_UNITS):
            return False
        if not going:  # a new line, or the pointer put on it again since (the aim, a cast of the build's)
            self.line, self.shift, self.tried = (unit, focal, here), 0, []
        self.tried.append(f'{LABEL_SHIFTS[self.shift]:+.0f}: item {over[1]}')
        away = math.dist(here, focal)
        for index in range(self.shift + 1, len(LABEL_SHIFTS)):
            shift = LABEL_SHIFTS[index]
            if not shift or away + shift < MIN_FOCAL:
                continue
            share = (away + shift) / away
            where = view.aim(here, (here[0] + (focal[0] - here[0]) * share, here[1] + (focal[1] - here[1]) * share))
            if where is None:
                continue
            run.actuator.aim(*where, scatter=(2, 2))
            self.shift, self.put = index, run.actuator.keys.pointer()
            return True
        LOG.info(
            "Macro: an item's label under every aim along the line to (%.1f, %.1f): %s; the line is kept",
            *focal, ', '.join(self.tried),
        )  # fmt: skip
        self.covered, self.line, self.tried = self.line, None, []
        return False
