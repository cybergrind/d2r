"""Fight casts that waste the strike's time (the player, 2026-10-23: "try to push exp/hour more";
rca/2026-10-23/exp-casts-findings.md): Engorge aimed only at corpses no live unit stands on (casters.py
ENGORGE_CLEAR_AIM), and a pack's sigil kept while it covers half of what a new one would (SIGIL_KEEP_SHARE_ON).
Each switch off gives the old behaviour."""

from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock import casters
from inventory_tracking.builds.warlock.buffs import SIGIL_GAP
from inventory_tracking.builds.warlock.casters import ENGORGE_CLEAR, clear_corpses
from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.buffs import Buffs
from tests.inventory_tracking.builds.warlock.test_engorge import FULL, ROW, game
from tests.inventory_tracking.builds.warlock.test_pack_sigil import BUNCH, BY_ME, HERALD, Fight, hulk
from tests.inventory_tracking.macros.fakes import KEYS


@pytest.fixture(autouse=True)
def switched_on(monkeypatch):
    monkeypatch.setattr(casters, 'ENGORGE_CLEAR_AIM', True)
    monkeypatch.setattr(casters, 'SIGIL_KEEP_SHARE_ON', True)


# --- ENGORGE_CLEAR_AIM ---

# The character at (5000, 5000). The nearer corpse has a Gorebelly on it (1.1 off its feet, as the refused tries of
# the take 20261022T234119Z-68: a median 2.0); the further one lies clear.
CROWDED = (91, 5004.0, 5006.0)
CLEAR = (92, 5009.0, 4994.0)
ON_IT = Monster(30, 187, 2, 5004.5, 5007.0, 0xFFFFFFFF)


def engorge(play, corpses, over_crowded):
    """Engorge cast from the lazy row with these corpses, the record naming ON_IT while the pointer is on CROWDED
    (`over_crowded`, by its order of looks); (tried, the pointer moved, keys pressed, records read, corpses keyed)."""
    buffs, run = Buffs(ECHOING_STRIKE_BUILD), play.run()
    buffs.let_go = None
    run.corpses = lambda: corpses
    reads: list[int] = []

    def hovered():
        reads.append(1)
        return (1, ON_IT.unit_id) if over_crowded(len(reads)) else None

    run.hovered = hovered
    play.clock.now = 50.0
    before = play.keys.pointer()
    due = buffs.due(run, ROW, buffs.facts(run, play.world))
    assert due is not None
    tried = buffs.cast(run, due, lambda w, skills: dict(KEYS), 1.8)
    return tried, play.keys.pointer() != before, play.pressed(), len(reads)


def test_a_corpse_a_live_monster_stands_on_is_not_tried_the_clear_one_is():
    play = game(FULL, ON_IT)
    tried, moved, pressed, reads = engorge(play, (CROWDED, CLEAR), lambda n: False)
    assert (tried.cast, moved, pressed, reads) == (True, True, ['e'], 1)  # one look, at the clear corpse


def test_without_the_switch_the_crowded_corpse_is_tried_first_and_refused(monkeypatch):
    monkeypatch.setattr(casters, 'ENGORGE_CLEAR_AIM', False)
    play = game(FULL, ON_IT)
    tried, _, pressed, reads = engorge(play, (CROWDED, CLEAR), lambda n: n == 1)
    assert (tried.cast, pressed, reads) == (True, ['e'], 2)  # the refused look first


def test_with_every_corpse_crowded_nothing_is_touched():
    play = game(FULL, ON_IT)
    tried, moved, pressed, reads = engorge(play, (CROWDED,), lambda n: True)
    assert (tried.cast, tried.touched, moved, pressed, reads) == (False, False, False, [], 0)


def test_without_the_switch_a_crowded_corpse_moves_the_pointer_for_nothing(monkeypatch):
    monkeypatch.setattr(casters, 'ENGORGE_CLEAR_AIM', False)
    play = game(FULL, ON_IT)
    tried, moved, pressed, reads = engorge(play, (CROWDED,), lambda n: True)
    assert (tried.cast, tried.touched, moved, pressed, reads) == (False, True, True, [], 1)


def test_a_pet_in_danger_tries_the_clear_corpses_first_then_the_crowded():
    world = game(FULL, ON_IT).world
    far = (93, 5015.0, 5000.0)
    assert clear_corpses((CROWDED, far, CLEAR), world, (5000.0, 5000.0), set(), crowded_too=True) == [
        CLEAR,
        far,
        CROWDED,
    ]
    assert clear_corpses((CROWDED, far, CLEAR), world, (5000.0, 5000.0), set(), crowded_too=False) == [CLEAR, far]


def test_a_monster_lying_dead_now_and_one_further_than_the_clearance_do_not_crowd_a_corpse():
    killed = replace(ON_IT, unit_id=91)  # still in the look, a corpse now
    off = replace(ON_IT, unit_id=31, x=CROWDED[1] + ENGORGE_CLEAR + 0.1, y=CROWDED[2])
    world = replace(game(FULL).world, monsters=(FULL, killed, off))
    assert clear_corpses((CROWDED,), world, (5000.0, 5000.0), {91}, crowded_too=False) == [CROWDED]


# --- SIGIL_KEEP_SHARE_ON ---

# A pack of ten: the Herald alone, the bunch of five the sigil goes on, and four spread far from each other (no disc
# covers two of them).
SPREAD = tuple(hulk(40 + k, x, y) for k, (x, y) in enumerate(((4986, 5000), (5000, 4985), (4985, 4985), (4990, 5020))))


def walked(count):
    """The bunch with `count` of it gone to stand by the Herald."""
    by_herald = ((HERALD.x - 1.0, HERALD.y + 1.0), (HERALD.x + 1.0, HERALD.y - 1.0), (HERALD.x, HERALD.y + 1.5))
    by_herald += ((HERALD.x - 1.5, HERALD.y),)
    gone = tuple(replace(m, x=x, y=y) for m, (x, y) in zip(BUNCH[:count], by_herald, strict=False))
    return (*gone, *BUNCH[count:])


def test_a_sigil_holding_half_of_what_a_new_one_would_is_kept():
    fight = Fight(HERALD, *BUNCH, *SPREAD, *BY_ME)
    assert fight.look(100.0)  # on the bunch: 5 of 10
    fight.place(HERALD, *walked(2), *SPREAD, *BY_ME)  # it holds 3 of 10; the Herald's disc 2 + 2 (weight 4)
    assert fight.looks(100.1, 104.0) == []


def test_without_the_switch_a_disc_covering_one_more_lays_it_again(monkeypatch):
    monkeypatch.setattr(casters, 'SIGIL_KEEP_SHARE_ON', False)
    fight = Fight(HERALD, *BUNCH, *SPREAD, *BY_ME)
    assert fight.look(100.0)
    fight.place(HERALD, *walked(2), *SPREAD, *BY_ME)
    assert len(fight.looks(100.1, 100.0 + SIGIL_GAP + 0.6)) == 1


def test_a_sigil_the_pack_has_left_is_laid_again():
    fight = Fight(HERALD, *BUNCH, *SPREAD, *BY_ME)
    assert fight.look(100.0)
    fight.place(HERALD, *walked(4), *SPREAD, *BY_ME)  # it holds 1; the Herald's disc 2 + 4 (weight 6)
    laid = fight.looks(100.1, 100.0 + SIGIL_GAP + 0.6)
    assert len(laid) == 1
    assert laid[0] == pytest.approx((HERALD.x, HERALD.y), abs=2.5)
