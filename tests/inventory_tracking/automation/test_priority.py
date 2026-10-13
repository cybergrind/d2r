"""The healer's priority between the mercenary and the character (automation/priority.py), and the stock alarm.

The player's ruling (2026-10-13): "healer should feed merc, then me. but if situation is critical - then feed
player"; "usually we shouldn't get into situation when we have no potions. something is wrong if we're empty".
And later that day: "we're trying to heal merc, but keep at least 2 rev potions for user": no healing reserve is
held from the mercenary by default (`HealPriorityConfig.keep_healing`); the tests of the hold pin it (`KEEP`).
"""

import logging
from dataclasses import replace

import pytest

from inventory_tracking.automation.controller import Automation
from inventory_tracking.automation.priority import Level, StockWatch, judge, reserve
from inventory_tracking.combat.harm import SafetySettings
from inventory_tracking.combat.survival import DrinkSettings
from inventory_tracking.config import HEAL_PRIORITY, MERC_HEALING, PLAYER_HEALING, with_overrides
from inventory_tracking.models import (
    Actor,
    BeltCell,
    BeltSnapshot,
    Hold,
    Outcome,
    PlayerHealth,
    PotionRequest,
    PotionSent,
    PotionType,
)
from inventory_tracking.native.mercenary import Mercenary


MOST = 1818  # the character's most life in the game of 21:42 (2026-10-13)
JUV, HP = 531, 606
OFF = with_overrides(HEAL_PRIORITY, enabled=False)
# The reserve held back from the mercenary: the first version of the priority (2026-10-13), off by default since the
# player's ruling that day ("we're trying to heal merc, but keep at least 2 rev potions for user"). The tests of the
# hold pin it.
KEEP = with_overrides(HEAL_PRIORITY, keep_healing=True)


class Belt:
    """A belt in play, by column (bottom first): a drunk potion leaves its column and the rest drop down."""

    def __init__(self, healing: tuple[int, int], rejuvenations: tuple[int, int] = (3, 3)) -> None:
        counts = dict(zip((1, 2, 3, 4), (*rejuvenations, *healing), strict=True))
        self.columns = {column: [column * 100 + row for row in range(counts[column])] for column in counts}

    def drink(self, item_id: int) -> None:
        for items in self.columns.values():
            if item_id in items:
                items.remove(item_id)

    def snapshot(self) -> BeltSnapshot:
        contents: list[int | None] = [None] * 16
        for column, items in self.columns.items():
            for row, _ in enumerate(items):
                contents[row * 4 + column - 1] = JUV if column <= 2 else HP
        bottom = {column: BeltCell(column, items[0]) for column, items in self.columns.items() if items}
        return BeltSnapshot(
            tuple(contents),
            tuple(cell for column, cell in bottom.items() if column > 2),
            tuple(cell for column, cell in bottom.items() if column <= 2),
            tuple(item for items in self.columns.values() for item in items),
        )


def life(points: int, most: int = MOST) -> PlayerHealth:
    return PlayerHealth(points * 256, most * 256)


