import json

import pytest

from inventory_tracking.config import MERC_HEALING, PLAYER_HEALING
from inventory_tracking.models import Actor, Outcome, SessionIdentity
from inventory_tracking.potion_ledger import PotionLedger


@pytest.mark.parametrize('contents', ['{broken', '[]', 'null', '{"boot":"test","version":99}'])
def test_corrupt_or_unknown_ledger_refuses_input(tmp_path, healing_setup, sample, contents):
    (tmp_path / 'merc-input.lock').write_text(contents)
    make, sent = healing_setup
    assert make(PLAYER_HEALING).step(sample()).outcome == Outcome.UNAVAILABLE
    sent.assert_not_called()
    assert (tmp_path / 'merc-input.lock').read_text() == contents


def test_existing_legacy_timestamp_is_migrated_conservatively(tmp_path, healing_setup, sample, clock):
    path = tmp_path / 'merc-input.lock'
    path.write_text(json.dumps({'boot': 'test', 'sent_at': 100}))
    make, sent = healing_setup
    clock.now = 101
    # The shared timestamp now seeds every per-type cooldown (player healing: 3 s).
    assert make(PLAYER_HEALING).step(sample(101)).outcome == Outcome.COOLDOWN
    assert json.loads((tmp_path / 'potions.json').read_text())['version'] == 2
    clock.now = 103
    assert make(PLAYER_HEALING).step(sample(103)).outcome == Outcome.SENT
    assert sent.call_count == 1


def test_other_boot_does_not_apply_monotonic_history(tmp_path, healing_setup, sample):
    (tmp_path / 'merc-input.lock').write_text(json.dumps({'boot': 'old', 'sent_at': 1000}))
    make, _ = healing_setup
    assert make(PLAYER_HEALING).step(sample()).outcome == Outcome.SENT


def test_concurrent_instance_cannot_enter_during_delivery(tmp_path, healing_setup, sample):
    make, sent = healing_setup
    with PotionLedger(tmp_path, boot_id='test').transaction():
        assert make(MERC_HEALING).step(sample()).outcome == Outcome.BUSY
    sent.assert_not_called()


@pytest.mark.parametrize('damage', ['actors', 'cooldown', 'pending'])
def test_malformed_persisted_state_refuses_input(tmp_path, healing_setup, sample, clock, damage):
    make, sent = healing_setup
    controller = make(PLAYER_HEALING)
    controller.step(sample())
    sent.reset_mock()
    path = tmp_path / 'potions.json'
    data = json.loads(path.read_text())
    if damage == 'actors':
        data['actors'] = None
    elif damage == 'cooldown':
        data['cooldowns']['player:healing'] = float('nan')
        data['actors']['player']['pending'] = None
    else:
        data['actors']['player']['pending'] = 'broken'
    path.write_text(json.dumps(data))
    clock.now = 104
    assert controller.step(sample(104)).outcome == Outcome.UNAVAILABLE
    sent.assert_not_called()


def test_failed_atomic_save_keeps_previous_ledger_and_never_sends(tmp_path, healing_setup, sample):
    from unittest.mock import patch

    make, sent = healing_setup
    ledger = PotionLedger(tmp_path, boot_id='test')
    with ledger.transaction():
        pass
    before = ledger.path.read_text()
    with patch('inventory_tracking.potion_ledger.publish', side_effect=OSError('disk full')):
        assert make(PLAYER_HEALING).step(sample()).outcome == Outcome.UNAVAILABLE
    assert ledger.path.read_text() == before
    sent.assert_not_called()


def test_idle_steps_do_not_rewrite_ledger_but_mutations_do(tmp_path, healing_setup, sample, clock):
    from unittest.mock import patch

    from inventory_tracking import potion_ledger

    make, _ = healing_setup
    controller = make(PLAYER_HEALING)
    with patch('inventory_tracking.potion_ledger.publish', wraps=potion_ledger.publish) as publish:
        assert controller.step(sample()).outcome == Outcome.SENT
        writes = publish.call_count
        clock.now = 100.1
        # Pending acknowledgement still in flight and healthy again: nothing changed.
        assert controller.step(sample(100.1, current_raw=1000)).outcome == Outcome.PENDING
        assert publish.call_count == writes
        # A first merc step creates its session record; the next idle step does not rewrite.
        merc = make(MERC_HEALING)
        clock.now = 100.2
        assert merc.step(sample(100.2, merc=None)).outcome == Outcome.IDLE
        assert merc.step(sample(100.2, merc=None)).outcome == Outcome.IDLE
        assert publish.call_count == writes + 1
        writes += 1
        clock.now = 100.3
        # Consumption acknowledged: pending cleared and persisted.
        assert controller.step(sample(100.3, current_raw=1000, belt_ids=(102, 103))).outcome == Outcome.IDLE
        assert publish.call_count == writes + 1
        clock.now = 100.4
        assert controller.step(sample(100.4, current_raw=1000, belt_ids=(102, 103))).outcome == Outcome.IDLE
        assert publish.call_count == writes + 1


def test_ack_timeout_suspension_is_persisted_without_delivery(tmp_path, healing_setup, sample, clock):
    make, _ = healing_setup
    controller = make(PLAYER_HEALING)
    assert controller.step(sample()).outcome == Outcome.SENT
    clock.now = 103
    assert controller.step(sample(103)).outcome == Outcome.SUSPENDED
    assert json.loads((tmp_path / 'potions.json').read_text())['actors']['player']['suspended'] is True


