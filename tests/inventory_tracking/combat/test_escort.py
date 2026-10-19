"""The mercenary taken out of a place it dies at by a jump that brings the companions along (combat/escort.py; the
player, 2026-10-14: "Blade Warp teleports minions with me, so it can be used to reposition the merc to avoid his death,
for example in the Diablo fight")."""

import math

from inventory_tracking.combat import escort
from inventory_tracking.combat.harm import Hostile, Look, SafetySettings
from inventory_tracking.game.records import Monster
from inventory_tracking.native.layout import HIRELING_CLASS_ID


DIABLO = 243  # monstats row
HERE = (80.0, 0.0)  # the character
MERC = (100.0, 0.0)  # the mercenary, Diablo beside it
SETTINGS = SafetySettings()


def look() -> Look:
    return Look((Hostile(1, DIABLO, (102.0, 1.0), active=True),), companions=(MERC,), life=1800.0)


def test_the_mercenary_is_the_characters_hireling_alive_with_its_life_read() -> None:
    mine = Monster(7, HIRELING_CLASS_ID, 1, *MERC, 42, life=32, max_life=1450)  # a quarter of its life
    other = Monster(8, HIRELING_CLASS_ID, 1, *MERC, 43, life=400, max_life=1450)  # another player's
    dead = Monster(9, HIRELING_CLASS_ID, 1, *MERC, 42, life=0, max_life=1450)
    unread = Monster(10, HIRELING_CLASS_ID, 1, *MERC, 42)
    summon = Monster(11, 999, 1, *MERC, 42, life=300, max_life=300)
    (kept,) = escort.kept_alive([mine, other, dead, unread, summon], 42)
    assert (kept.unit, kept.at, kept.life, kept.most, kept.worth) == (7, MERC, 362.5, 1450.0, escort.REHIRE_SECONDS)


def test_a_mercenary_beside_diablo_is_in_lethal_danger_and_a_landing_away_from_him_saves_it() -> None:
    (kept,) = escort.kept_alive([Monster(7, HIRELING_CLASS_ID, 1, *MERC, 42, life=35, max_life=1450)], 42)
    endangered = escort.in_danger(look(), [kept], SETTINGS)
    assert [(found.unit, share >= escort.LETHAL) for found, share in endangered] == [(7, True)]
    spots = escort.around(HERE, 26.0, 8.0)
    assert len(spots) == escort.RAYS * len(escort.RINGS)
    found = escort.escorts(look(), endangered, spots, SETTINGS)
    assert 0 < len(found) <= escort.ESCORTS_MOST
    best = found[0]
    assert best.there < best.here
    assert best.credit == (best.here - best.there) * escort.REHIRE_SECONDS
    assert math.dist(best.spot, (102.0, 1.0)) > math.dist(MERC, (102.0, 1.0))  # away from him
    assert best.line().startswith(escort.ESCORTING)


def test_a_mercenary_far_from_any_hostile_is_left_where_it_is() -> None:
    (kept,) = escort.kept_alive([Monster(7, HIRELING_CLASS_ID, 1, -200.0, 0.0, 42, life=35, max_life=1450)], 42)
    assert escort.in_danger(look(), [kept], SETTINGS) == []
    assert escort.escorts(look(), [], escort.around(HERE, 26.0, 8.0), SETTINGS) == []


def test_a_whole_mercenarys_life_is_its_most_life_in_points_not_the_share_it_is_read_as() -> None:
    """Lower Kurast, 2026-10-17: the mercenary read as 128 of 2367 was a whole one, and was escorted out of trash
    35 times in 65 stays."""
    (kept,) = escort.kept_alive(
        [Monster(7, HIRELING_CLASS_ID, 1, *MERC, 42, life=escort.LIFE_SHARE, max_life=2367)], 42
    )
    assert kept.life == kept.most == 2367.0