def merc(fraction: int) -> Mercenary:
    """The 21:42 game's mercenary by the client's life fraction (32768 = full), as osd.log printed it."""
    return Mercenary(3898082581, fraction * 606080 // 32768, 606080, fraction, True)


# --- the model -------------------------------------------------------------------------------------------------


def test_the_named_constants_are_the_macros_own():
    # consistent with the macro's life budget (rca/2026-10-13/safety-pricing.md): the floor, the look ahead and
    # a healing potion's points are harm.py's; the reserve at this character's life is the drinker's keep_healing.
    safety = SafetySettings()
    assert HEAL_PRIORITY.floor == safety.floor
    assert HEAL_PRIORITY.horizon == safety.horizon
    assert HEAL_PRIORITY.healing_points == safety.healing_points
    assert HEAL_PRIORITY.window == PLAYER_HEALING.burst_window
    assert reserve(MOST, 6, HEAL_PRIORITY) == DrinkSettings().keep_healing == 2


@pytest.mark.parametrize(
    ('most', 'rejuvenations', 'kept'),
    [
        (MOST, 6, 2),  # 35% of 1818 = 636 points: two potions of 480
        (MOST, 0, 3),  # no rejuvenation left: one more
        (1371, 6, 1),  # 480 points exactly: one
        (3000, 6, 3),
        (None, 6, 1),  # life unread: never the last one
        (None, 0, 1),
    ],
)
def test_the_reserve_brings_the_character_from_the_floor_back_to_full_life(most, rejuvenations, kept):
    assert reserve(most, rejuvenations, HEAL_PRIORITY) == kept


def test_critical_is_the_life_played_ahead_at_the_last_seconds_fall_under_the_floor():
    calm = judge(0.70, 0.0, MOST, 3, 6, HEAL_PRIORITY)
    assert (calm.critical, calm.hold) == (False, None)
    # 21:50:03.48: 77% -> 63% within the second; 42% ahead.
    falling = judge(0.63, 0.14, MOST, 4, 6, HEAL_PRIORITY)
    assert (falling.critical, falling.hold) == (True, Hold.CRITICAL)
    assert falling.ahead == pytest.approx(0.42)
    # Above the floor still, but going under it within 1.5 s: 90% -> 76%, 55% ahead.
    assert judge(0.76, 0.14, MOST, 8, 6, HEAL_PRIORITY).critical
    # Under the floor and mending: still critical, the life budget is gone.
    assert judge(0.64, 0.0, MOST, 8, 6, HEAL_PRIORITY).critical


@pytest.mark.parametrize('percent', [64, 50, 39, 1])
def test_whenever_the_healer_would_feed_the_character_he_is_critical(percent):
    # The healer's own marks (65% healing, 40% rejuvenation) lie at or under the floor: a potion it gives the
    # character is always given first.
    assert percent < PLAYER_HEALING.thresholds[PotionType.HEALING] <= HEAL_PRIORITY.floor
    assert judge(percent / 100, 0.0, MOST, 8, 6, HEAL_PRIORITY).critical


@pytest.mark.parametrize(('healing', 'hold'), [(3, None), (2, Hold.RESERVE), (1, Hold.RESERVE), (0, Hold.RESERVE)])
def test_with_the_reserve_held_the_mercenary_is_given_no_healing_potion_of_it(healing, hold):
    assert judge(1.0, 0.0, MOST, healing, 6, KEEP).hold == hold


@pytest.mark.parametrize('healing', [3, 2, 1, 0])
def test_by_default_the_mercenary_may_have_the_reserve_unless_the_character_is_critical(healing):
    # The player's ruling (2026-10-13): the mercenary is healed from the belt's healing potions; the character
    # first only when critical. The reserve is still counted: the `Potion stock:` low mark.
    assert not HEAL_PRIORITY.keep_healing
    calm = judge(1.0, 0.0, MOST, healing, 6, HEAL_PRIORITY)
    assert (calm.reserve, calm.keeps, calm.hold) == (2, False, None)
    assert judge(0.63, 0.14, MOST, healing, 6, HEAL_PRIORITY).hold == Hold.CRITICAL


# --- the orchestration -----------------------------------------------------------------------------------------


def step(automation, sample, clock, at, belt, points, fraction, **changes):
    clock.now = at
    state = sample(at, health=life(points), merc=merc(fraction), belt=belt.snapshot(), **changes)
    return automation.step(state)


def test_both_wanting_a_potion_when_calm_the_mercenary_drinks_first(healing_setup, sample, clock):
    make, sent = healing_setup
    # A character's mark above the floor (95%), so that both want a healing potion while he is calm.
    eager = with_overrides(PLAYER_HEALING, thresholds={PotionType.HEALING: 95, PotionType.REJUVENATION: 40})
    automation = Automation([make(eager), make(MERC_HEALING)])
    belt = Belt((4, 4))
    result = step(automation, sample, clock, 100.0, belt, 1640, 20000)  # 90%, steady; mercenary 61%
    assert (result[Actor.MERC].outcome, result[Actor.PLAYER].outcome) == (Outcome.SENT, Outcome.STALE_BELT)
    belt.drink(sent.call_args.args[0].item.item_id)
    result = step(automation, sample, clock, 100.3, belt, 1640, 21000)
    assert result[Actor.PLAYER].outcome == Outcome.SENT  # his at the next sample


def test_the_character_critical_drinks_first_and_the_mercenary_gets_no_healing_potion(healing_setup, sample, clock):
    make, sent = healing_setup
    automation = Automation([make(MERC_HEALING), make(PLAYER_HEALING)])
    belt = Belt((4, 4))
    result = step(automation, sample, clock, 100.0, belt, 1100, 20000)  # 60%: the character's mark and critical
    assert result[Actor.PLAYER].outcome == Outcome.SENT
    assert (result[Actor.MERC].outcome, result[Actor.MERC].reason) == (Outcome.HELD, Hold.CRITICAL)
    assert sent.call_count == 1


def test_a_fast_fall_above_the_floor_is_critical_and_keeps_the_healing_potions(healing_setup, sample, clock):
    make, sent = healing_setup
    automation = Automation([make(MERC_HEALING), make(PLAYER_HEALING)])
    belt = Belt((4, 4))
    step(automation, sample, clock, 100.0, belt, 1636, 32768)  # 90%, mercenary full
    result = step(automation, sample, clock, 100.5, belt, 1380, 20000)  # 76% half a second later: 55% ahead
    assert result[Actor.PLAYER].outcome == Outcome.IDLE  # not the healer's mark yet (the macro's drinker's)
    assert (result[Actor.MERC].outcome, result[Actor.MERC].reason) == (Outcome.HELD, Hold.CRITICAL)
    sent.assert_not_called()


def test_with_the_reserve_held_the_mercenary_drinks_down_to_it_and_gets_rejuvenations_by_their_own_rule(
    healing_setup, sample, clock
):
    make, sent = healing_setup
    automation = Automation([make(MERC_HEALING), make(PLAYER_HEALING)], priority=KEEP)
    belt = Belt((2, 1), rejuvenations=(4, 4))
    assert step(automation, sample, clock, 100.0, belt, MOST, 20000)[Actor.MERC].outcome == Outcome.SENT
    belt.drink(sent.call_args.args[0].item.item_id)
    result = step(automation, sample, clock, 104.0, belt, MOST, 20000)  # 2 healing left: the character's
    assert (result[Actor.MERC].outcome, result[Actor.MERC].reason) == (Outcome.HELD, Hold.RESERVE)
    result = step(automation, sample, clock, 105.0, belt, MOST, 9000)  # under 40%, 8 rejuvenations
    assert result[Actor.MERC].outcome == Outcome.SENT
    assert sent.call_args.args[0].potion == PotionType.REJUVENATION


def test_by_default_the_calm_character_lets_the_mercenary_drink_at_the_reserve(healing_setup, sample, clock):
    # The player's ruling (2026-10-13): 2 healing potions on the belt, the old reserve at 1818 life, and the
    # character calm (full life): the mercenary (61%) is given one.
    make, sent = healing_setup
    automation = Automation([make(MERC_HEALING), make(PLAYER_HEALING)])
    result = step(automation, sample, clock, 100.0, Belt((1, 1)), MOST, 20000)
    assert result[Actor.MERC].outcome == Outcome.SENT
    assert sent.call_args.args[0].potion == PotionType.HEALING


def test_by_default_the_critical_character_still_keeps_the_mercenary_from_the_last_ones(healing_setup, sample, clock):
    make, sent = healing_setup
    automation = Automation([make(MERC_HEALING), make(PLAYER_HEALING)])
    result = step(automation, sample, clock, 100.0, Belt((1, 1)), 1100, 20000)  # 60%: critical
    assert result[Actor.PLAYER].outcome == Outcome.SENT
    assert (result[Actor.MERC].outcome, result[Actor.MERC].reason) == (Outcome.HELD, Hold.CRITICAL)
    assert sent.call_count == 1


def test_with_the_priority_off_the_character_is_first_and_nothing_is_kept(healing_setup, sample, clock):
    make, _ = healing_setup
    automation = Automation([make(MERC_HEALING), make(PLAYER_HEALING)], priority=OFF)
    belt = Belt((1, 0))
    assert step(automation, sample, clock, 100.0, belt, MOST, 20000)[Actor.MERC].outcome == Outcome.SENT


def test_held_is_logged_once_with_the_verdict_and_shown(healing_setup, sample, clock, caplog):
    make, _ = healing_setup
    automation = Automation([make(MERC_HEALING), make(PLAYER_HEALING)], priority=KEEP)
    belt = Belt((1, 1))
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        step(automation, sample, clock, 100.0, belt, MOST, 20000)
        step(automation, sample, clock, 100.3, belt, MOST, 19000)
    held = [record.getMessage() for record in caplog.records if record.getMessage().startswith('merc healing')]
    assert held == [
        'merc healing: held (reserve): life 100%, 100% ahead (fell 0%); belt healing 2 (the character keeps 2), '
        'rejuvenations 6'
    ]
    assert automation.outcomes[Actor.MERC].outcome == Outcome.HELD


# --- the replay of 21:50 (game of 21:42, 2026-10-13) -----------------------------------------------------------

# (seconds after 21:50:00, the character's life of 1818 from the take 20261013T184953Z-108's frames, the
# mercenary's life fraction from osd.log 20261013T181041Z-fb5bfadf). The belt held 4 healing potions (the macro
# had drunk the fifth at 02.08) and 6 rejuvenations.
TIMELINE = (
    (2.85, 1401, 32768),
    (3.75, 1146, 32768),  # 77% -> 63% within the second; the character's healing potion (osd.log 21:50:03.749)
    (4.30, 1149, 32768),
    (6.40, 1218, 28416),
    (7.25, 1264, 23808),  # the mercenary 73%: his first (21:50:07.249)
    (8.30, 1342, 25344),
    (9.45, 1451, 20736),
    (10.32, 1451, 18432),  # 56%: his second as it ran (21:50:10.315)
    (11.75, 1559, 19200),
    (12.49, 1637, 21760),
    (13.52, 1668, 22272),  # 68%: his third as it ran (21:50:13.515), the belt's last
    (13.78, 1699, 22272),  # as it ran: "merc healing: no_stock"
)


def replay(make, sample, clock, priority):
    automation = Automation([make(PLAYER_HEALING), make(MERC_HEALING)], priority=priority)
    belt = Belt((2, 2))
    given, outcomes = [], {}
    for at, points, fraction in TIMELINE:
        result = step(automation, sample, clock, 1000 + at, belt, points, fraction)
        outcomes[at] = result
        for actor, outcome in result.items():
            if outcome.event is not None:
                given.append((at, actor))
                belt.drink(outcome.event.request.item.item_id)
    healing = sum(len(belt.columns[column]) for column in (3, 4))
    return given, outcomes, healing


def test_replay_as_it_ran_the_mercenary_drinks_the_last_three(healing_setup, sample, clock):
    make, _ = healing_setup
    given, outcomes, healing = replay(make, sample, clock, OFF)
    assert given == [(3.75, Actor.PLAYER), (7.25, Actor.MERC), (10.32, Actor.MERC), (13.52, Actor.MERC)]
    assert healing == 0
    assert outcomes[13.78][Actor.MERC].outcome == Outcome.NO_STOCK


def test_replay_with_the_reserve_held_keeps_two_healing_potions_for_the_character(healing_setup, sample, clock, caplog):
    make, _ = healing_setup
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        given, outcomes, healing = replay(make, sample, clock, KEEP)
    # 03.75: critical (63%, 42% ahead): the character first. 07.25: calm (70%, rising) and 3 healing potions,
    # one above the reserve of 2: the mercenary's. 10.32 and 13.52: the reserve.
    assert given == [(3.75, Actor.PLAYER), (7.25, Actor.MERC)]
    assert healing == 2
    assert (outcomes[10.32][Actor.MERC].outcome, outcomes[10.32][Actor.MERC].reason) == (Outcome.HELD, Hold.RESERVE)
    assert outcomes[13.52][Actor.MERC].outcome == Outcome.HELD
    stock = [record for record in caplog.records if record.getMessage().startswith('Potion stock:')]
    assert [(record.levelname, record.getMessage()) for record in stock] == [
        (
            'INFO',
            'Potion stock: the game begins with healing potions stocked: 4 on the belt, the character keeps 2 '
            '(rejuvenations 6)',
        ),
        (
            'WARNING',
            'Potion stock: healing potions low: 2 on the belt, the character keeps 2 (rejuvenations 6); '
            'the last gone, newest first: merc by the healer 0.0 s ago, player by the healer 4.0 s ago',
        ),
    ]


def test_replay_under_the_default_rulings_the_mercenary_drinks_the_belts_healing_potions_dry(
    healing_setup, sample, clock, caplog
):
    # The player's rulings (2026-10-13): no healing reserve held from the mercenary, the character first only when
    # critical. 03.75: critical (63%, 42% ahead): the character's. 07.25, 10.32 and 13.52: the character calm
    # (70% and rising, 80% steady, 92%): the mercenary's, as it ran. The belt ends with no healing potion and its
    # 6 rejuvenations, all the character's (the mercenary is never under 40% here; he is given none of the last 2).
    make, _ = healing_setup
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        given, outcomes, healing = replay(make, sample, clock, HEAL_PRIORITY)
    assert given == [(3.75, Actor.PLAYER), (7.25, Actor.MERC), (10.32, Actor.MERC), (13.52, Actor.MERC)]
    assert healing == 0
    assert outcomes[13.78][Actor.MERC].outcome == Outcome.NO_STOCK
    assert not any(outcome.outcome == Outcome.HELD for result in outcomes.values() for outcome in result.values())
    # The stock card and log still say it: low at the reserve of 2, then empty, and who took the last ones.
    stock = [record for record in caplog.records if record.getMessage().startswith('Potion stock:')]
    assert [(record.levelname, record.getMessage()) for record in stock] == [
        (
            'INFO',
            'Potion stock: the game begins with healing potions stocked: 4 on the belt, the character keeps 2 '
            '(rejuvenations 6)',
        ),
        (
            'WARNING',
            'Potion stock: healing potions low: 2 on the belt, the character keeps 2 (rejuvenations 6); '
            'the last gone, newest first: merc by the healer 0.0 s ago, player by the healer 4.0 s ago',
        ),
        (
            'WARNING',
            'Potion stock: no healing potion on the belt (rejuvenations 6); the last gone, newest first: '
            'merc by the healer 0.0 s ago, merc by the healer 2.0 s ago, merc by the healer 5.5 s ago, '
            'player by the healer 9.5 s ago',
        ),
    ]


def test_replay_as_it_ran_says_when_and_who_emptied_the_belt(healing_setup, sample, clock, caplog):
    make, _ = healing_setup
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        replay(make, sample, clock, OFF)
    stock = [record.getMessage() for record in caplog.records if record.getMessage().startswith('Potion stock:')]
    assert stock[-1] == (
        'Potion stock: no healing potion on the belt (rejuvenations 6); the last gone, newest first: '
        'merc by the healer 0.0 s ago, merc by the healer 2.0 s ago, merc by the healer 5.5 s ago, '
        'player by the healer 9.5 s ago'
    )


# --- the stock watch --------------------------------------------------------------------------------------------


def look(watch, sample, at, belt):
    return watch.look(sample(at, health=life(MOST), belt=belt.snapshot()))


def test_a_game_that_begins_low_warns_once_without_the_card(sample):
    watch = StockWatch(HEAL_PRIORITY)
    first = look(watch, sample, 100.0, Belt((1, 0)))
    assert first is not None
    assert (first.fell, first.before) == (True, None)
    assert look(watch, sample, 101.0, Belt((1, 0))) is None
    assert (watch.level, watch.alarm) == (Level.LOW, False)


def test_a_fall_during_the_game_raises_the_card_until_restocked_and_a_new_game_forgets(sample):
    watch = StockWatch(HEAL_PRIORITY)
    belt = Belt((2, 2))
    assert look(watch, sample, 100.0, belt).after == Level.STOCKED
    watch.sent(PotionSent(PotionRequest(Actor.MERC, PotionType.HEALING, BeltCell(3, 300)), 100.5))
    belt.drink(300)
    belt.drink(401)  # not the healer's: the macro's drinker or a hand
    change = look(watch, sample, 101.0, belt)
    assert (change.fell, change.after, watch.alarm) == (True, Level.LOW, True)
    assert [gone.by for gone in change.gone] == [Actor.MERC, None]
    belt.drink(301)
    belt.drink(400)
    assert (look(watch, sample, 102.0, belt).after, watch.alarm) == (Level.EMPTY, True)
    assert (look(watch, sample, 103.0, Belt((2, 2))).fell, watch.alarm) == (False, False)  # restocked
    look(watch, sample, 104.0, Belt((1, 1)))
    assert watch.alarm
    other = sample(105.0, health=life(MOST), belt=Belt((1, 1)).snapshot())
    watch.look(replace(other, session=other.session._replace(player_id=99)))
    assert not watch.alarm  # another game: its first look is no fall of this one
