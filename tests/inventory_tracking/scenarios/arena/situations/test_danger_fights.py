"""The thirteen most dangerous fights beside the Fane (danger_fights.py; rca/2026-10-21/fane-death-sim-findings.md §9,
§10), played with every fix on over 20 seeds, late looks (lap 0.02): none loses a seed. Two lost seeds before §10 to
arena defects (a Slinger's throw raised by its stat 25 and its Herald tier; the swap set a Teleport staff in place of
the Call to Arms)."""

import pytest

from tests.inventory_tracking.scenarios.arena.situations.danger_fights import FIGHTS, played, stored
from tests.inventory_tracking.scenarios.arena.situations.fane_death import ALL_ON


TWENTY = tuple(range(1, 21))


def test_every_fight_carries_walls_the_cap_the_take_s_readings_and_the_call_to_arms():
    for name in FIGHTS:
        situation = stored(name)
        assert situation.scene.ground, name
        assert situation.capped, name
        assert situation.damage_percent is not None, name
        assert situation.aware == 35.0, name
        assert situation.orders is not None, name
        assert situation.scene.hero.sets[1].codes == ('cta',), name


@pytest.mark.slow
@pytest.mark.parametrize('name', sorted(FIGHTS))
def test_with_every_fix_on_no_seed_dies(name):
    plays = played(name, ALL_ON, TWENTY)
    assert not [play.seed for play in plays if play.dead], name
    assert sum(play.off_footing for play in plays) == 0, name
