"""FIGHT_CAST_OWN (macros/safety.py, 2026-10-24; rca/2026-10-24/cast-hold-findings.md): the bout's casts under the
strike wait by the bout's own horizon, a fight cast being as long as a strike, not by the Call to Arms' swap's 1.0 s.
The look of 10:58:55 (take 20261024T075622Z-106): a tier 5 Pit Lord pack (Cursed, Fire Enchanted, Extra Strong) at
11.7 units a second, the character at 2937 life under Amplify Damage."""

import pytest

from inventory_tracking.combat.harm import Hostile, Protection
from inventory_tracking.macros import safety as module


PIT_LORD, GRIZZLY = 361, 14
MINION, MODS = 16, (7, 9, 5)
HERE = (5647.5, 4297.5)
LIFE = 2937.0
# The take's resists at the look (physical under Amplify Damage), less Hell's penalty
PROTECTION = Protection(
    resists=(('physical', -82), ('fire', 88.0), ('lightning', 83.0), ('cold', 103.0), ('poison', 81.0)), level=96
)


def look() -> list[Hostile]:
    """The nearest of the look: a Grizzly 8.1 off and Pit Lord minions 8.6-17.5 off, as the take had them east."""
    found = [Hostile(1, GRIZZLY, (HERE[0] + 8.1, HERE[1]), 0, (5,), 0, level=85, speed=7.7)]
    for unit, away in enumerate((8.6, 13.4, 14.3, 15.3, 16.4, 16.5, 17.5), 2):
        found.append(Hostile(unit, PIT_LORD, (HERE[0] + away, HERE[1]), MINION, MODS, 5, level=85, speed=11.7))
    return found


def test_the_swaps_horizon_holds_and_the_bouts_does_not():
    assert module.cast_reach(look(), HERE, PROTECTION, LIFE, seconds=module.CAST_SECONDS) is not None
    assert module.cast_reach(look(), HERE, PROTECTION, LIFE, seconds=module.FIGHT_CAST_SECONDS) is None


@pytest.mark.parametrize(('own', 'seconds'), [(False, module.CAST_SECONDS), (True, module.FIGHT_CAST_SECONDS)])
def test_the_fight_casts_hold_asks_its_horizon(monkeypatch, own, seconds):
    monkeypatch.setattr(module, 'FIGHT_CAST_OWN', own)
    asked = []
    safety = module.Safety()
    monkeypatch.setattr(safety, 'cast_threat', lambda world, life, **kw: asked.append(kw['seconds']))
    safety.fight_cast_threat(object(), LIFE)  # type: ignore[arg-type]
    assert asked == [seconds]
