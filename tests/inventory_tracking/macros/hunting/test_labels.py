"""The strike's pointer off items' labels, one shift a look (hunting/labels.py, LABEL_CLEAR_AIM).

Session of 2026-10-23 01:35-02:56 (rca/2026-10-23/label-aim-findings.md): the old `off_labels` held the bout 0.88 s
a call through all its shifts and tried them all again at the next look while the label stayed.
"""

import pytest

from inventory_tracking.game.layout import ITEM_UNIT
from inventory_tracking.game.view import Viewport
from inventory_tracking.macros import hunt as hunt_module
from inventory_tracking.macros.hunting.base import LABEL_SHIFTS
from inventory_tracking.macros.hunting.labels import LabelLook
from tests.inventory_tracking.macros.test_hunt import attack_mode, foe, game, hunter


ASPECT = 2560 / 1418
HERE, FOCAL = (5000.0, 5000.0), (5012.0, 5000.0)
ITEM = (ITEM_UNIT, 77)


class Keys:
    def __init__(self) -> None:
        self.at: tuple[float, float] | None = (0.5, 0.5)

    def pointer(self) -> tuple[float, float] | None:
        return self.at


class Actuator:
    def __init__(self) -> None:
        self.keys = Keys()
        self.aims: list[tuple[float, float]] = []

    def aim(self, x: float, y: float, scatter: tuple[int, int] = (0, 0)) -> None:
        self.aims.append((x, y))
        self.keys.at = (x, y)


class Run:
    """No pace: a look that slept would fail here."""

    def __init__(self) -> None:
        self.actuator = Actuator()


def looks(label: LabelLook, run: Run, over, *, unit: int = 10, focal=FOCAL) -> bool:
    return label.look(run, Viewport(ASPECT), HERE, focal, unit, over)  # pyrefly: ignore[bad-argument-type]


def test_a_look_moves_the_pointer_one_shift_along_the_line_and_returns():
    run, label = Run(), LabelLook()
    assert looks(label, run, ITEM)
    assert len(run.actuator.aims) == 1  # one shift, the bout goes on before the next
    assert looks(label, run, ITEM)
    assert len(run.actuator.aims) == 2
    view = Viewport(ASPECT)
    first, second = (view.world(HERE, *where) for where in run.actuator.aims)
    assert second[0] > first[0] > FOCAL[0]  # along the line, further out each time
    assert abs(first[1] - HERE[1]) < 0.5
    assert abs(second[1] - HERE[1]) < 0.5


def test_the_label_gone_says_the_shift_kept(caplog):
    run, label = Run(), LabelLook()
    assert looks(label, run, ITEM)
    with caplog.at_level('INFO'):
        assert not looks(label, run, (0, 0))
    assert f'label under the aim at (5012.0, 5000.0) (+0: item 77): the pointer {LABEL_SHIFTS[1]:+.0f}' in caplog.text


def test_a_line_under_every_shift_is_kept_and_not_tried_again(caplog):
    run, label = Run(), LabelLook()
    with caplog.at_level('INFO'):
        while looks(label, run, ITEM):
            pass
    shifts = len(run.actuator.aims)
    assert shifts == len(LABEL_SHIFTS) - 1
    assert caplog.text.count('under every aim along the line to (5012.0, 5000.0)') == 1
    # The next looks at the same line, the focal point a little on: nothing moved
    assert not looks(label, run, ITEM, focal=(5012.5, 5000.5))
    assert len(run.actuator.aims) == shifts
    # Another prey's line is tried
    assert looks(label, run, ITEM, unit=11)


def test_the_pointer_put_again_starts_the_shifts_over():
    run, label = Run(), LabelLook()
    assert looks(label, run, ITEM)
    assert looks(label, run, ITEM)
    run.actuator.keys.at = (0.5, 0.5)  # a cast of the build's, then the aim put it on the focal point again
    assert looks(label, run, ITEM)
    assert label.shift == 1
    assert label.tried == ['+0: item 77']


@pytest.mark.parametrize('clear_aim', [False, True])
def test_a_label_under_every_aim_holds_the_bout_once(monkeypatch, caplog, clear_aim):
    # 02:54:07-12 on 2026-10-23 (take 20261022T235241Z-54): an item's label under every shift along the line; the
    # old way tried them all again at every look, the bout held 0.9 s each time.
    monkeypatch.setattr(hunt_module, 'LABEL_CLEAR_AIM', clear_aim)
    play = game(foe(10, 5008.0, 5000.0, life=90, max_life=90))
    play.toughness[10] = 12
    play.unit_under_pointer = lambda: ITEM  # pyrefly: ignore[missing-attribute]
    with caplog.at_level('INFO'):
        attack_mode(play, hunter(play), until=6.0)
    every = caplog.text.count("an item's label under every aim along the line")
    struck = [unit for unit, _ in play.strikes]
    assert struck  # the strike goes on along the line either way
    assert set(struck) == {10}
    if clear_aim:
        assert every == 1
    else:
        assert every > 1
    assert all(abs(at[1] - 5000.0) < 1.5 and at[0] > 5000.0 for _, at in play.strikes)
