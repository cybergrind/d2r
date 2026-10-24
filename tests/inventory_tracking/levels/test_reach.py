"""levels/reach.py: the game's Teleport rule per level (levels.txt Teleport, D2MOO `SKILLS_SrvDo027_Teleport`), on
the Duriel's Lair rooms cut from take 20261023T121459Z-73 (rca/2026-10-23/gap-findings.md)."""

import json
from itertools import pairwise
from pathlib import Path

import pytest

from inventory_tracking.levels import reach
from inventory_tracking.levels.model import Ground, Walkable, pack_cells, pack_masks
from inventory_tracking.levels.presets import teleport_rule


FIXTURE = Path(__file__).parents[1] / 'fixtures' / 'duriels_lair_gap.json'
LAIR = 73
CANYON = 46  # Canyon of the Magi: levels.txt Teleport 1
HERE = (22622.5, 15692.5)  # where the character stood from 15:15:07.2
ACROSS = ((22603.3, 15703.1), (22606.9, 15708.1))  # the spots the game refused, 21.9 and 22.0 off


def lair() -> Ground:
    level = json.loads(FIXTURE.read_text())
    return Ground(tuple(Walkable(**grid) for grid in level['ground']))


def test_duriels_lair_alone_needs_a_clear_line():
    assert teleport_rule(LAIR) == reach.LINE
    assert teleport_rule(CANYON) == reach.ANY
    assert teleport_rule(1) == reach.ANY  # Rogue Encampment: the table names only what is not 1


@pytest.mark.parametrize('on', [True, False])
def test_the_switch_and_the_level_decide_whether_a_line_is_wanted(monkeypatch, on):
    monkeypatch.setattr(reach, 'TELEPORT_LINE', on)
    assert reach.lined(LAIR) is on
    assert not reach.lined(CANYON)
    assert not reach.lined(None)


def test_the_takes_hops_land_where_the_line_is_clear_and_not_where_it_is_barred():
    # 15:15:07.19 landed (16.6 over open floor); the six presses at the two spots across the wall cast and moved
    # nothing; on 2026-10-22 23:12:39 a hop of 8.1 round the wall's end landed
    ground = lair()
    assert reach.line_clear(ground, (22638.5, 15693.5), (22621.9, 15692.5))
    assert reach.line_clear(ground, HERE, (22626.1, 15699.8))
    for spot in ACROSS:
        assert not reach.line_clear(ground, HERE, spot)


@pytest.mark.parametrize('on', [True, False])
def test_hop_lands_is_the_line_only_on_a_lined_level(monkeypatch, on):
    monkeypatch.setattr(reach, 'TELEPORT_LINE', on)
    ground = lair()
    assert reach.hop_lands(LAIR, ground, HERE, ACROSS[0]) is not on
    assert reach.hop_lands(CANYON, ground, HERE, ACROSS[0])  # elsewhere a Teleport crosses the same wall
    assert reach.hop_lands(LAIR, None, HERE, ACROSS[0])  # no ground read: nothing known bars it


def test_the_ray_moves_both_ends_toward_each_other_and_keeps_every_cell_between():
    assert list(reach.ray((0, 0), (10, 0))) == [(x, 0) for x in range(2, 9)]
    assert list(reach.ray((0, 0), (0, -10))) == [(0, y) for y in range(-2, -9, -1)]
    cells = list(reach.ray((0, 0), (10, 4)))
    assert cells[0] == (2, 0)
    assert cells[-1] == (8, 4)
    assert all(abs(b[0] - a[0]) == 1 and abs(b[1] - a[1]) <= 1 for a, b in pairwise(cells))
    assert list(reach.ray((0, 0), (2, 1))) == []  # touching: no line to test


def strip(masks: list[int], walk: str) -> Ground:
    """One tile of 5x5 sub-tiles whose middle column (x 2) has `masks`/`walk` and the rest is open floor."""
    cells = ''.join(walk if x == 2 else '1' for _ in range(5) for x in range(5))
    values = [masks[0] if x == 2 else 0 for _ in range(5) for x in range(5)] if masks else []
    return Ground((Walkable(0, 0, 1, 1, pack_cells(cells), '', pack_masks(values)),))


def test_bars_are_the_flying_players_mask_bits_not_the_walk_bit():
    # A wall a player cannot walk through (0x0001) but that is no missile barrier bars no Teleport line
    assert not reach.bars(strip([0x0001], '0').grids)
    assert len(reach.bars(strip([0x0004], '1').grids)) == 5
    assert len(reach.bars(strip([0x0800], '1').grids)) == 5  # a door
    assert len(reach.bars(strip([], '0').grids)) == 5  # no masks read: the walk bit
