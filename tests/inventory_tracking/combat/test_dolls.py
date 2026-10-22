"""The exploding monsters' model (combat/threats/dolls.py; rca/2026-10-21/dolls-tz-findings.md F0-F3)."""

import csv
import math
from dataclasses import dataclass

import pytest

from inventory_tracking.combat import harm
from inventory_tracking.combat.threats import dolls


@dataclass(frozen=True)
class Doll:
    at: tuple[float, float]
    txt: int = 216
    mode: int = 1
    modifiers: tuple[int, ...] = ()


def test_f0_the_exploding_types_are_monstats_death_damage_rows() -> None:
    # The study's list: the undead fetishes 212-216, 690, 691, the siege beasts 441-444, the windows, the Baal clone
    assert dolls.exploding() == frozenset((212, 213, 214, 215, 216, 392, 393, 441, 442, 443, 444, 570, 690, 691))
    assert dolls.exploding() == harm.EXPLODING  # the corpse bar reads the same table
    assert dolls.runners() == frozenset((212, 213, 214, 215, 216, 690, 691))  # AI Fetish: the undead fetishes
    assert 141 not in dolls.exploding()  # the living Stygian Doll (fetish1) has no deathDmg


def test_f0_the_bundled_table_matches_the_installed_game() -> None:
    if not dolls.MONSTATS.exists():
        pytest.skip('pricing/raw is git-ignored: no installed monstats.txt here')
    with dolls.MONSTATS.open(encoding='utf-8', errors='replace', newline='') as handle:
        found = {
            int(row['*hcIdx'])
            for row in csv.DictReader(handle, delimiter='\t')
            if row.get('deathDmg') not in (None, '', '0')
        }
    assert found == dolls.exploding()


def test_f2_a_doll_bars_a_landing_within_16_and_20_under_extra_fast() -> None:
    here = (0.0, 0.0)
    assert dolls.barring(here, (30.0, 0.0), [Doll((30.0, 15.0))], 0.0) == pytest.approx((15.0, 16.0))
    assert dolls.barring(here, (30.0, 0.0), [Doll((30.0, 17.0))], 0.0) is None
    fast = Doll((30.0, 17.0), modifiers=(6,))
    assert dolls.barring(here, (30.0, 0.0), [fast], 0.0) == pytest.approx((17.0, 20.0))
    dead = Doll((30.0, 1.0), mode=12)
    assert dolls.barring(here, (30.0, 0.0), [dead], 0.0) is None
    siege = Doll((30.0, 1.0), txt=441)  # exploding, but no runner: the corpse bar alone
    assert dolls.barring(here, (30.0, 0.0), [siege], 0.0) is None


def test_f2_the_run_in_over_the_hops_time_counts() -> None:
    """A doll 30 behind the landing's way runs at the character while the hop is made: where it stands at the landing
    bars it, not where it stood."""
    here, spot = (0.0, 0.0), (20.0, 0.0)
    doll = Doll((50.0, 0.0))  # 30 beyond the landing, on the line
    assert dolls.barring(here, spot, [doll], 0.0) is None
    found = dolls.barring(here, spot, [doll], 1.0)  # 15.5 units nearer
    assert found is not None
    assert found[0] == pytest.approx(30.0 - 15.5)


def test_f3_dolls_in_reach_and_not_on_the_character_go_first(monkeypatch) -> None:
    monkeypatch.setattr(dolls, 'DOLL_FIRST', True)  # off by default (dolls.py)
    foes = {1: Doll((3.0, 0.0)), 2: Doll((12.0, 0.0)), 3: Doll((8.0, 0.0)), 4: Doll((5.0, 0.0), txt=133)}
    assert dolls.first_struck((0.0, 0.0), foes, [1, 2, 3, 4]) == [3, 2]  # nearest first, the one at 3 is on us
    assert dolls.first_struck((0.0, 0.0), foes, [1, 4]) == []


def test_each_switch_off_restores_the_old_rules(monkeypatch) -> None:
    monkeypatch.setattr(dolls, 'DOLL_FIRST', False)
    assert dolls.first_struck((0.0, 0.0), {2: Doll((12.0, 0.0))}, [2]) == []
    monkeypatch.setattr(dolls, 'DOLL_GUARD', False)
    assert dolls.guards((10.0, 0.0), (0.0, 0.0), [Doll((12.0, 0.0))]) == []
    monkeypatch.setattr(dolls, 'DOLL_GUARD', True)
    assert len(dolls.guards((10.0, 0.0), (0.0, 0.0), [Doll((29.0, 0.0))])) == 1  # 19 from the drop
    assert dolls.guards((10.0, 0.0), (0.0, 0.0), [Doll((31.0, 0.0))]) == []


