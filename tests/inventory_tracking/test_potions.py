from dataclasses import replace

from inventory_tracking.config import MERC_HEALING, PLAYER_HEALING, with_overrides
from inventory_tracking.models import BeltCell, Outcome, PotionType, SessionIdentity


PLAYER_8 = SessionIdentity(1, '2', 8)


def test_injected_thresholds_and_cooldowns_control_delivery(healing_setup, sample, clock):
    make, sent = healing_setup
    custom = with_overrides(
        PLAYER_HEALING,
        thresholds={PotionType.HEALING: 80, PotionType.REJUVENATION: 25},
        cooldowns={PotionType.HEALING: 7, PotionType.REJUVENATION: 0.5},
    )
    healer = make(custom)
    assert healer.step(sample(current_raw=750)).outcome == Outcome.SENT
    clock.now = 106.9
    consumed = sample(clock.now, current_raw=750, healing_cells=(BeltCell(4, 102),), belt_ids=(102, 103))
    assert healer.step(consumed).outcome == Outcome.COOLDOWN
    clock.now = 107
    assert healer.step(replace(consumed, sampled_at=107)).outcome == Outcome.SENT
    assert sent.call_count == 2


def test_actor_and_type_cooldowns_are_independent_but_snapshot_is_not_reused(healing_setup, sample, clock):
    make, sent = healing_setup
    player, merc = make(PLAYER_HEALING), make(MERC_HEALING)
    assert player.step(sample()).outcome == Outcome.SENT
    assert merc.step(sample()).outcome == Outcome.STALE_BELT
    clock.now = 100.1
    next_sample = sample(clock.now, healing_cells=(BeltCell(4, 102),), belt_ids=(102, 103))
    assert merc.step(next_sample).outcome == Outcome.SENT
    clock.now = 100.2
    # Player can now receive rejuvenation, despite a recent healing potion.
    assert player.step(sample(clock.now, current_raw=100, healing_cells=(), belt_ids=(103,))).outcome == Outcome.SENT
    assert [c.args[0].actor.value for c in sent.call_args_list] == ['player', 'merc', 'player']


def test_two_instances_cannot_consume_same_item_or_bypass_actor_pending(healing_setup, sample, clock):
    make, sent = healing_setup
    first, second = make(PLAYER_HEALING), make(PLAYER_HEALING)
    assert first.step(sample()).outcome == Outcome.SENT
    clock.now = 100.1
    assert second.step(sample(clock.now)).outcome == Outcome.PENDING
    # Other actor must skip the reserved bottom item.
    merc = make(MERC_HEALING)
    assert merc.step(sample(clock.now)).outcome == Outcome.SENT
    assert [c.args[0].item.item_id for c in sent.call_args_list] == [101, 102]


def test_missing_merc_does_not_skip_ack_timeout_and_restart_preserves_suspension(healing_setup, sample, clock):
    make, sent = healing_setup
    merc = make(MERC_HEALING)
    assert merc.step(sample()).outcome == Outcome.SENT
    clock.now = 102
    assert merc.step(sample(clock.now, merc=None)).outcome == Outcome.SUSPENDED
    clock.now = 110
    assert make(MERC_HEALING).step(sample(clock.now)).outcome == Outcome.SUSPENDED
    assert make(MERC_HEALING).step(sample(clock.now, session=PLAYER_8)).outcome == Outcome.SENT
    assert sent.call_count == 2


def test_session_change_resets_pending_but_preserves_type_cooldown(healing_setup, sample, clock):
    make, sent = healing_setup
    controller = make(MERC_HEALING)
    controller.step(sample())
    clock.now = 101
    assert controller.step(sample(101, session=PLAYER_8)).outcome == Outcome.COOLDOWN
    clock.now = 103
    assert controller.step(sample(103, session=PLAYER_8)).outcome == Outcome.SENT
    assert sent.call_count == 2


def test_player_rejuvenation_one_second_boundary_across_columns(healing_setup, sample, clock):
    make, sent = healing_setup
    controller = make(PLAYER_HEALING)
    controller.step(sample(current_raw=100))
    clock.now = 100.999
    next_sample = sample(clock.now, current_raw=100, rejuvenation_cells=(BeltCell(4, 104),), belt_ids=(104,))
    assert controller.step(next_sample).outcome == Outcome.COOLDOWN
    clock.now = 101
    assert controller.step(replace(next_sample, sampled_at=101)).outcome == Outcome.SENT
    assert sent.call_args.args[0].item.column == 4


def test_sample_must_start_after_key_delivery_finishes(healing_setup, sample, clock):
    make, _ = healing_setup
    player, merc = make(PLAYER_HEALING), make(MERC_HEALING)

    def slow_delivery(state, request, *, max_age, before_send):
        before_send()
        clock.now = 100.1
        return True

    player.potions.deliver = slow_delivery
    assert player.step(sample()).outcome == Outcome.SENT
    assert merc.step(sample(100.05)).outcome == Outcome.STALE_BELT


def test_partial_delivery_suspends_across_instances_without_success_event(healing_setup, sample, clock):
    make, _ = healing_setup
    controller = make(PLAYER_HEALING)

    def partial(state, request, *, max_age, before_send):
        before_send()
        raise OSError('input failed after key-down')

    controller.potions.deliver = partial
    result = controller.step(sample())
    assert result.outcome == Outcome.SUSPENDED
    assert result.event is None
    clock.now = 105
    assert make(PLAYER_HEALING).step(sample(105)).outcome == Outcome.SUSPENDED


def test_rejected_attempt_reserves_only_its_type_cooldown(healing_setup, sample, clock):
    from unittest.mock import Mock

    make, sent = healing_setup
    player = make(PLAYER_HEALING)
    player.potions.deliver = Mock(return_value=False)
    assert player.step(sample()).outcome == Outcome.REJECTED
    clock.now = 100.1
    assert make(PLAYER_HEALING).step(sample(100.1)).outcome == Outcome.COOLDOWN
    assert make(MERC_HEALING).step(sample(100.1)).outcome == Outcome.SENT
    assert sent.call_count == 1
