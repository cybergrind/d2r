"""A terrorized level's monster level in the foes' life (combat/mechanics/life.py TZ_LEVEL_LIFE, 2026-10-21): the
game's Terror Zone rule, how a look tells a terrorized level, and the forecasts of the tier 5 Herald fight of 09:30:41
(take 20261021T063019Z-77, rca/2026-10-21/herald-fight-findings.md) with the switch on and off."""

import json
from pathlib import Path

import pytest

from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.combat.mechanics import life
from inventory_tracking.combat.mechanics.tables import ZONES, area_level, points_of, tables
from inventory_tracking.combat.policy import observe
from inventory_tracking.combat.stance import Field, falls
from inventory_tracking.game.layout import CHAMPION_FLAG, MINION_FLAG, NO_OWNER, UNIQUE_FLAG
from inventory_tracking.game.records import Monster, Player


BRAMBLE_HULK, GREAT_MARSH, ROGUE_ENCAMPMENT = 128, 77, 1
EXTRA_STRONG, NOT_FORCED = 5, 8  # monumod ids: Extra Strong is in the zone's forced pool, 8 (Magic Resistant) is not
FIXTURES = Path(__file__).parents[2] / 'macros' / 'fixtures'
HERALD_A = 1966408054  # the tier 5 Herald of 09:30:41
HERALD_A_DIES = 16.53  # s after the tanked look (09:30:50.95): its mode 0 / life 0 frame at monotonic 587026.617


@pytest.fixture(autouse=True)
def unattached(monkeypatch) -> None:
    monkeypatch.setattr(life, 'SOURCE', life.ZoneSource())
    monkeypatch.setattr(life, 'TZ_LEVEL_LIFE', True)


def hulk(unit: int, *, flags: int = 0, tier: int = 0, mods: tuple[int, ...] = (EXTRA_STRONG,)) -> Monster:
    return Monster(unit, BRAMBLE_HULK, 1, 5000.0 + unit, 5000.0, flags=flags, life=128, max_life=128, modifiers=mods,
                   tier=tier)  # fmt: skip


def here(area: int = GREAT_MARSH) -> Player:
    return Player(1, 'Warlock', 5, area, 5000.0, 5000.0, False)


def test_the_bundled_rule_is_the_games_terror_zone_config() -> None:
    config = json.loads(ZONES.read_text())['desecrated_zones'][0]
    hell = config['game_difficulties']['rotw']['hell']
    rule = tables()['terror']
    assert (rule['bound_min'], rule['bound_max'], rule['boost_level']) == (70, 96, 2)
    assert rule['bound_min'] == hell['defaults']['bound_incl_min']
    assert rule['bound_max'] == hell['defaults']['bound_incl_max']
    assert rule['boost_level'] == hell['defaults']['boost_level']
    assert rule['modifiers'] == sorted({row['unique_mod'] for row in hell['always_unique_mod_pool']})
    assert GREAT_MARSH in rule['levels']
    assert ROGUE_ENCAMPMENT not in rule['levels']


@pytest.mark.parametrize(
    ('player_level', 'level'),
    [
        (95, 96),  # the character on 2026-10-21: the client's entries read 96 for Great Marsh
        (93, 95),  # 'Terrorized: 95' at character level 93 (terror/tracker.py, 2026-10-06)
        (99, 96),  # the cap
        (60, 80),  # never under the area's own (Great Marsh 80), the floor 70 under it
        (None, 96),  # no character level: the cap, the most life
    ],
)
def test_the_zone_level_is_the_characters_plus_two_within_the_bounds(player_level, level) -> None:
    assert area_level(GREAT_MARSH) == 80
    assert life.zone_level(GREAT_MARSH, player_level) == level


def test_an_attached_character_level_is_read_when_none_is_given() -> None:
    life.attach(player_level=lambda: 90)
    assert life.zone_level(GREAT_MARSH) == 92


def test_a_herald_tier_or_most_plain_monsters_forced_modifier_shows_the_zone() -> None:
    assert life.evident([hulk(1, flags=MINION_FLAG, tier=5, mods=())])
    assert life.evident([hulk(1), hulk(2), hulk(3, mods=())])
    assert not life.evident([hulk(1), hulk(2, mods=()), hulk(3, mods=())])
    assert not life.evident([hulk(1, mods=(NOT_FORCED,))])
    # a champion pack's modifiers come from the same pool outside a Terror Zone: no evidence
    assert not life.evident([hulk(1, flags=CHAMPION_FLAG), hulk(2, flags=CHAMPION_FLAG)])
    assert not life.evident([])