@dataclass(frozen=True)
class Marked:
    unit_id: int
    at: tuple[float, float]
    txt: int = 216
    mode: int = 1


def test_bait_is_off_by_default_and_picks_the_far_packs_middle_when_on(monkeypatch) -> None:
    pack = [Marked(1, (20.0, 0.0)), Marked(2, (22.0, 1.0)), Marked(3, (21.0, -1.0)), Marked(4, (12.0, 9.0))]
    near = Marked(5, (4.0, 0.0))  # on the character already: never the bait
    args = ((0.0, 0.0), [*pack, near], 8.0, lambda m: False, lambda m: 0)
    assert dolls.bait_target(*args) is None
    monkeypatch.setattr(dolls, 'DOLL_BAIT', True)
    chosen = dolls.bait_target(*args)
    assert chosen is not None
    assert chosen.unit_id in (1, 2, 3)  # in the disc that covers the most dolls
    assert dolls.bait_target((0.0, 0.0), [near], 8.0, lambda m: False, lambda m: 0) is None
    assert dolls.bait_target(*args[:3], lambda m: m.unit_id == 2, lambda m: 0) is None  # a mark lasts on one
    tried = dolls.bait_target(*args[:3], lambda m: False, lambda m: 1 if m.unit_id == chosen.unit_id else 0)
    assert tried is not None
    assert tried.unit_id != chosen.unit_id  # a key that did not take goes on another
    assert dolls.bait_target((0.0, 0.0), [Marked(6, (40.0, 0.0))], 8.0, lambda m: False, lambda m: 0) is None


def test_bait_marks_a_doll_only_with_a_demon_out(monkeypatch) -> None:
    from inventory_tracking.builds.warlock import mark
    from inventory_tracking.game.layout import DEFILER_CLASS
    from inventory_tracking.game.records import Monster
    from inventory_tracking.macros.build import BuffFacts
    from tests.inventory_tracking.macros.fakes import player, world

    doll = Monster(10, 216, 1, 5020.0, 5000.0, life=128, max_life=128)
    defiler = Monster(20, DEFILER_CLASS, 1, 4998.0, 5000.0, owner=1, ally=True)
    here = player(101, x=5000.0, y=5000.0)
    alone = BuffFacts(world(101, player=here, monsters=(doll,)), 10.0, foes=(doll,), reachable=(doll,))
    with_demon = BuffFacts(world(101, player=here, monsters=(doll, defiler)), 10.0, foes=(doll,), reachable=(doll,))
    assert mark.doll_bait(with_demon) is None  # off
    monkeypatch.setattr(dolls, 'DOLL_BAIT', True)
    assert mark.doll_bait(alone) is None  # the skill needs a demon
    assert mark.doll_bait(with_demon) == doll
    assert mark.target(with_demon) == doll
    assert mark.why_not(with_demon, doll) is None  # trash, but the bait
    monkeypatch.setattr(dolls, 'DOLL_BAIT', False)
    assert mark.why_not(with_demon, doll) is not None  # trash: never marked, as before


def test_the_pack_a_demon_holds_and_the_stand_to_strike_it_from() -> None:
    here, demon = (0.0, 0.0), (30.0, 0.0)
    pack = [Marked(1, (32.0, 1.0)), Marked(2, (33.0, -1.0)), Marked(3, (8.0, 0.0))]  # 3 is on the character
    found = dolls.held_pack(here, pack, [demon])
    assert found is not None
    middle, key = found
    assert middle == pytest.approx((32.5, 0.0))
    assert key == 1
    stand = dolls.bait_stand(here, middle)
    assert stand is not None
    assert math.dist(stand, middle) == pytest.approx(dolls.BAIT_STAND)
    assert dolls.bait_stand((20.0, 0.0), middle) is None  # within BAIT_STAND + BAIT_SLACK: it strikes from there
    assert dolls.held_pack(here, pack, []) is None  # no demon out
