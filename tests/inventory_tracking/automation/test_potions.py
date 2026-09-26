from dataclasses import replace

import pytest

from inventory_tracking.config import MERC_HEALING, PLAYER_HEALING, with_overrides
from inventory_tracking.input.facade import InputError
from inventory_tracking.models import Actor, BeltCell, Outcome, PotionType, Refusal, SessionIdentity
from tests.inventory_tracking.input.fakes import FakeDelivery


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


def test_unconsumed_potion_is_retried_after_backoff_even_when_merc_is_missing(healing_setup, sample, clock):
    make, sent = healing_setup
    merc = make(MERC_HEALING)
    assert merc.step(sample()).outcome == Outcome.SENT
    clock.now = 102
    # The timeout is processed without a merc; nothing is needed, so the actor is idle, not suspended.
    assert merc.step(sample(clock.now, merc=None)).outcome == Outcome.IDLE
    clock.now = 103
    assert make(MERC_HEALING).step(sample(clock.now)).outcome == Outcome.BACKOFF
    clock.now = 104
    assert make(MERC_HEALING).step(sample(clock.now)).outcome == Outcome.SENT
    assert sent.call_count == 2


def test_backoff_doubles_per_miss_and_resets_after_acknowledged_consumption(healing_setup, sample, clock):
    make, sent = healing_setup
    player = make(PLAYER_HEALING)
    assert player.step(sample()).outcome == Outcome.SENT
    clock.now = 102.5
    assert player.step(sample(clock.now)).outcome == Outcome.BACKOFF  # miss 1: retry at 104.5
    clock.now = 104.5
    assert player.step(sample(clock.now)).outcome == Outcome.SENT
    clock.now = 106.5
    assert player.step(sample(clock.now)).outcome == Outcome.BACKOFF  # miss 2: retry at 110.5
    clock.now = 109
    assert player.step(sample(clock.now)).outcome == Outcome.BACKOFF
    clock.now = 110.5
    assert player.step(sample(clock.now)).outcome == Outcome.SENT
    clock.now = 110.6
    consumed = sample(clock.now, healing_cells=(BeltCell(4, 102),), belt_ids=(102, 103))
    assert player.step(consumed).outcome == Outcome.COOLDOWN
    with player.potions.ledger.transaction() as tx:
        record = tx.data.actors[Actor.PLAYER]
        assert (record.misses, record.retry_at, record.pending) == (0, None, None)
    assert sent.call_count == 3


def test_repeated_misses_pause_the_actor_temporarily_across_instances(healing_setup, sample, clock):
    make, sent = healing_setup
    config = with_overrides(PLAYER_HEALING, max_consecutive_misses=2, suspend_seconds=10)
    player = make(config)
    assert player.step(sample()).outcome == Outcome.SENT
    clock.now = 102
    assert player.step(sample(clock.now)).outcome == Outcome.BACKOFF
    clock.now = 104
    assert player.step(sample(clock.now)).outcome == Outcome.SENT
    clock.now = 106
    assert player.step(sample(clock.now)).outcome == Outcome.SUSPENDED
    clock.now = 115.9
    assert make(config).step(sample(clock.now)).outcome == Outcome.SUSPENDED
    clock.now = 116
    assert make(config).step(sample(clock.now)).outcome == Outcome.SENT
    assert sent.call_count == 3


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

    player.potions.delivery = FakeDelivery(clock=clock, on_send=lambda request: setattr(clock, 'now', 100.1))
    assert player.step(sample()).outcome == Outcome.SENT
    assert merc.step(sample(100.05)).outcome == Outcome.STALE_BELT


def test_partial_delivery_suspends_across_instances_without_success_event(healing_setup, sample, clock):
    make, _ = healing_setup
    controller = make(PLAYER_HEALING)

    controller.potions.delivery = FakeDelivery(error=InputError('input failed after key-down'))
    result = controller.step(sample())
    assert result.outcome == Outcome.SUSPENDED
    assert result.event is None
    clock.now = 105
    assert make(PLAYER_HEALING).step(sample(105)).outcome == Outcome.SUSPENDED


def test_rejected_attempt_reserves_only_its_type_cooldown(healing_setup, sample, clock):
    make, sent = healing_setup
    player = make(PLAYER_HEALING)
    player.potions.delivery = FakeDelivery(refusal=Refusal.UNFOCUSED)
    assert player.step(sample()).outcome == Outcome.REJECTED
    clock.now = 100.1
    assert make(PLAYER_HEALING).step(sample(100.1)).outcome == Outcome.COOLDOWN
    assert make(MERC_HEALING).step(sample(100.1)).outcome == Outcome.SENT
    assert sent.call_count == 1


def test_fullest_column_is_used_first_and_reserved_columns_are_skipped(healing_setup, sample, clock):
    make, sent = healing_setup
    # Column 3 holds two healing potions, column 4 holds four; the merc must not follow the player into 4.
    contents = tuple(606 if index % 4 == 3 or index in (2, 6) else None for index in range(16))
    state = sample(belt_contents=contents)
    assert make(PLAYER_HEALING).step(state).outcome == Outcome.SENT
    clock.now = 100.1
    assert make(MERC_HEALING).step(replace(state, sampled_at=100.1)).outcome == Outcome.SENT
    assert [c.args[0].item.column for c in sent.call_args_list] == [4, 3]


