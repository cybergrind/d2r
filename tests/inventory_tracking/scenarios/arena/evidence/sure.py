"""For a test of something else than the fitted chances: a monster model in which every swing and
every shot takes life, as before the refit (combat/sim/monsters.py reads data/monsters_fit.json).

    sure(monkeypatch)

sets, until the test is over: no swing cut short, every whole swing on the character a blow, every
shot at the character and every missile under it a hit, every blow of the table's own roll (no
spread), no reach beyond the body's. What is left to chance is what the test is about; the rates
(swings and shots a second) stay the fitted ones.
"""

from typing import Any

from inventory_tracking.combat.sim.monsters import fitted


def sure(monkeypatch: Any, *, spread: bool = False, tail: bool = False, instant: bool = False) -> None:
    """Make every swing and shot land; `spread` and `tail` keep the fitted size of a blow and the
    fitted reach beyond the body's; `instant` has a missile arrive the frame after it is let go."""
    found = fitted()
    for row in (found['melee']['pooled'], *found['melee']['types'].values()):
        monkeypatch.setitem(row, 'takes_life', {**row['takes_life'], 'value': 1.0})
        monkeypatch.setitem(row, 'cut', {**row['cut'], 'value': 0.0})
    for row in (found['shots']['pooled'], *found['shots']['types'].values()):
        monkeypatch.setitem(row, 'takes_life', {**row['takes_life'], 'value': 1.0})
        monkeypatch.setitem(row, 'aim', {**row['aim'], 'value': 1.0})
        if instant:
            monkeypatch.setitem(row, 'speed', {**row['speed'], 'value': 1e9})
    if not spread:
        for part in ('melee', 'shots'):
            flat = {**found[part]['spread'], 'knots': [[0.0, 1.0], [1.0, 1.0]]}
            monkeypatch.setitem(found[part], 'spread', flat)
    if not tail:
        monkeypatch.setitem(found['reach'], 'tail', [])
