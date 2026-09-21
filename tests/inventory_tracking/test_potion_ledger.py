import json

import pytest

from inventory_tracking.config import MERC_HEALING, PLAYER_HEALING
from inventory_tracking.models import Outcome
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
    assert make(PLAYER_HEALING).step(sample(101, current_raw=100)).outcome == Outcome.COOLDOWN
    assert json.loads((tmp_path / 'potions.json').read_text())['version'] == 1
    clock.now = 103
    assert make(PLAYER_HEALING).step(sample(103, current_raw=100)).outcome == Outcome.SENT
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
