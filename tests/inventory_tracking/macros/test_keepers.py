"""The amulet keeper (macros/keepers.py): the player's words, 16:50 on 2026-10-18, and the two sold at 03:48 on
2026-10-19."""

import pytest

from inventory_tracking.macros.game.records import Carried
from inventory_tracking.macros.keepers import amulet_keeper


AMULET, RING = 535, 537
RARE, MAGIC, CRAFTED = 6, 4, 8


def item(txt: int = AMULET, quality: int = RARE) -> Carried:
    return Carried(1, txt, 0, 0, (1, 1), quality)


@pytest.mark.parametrize(
    ('stats', 'why'),
    [
        ({7: 41 << 8, 39: 35}, '+41 life'),  # Corruption Scarab: +41 life, fire resistance 35%
        ({7: 59 << 8, 188: 1, 74: 4}, '+59 life'),  # Havoc Torc: +59 life, +1 Eldritch Skills, replenish life 4
        ({105: 10, 39: 12}, '10% faster cast rate'),
        ({83: 2}, '+2 skills'),
        ({188: 2}, '+2 skills'),
        ({127: 2}, '+2 skills'),
        ({}, 'its stats unread'),
    ],
)
def test_a_rare_amulet_with_life_fcr_or_two_skills_is_kept(stats, why):
    assert amulet_keeper(item(), stats) == why


@pytest.mark.parametrize(
    'stats',
    [
        {83: 1, 39: 13, 43: 13, 41: 13, 45: 13, 80: 8},  # Rune Wing, 03:02: +1 Warlock skills, all resistances 13, 8 MF
        {16: 20, 1: 17, 39: 12},  # Chaos Mark: +20 attack rating, +17 energy, fire resistance 12
        {188: 1, 45: 21, 74: 9},  # Plagueri Mark: +1 Lightning Skills, poison resistance 21, replenish life 9
    ],
)
def test_a_rare_amulet_with_none_of_them_is_not_kept(stats):
    assert amulet_keeper(item(), stats) is None


def test_a_crafted_amulet_is_judged_too_and_a_magic_one_or_a_ring_is_not():
    assert amulet_keeper(item(quality=CRAFTED), {7: 30 << 8}) == '+30 life'
    assert amulet_keeper(item(quality=MAGIC), {7: 30 << 8}) is None
    assert amulet_keeper(item(RING), {7: 30 << 8}) is None