def test_a_level_no_terror_zone_holds_is_never_terrorized() -> None:
    life.attach(terrorized=lambda area: True)
    assert not life.terrorized(ROGUE_ENCAMPMENT, [hulk(1, flags=UNIQUE_FLAG, tier=5)])
    assert life.monster_level(ROGUE_ENCAMPMENT, [hulk(1)]) is None


def test_the_attached_tracker_or_the_looks_evidence_is_enough() -> None:
    assert not life.terrorized(GREAT_MARSH, [hulk(1, mods=())])
    life.attach(terrorized=lambda area: True)
    assert life.terrorized(GREAT_MARSH, [])
    life.attach(terrorized=lambda area: False)  # a wrong word against a Herald in sight: the Herald wins
    assert life.terrorized(GREAT_MARSH, [hulk(1, flags=UNIQUE_FLAG, tier=5)])


def test_a_terrorized_levels_foes_are_priced_at_the_zones_level() -> None:
    seen = observe(here(), [hulk(1), hulk(2)])
    assert seen.foes[1].left == pytest.approx(points_of(BRAMBLE_HULK, GREAT_MARSH, 96))
    assert points_of(BRAMBLE_HULK, GREAT_MARSH, 96) / points_of(BRAMBLE_HULK, GREAT_MARSH) == pytest.approx(
        int(tables()['monlvl']['96']['HP(H)']) / int(tables()['monlvl']['80']['HP(H)']), rel=1e-3
    )  # monlvl HP(H) 5585 for 4205


def test_the_herald_tier_comes_on_top_of_the_zones_level() -> None:
    seen = observe(here(), [hulk(1, flags=UNIQUE_FLAG, tier=5, mods=()), hulk(2, flags=MINION_FLAG, tier=5, mods=())])
    assert seen.foes[1].left == pytest.approx(points_of(BRAMBLE_HULK, GREAT_MARSH, 96) * 21)
    assert seen.foes[2].left == pytest.approx(points_of(BRAMBLE_HULK, GREAT_MARSH, 96) * 8.5)


def test_off_or_outside_a_terror_zone_the_areas_level_prices_them(monkeypatch) -> None:
    plain = points_of(BRAMBLE_HULK, GREAT_MARSH)
    assert observe(here(), [hulk(1, mods=())]).foes[1].left == plain  # no evidence, nothing attached
    monkeypatch.setattr(life, 'TZ_LEVEL_LIFE', False)
    assert observe(here(), [hulk(1), hulk(2)]).foes[1].left == plain
    assert life.monster_level(GREAT_MARSH, [hulk(1, flags=UNIQUE_FLAG, tier=5)]) is None


def herald_forecast(name: str) -> dict[int, float]:
    """Seconds until each foe of the fixture's look dies by the strikes from where the character stood (stance.py
    `falls` over 120 s), as the safety forecasts its kills (macros/safety.py `Pricing`) but past its horizon."""
    snap = json.loads((FIXTURES / f'{name}.json').read_text(encoding='utf-8'))
    monsters = [
        Monster(
            m['unit'], m['txt'], m['mode'], m['x'], m['y'], m['owner'], flags=m['flags'], ally=m['ally'],
            life=m['life'], max_life=m['max_life'], modifiers=tuple(m['mods']), tier=m['tier'],
        )
        for m in snap['monsters']
    ]  # fmt: skip
    foes = [m for m in monsters if not m.ally and m.owner == NO_OWNER]
    companions = [m for m in monsters if m.ally or m.owner != NO_OWNER]
    attack = ECHOING_STRIKE_BUILD.attack
    assert attack is not None
    who = Player(1, 'Warlock', 5, snap['area'], snap['player']['x'], snap['player']['y'], False)
    seen = attack.sees(observe(who, foes, companions), companions)
    return falls(seen, attack, Field(seen.blocked, None), seen.origin, 0.0, 120.0)


def test_the_tanked_heralds_forecast_death_comes_nearer_what_the_game_took(monkeypatch) -> None:
    monkeypatch.setattr(life, 'TZ_LEVEL_LIFE', False)
    before = herald_forecast('herald-t5-tanked')[HERALD_A]
    monkeypatch.setattr(life, 'TZ_LEVEL_LIFE', True)
    after = herald_forecast('herald-t5-tanked')[HERALD_A]
    assert before == pytest.approx(10.08)
    assert after == pytest.approx(13.32)
    assert before < after < HERALD_A_DIES  # the strikes there landed 1.6 a second, the forecast's 2.8