def test_raising_transaction_body_never_publishes(tmp_path):
    ledger = PotionLedger(tmp_path, boot_id='test')
    with ledger.transaction():
        pass
    before = ledger.path.read_bytes()

    def mutate_then_fail():
        with ledger.transaction() as transaction:
            transaction.data.cooldowns['player:healing'] = 5
            raise RuntimeError('boom')

    with pytest.raises(RuntimeError, match='boom'):
        mutate_then_fail()
    assert ledger.path.read_bytes() == before


def valid_document():
    return {
        'version': 2,
        'boot': 'test',
        'cooldowns': {'player:healing': 100.0},
        'actors': {
            'player': {'session': [1, '2', 7, None], 'pending': {'item_id': 101, 'sent_at': 100.0}, 'suspended': False},
            'merc': {'session': [1, '2', 7, 99], 'pending': None, 'suspended': True},
        },
        'last_delivery': {'session': [1, '2', 7], 'at': 100.0},
    }


def test_ledger_document_round_trips_byte_for_byte(tmp_path):
    from inventory_tracking.potion_ledger import LedgerData
    from inventory_tracking.reports import publish

    text = json.dumps(valid_document(), indent=2) + '\n'
    model = LedgerData.model_validate_json(text)
    assert model.actors[Actor.PLAYER].session == SessionIdentity(1, '2', 7)
    publish(tmp_path / 'copy.json', model.model_dump(mode='json'))
    assert (tmp_path / 'copy.json').read_text() == text


@pytest.mark.parametrize(
    'damage',
    [
        lambda d: d.__setitem__('actors', []),
        lambda d: d.__setitem__('cooldowns', {'player:mana': 1.0}),
        lambda d: d['cooldowns'].__setitem__('player:healing', -1),
        lambda d: d['cooldowns'].__setitem__('player:healing', float('nan')),
        lambda d: d['cooldowns'].__setitem__('player:healing', True),
        lambda d: d.__setitem__('legacy_sent_at', None),
        lambda d: d['actors'].__setitem__('wizard', d['actors']['player']),
        lambda d: d['actors']['player'].__setitem__('session', [1, '2']),
        lambda d: d['actors']['player'].__setitem__('session', ['1', '2', 7, None]),
        lambda d: d['actors']['player'].__setitem__('suspended', 1),
        lambda d: d['actors']['player'].__setitem__('pending', 'broken'),
        lambda d: d['actors']['player']['pending'].__setitem__('item_id', 1.5),
        lambda d: d['actors']['player'].__setitem__('extra', 1),
        lambda d: d['last_delivery'].__setitem__('session', [1, '2']),
        lambda d: d['last_delivery'].__setitem__('at', None),
        lambda d: d.__setitem__('version', 1),
        lambda d: d.pop('boot'),
    ],
)
def test_ledger_model_rejects_malformed_documents(damage):
    from inventory_tracking.potion_ledger import LedgerData

    document = valid_document()
    damage(document)
    with pytest.raises(ValueError):  # ruff: ignore[pytest-raises-too-broad] - pydantic's ValidationError names the offending field
        LedgerData.model_validate_json(json.dumps(document))


def test_version_one_ledger_migrates_without_forgetting_its_timestamps(tmp_path, healing_setup, sample, clock):
    document = {
        'version': 1,
        'boot': 'test',
        'legacy_sent_at': 100,
        'cooldowns': {'player:healing': 98.0, 'merc:healing': 100.5},
        'actors': {'merc': {'session': [1, '2', 7, 99], 'pending': None, 'suspended': True}},
        'last_delivery': None,
    }
    (tmp_path / 'potions.json').write_text(json.dumps(document))
    make, sent = healing_setup
    clock.now = 101
    assert make(PLAYER_HEALING).step(sample(101)).outcome == Outcome.COOLDOWN
    assert make(MERC_HEALING).step(sample(101)).outcome == Outcome.SUSPENDED
    migrated = json.loads((tmp_path / 'potions.json').read_text())
    assert migrated['version'] == 2
    assert 'legacy_sent_at' not in migrated
    assert migrated['cooldowns'] == {
        'player:healing': 100.0,
        'player:rejuvenation': 100.0,
        'merc:healing': 100.5,
        'merc:rejuvenation': 100.0,
    }
    clock.now = 103
    assert make(PLAYER_HEALING).step(sample(103)).outcome == Outcome.SENT
    assert sent.call_count == 1


def test_legacy_lock_keeps_serializing_same_boot_instances(tmp_path, healing_setup, sample):
    (tmp_path / 'merc-input.lock').write_text(json.dumps({'boot': 'test', 'sent_at': 1}))
    make, _ = healing_setup
    with PotionLedger(tmp_path, boot_id='test').transaction():
        assert make(PLAYER_HEALING).step(sample()).outcome == Outcome.BUSY
    assert not (tmp_path / 'potions.lock').exists()
    assert PotionLedger(tmp_path, boot_id='test').lock_path.name == 'merc-input.lock'


def test_new_boot_or_fresh_host_uses_the_new_lock_name(tmp_path, healing_setup, sample):
    (tmp_path / 'merc-input.lock').write_text(json.dumps({'boot': 'old', 'sent_at': 1}))
    make, _ = healing_setup
    assert make(PLAYER_HEALING).step(sample()).outcome == Outcome.SENT
    assert (tmp_path / 'potions.lock').exists()
    assert (tmp_path / 'merc-input.lock').read_text() == json.dumps({'boot': 'old', 'sent_at': 1})
    fresh = tmp_path / 'fresh'
    fresh.mkdir()
    assert PotionLedger(fresh, boot_id='test').lock_path.name == 'potions.lock'