def test_equal_stock_prefers_the_lowest_column(healing_setup, sample):
    make, sent = healing_setup
    contents = tuple(606 if index % 4 in (2, 3) else None for index in range(16))
    assert make(PLAYER_HEALING).step(sample(belt_contents=contents)).outcome == Outcome.SENT
    assert sent.call_args.args[0].item.column == 3


@pytest.mark.parametrize('late', [False, True])
@pytest.mark.parametrize('reason', [Refusal.UNFOCUSED, Refusal.KEY_HELD, Refusal.STALE])
def test_refusal_rolls_back_reservation_and_preserves_prior_delivery(late, reason, healing_setup, sample, clock):
    from inventory_tracking.automation.ledger import LastDelivery

    make, _ = healing_setup
    player = make(PLAYER_HEALING)
    ledger = player.potions.ledger
    previous = LastDelivery(session=(1, '2', 7), at=99)
    with ledger.transaction() as tx:
        tx.data.last_delivery = previous
    player.potions.delivery = FakeDelivery(**{'late_refusal' if late else 'refusal': reason})
    result = player.step(sample())
    assert (result.outcome, result.reason, result.event) == (Outcome.REJECTED, reason, None)
    with ledger.transaction() as tx:
        assert tx.data.actors[Actor.PLAYER].pending is None
        assert not tx.data.actors[Actor.PLAYER].suspended
        assert tx.data.last_delivery == previous
        assert tx.data.cooldowns['player:healing'] == 100
    clock.now = 100.1
    assert make(PLAYER_HEALING).step(sample(100.1)).outcome == Outcome.COOLDOWN
    clock.now = 103
    assert make(PLAYER_HEALING).step(sample(103)).outcome == Outcome.SENT


@pytest.mark.parametrize('stage', ['entry_error', 'error', 'exit_error'])
def test_entire_input_lifecycle_suspends_durably(stage, healing_setup, sample, clock):
    make, _ = healing_setup
    player = make(PLAYER_HEALING)
    player.potions.delivery = FakeDelivery(**{stage: InputError(stage)})
    result = player.step(sample())
    assert (result.outcome, result.event) == (Outcome.SUSPENDED, None)
    clock.now = 105
    assert make(PLAYER_HEALING).step(sample(105)).outcome == Outcome.SUSPENDED


def test_delayed_entry_uses_fresh_reservation_and_completion_times(healing_setup, sample, clock):
    make, _ = healing_setup
    player = make(PLAYER_HEALING)
    ledger = player.potions.ledger

    def on_send(request):
        from inventory_tracking.automation.ledger import LedgerData

        saved = LedgerData.model_validate_json(ledger.path.read_text())
        assert saved.cooldowns['player:healing'] == pytest.approx(100.5)
        assert saved.last_delivery is not None
        pending = saved.actors[Actor.PLAYER].pending
        assert pending is not None
        assert saved.last_delivery.at == pytest.approx(100.5)
        assert pending.sent_at == pytest.approx(100.5)
        clock.now = 100.7

    player.potions.delivery = FakeDelivery(
        clock=clock,
        on_entry=lambda: setattr(clock, 'now', 100.5),
        on_send=on_send,
    )
    result = player.step(sample())
    assert result.event.sent_at == pytest.approx(100.7)
    with ledger.transaction() as tx:
        assert tx.data.last_delivery.at == pytest.approx(100.7)
        assert tx.data.actors[Actor.PLAYER].pending.sent_at == pytest.approx(100.7)
    clock.now = 103.1
    assert make(PLAYER_HEALING).step(sample(103.1, belt_ids=(102, 103))).outcome == Outcome.COOLDOWN


@pytest.mark.parametrize('save_number', [2, 3])
def test_failed_reservation_or_final_save_reports_unavailable(save_number, healing_setup, sample, clock, monkeypatch):
    from inventory_tracking.automation.ledger import LedgerData, LedgerTransaction

    make, sent = healing_setup
    player = make(PLAYER_HEALING)
    original = LedgerTransaction.save
    calls = 0

    def save(tx):
        nonlocal calls
        calls += 1
        if calls == save_number:
            raise OSError('disk failure')
        original(tx)

    monkeypatch.setattr(LedgerTransaction, 'save', save)
    # Advance completion to ensure the final transaction is dirty.
    sent.side_effect = lambda request: setattr(clock, 'now', 100.1)
    result = player.step(sample())
    assert (result.outcome, result.event) == (Outcome.UNAVAILABLE, None)
    assert sent.call_count == (0 if save_number == 2 else 1)
    saved = LedgerData.model_validate_json(player.potions.ledger.path.read_text())
    if save_number == 3:
        pending = saved.actors[Actor.PLAYER].pending
        assert pending is not None
        assert pending.sent_at == 100
        assert saved.last_delivery is not None
        pending = saved.actors[Actor.PLAYER].pending
        assert pending is not None
        assert saved.last_delivery.at == 100
        clock.now = 100.2
        assert make(PLAYER_HEALING).step(sample(100.2)).outcome == Outcome.PENDING
    else:
        assert saved.actors[Actor.PLAYER].pending is None
